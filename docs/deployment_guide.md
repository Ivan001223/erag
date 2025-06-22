# 部署指南

本文档提供了企业知识库系统的完整部署指南，包括本地开发环境、测试环境和生产环境的部署配置。

## 目录

1. [系统要求](#系统要求)
2. [环境配置](#环境配置)
3. [本地开发部署](#本地开发部署)
4. [Docker 部署](#docker-部署)
5. [Kubernetes 部署](#kubernetes-部署)
6. [生产环境部署](#生产环境部署)
7. [监控和日志](#监控和日志)
8. [备份和恢复](#备份和恢复)
9. [故障排除](#故障排除)
10. [性能优化](#性能优化)

## 系统要求

### 最低硬件要求

#### 开发环境
- **CPU**: 4核心
- **内存**: 8GB RAM
- **存储**: 50GB 可用空间
- **网络**: 稳定的互联网连接

#### 生产环境
- **CPU**: 8核心（推荐16核心）
- **内存**: 32GB RAM（推荐64GB）
- **存储**: 500GB SSD（推荐1TB NVMe SSD）
- **网络**: 千兆网络连接

### 软件要求

- **操作系统**: Ubuntu 20.04+ / CentOS 8+ / Windows 10+
- **Python**: 3.9+
- **Node.js**: 16+
- **Docker**: 20.10+
- **Docker Compose**: 2.0+
- **Kubernetes**: 1.20+（生产环境）

## 环境配置

### 1. 基础环境设置

#### Ubuntu/Debian
```bash
# 更新系统
sudo apt update && sudo apt upgrade -y

# 安装基础依赖
sudo apt install -y curl wget git vim build-essential

# 安装Python 3.9+
sudo apt install -y python3.9 python3.9-pip python3.9-venv

# 安装Node.js
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs

# 安装Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# 安装Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.12.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

#### CentOS/RHEL
```bash
# 更新系统
sudo yum update -y

# 安装基础依赖
sudo yum groupinstall -y "Development Tools"
sudo yum install -y curl wget git vim

# 安装Python 3.9+
sudo yum install -y python39 python39-pip

# 安装Node.js
curl -fsSL https://rpm.nodesource.com/setup_18.x | sudo bash -
sudo yum install -y nodejs

# 安装Docker
sudo yum install -y yum-utils
sudo yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
sudo yum install -y docker-ce docker-ce-cli containerd.io
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker $USER
```

### 2. 环境变量配置

创建环境配置文件：

```bash
# .env.development
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=DEBUG

# 数据库配置
DATABASE_URL=postgresql://erag_user:erag_password@localhost:5432/erag_dev
REDIS_URL=redis://localhost:6379/0
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=neo4j_password

# StarRocks配置
STARROCKS_HOST=localhost
STARROCKS_PORT=9030
STARROCKS_USER=root
STARROCKS_PASSWORD=
STARROCKS_DATABASE=erag

# MinIO配置
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=erag-documents
MINIO_SECURE=false

# API配置
API_HOST=0.0.0.0
API_PORT=8000
API_WORKERS=4

# 安全配置
SECRET_KEY=your-secret-key-here
JWT_SECRET_KEY=your-jwt-secret-key-here
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=1440

# 外部服务
DIFY_API_KEY=your-dify-api-key
DIFY_BASE_URL=https://api.dify.ai

# 向量数据库
VECTOR_DB_TYPE=chroma
CHROMA_HOST=localhost
CHROMA_PORT=8001

# 向量数据库
STARROCKS_HOST=localhost
STARROCKS_PORT=9030
STARROCKS_USER=root
STARROCKS_PASSWORD=
```

```bash
# .env.production
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO

# 数据库配置（使用实际生产环境地址）
DATABASE_URL=postgresql://erag_user:secure_password@db.example.com:5432/erag_prod
REDIS_URL=redis://redis.example.com:6379/0
NEO4J_URI=bolt://neo4j.example.com:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=secure_neo4j_password

# 其他配置...
```

## 本地开发部署

### 1. 克隆项目

```bash
git clone https://github.com/your-org/erag.git
cd erag
```

### 2. 后端设置

```bash
# 创建虚拟环境
cd backend
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# 或 venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt
pip install -r requirements-dev.txt

# 复制环境配置
cp .env.example .env.development
# 编辑 .env.development 文件，配置数据库连接等

# 初始化数据库
python scripts/init_db.py
python scripts/migrate.py
python scripts/seed_data.py

# 启动开发服务器
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

### 3. 前端设置

```bash
# 安装依赖
cd frontend
npm install

# 复制环境配置
cp .env.example .env.development
# 编辑 .env.development 文件

# 启动开发服务器
npm run dev
```

### 4. 启动依赖服务

使用Docker Compose启动数据库和其他服务：

```bash
# 启动基础服务
docker-compose -f docker-compose.dev.yml up -d

# 查看服务状态
docker-compose -f docker-compose.dev.yml ps

# 查看日志
docker-compose -f docker-compose.dev.yml logs -f
```

## Docker 部署

### 1. Docker Compose 配置

创建 `docker-compose.yml`：

```yaml
version: '3.8'

services:
  # 前端服务
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "3000:3000"
    environment:
      - NODE_ENV=production
      - NEXT_PUBLIC_API_URL=http://backend:8000
    depends_on:
      - backend
    networks:
      - erag-network

  # 后端API服务
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      - ENVIRONMENT=production
      - DATABASE_URL=postgresql://erag_user:erag_password@postgres:5432/erag
      - REDIS_URL=redis://redis:6379/0
      - NEO4J_URI=bolt://neo4j:7687
      - NEO4J_USER=neo4j
      - NEO4J_PASSWORD=neo4j_password
      - MINIO_ENDPOINT=minio:9000
      - MINIO_ACCESS_KEY=minioadmin
      - MINIO_SECRET_KEY=minioadmin
    depends_on:
      - postgres
      - redis
      - neo4j
      - minio
      - starrocks
    volumes:
      - ./logs:/app/logs
    networks:
      - erag-network

  # PostgreSQL数据库
  postgres:
    image: postgres:14
    environment:
      - POSTGRES_DB=erag
      - POSTGRES_USER=erag_user
      - POSTGRES_PASSWORD=erag_password
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./backend/scripts/init.sql:/docker-entrypoint-initdb.d/init.sql
    ports:
      - "5432:5432"
    networks:
      - erag-network

  # Redis缓存
  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    ports:
      - "6379:6379"
    networks:
      - erag-network

  # Neo4j图数据库
  neo4j:
    image: neo4j:4.4
    environment:
      - NEO4J_AUTH=neo4j/neo4j_password
      - NEO4J_PLUGINS=["apoc"]
      - NEO4J_dbms_security_procedures_unrestricted=apoc.*
    volumes:
      - neo4j_data:/data
      - neo4j_logs:/logs
    ports:
      - "7474:7474"
      - "7687:7687"
    networks:
      - erag-network

  # StarRocks分析数据库
  starrocks:
    image: starrocks/allin1-ubuntu:latest
    environment:
      - SR_USER=root
      - SR_PASSWORD=
    volumes:
      - starrocks_data:/opt/starrocks/fe/meta
      - starrocks_logs:/opt/starrocks/fe/log
    ports:
      - "9030:9030"
      - "8030:8030"
    networks:
      - erag-network

  # MinIO对象存储
  minio:
    image: minio/minio:latest
    command: server /data --console-address ":9001"
    environment:
      - MINIO_ROOT_USER=minioadmin
      - MINIO_ROOT_PASSWORD=minioadmin
    volumes:
      - minio_data:/data
    ports:
      - "9000:9000"
      - "9001:9001"
    networks:
      - erag-network

  # StarRocks分析数据库
  starrocks:
    image: starrocks/allin1-ubuntu:latest
    environment:
      - SR_USER=root
      - SR_PASSWORD=
    volumes:
      - starrocks_data:/opt/starrocks/fe/meta
      - starrocks_logs:/opt/starrocks/fe/log
    ports:
      - "9030:9030"
      - "8030:8030"
    networks:
      - erag-network

  # Chroma向量数据库
  chroma:
    image: chromadb/chroma:latest
    environment:
      - CHROMA_SERVER_HOST=0.0.0.0
      - CHROMA_SERVER_PORT=8001
    volumes:
      - chroma_data:/chroma/chroma
    ports:
      - "8001:8001"
    networks:
      - erag-network

  # Nginx反向代理
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf
      - ./nginx/ssl:/etc/nginx/ssl
      - ./logs/nginx:/var/log/nginx
    depends_on:
      - frontend
      - backend
    networks:
      - erag-network

volumes:
  postgres_data:
  redis_data:
  neo4j_data:
  neo4j_logs:
  starrocks_data:
  starrocks_logs:
  minio_data:
  starrocks_data:
  starrocks_logs:
  chroma_data:

networks:
  erag-network:
    driver: bridge
```

### 2. Dockerfile 配置

#### 后端 Dockerfile

```dockerfile
# backend/Dockerfile
FROM python:3.9-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .

# 创建非root用户
RUN useradd --create-home --shell /bin/bash app \
    && chown -R app:app /app
USER app

# 暴露端口
EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 启动命令
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### 前端 Dockerfile

```dockerfile
# frontend/Dockerfile
FROM node:18-alpine AS builder

# 设置工作目录
WORKDIR /app

# 复制package文件
COPY package*.json ./

# 安装依赖
RUN npm ci --only=production

# 复制源代码
COPY . .

# 构建应用
RUN npm run build

# 生产阶段
FROM node:18-alpine AS runner

WORKDIR /app

# 创建非root用户
RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

# 复制构建产物
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static

# 设置权限
USER nextjs

# 暴露端口
EXPOSE 3000

ENV PORT 3000

# 启动命令
CMD ["node", "server.js"]
```

### 3. 部署命令

```bash
# 构建并启动所有服务
docker-compose up -d --build

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f backend

# 进入容器调试
docker-compose exec backend bash

# 停止服务
docker-compose down

# 停止并删除数据卷
docker-compose down -v
```

## Kubernetes 部署

### 1. 命名空间配置

```yaml
# k8s/namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: erag
  labels:
    name: erag
```

### 2. ConfigMap 配置

```yaml
# k8s/configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: erag-config
  namespace: erag
data:
  ENVIRONMENT: "production"
  LOG_LEVEL: "INFO"
  API_HOST: "0.0.0.0"
  API_PORT: "8000"
  REDIS_URL: "redis://redis-service:6379/0"
  NEO4J_URI: "bolt://neo4j-service:7687"
  MINIO_ENDPOINT: "minio-service:9000"
      STARROCKS_HOST: "starrocks-service"
    STARROCKS_PORT: "9030"
  CHROMA_HOST: "chroma-service"
  CHROMA_PORT: "8001"
```

### 3. Secret 配置

```yaml
# k8s/secret.yaml
apiVersion: v1
kind: Secret
metadata:
  name: erag-secrets
  namespace: erag
type: Opaque
data:
  DATABASE_URL: cG9zdGdyZXNxbDovL2VyYWdfdXNlcjplcmFnX3Bhc3N3b3JkQHBvc3RncmVzLXNlcnZpY2U6NTQzMi9lcmFn  # base64编码
  SECRET_KEY: eW91ci1zZWNyZXQta2V5LWhlcmU=
  JWT_SECRET_KEY: eW91ci1qd3Qtc2VjcmV0LWtleS1oZXJl
  NEO4J_PASSWORD: bmVvNGpfcGFzc3dvcmQ=
  MINIO_ACCESS_KEY: bWluaW9hZG1pbg==
  MINIO_SECRET_KEY: bWluaW9hZG1pbg==
  DIFY_API_KEY: eW91ci1kaWZ5LWFwaS1rZXk=
```

### 4. 数据库部署

```yaml
# k8s/postgres.yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: postgres
  namespace: erag
spec:
  serviceName: postgres-service
  replicas: 1
  selector:
    matchLabels:
      app: postgres
  template:
    metadata:
      labels:
        app: postgres
    spec:
      containers:
      - name: postgres
        image: postgres:14
        env:
        - name: POSTGRES_DB
          value: "erag"
        - name: POSTGRES_USER
          value: "erag_user"
        - name: POSTGRES_PASSWORD
          valueFrom:
            secretKeyRef:
              name: erag-secrets
              key: POSTGRES_PASSWORD
        ports:
        - containerPort: 5432
        volumeMounts:
        - name: postgres-storage
          mountPath: /var/lib/postgresql/data
        resources:
          requests:
            memory: "1Gi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "1000m"
  volumeClaimTemplates:
  - metadata:
      name: postgres-storage
    spec:
      accessModes: ["ReadWriteOnce"]
      resources:
        requests:
          storage: 20Gi
---
apiVersion: v1
kind: Service
metadata:
  name: postgres-service
  namespace: erag
spec:
  selector:
    app: postgres
  ports:
  - port: 5432
    targetPort: 5432
  type: ClusterIP
```

### 5. 后端应用部署

```yaml
# k8s/backend.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: backend
  namespace: erag
spec:
  replicas: 3
  selector:
    matchLabels:
      app: backend
  template:
    metadata:
      labels:
        app: backend
    spec:
      containers:
      - name: backend
        image: erag/backend:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: erag-secrets
              key: DATABASE_URL
        - name: SECRET_KEY
          valueFrom:
            secretKeyRef:
              name: erag-secrets
              key: SECRET_KEY
        envFrom:
        - configMapRef:
            name: erag-config
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: backend-service
  namespace: erag
spec:
  selector:
    app: backend
  ports:
  - port: 8000
    targetPort: 8000
  type: ClusterIP
```

### 6. Ingress 配置

```yaml
# k8s/ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: erag-ingress
  namespace: erag
  annotations:
    kubernetes.io/ingress.class: nginx
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    nginx.ingress.kubernetes.io/proxy-body-size: "100m"
spec:
  tls:
  - hosts:
    - erag.example.com
    - api.erag.example.com
    secretName: erag-tls
  rules:
  - host: erag.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: frontend-service
            port:
              number: 3000
  - host: api.erag.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: backend-service
            port:
              number: 8000
```

### 7. 部署命令

```bash
# 创建命名空间
kubectl apply -f k8s/namespace.yaml

# 应用配置
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secret.yaml

# 部署数据库
kubectl apply -f k8s/postgres.yaml
kubectl apply -f k8s/redis.yaml
kubectl apply -f k8s/neo4j.yaml

# 等待数据库就绪
kubectl wait --for=condition=ready pod -l app=postgres -n erag --timeout=300s

# 部署应用
kubectl apply -f k8s/backend.yaml
kubectl apply -f k8s/frontend.yaml

# 配置Ingress
kubectl apply -f k8s/ingress.yaml

# 查看部署状态
kubectl get pods -n erag
kubectl get services -n erag
kubectl get ingress -n erag
```

## 生产环境部署

### 1. 安全配置

#### SSL/TLS 证书

```bash
# 使用Let's Encrypt获取免费SSL证书
sudo apt install certbot python3-certbot-nginx

# 获取证书
sudo certbot --nginx -d erag.example.com -d api.erag.example.com

# 自动续期
sudo crontab -e
# 添加以下行：
0 12 * * * /usr/bin/certbot renew --quiet
```

#### 防火墙配置

```bash
# 配置UFW防火墙
sudo ufw enable
sudo ufw default deny incoming
sudo ufw default allow outgoing

# 允许必要端口
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# 查看状态
sudo ufw status
```

#### 数据库安全

```sql
-- PostgreSQL安全配置
-- 创建专用用户
CREATE USER erag_user WITH PASSWORD 'secure_random_password';
GRANT CONNECT ON DATABASE erag TO erag_user;
GRANT USAGE ON SCHEMA public TO erag_user;
GRANT CREATE ON SCHEMA public TO erag_user;

-- 限制连接
ALTER USER erag_user CONNECTION LIMIT 20;
```

### 2. 性能优化

#### Nginx 配置

```nginx
# /etc/nginx/sites-available/erag
server {
    listen 80;
    server_name erag.example.com api.erag.example.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name erag.example.com;
    
    ssl_certificate /etc/letsencrypt/live/erag.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/erag.example.com/privkey.pem;
    
    # SSL配置
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    
    # 安全头
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options DENY always;
    add_header X-Content-Type-Options nosniff always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    
    # Gzip压缩
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css text/xml text/javascript application/javascript application/xml+rss application/json;
    
    # 前端代理
    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
    }
}

server {
    listen 443 ssl http2;
    server_name api.erag.example.com;
    
    ssl_certificate /etc/letsencrypt/live/erag.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/erag.example.com/privkey.pem;
    
    # API代理
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # 超时设置
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
        
        # 缓存设置
        proxy_cache api_cache;
        proxy_cache_valid 200 5m;
        proxy_cache_use_stale error timeout updating http_500 http_502 http_503 http_504;
    }
    
    # 文件上传限制
    client_max_body_size 100M;
}
```

### 3. 监控配置

#### Prometheus 配置

```yaml
# prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  - "rules/*.yml"

scrape_configs:
  - job_name: 'erag-backend'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'
    scrape_interval: 30s
  
  - job_name: 'postgres'
    static_configs:
      - targets: ['localhost:9187']
  
  - job_name: 'redis'
    static_configs:
      - targets: ['localhost:9121']
  
  - job_name: 'nginx'
    static_configs:
      - targets: ['localhost:9113']

alerting:
  alertmanagers:
    - static_configs:
        - targets:
          - alertmanager:9093
```

#### Grafana 仪表板

```json
{
  "dashboard": {
    "title": "ERAG System Monitoring",
    "panels": [
      {
        "title": "API Response Time",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))",
            "legendFormat": "95th percentile"
          }
        ]
      },
      {
        "title": "Request Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(http_requests_total[5m])",
            "legendFormat": "Requests/sec"
          }
        ]
      },
      {
        "title": "Database Connections",
        "type": "graph",
        "targets": [
          {
            "expr": "pg_stat_database_numbackends",
            "legendFormat": "Active connections"
          }
        ]
      }
    ]
  }
}
```

## 监控和日志

### 1. 应用监控

#### 健康检查端点

```python
# backend/api/health.py
from fastapi import APIRouter, Depends
from backend.core.database import get_database
from backend.core.redis import get_redis
from backend.core.neo4j import get_neo4j

router = APIRouter()

@router.get("/health")
async def health_check():
    """基础健康检查"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@router.get("/ready")
async def readiness_check(
    db=Depends(get_database),
    redis=Depends(get_redis),
    neo4j=Depends(get_neo4j)
):
    """就绪检查"""
    checks = {}
    
    # 检查PostgreSQL
    try:
        await db.execute("SELECT 1")
        checks["postgres"] = "healthy"
    except Exception as e:
        checks["postgres"] = f"unhealthy: {str(e)}"
    
    # 检查Redis
    try:
        await redis.ping()
        checks["redis"] = "healthy"
    except Exception as e:
        checks["redis"] = f"unhealthy: {str(e)}"
    
    # 检查Neo4j
    try:
        result = await neo4j.run("RETURN 1")
        await result.single()
        checks["neo4j"] = "healthy"
    except Exception as e:
        checks["neo4j"] = f"unhealthy: {str(e)}"
    
    all_healthy = all(status == "healthy" for status in checks.values())
    
    return {
        "status": "ready" if all_healthy else "not_ready",
        "checks": checks,
        "timestamp": datetime.now().isoformat()
    }
```

### 2. 日志配置

#### 结构化日志

```python
# backend/core/logging.py
import logging
import json
from datetime import datetime
from typing import Dict, Any

class JSONFormatter(logging.Formatter):
    """JSON格式日志格式化器"""
    
    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        # 添加异常信息
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        
        # 添加额外字段
        if hasattr(record, "user_id"):
            log_entry["user_id"] = record.user_id
        if hasattr(record, "request_id"):
            log_entry["request_id"] = record.request_id
        
        return json.dumps(log_entry)

def setup_logging(log_level: str = "INFO"):
    """设置日志配置"""
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format="%(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler("logs/app.log")
        ]
    )
    
    # 设置JSON格式化器
    for handler in logging.root.handlers:
        handler.setFormatter(JSONFormatter())
```

### 3. 指标收集

```python
# backend/core/metrics.py
from prometheus_client import Counter, Histogram, Gauge, generate_latest
from fastapi import Request, Response
import time

# 定义指标
REQUEST_COUNT = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status_code']
)

REQUEST_DURATION = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint']
)

ACTIVE_CONNECTIONS = Gauge(
    'active_connections',
    'Number of active database connections'
)

TASK_QUEUE_SIZE = Gauge(
    'task_queue_size',
    'Number of tasks in queue'
)

async def metrics_middleware(request: Request, call_next):
    """指标收集中间件"""
    start_time = time.time()
    
    response = await call_next(request)
    
    # 记录请求指标
    REQUEST_COUNT.labels(
        method=request.method,
        endpoint=request.url.path,
        status_code=response.status_code
    ).inc()
    
    REQUEST_DURATION.labels(
        method=request.method,
        endpoint=request.url.path
    ).observe(time.time() - start_time)
    
    return response

@router.get("/metrics")
async def get_metrics():
    """Prometheus指标端点"""
    return Response(
        content=generate_latest(),
        media_type="text/plain"
    )
```

## 备份和恢复

### 1. 数据库备份

```bash
#!/bin/bash
# scripts/backup.sh

set -e

# 配置
BACKUP_DIR="/backups"
DATE=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=30

# 创建备份目录
mkdir -p $BACKUP_DIR

# PostgreSQL备份
echo "Backing up PostgreSQL..."
pg_dump -h localhost -U erag_user -d erag | gzip > $BACKUP_DIR/postgres_$DATE.sql.gz

# Neo4j备份
echo "Backing up Neo4j..."
neo4j-admin dump --database=neo4j --to=$BACKUP_DIR/neo4j_$DATE.dump

# Redis备份
echo "Backing up Redis..."
redis-cli --rdb $BACKUP_DIR/redis_$DATE.rdb

# MinIO备份
echo "Backing up MinIO..."
mc mirror minio/erag-documents $BACKUP_DIR/minio_$DATE/

# 清理旧备份
echo "Cleaning up old backups..."
find $BACKUP_DIR -name "*.gz" -mtime +$RETENTION_DAYS -delete
find $BACKUP_DIR -name "*.dump" -mtime +$RETENTION_DAYS -delete
find $BACKUP_DIR -name "*.rdb" -mtime +$RETENTION_DAYS -delete
find $BACKUP_DIR -type d -name "minio_*" -mtime +$RETENTION_DAYS -exec rm -rf {} +

echo "Backup completed successfully!"
```

### 2. 自动备份

```bash
# 添加到crontab
crontab -e

# 每天凌晨2点执行备份
0 2 * * * /path/to/scripts/backup.sh >> /var/log/backup.log 2>&1

# 每周日执行完整备份
0 1 * * 0 /path/to/scripts/full_backup.sh >> /var/log/backup.log 2>&1
```

### 3. 恢复脚本

```bash
#!/bin/bash
# scripts/restore.sh

set -e

if [ $# -ne 2 ]; then
    echo "Usage: $0 <backup_date> <component>"
    echo "Components: postgres, neo4j, redis, minio, all"
    exit 1
fi

BACKUP_DATE=$1
COMPONENT=$2
BACKUP_DIR="/backups"

restore_postgres() {
    echo "Restoring PostgreSQL..."
    dropdb -h localhost -U erag_user erag
    createdb -h localhost -U erag_user erag
    gunzip -c $BACKUP_DIR/postgres_$BACKUP_DATE.sql.gz | psql -h localhost -U erag_user -d erag
}

restore_neo4j() {
    echo "Restoring Neo4j..."
    neo4j stop
    neo4j-admin load --from=$BACKUP_DIR/neo4j_$BACKUP_DATE.dump --database=neo4j --force
    neo4j start
}

restore_redis() {
    echo "Restoring Redis..."
    redis-cli FLUSHALL
    redis-cli --rdb $BACKUP_DIR/redis_$BACKUP_DATE.rdb
}

restore_minio() {
    echo "Restoring MinIO..."
    mc rm --recursive --force minio/erag-documents
    mc mirror $BACKUP_DIR/minio_$BACKUP_DATE/ minio/erag-documents
}

case $COMPONENT in
    postgres)
        restore_postgres
        ;;
    neo4j)
        restore_neo4j
        ;;
    redis)
        restore_redis
        ;;
    minio)
        restore_minio
        ;;
    all)
        restore_postgres
        restore_neo4j
        restore_redis
        restore_minio
        ;;
    *)
        echo "Unknown component: $COMPONENT"
        exit 1
        ;;
esac

echo "Restore completed successfully!"
```

## 故障排除

### 1. 常见问题

#### 数据库连接问题

```bash
# 检查PostgreSQL状态
sudo systemctl status postgresql

# 检查连接
psql -h localhost -U erag_user -d erag -c "SELECT 1;"

# 查看连接数
psql -h localhost -U erag_user -d erag -c "SELECT count(*) FROM pg_stat_activity;"

# 检查慢查询
psql -h localhost -U erag_user -d erag -c "SELECT query, query_start, state FROM pg_stat_activity WHERE state = 'active';"
```

#### 内存问题

```bash
# 检查内存使用
free -h
top -o %MEM

# 检查交换空间
swapon --show

# 检查进程内存使用
ps aux --sort=-%mem | head -10
```

#### 磁盘空间问题

```bash
# 检查磁盘使用
df -h

# 查找大文件
find / -type f -size +100M 2>/dev/null | head -10

# 清理日志
journalctl --vacuum-time=7d
```

### 2. 性能调优

#### PostgreSQL 优化

```sql
-- postgresql.conf 优化建议
shared_buffers = 256MB                 -- 25% of RAM
effective_cache_size = 1GB             -- 75% of RAM
work_mem = 4MB                         -- Per connection
maintenance_work_mem = 64MB
wal_buffers = 16MB
checkpoint_completion_target = 0.9
random_page_cost = 1.1                 -- For SSD
effective_io_concurrency = 200         -- For SSD

-- 创建索引
CREATE INDEX CONCURRENTLY idx_documents_user_id ON documents(user_id);
CREATE INDEX CONCURRENTLY idx_documents_created_at ON documents(created_at);
CREATE INDEX CONCURRENTLY idx_tasks_status ON tasks(status);
CREATE INDEX CONCURRENTLY idx_tasks_user_id ON tasks(user_id);
```

#### Redis 优化

```bash
# redis.conf 优化
maxmemory 2gb
maxmemory-policy allkeys-lru
save 900 1
save 300 10
save 60 10000
```

#### Neo4j 优化

```bash
# neo4j.conf 优化
dbms.memory.heap.initial_size=2g
dbms.memory.heap.max_size=2g
dbms.memory.pagecache.size=1g
dbms.tx_log.rotation.retention_policy=1 days
```

## 性能优化

### 1. 应用层优化

#### 连接池配置

```python
# backend/core/database.py
from sqlalchemy.pool import QueuePool

engine = create_async_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=20,
    max_overflow=30,
    pool_pre_ping=True,
    pool_recycle=3600
)
```

#### 缓存策略

```python
# backend/core/cache.py
from functools import wraps
import json
import hashlib

def cache_result(expire_time: int = 300):
    """结果缓存装饰器"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 生成缓存键
            cache_key = f"{func.__name__}:{hashlib.md5(json.dumps([args, kwargs], sort_keys=True).encode()).hexdigest()}"
            
            # 尝试从缓存获取
            cached_result = await redis.get(cache_key)
            if cached_result:
                return json.loads(cached_result)
            
            # 执行函数并缓存结果
            result = await func(*args, **kwargs)
            await redis.setex(cache_key, expire_time, json.dumps(result))
            
            return result
        return wrapper
    return decorator
```

### 2. 数据库优化

#### 查询优化

```sql
-- 使用EXPLAIN ANALYZE分析查询
EXPLAIN ANALYZE SELECT * FROM documents WHERE user_id = 123;

-- 优化复杂查询
WITH user_docs AS (
    SELECT id, title, created_at
    FROM documents
    WHERE user_id = $1
    ORDER BY created_at DESC
    LIMIT 10
)
SELECT d.*, t.status as task_status
FROM user_docs d
LEFT JOIN tasks t ON t.document_id = d.id
ORDER BY d.created_at DESC;
```

### 3. 前端优化

#### 代码分割

```javascript
// frontend/next.config.js
module.exports = {
  experimental: {
    esmExternals: true
  },
  webpack: (config) => {
    config.optimization.splitChunks = {
      chunks: 'all',
      cacheGroups: {
        vendor: {
          test: /[\\/]node_modules[\\/]/,
          name: 'vendors',
          chunks: 'all'
        }
      }
    }
    return config
  }
}
```

#### 图片优化

```javascript
// 使用Next.js Image组件
import Image from 'next/image'

const OptimizedImage = ({ src, alt, width, height }) => {
  return (
    <Image
      src={src}
      alt={alt}
      width={width}
      height={height}
      placeholder="blur"
      blurDataURL="data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAYEBQYFBAYGBQYHBwYIChAKCgkJChQODwwQFxQYGBcUFhYaHSUfGhsjHBYWICwgIyYnKSopGR8tMC0oMCUoKSj/2wBDAQcHBwoIChMKChMoGhYaKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCj/wAARCAAIAAoDASIAAhEBAxEB/8QAFQABAQAAAAAAAAAAAAAAAAAAAAv/xAAhEAACAQMDBQAAAAAAAAAAAAABAgMABAUGIWEREiMxUf/EABUBAQEAAAAAAAAAAAAAAAAAAAMF/8QAGhEAAgIDAAAAAAAAAAAAAAAAAAECEgMRkf/aAAwDAQACEQMRAD8AltJagyeH0AthI5xdrLcNM91BF5pX2HaH9bcfaSXWGaRmknyJckliyjqTzSlT54b6bk+h0R//2Q=="
      priority
    />
  )
}
```

通过遵循本部署指南，您可以成功部署和运维企业知识库系统，确保系统的稳定性、安全性和高性能。