# 企业知识库系统性能优化策略

## 概述

本文档详细描述了企业知识库系统(ERAG)的性能优化策略，涵盖数据库优化、缓存策略、并发处理、资源管理等多个方面，旨在确保系统在高负载下的稳定性和响应速度。

## 1. 数据库性能优化

### 1.1 Neo4j 图数据库优化

#### 索引策略
```cypher
-- 实体索引
CREATE INDEX entity_name_index FOR (e:Entity) ON (e.name)
CREATE INDEX entity_type_index FOR (e:Entity) ON (e.type)
CREATE INDEX entity_confidence_index FOR (e:Entity) ON (e.confidence)

-- 关系索引
CREATE INDEX relation_type_index FOR ()-[r:RELATES_TO]-() ON (r.type)
CREATE INDEX relation_confidence_index FOR ()-[r:RELATES_TO]-() ON (r.confidence)

-- 复合索引
CREATE INDEX entity_composite_index FOR (e:Entity) ON (e.type, e.confidence)
```

#### 查询优化
- **使用PROFILE和EXPLAIN**：分析查询执行计划
- **避免笛卡尔积**：使用适当的WHERE子句
- **限制结果集**：使用LIMIT和分页
- **优化路径查询**：使用变长路径时设置合理的深度限制

```cypher
-- 优化前
MATCH (a:Entity)-[*1..5]-(b:Entity)
WHERE a.name = 'target_entity'
RETURN b

-- 优化后
MATCH (a:Entity {name: 'target_entity'})-[r*1..3]-(b:Entity)
WHERE ALL(rel in r WHERE rel.confidence > 0.7)
RETURN b
LIMIT 100
```

#### 内存配置
```properties
# neo4j.conf
dbms.memory.heap.initial_size=2G
dbms.memory.heap.max_size=8G
dbms.memory.pagecache.size=4G
dbms.tx_state.memory_allocation=ON_HEAP
```

### 1.2 StarRocks 数据仓库优化

#### 表设计优化
```sql
-- 分区策略
CREATE TABLE documents (
    id VARCHAR(64),
    title VARCHAR(500),
    content TEXT,
    created_at DATETIME,
    updated_at DATETIME,
    category VARCHAR(100)
) ENGINE=OLAP
DUPLICATE KEY(id)
PARTITION BY RANGE(created_at) (
    PARTITION p202401 VALUES [("2024-01-01"), ("2024-02-01")),
    PARTITION p202402 VALUES [("2024-02-01"), ("2024-03-01"))
)
DISTRIBUTED BY HASH(id) BUCKETS 32
PROPERTIES (
    "replication_num" = "3",
    "storage_medium" = "SSD",
    "compression" = "LZ4"
);

-- 物化视图
CREATE MATERIALIZED VIEW document_stats AS
SELECT 
    category,
    DATE_TRUNC('day', created_at) as date,
    COUNT(*) as doc_count,
    AVG(LENGTH(content)) as avg_content_length
FROM documents
GROUP BY category, DATE_TRUNC('day', created_at);
```

#### 查询优化
- **分区裁剪**：查询时指定分区条件
- **列式存储**：只查询需要的列
- **预聚合**：使用物化视图
- **并行执行**：合理设置并行度

```sql
-- 优化查询示例
SELECT /*+ SET_VAR(parallel_fragment_exec_instance_num=8) */
    category,
    COUNT(*) as doc_count
FROM documents
WHERE created_at >= '2024-01-01' 
    AND created_at < '2024-02-01'
    AND category IN ('tech', 'business')
GROUP BY category;
```

### 1.3 Redis 缓存优化

#### 内存优化
```redis
# redis.conf
maxmemory 8gb
maxmemory-policy allkeys-lru
maxmemory-samples 10

# 启用压缩
hash-max-ziplist-entries 512
hash-max-ziplist-value 64
list-max-ziplist-size -2
set-max-intset-entries 512
```

#### 缓存策略
```python
# 缓存层次结构
class CacheStrategy:
    def __init__(self):
        self.l1_cache = {}  # 内存缓存
        self.l2_cache = redis_client  # Redis缓存
        self.l3_cache = database  # 数据库
    
    async def get(self, key: str):
        # L1缓存
        if key in self.l1_cache:
            return self.l1_cache[key]
        
        # L2缓存
        value = await self.l2_cache.get(key)
        if value:
            self.l1_cache[key] = value
            return value
        
        # L3数据库
        value = await self.l3_cache.get(key)
        if value:
            await self.l2_cache.setex(key, 3600, value)
            self.l1_cache[key] = value
        
        return value
```

## 2. 应用层性能优化

### 2.1 异步处理优化

#### 连接池管理
```python
# 数据库连接池配置
class DatabaseConfig:
    NEO4J_POOL_SIZE = 50
    NEO4J_MAX_CONNECTION_LIFETIME = 3600
    STARROCKS_POOL_SIZE = 20
    REDIS_POOL_SIZE = 100
    
    # 连接池配置
    @staticmethod
    def get_neo4j_driver():
        return GraphDatabase.driver(
            uri=NEO4J_URL,
            auth=(NEO4J_USER, NEO4J_PASSWORD),
            max_connection_pool_size=DatabaseConfig.NEO4J_POOL_SIZE,
            max_connection_lifetime=DatabaseConfig.NEO4J_MAX_CONNECTION_LIFETIME,
            connection_acquisition_timeout=30
        )
```

#### 批处理优化
```python
class BatchProcessor:
    def __init__(self, batch_size: int = 100):
        self.batch_size = batch_size
        self.batch_queue = []
    
    async def process_batch(self, items: List[Any]):
        """批量处理数据"""
        tasks = []
        for i in range(0, len(items), self.batch_size):
            batch = items[i:i + self.batch_size]
            task = asyncio.create_task(self._process_single_batch(batch))
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return results
    
    async def _process_single_batch(self, batch: List[Any]):
        """处理单个批次"""
        # 批量数据库操作
        async with self.db_session() as session:
            await session.execute_batch(batch)
```

### 2.2 并发控制

#### 信号量限制
```python
class ConcurrencyManager:
    def __init__(self):
        self.ocr_semaphore = asyncio.Semaphore(5)  # OCR并发限制
        self.llm_semaphore = asyncio.Semaphore(3)  # LLM并发限制
        self.db_semaphore = asyncio.Semaphore(20)  # 数据库并发限制
    
    async def process_document(self, document):
        async with self.ocr_semaphore:
            ocr_result = await self.ocr_service.process(document)
        
        async with self.llm_semaphore:
            entities = await self.llm_service.extract_entities(ocr_result)
        
        async with self.db_semaphore:
            await self.db_service.save_entities(entities)
```

#### 任务队列
```python
from celery import Celery

# Celery配置
app = Celery('erag')
app.conf.update(
    broker_url='redis://localhost:6379/0',
    result_backend='redis://localhost:6379/0',
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    worker_concurrency=4,
    worker_prefetch_multiplier=1
)

@app.task(bind=True, max_retries=3)
def process_document_task(self, document_id: str):
    try:
        # 文档处理逻辑
        return process_document(document_id)
    except Exception as exc:
        self.retry(countdown=60, exc=exc)
```

## 3. 向量搜索优化

### 3.1 向量索引优化

#### Faiss索引配置
```python
import faiss

class VectorIndexOptimizer:
    def __init__(self, dimension: int, num_vectors: int):
        self.dimension = dimension
        self.num_vectors = num_vectors
    
    def create_optimized_index(self):
        if self.num_vectors < 10000:
            # 小数据集使用暴力搜索
            index = faiss.IndexFlatIP(self.dimension)
        elif self.num_vectors < 100000:
            # 中等数据集使用IVF
            nlist = int(4 * math.sqrt(self.num_vectors))
            quantizer = faiss.IndexFlatIP(self.dimension)
            index = faiss.IndexIVFFlat(quantizer, self.dimension, nlist)
        else:
            # 大数据集使用HNSW
            index = faiss.IndexHNSWFlat(self.dimension, 32)
            index.hnsw.efConstruction = 200
            index.hnsw.efSearch = 100
        
        return index
```

### 3.2 搜索优化

#### 多级搜索策略
```python
class HierarchicalSearch:
    def __init__(self):
        self.coarse_index = self._build_coarse_index()  # 粗粒度索引
        self.fine_index = self._build_fine_index()      # 细粒度索引
    
    async def search(self, query_vector, top_k=10):
        # 第一阶段：粗粒度搜索
        coarse_candidates = await self._coarse_search(query_vector, top_k * 10)
        
        # 第二阶段：细粒度重排
        fine_results = await self._fine_search(query_vector, coarse_candidates, top_k)
        
        return fine_results
```

## 4. 缓存策略

### 4.1 多级缓存架构

```python
class MultiLevelCache:
    def __init__(self):
        self.memory_cache = LRUCache(maxsize=1000)  # L1: 内存缓存
        self.redis_cache = RedisCache()             # L2: Redis缓存
        self.disk_cache = DiskCache()               # L3: 磁盘缓存
    
    async def get(self, key: str):
        # L1缓存
        if key in self.memory_cache:
            return self.memory_cache[key]
        
        # L2缓存
        value = await self.redis_cache.get(key)
        if value:
            self.memory_cache[key] = value
            return value
        
        # L3缓存
        value = await self.disk_cache.get(key)
        if value:
            await self.redis_cache.set(key, value, ttl=3600)
            self.memory_cache[key] = value
            return value
        
        return None
```

### 4.2 缓存预热策略

```python
class CacheWarmer:
    def __init__(self, cache_service: CacheService):
        self.cache_service = cache_service
    
    async def warm_up(self):
        """系统启动时预热缓存"""
        # 预热热门实体
        hot_entities = await self.get_hot_entities()
        for entity in hot_entities:
            await self.cache_service.set(f"entity:{entity.id}", entity)
        
        # 预热常用查询
        common_queries = await self.get_common_queries()
        for query in common_queries:
            result = await self.execute_query(query)
            await self.cache_service.set(f"query:{query.hash}", result)
```

## 5. 监控和性能指标

### 5.1 关键性能指标(KPI)

```python
class PerformanceMetrics:
    def __init__(self):
        self.metrics = {
            'response_time': [],
            'throughput': [],
            'error_rate': [],
            'cache_hit_rate': [],
            'db_connection_pool_usage': [],
            'memory_usage': [],
            'cpu_usage': []
        }
    
    def record_response_time(self, endpoint: str, duration: float):
        self.metrics['response_time'].append({
            'endpoint': endpoint,
            'duration': duration,
            'timestamp': time.time()
        })
    
    def get_p95_response_time(self, endpoint: str = None) -> float:
        times = [m['duration'] for m in self.metrics['response_time']
                if endpoint is None or m['endpoint'] == endpoint]
        return np.percentile(times, 95) if times else 0
```

### 5.2 性能监控

```python
import prometheus_client
from prometheus_client import Counter, Histogram, Gauge

# Prometheus指标
REQUEST_COUNT = Counter('requests_total', 'Total requests', ['method', 'endpoint'])
REQUEST_DURATION = Histogram('request_duration_seconds', 'Request duration')
ACTIVE_CONNECTIONS = Gauge('active_connections', 'Active database connections')
CACHE_HIT_RATE = Gauge('cache_hit_rate', 'Cache hit rate')

class PerformanceMonitor:
    @staticmethod
    def monitor_request(func):
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                REQUEST_COUNT.labels(method='GET', endpoint=func.__name__).inc()
                return result
            finally:
                REQUEST_DURATION.observe(time.time() - start_time)
        return wrapper
```

## 6. 资源管理和调优

### 6.1 内存管理

```python
class MemoryManager:
    def __init__(self, max_memory_mb: int = 8192):
        self.max_memory = max_memory_mb * 1024 * 1024
        self.current_usage = 0
    
    def check_memory_usage(self):
        import psutil
        process = psutil.Process()
        memory_info = process.memory_info()
        
        if memory_info.rss > self.max_memory * 0.9:
            self.trigger_gc()
            self.clear_caches()
    
    def trigger_gc(self):
        import gc
        gc.collect()
    
    def clear_caches(self):
        # 清理缓存
        pass
```

### 6.2 CPU优化

```python
import multiprocessing
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor

class CPUOptimizer:
    def __init__(self):
        self.cpu_count = multiprocessing.cpu_count()
        self.process_pool = ProcessPoolExecutor(max_workers=self.cpu_count)
        self.thread_pool = ThreadPoolExecutor(max_workers=self.cpu_count * 2)
    
    async def cpu_intensive_task(self, data):
        """CPU密集型任务使用进程池"""
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            self.process_pool, self._process_data, data
        )
        return result
    
    async def io_intensive_task(self, data):
        """IO密集型任务使用线程池"""
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            self.thread_pool, self._io_operation, data
        )
        return result
```

## 7. 部署优化

### 7.1 容器化优化

```dockerfile
# 多阶段构建优化
FROM python:3.11-slim as builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

FROM python:3.11-slim
WORKDIR /app
COPY --from=builder /root/.local /root/.local
COPY . .

# 性能优化环境变量
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONHASHSEED=random
ENV PYTHONIOENCODING=utf-8

# 资源限制
ENV MALLOC_ARENA_MAX=2
ENV MALLOC_MMAP_THRESHOLD_=131072
ENV MALLOC_TRIM_THRESHOLD_=131072
ENV MALLOC_TOP_PAD_=131072
ENV MALLOC_MMAP_MAX_=65536

CMD ["gunicorn", "--workers", "4", "--worker-class", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000", "main:app"]
```

### 7.2 Kubernetes优化

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: erag-backend
spec:
  replicas: 3
  template:
    spec:
      containers:
      - name: backend
        image: erag-backend:latest
        resources:
          requests:
            memory: "2Gi"
            cpu: "1000m"
          limits:
            memory: "4Gi"
            cpu: "2000m"
        env:
        - name: WORKERS
          value: "4"
        - name: MAX_CONNECTIONS
          value: "100"
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 60
          periodSeconds: 30
---
apiVersion: v1
kind: Service
metadata:
  name: erag-backend-service
spec:
  selector:
    app: erag-backend
  ports:
  - port: 80
    targetPort: 8000
  type: LoadBalancer
```

## 8. 性能测试和基准

### 8.1 负载测试

```python
import asyncio
import aiohttp
import time
from concurrent.futures import ThreadPoolExecutor

class LoadTester:
    def __init__(self, base_url: str, concurrent_users: int = 100):
        self.base_url = base_url
        self.concurrent_users = concurrent_users
        self.results = []
    
    async def test_endpoint(self, session, endpoint: str):
        start_time = time.time()
        try:
            async with session.get(f"{self.base_url}{endpoint}") as response:
                await response.text()
                duration = time.time() - start_time
                self.results.append({
                    'endpoint': endpoint,
                    'duration': duration,
                    'status': response.status
                })
        except Exception as e:
            self.results.append({
                'endpoint': endpoint,
                'duration': time.time() - start_time,
                'error': str(e)
            })
    
    async def run_load_test(self, endpoints: list, duration_seconds: int = 60):
        async with aiohttp.ClientSession() as session:
            end_time = time.time() + duration_seconds
            tasks = []
            
            while time.time() < end_time:
                for endpoint in endpoints:
                    if len(tasks) < self.concurrent_users:
                        task = asyncio.create_task(
                            self.test_endpoint(session, endpoint)
                        )
                        tasks.append(task)
                
                # 清理完成的任务
                tasks = [t for t in tasks if not t.done()]
                await asyncio.sleep(0.1)
            
            # 等待所有任务完成
            await asyncio.gather(*tasks, return_exceptions=True)
```

### 8.2 性能基准

```python
class PerformanceBenchmark:
    def __init__(self):
        self.benchmarks = {
            'entity_extraction': {'target': 100, 'unit': 'entities/second'},
            'graph_query': {'target': 50, 'unit': 'queries/second'},
            'vector_search': {'target': 200, 'unit': 'searches/second'},
            'document_processing': {'target': 10, 'unit': 'documents/second'}
        }
    
    async def run_benchmark(self, operation: str, test_data: list):
        start_time = time.time()
        
        if operation == 'entity_extraction':
            results = await self.benchmark_entity_extraction(test_data)
        elif operation == 'graph_query':
            results = await self.benchmark_graph_query(test_data)
        # ... 其他基准测试
        
        duration = time.time() - start_time
        throughput = len(test_data) / duration
        
        target = self.benchmarks[operation]['target']
        unit = self.benchmarks[operation]['unit']
        
        print(f"{operation}: {throughput:.2f} {unit} (target: {target} {unit})")
        
        return {
            'operation': operation,
            'throughput': throughput,
            'target': target,
            'passed': throughput >= target
        }
```

## 9. 故障排除和调优指南

### 9.1 常见性能问题

1. **数据库连接池耗尽**
   - 症状：连接超时错误
   - 解决：增加连接池大小，优化查询，添加连接监控

2. **内存泄漏**
   - 症状：内存使用持续增长
   - 解决：使用内存分析工具，检查缓存策略，定期GC

3. **CPU使用率过高**
   - 症状：响应时间增加，系统负载高
   - 解决：优化算法，使用异步处理，增加实例数量

### 9.2 调优检查清单

- [ ] 数据库索引是否合适
- [ ] 缓存命中率是否达标(>80%)
- [ ] 连接池配置是否合理
- [ ] 异步处理是否正确实现
- [ ] 资源限制是否合适
- [ ] 监控指标是否正常
- [ ] 日志级别是否合适
- [ ] 垃圾回收是否频繁

## 10. 总结

本性能优化策略涵盖了企业知识库系统的各个层面，从数据库到应用层，从缓存到监控。通过实施这些优化措施，系统能够：

- 支持高并发访问（1000+ 并发用户）
- 实现低延迟响应（P95 < 500ms）
- 保证高可用性（99.9% uptime）
- 提供可扩展性（水平扩展能力）

定期评估和调整这些策略，确保系统性能始终满足业务需求。