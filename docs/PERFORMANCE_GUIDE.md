# 性能优化指南

## 概述

本文档提供智能知识库系统的性能优化策略、调优方法和最佳实践。

## 应用层优化

### FastAPI优化

#### 异步编程
```python
# 使用异步数据库连接
async def get_entities(limit: int = 100):
    async with database.transaction():
        query = "SELECT * FROM entities LIMIT :limit"
        return await database.fetch_all(query, {"limit": limit})

# 并发处理
import asyncio
async def batch_process_documents(documents: List[Document]):
    tasks = [process_document(doc) for doc in documents]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return results
```

#### 连接池配置
```python
# database.py
DATABASE_CONFIG = {
    "pool_size": 20,
    "max_overflow": 30,
    "pool_timeout": 30,
    "pool_recycle": 3600,
    "pool_pre_ping": True,
}

# Neo4j连接池
NEO4J_CONFIG = {
    "max_connection_lifetime": 3600,
    "max_connection_pool_size": 50,
    "connection_acquisition_timeout": 60,
}
```

#### 缓存策略
```python
from functools import lru_cache
import redis
import json

# 内存缓存
@lru_cache(maxsize=1000)
def get_entity_type_config(entity_type: str):
    return load_entity_config(entity_type)

# Redis缓存
class CacheService:
    def __init__(self, redis_client):
        self.redis = redis_client
        
    async def get_or_set(self, key: str, factory, ttl: int = 3600):
        cached = await self.redis.get(key)
        if cached:
            return json.loads(cached)
            
        data = await factory()
        await self.redis.setex(key, ttl, json.dumps(data))
        return data
```

### 数据库优化

#### PostgreSQL优化
```sql
-- 索引优化
CREATE INDEX CONCURRENTLY idx_entities_type_name 
ON entities(entity_type, name);

CREATE INDEX CONCURRENTLY idx_documents_created_at 
ON documents(created_at DESC);

-- 分区表
CREATE TABLE entities_partitioned (
    id UUID DEFAULT gen_random_uuid(),
    entity_type VARCHAR(50),
    name VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW()
) PARTITION BY HASH (entity_type);

-- 查询优化
EXPLAIN (ANALYZE, BUFFERS) 
SELECT * FROM entities 
WHERE entity_type = 'PERSON' 
AND name ILIKE '%张%'
LIMIT 20;
```

#### Neo4j优化
```cypher
// 索引创建
CREATE INDEX entity_name_index FOR (e:Entity) ON (e.name);
CREATE INDEX relation_type_index FOR ()-[r:RELATION]-() ON (r.type);

// 查询优化
PROFILE MATCH (p:PERSON)-[r:WORKS_FOR]->(o:ORGANIZATION)
WHERE p.name CONTAINS '张'
RETURN p, r, o
LIMIT 10;

// 批量操作
UNWIND $entities AS entity
MERGE (e:Entity {id: entity.id})
SET e += entity.properties;
```

#### Redis优化
```bash
# redis.conf 优化配置
maxmemory 2gb
maxmemory-policy allkeys-lru
save 900 1
save 300 10
save 60 10000

# 连接池配置
timeout 300
tcp-keepalive 300
```

## 搜索性能优化

### 向量搜索优化
```python
# 使用FAISS进行向量搜索
import faiss
import numpy as np

class VectorSearchOptimizer:
    def __init__(self, dimension: int):
        self.dimension = dimension
        self.index = faiss.IndexIVFFlat(
            faiss.IndexFlatL2(dimension), 
            dimension, 
            100  # nlist
        )
        
    def build_index(self, vectors: np.ndarray):
        # 训练索引
        self.index.train(vectors)
        # 添加向量
        self.index.add(vectors)
        
    def search(self, query_vector: np.ndarray, k: int = 10):
        # 设置搜索参数
        self.index.nprobe = 10
        distances, indices = self.index.search(query_vector, k)
        return distances, indices
```

### 向量搜索优化
```python
# StarRocks配置
STARROCKS_SETTINGS = {
    "replication_num": 3,
    "storage_medium": "SSD",
    "refresh_interval": 30,
    "max_scan_key_num": 10000,
}

STARROCKS_TABLE_SCHEMA = {
    "vector_embeddings": {
        "id": "BIGINT",
        "entity_id": "VARCHAR(255)",
        "content": "TEXT",
        "embedding": "ARRAY<FLOAT>",
        "entity_type": "VARCHAR(50)",
        "created_at": "DATETIME",
        "INDEX": "INDEX idx_entity_type (entity_type) USING BITMAP"
    }
}

# 向量相似度搜索优化
VECTOR_SEARCH_CONFIG = {
    "similarity_threshold": 0.8,
    "max_results": 100,
    "use_approximate": True,
    "index_type": "HNSW"
}
```

## 系统层优化

### 操作系统调优
```bash
# /etc/sysctl.conf
# 网络优化
net.core.rmem_max = 134217728
net.core.wmem_max = 134217728
net.ipv4.tcp_rmem = 4096 87380 134217728
net.ipv4.tcp_wmem = 4096 65536 134217728

# 文件描述符
fs.file-max = 1000000
fs.nr_open = 1000000

# 内存管理
vm.swappiness = 10
vm.dirty_ratio = 15
vm.dirty_background_ratio = 5

# 应用limits.conf
echo "* soft nofile 65536" >> /etc/security/limits.conf
echo "* hard nofile 65536" >> /etc/security/limits.conf
```

### Docker优化
```dockerfile
# 多阶段构建
FROM python:3.11-slim as builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM python:3.11-slim
WORKDIR /app
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY . .

# 优化配置
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONPATH=/app

# 资源限制
LABEL memory="2g"
LABEL cpu="1"
```

### Nginx优化
```nginx
# nginx.conf
worker_processes auto;
worker_rlimit_nofile 65535;

events {
    worker_connections 65535;
    use epoll;
    multi_accept on;
}

http {
    # 基础优化
    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    keepalive_requests 10000;
    
    # 缓存配置
    proxy_cache_path /var/cache/nginx levels=1:2 keys_zone=api_cache:10m max_size=1g inactive=60m;
    
    # 压缩配置
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain application/json application/javascript text/css;
    
    # 限流配置
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    
    upstream app_servers {
        least_conn;
        server app1:8000 max_fails=3 fail_timeout=30s;
        server app2:8000 max_fails=3 fail_timeout=30s;
        server app3:8000 max_fails=3 fail_timeout=30s;
    }
    
    server {
        listen 80;
        
        location /api/ {
            limit_req zone=api burst=20 nodelay;
            proxy_pass http://app_servers;
            proxy_cache api_cache;
            proxy_cache_valid 200 5m;
            proxy_cache_key $scheme$proxy_host$request_uri;
        }
    }
}
```

## 监控和调优

### 性能指标监控
```python
# 关键性能指标
PERFORMANCE_METRICS = {
    # 响应时间
    "response_time_p50": "50%响应时间",
    "response_time_p95": "95%响应时间", 
    "response_time_p99": "99%响应时间",
    
    # 吞吐量
    "requests_per_second": "每秒请求数",
    "concurrent_users": "并发用户数",
    
    # 资源使用
    "cpu_usage": "CPU使用率",
    "memory_usage": "内存使用率",
    "disk_io": "磁盘I/O",
    "network_io": "网络I/O",
    
    # 数据库性能
    "db_connection_pool": "数据库连接池使用率",
    "db_query_time": "数据库查询时间",
    "cache_hit_rate": "缓存命中率",
}
```

### 性能测试
```python
# locustfile.py
from locust import HttpUser, task, between

class KnowledgeSystemUser(HttpUser):
    wait_time = between(1, 3)
    
    def on_start(self):
        # 登录获取token
        response = self.client.post("/auth/login", json={
            "username": "test_user",
            "password": "test_password"
        })
        self.token = response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    @task(3)
    def search_entities(self):
        self.client.get("/api/v1/entities/search?q=测试", 
                       headers=self.headers)
    
    @task(2)
    def get_entity_details(self):
        self.client.get("/api/v1/entities/123", 
                       headers=self.headers)
    
    @task(1)
    def create_entity(self):
        self.client.post("/api/v1/entities", 
                        headers=self.headers,
                        json={
                            "name": "测试实体",
                            "entity_type": "CONCEPT"
                        })
```

### 性能调优流程
```bash
#!/bin/bash
# 性能调优脚本

echo "开始性能调优..."

# 1. 基准测试
echo "1. 执行基准测试..."
locust -f locustfile.py --headless -u 100 -r 10 -t 300s --html=baseline_report.html

# 2. 分析瓶颈
echo "2. 分析系统瓶颈..."
# CPU分析
top -bn1 | head -20
# 内存分析  
free -h
# I/O分析
iostat -x 1 10
# 网络分析
iftop -t -s 10

# 3. 数据库性能分析
echo "3. 分析数据库性能..."
docker-compose exec postgres psql -c "
SELECT query, calls, total_time, mean_time 
FROM pg_stat_statements 
ORDER BY total_time DESC 
LIMIT 10;"

# 4. 应用性能分析
echo "4. 分析应用性能..."
curl -s http://localhost:8000/metrics | grep -E "(http_request_duration|http_requests_total)"

# 5. 生成优化建议
echo "5. 生成优化建议..."
python performance_analyzer.py --generate-recommendations

echo "性能调优完成，请查看报告文件"
```

## 扩展性设计

### 水平扩展
```yaml
# docker-compose.scale.yml
version: '3.8'
services:
  app:
    deploy:
      replicas: 3
      update_config:
        parallelism: 1
        delay: 10s
      restart_policy:
        condition: on-failure
        
  nginx:
    depends_on:
      - app
    ports:
      - "80:80"
      - "443:443"
```

### 数据库分片
```python
# 数据库分片策略
class DatabaseSharding:
    def __init__(self):
        self.shards = {
            "shard1": "postgresql://user:pass@db1:5432/knowledge_shard1",
            "shard2": "postgresql://user:pass@db2:5432/knowledge_shard2", 
            "shard3": "postgresql://user:pass@db3:5432/knowledge_shard3",
        }
    
    def get_shard(self, entity_id: str) -> str:
        """根据实体ID选择分片"""
        shard_key = hash(entity_id) % len(self.shards)
        return list(self.shards.keys())[shard_key]
    
    def get_connection(self, shard_name: str):
        """获取分片连接"""
        return create_engine(self.shards[shard_name])
```

### 缓存层设计
```python
# 多层缓存架构
class CacheLayer:
    def __init__(self):
        self.l1_cache = {}  # 应用内存缓存
        self.l2_cache = redis.Redis()  # Redis缓存
        self.l3_cache = memcached.Client()  # Memcached缓存
    
    async def get(self, key: str):
        # L1缓存
        if key in self.l1_cache:
            return self.l1_cache[key]
        
        # L2缓存
        value = await self.l2_cache.get(key)
        if value:
            self.l1_cache[key] = value
            return value
            
        # L3缓存
        value = self.l3_cache.get(key)
        if value:
            await self.l2_cache.setex(key, 3600, value)
            self.l1_cache[key] = value
            return value
            
        return None
```

## 性能最佳实践

### 代码优化
1. **避免N+1查询**: 使用JOIN或批量查询
2. **合理使用缓存**: 缓存热点数据和计算结果
3. **异步处理**: 使用异步I/O和任务队列
4. **资源池化**: 使用连接池和对象池
5. **懒加载**: 按需加载数据和资源

### 数据库优化
1. **索引策略**: 为查询字段创建合适索引
2. **查询优化**: 避免全表扫描和复杂子查询
3. **数据分区**: 按时间或业务逻辑分区
4. **读写分离**: 分离读写操作到不同实例
5. **连接管理**: 合理配置连接池参数

### 系统优化
1. **负载均衡**: 分散请求到多个实例
2. **CDN加速**: 静态资源使用CDN
3. **压缩传输**: 启用gzip压缩
4. **Keep-Alive**: 复用HTTP连接
5. **资源限制**: 合理设置资源限制

### 监控优化
1. **关键指标**: 监控核心业务指标
2. **实时告警**: 设置性能阈值告警
3. **趋势分析**: 分析性能变化趋势
4. **容量规划**: 基于监控数据规划容量
5. **持续改进**: 定期性能评估和优化 