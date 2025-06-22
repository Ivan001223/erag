# 企业级智能知识库系统 - 部署与运维指南

## 🚀 项目概述

本项目是一个完整的企业级智能知识库系统，集成了以下高级功能：

### 🔧 核心技术栈
- **后端框架**: FastAPI + Python 3.11
- **数据库**: PostgreSQL + Neo4j + Redis
- **存储**: MinIO (S3兼容)
- **监控**: Prometheus + Grafana + Jaeger
- **容器化**: Docker + Docker Compose
- **CI/CD**: GitHub Actions

### 🛡️ 安全特性
- JWT认证和权限控制
- API限流和IP白名单
- 输入验证和SQL注入防护
- 安全头和HTTPS支持

### 📊 监控和追踪
- 分布式追踪 (OpenTelemetry + Jaeger)
- 应用指标监控 (Prometheus)
- 可视化仪表板 (Grafana)
- 结构化日志 (Structlog)

### 💾 数据备份和恢复
- 自动化备份策略
- 多存储后端支持 (本地/S3/MinIO)
- 增量和全量备份
- 数据完整性验证

## 📋 部署前准备

### 系统要求
- **操作系统**: Linux/macOS/Windows
- **内存**: 最少 8GB RAM (推荐 16GB+)
- **存储**: 最少 50GB 可用空间
- **CPU**: 4核心以上
- **网络**: 稳定的互联网连接

### 必需软件
```bash
# Docker 和 Docker Compose
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Python 3.11+
sudo apt update
sudo apt install python3.11 python3.11-venv python3-pip

# Git
sudo apt install git
```

## 🚀 快速部署

### 1. 克隆项目
```bash
git clone <repository-url>
cd knowledge-system
```

### 2. 环境配置
```bash
# 复制环境变量模板
cp .env.example .env

# 编辑环境变量
nano .env
```

### 3. 启动服务
```bash
# 开发环境
docker-compose up -d

# 生产环境
docker-compose -f docker-compose.prod.yml up -d
```

### 4. 验证部署
```bash
# 检查服务状态
docker-compose ps

# 健康检查
curl http://localhost:8000/health

# 查看日志
docker-compose logs -f app
```

## 🔧 配置详解

### 环境变量配置
```bash
# 应用配置
APP_NAME="智能知识库系统"
APP_VERSION="1.0.0"
APP_ENV="production"
APP_DEBUG="false"

# 数据库配置
DATABASE_URL="postgresql://user:password@postgres:5432/knowledge_db"
NEO4J_URL="bolt://neo4j:7687"
NEO4J_USER="neo4j"
NEO4J_PASSWORD="your_password"
REDIS_URL="redis://redis:6379"

# 存储配置
MINIO_ENDPOINT="minio:9000"
MINIO_ACCESS_KEY="your_access_key"
MINIO_SECRET_KEY="your_secret_key"

# 安全配置
JWT_SECRET_KEY="your_jwt_secret"
ENCRYPTION_KEY="your_encryption_key"

# 监控配置
JAEGER_ENDPOINT="jaeger:14268"
PROMETHEUS_URL="http://prometheus:9090"

# 外部服务
LLM_API_URL="your_llm_service_url"
LLM_API_KEY="your_llm_api_key"
```

### Docker Compose 服务说明

#### 核心服务
- **app**: 主应用服务 (端口: 8000)
- **postgres**: PostgreSQL数据库 (端口: 5432)
- **neo4j**: Neo4j图数据库 (端口: 7474, 7687)
- **redis**: Redis缓存 (端口: 6379)
- **minio**: 对象存储 (端口: 9000, 9001)

#### 监控服务
- **jaeger**: 分布式追踪 (端口: 16686)
- **prometheus**: 指标收集 (端口: 9090)
- **grafana**: 可视化仪表板 (端口: 3000)

#### 可选服务
- **nginx**: 反向代理 (端口: 80, 443)
- **elasticsearch**: 日志聚合 (端口: 9200)
- **kibana**: 日志可视化 (端口: 5601)

## 🔍 监控和运维

### 健康检查端点
```bash
# 基础健康检查
curl http://localhost:8000/health

# 详细健康状态
curl http://localhost:8000/health/detailed

# 就绪检查
curl http://localhost:8000/health/readiness

# 存活检查
curl http://localhost:8000/health/liveness

# 应用指标
curl http://localhost:8000/metrics
```

### 日志管理
```bash
# 查看应用日志
docker-compose logs -f app

# 查看特定服务日志
docker-compose logs -f neo4j

# 日志文件位置
tail -f logs/app.log
tail -f logs/error.log
```

### 性能监控
- **Grafana仪表板**: http://localhost:3000 (admin/admin)
- **Prometheus指标**: http://localhost:9090
- **Jaeger追踪**: http://localhost:16686

### 数据备份
```bash
# 手动创建备份
curl -X POST http://localhost:8000/admin/backup \
  -H "Authorization: Bearer your_token" \
  -H "Content-Type: application/json" \
  -d '{"backup_type": "full", "description": "手动备份"}'

# 查看备份列表
curl http://localhost:8000/admin/backups \
  -H "Authorization: Bearer your_token"

# 恢复备份
curl -X POST http://localhost:8000/admin/restore \
  -H "Authorization: Bearer your_token" \
  -H "Content-Type: application/json" \
  -d '{"backup_id": "backup_20240101_120000"}'
```

## 🧪 测试

### 运行测试套件
```bash
# 安装测试依赖
pip install -r requirements-test.txt

# 运行所有测试
pytest

# 运行单元测试
pytest tests/unit/

# 运行集成测试
pytest tests/integration/

# 运行性能测试
pytest tests/performance/ --benchmark-only

# 生成覆盖率报告
pytest --cov=backend --cov-report=html
```

### CI/CD 流水线
GitHub Actions 自动执行：
- 代码质量检查 (Black, Flake8, MyPy)
- 安全扫描 (Bandit, Safety)
- 单元测试和集成测试
- Docker镜像构建和推送
- 自动部署到测试/生产环境

## 📊 性能优化

### 数据库优化
```sql
-- Neo4j 索引优化
CREATE INDEX entity_name_index FOR (n:Entity) ON (n.name)
CREATE INDEX relation_type_index FOR ()-[r:RELATIONSHIP]-() ON (r.type)

-- PostgreSQL 索引优化
CREATE INDEX idx_documents_created_at ON documents(created_at);
CREATE INDEX idx_entities_type ON entities(entity_type);
```

### 缓存策略
- **Redis缓存**: 热点数据缓存 (TTL: 300s)
- **应用缓存**: LRU内存缓存 (大小: 1000项)
- **CDN缓存**: 静态资源缓存

### 连接池配置
```python
# Neo4j连接池
max_connection_pool_size = 50
max_connection_lifetime = 3600

# PostgreSQL连接池
pool_size = 20
max_overflow = 30
pool_timeout = 30
```

## 🚨 故障排除

### 常见问题

#### 1. 服务启动失败
```bash
# 检查端口占用
netstat -tulpn | grep :8000

# 检查Docker状态
docker ps -a
docker-compose logs app
```

#### 2. 数据库连接失败
```bash
# 检查数据库状态
docker-compose exec postgres pg_isready
docker-compose exec neo4j cypher-shell -u neo4j -p password "RETURN 1"
docker-compose exec redis redis-cli ping
```

#### 3. 内存不足
```bash
# 检查内存使用
docker stats
free -h

# 调整容器内存限制
# 在docker-compose.yml中添加:
deploy:
  resources:
    limits:
      memory: 2G
```

#### 4. 磁盘空间不足
```bash
# 清理Docker资源
docker system prune -a

# 清理日志文件
truncate -s 0 logs/*.log

# 清理备份文件
find backups/ -name "*.gz" -mtime +30 -delete
```

### 应急恢复

#### 数据恢复
```bash
# 从最新备份恢复
curl -X POST http://localhost:8000/admin/restore \
  -H "Authorization: Bearer your_token" \
  -d '{"backup_id": "latest"}'

# 手动数据库恢复
docker-compose exec postgres pg_restore -U postgres -d knowledge_db /backups/latest.sql
```

#### 服务重启
```bash
# 重启所有服务
docker-compose restart

# 重启特定服务
docker-compose restart app

# 强制重新创建容器
docker-compose up -d --force-recreate app
```

## 🔒 安全最佳实践

### 1. 访问控制
- 使用强密码和JWT令牌
- 定期轮换密钥和证书
- 实施最小权限原则

### 2. 网络安全
- 配置防火墙规则
- 使用HTTPS/TLS加密
- 限制对外暴露的端口

### 3. 数据保护
- 加密敏感数据
- 定期备份验证
- 实施数据保留策略

### 4. 监控告警
```bash
# 设置Prometheus告警规则
# 在monitoring/prometheus/rules.yml中配置:
groups:
  - name: application
    rules:
      - alert: HighErrorRate
        expr: rate(http_errors_total[5m]) > 0.1
        for: 5m
        annotations:
          summary: "应用错误率过高"
```

## 📞 支持和维护

### 定期维护任务
- [ ] 每日：检查服务状态和日志
- [ ] 每周：清理临时文件和日志
- [ ] 每月：更新依赖和安全补丁
- [ ] 每季度：性能评估和优化
- [ ] 每年：灾难恢复演练

### 联系方式
- **技术支持**: support@company.com
- **紧急联系**: emergency@company.com
- **文档更新**: docs@company.com

---

## 📝 更新日志

### v1.0.0 (2024-01-01)
- ✅ 完整的后端架构重构
- ✅ API限流和安全增强
- ✅ 分布式追踪和监控
- ✅ 自动化备份和恢复
- ✅ 完整的测试套件
- ✅ CI/CD流水线

### 下一版本计划
- 🔄 多租户支持
- 🔄 AI模型集成优化
- 🔄 实时协作功能
- 🔄 移动端支持 