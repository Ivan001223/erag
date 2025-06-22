# 监控和运维指南

## 概述

本文档详细说明了智能知识库系统的监控配置、指标收集、告警设置和运维最佳实践。

## 监控架构

### 监控组件
```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  应用服务   │───▶│ Prometheus  │───▶│   Grafana   │
│  (Metrics)  │    │ (时序数据库) │    │  (可视化)   │
└─────────────┘    └─────────────┘    └─────────────┘
       │                   │                   │
       ▼                   ▼                   ▼
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Jaeger    │    │ AlertManager│    │  Grafana    │
│ (分布式追踪) │    │  (告警管理)  │    │ (告警通知)  │
└─────────────┘    └─────────────┘    └─────────────┘
```

## Prometheus配置

### 基础配置
```yaml
# prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  - "alert_rules.yml"

alerting:
  alertmanagers:
    - static_configs:
        - targets:
          - alertmanager:9093

scrape_configs:
  - job_name: 'knowledge-system'
    static_configs:
      - targets: ['app:8000']
    metrics_path: '/metrics'
    scrape_interval: 10s

  - job_name: 'neo4j'
    static_configs:
      - targets: ['neo4j:2004']

  - job_name: 'redis'
    static_configs:
      - targets: ['redis:6379']

  - job_name: 'postgres'
    static_configs:
      - targets: ['postgres:5432']

  - job_name: 'node-exporter'
    static_configs:
      - targets: ['node-exporter:9100']
```

### 告警规则
```yaml
# alert_rules.yml
groups:
  - name: application
    rules:
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.05
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "应用错误率过高"
          description: "错误率超过5%，当前值: {{ $value }}"

      - alert: HighResponseTime
        expr: histogram_quantile(0.95, http_request_duration_seconds_bucket) > 2
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "响应时间过长"
          description: "95%响应时间超过2秒"

      - alert: HighMemoryUsage
        expr: (node_memory_MemTotal_bytes - node_memory_MemAvailable_bytes) / node_memory_MemTotal_bytes > 0.8
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "内存使用率过高"
          description: "内存使用率超过80%"

      - alert: DatabaseConnectionFailure
        expr: up{job="neo4j"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "数据库连接失败"
          description: "Neo4j数据库无法连接"
```

## Grafana仪表板

### 应用监控仪表板
```json
{
  "dashboard": {
    "id": null,
    "title": "知识库系统监控",
    "panels": [
      {
        "title": "HTTP请求量",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(http_requests_total[5m])",
            "legendFormat": "{{method}} {{endpoint}}"
          }
        ]
      },
      {
        "title": "响应时间",
        "type": "graph", 
        "targets": [
          {
            "expr": "histogram_quantile(0.95, http_request_duration_seconds_bucket)",
            "legendFormat": "95th percentile"
          },
          {
            "expr": "histogram_quantile(0.50, http_request_duration_seconds_bucket)",
            "legendFormat": "50th percentile"
          }
        ]
      },
      {
        "title": "错误率",
        "type": "singlestat",
        "targets": [
          {
            "expr": "rate(http_requests_total{status=~\"5..\"}[5m]) / rate(http_requests_total[5m])",
            "legendFormat": "Error Rate"
          }
        ]
      }
    ]
  }
}
```

### 系统资源仪表板
```json
{
  "dashboard": {
    "title": "系统资源监控",
    "panels": [
      {
        "title": "CPU使用率",
        "type": "graph",
        "targets": [
          {
            "expr": "100 - (avg by (instance) (rate(node_cpu_seconds_total{mode=\"idle\"}[5m])) * 100)",
            "legendFormat": "{{instance}}"
          }
        ]
      },
      {
        "title": "内存使用率",
        "type": "graph",
        "targets": [
          {
            "expr": "(node_memory_MemTotal_bytes - node_memory_MemAvailable_bytes) / node_memory_MemTotal_bytes * 100",
            "legendFormat": "Memory Usage"
          }
        ]
      },
      {
        "title": "磁盘I/O",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(node_disk_read_bytes_total[5m])",
            "legendFormat": "Read {{device}}"
          },
          {
            "expr": "rate(node_disk_written_bytes_total[5m])",
            "legendFormat": "Write {{device}}"
          }
        ]
      }
    ]
  }
}
```

## Jaeger分布式追踪

### 配置
```yaml
# jaeger.yml
apiVersion: jaegertracing.io/v1
kind: Jaeger
metadata:
  name: knowledge-system-jaeger
spec:
  strategy: production
  storage:
    type: elasticsearch  # 用于日志存储，非主要搜索引擎
    elasticsearch:
      nodeCount: 3
      storage:
        size: 100Gi
  collector:
    maxReplicas: 5
    resources:
      limits:
        cpu: 100m
        memory: 128Mi
  query:
    replicas: 3
    resources:
      limits:
        cpu: 100m
        memory: 128Mi
```

### 追踪配置
```python
# backend/middleware/tracing.py
JAEGER_CONFIG = {
    "service_name": "knowledge-system",
    "agent_host_name": "jaeger-agent",
    "agent_port": 6831,
    "collector_endpoint": "http://jaeger-collector:14268/api/traces",
    "sampling": {
        "type": "probabilistic",
        "param": 0.1  # 10%采样率
    },
    "logging": True,
    "local_agent_reporting_host": "jaeger-agent",
    "local_agent_reporting_port": 6832,
}
```

## 日志管理

### 日志配置
```python
# logging.yml
version: 1
disable_existing_loggers: false

formatters:
  standard:
    format: "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
  json:
    format: '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "logger": "%(name)s", "message": "%(message)s"}'

handlers:
  console:
    class: logging.StreamHandler
    level: INFO
    formatter: standard
    stream: ext://sys.stdout

  file:
    class: logging.handlers.RotatingFileHandler
    level: INFO
    formatter: json
    filename: /var/log/knowledge-system/app.log
    maxBytes: 10485760  # 10MB
    backupCount: 10

  error_file:
    class: logging.handlers.RotatingFileHandler
    level: ERROR
    formatter: json
    filename: /var/log/knowledge-system/error.log
    maxBytes: 10485760
    backupCount: 10

loggers:
  "":
    level: INFO
    handlers: [console, file]
    propagate: false

  error:
    level: ERROR
    handlers: [error_file]
    propagate: false
```

### ELK Stack配置
```yaml
# elasticsearch.yml (仅用于日志存储)
cluster.name: knowledge-system-logs
network.host: 0.0.0.0
discovery.type: single-node
xpack.security.enabled: false

# logstash.conf
input {
  beats {
    port => 5044
  }
}

filter {
  if [fields][service] == "knowledge-system" {
    json {
      source => "message"
    }
    
    date {
      match => [ "timestamp", "yyyy-MM-dd HH:mm:ss,SSS" ]
    }
    
    mutate {
      add_field => { "service" => "knowledge-system" }
    }
  }
}

output {
  elasticsearch {  # 日志输出到Elasticsearch
    hosts => ["elasticsearch:9200"]
    index => "knowledge-system-logs-%{+YYYY.MM.dd}"
  }
}

# kibana.yml
server.host: 0.0.0.0
elasticsearch.hosts: ["http://elasticsearch:9200"]
```

## 健康检查

### 应用健康检查
```python
# backend/api/health.py
@router.get("/health")
async def health_check():
    """基础健康检查"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "2.0.0"
    }

@router.get("/health/detailed")
async def detailed_health_check():
    """详细健康检查"""
    checks = {}
    
    # 数据库连接检查
    try:
        await database.execute("SELECT 1")
        checks["database"] = {"status": "healthy"}
    except Exception as e:
        checks["database"] = {"status": "unhealthy", "error": str(e)}
    
    # Neo4j连接检查
    try:
        await neo4j_client.verify_connectivity()
        checks["neo4j"] = {"status": "healthy"}
    except Exception as e:
        checks["neo4j"] = {"status": "unhealthy", "error": str(e)}
    
    # Redis连接检查
    try:
        await redis_client.ping()
        checks["redis"] = {"status": "healthy"}
    except Exception as e:
        checks["redis"] = {"status": "unhealthy", "error": str(e)}
    
    overall_status = "healthy" if all(
        check["status"] == "healthy" for check in checks.values()
    ) else "unhealthy"
    
    return {
        "status": overall_status,
        "checks": checks,
        "timestamp": datetime.utcnow().isoformat()
    }
```

### Kubernetes健康检查
```yaml
# k8s/deployment.yml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: knowledge-system
spec:
  template:
    spec:
      containers:
      - name: app
        image: knowledge-system:latest
        ports:
        - containerPort: 8000
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 3
        readinessProbe:
          httpGet:
            path: /health/readiness
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
          timeoutSeconds: 3
          failureThreshold: 3
```

## 性能监控

### 关键指标
```python
# 应用性能指标
APPLICATION_METRICS = {
    # HTTP指标
    "http_requests_total": "HTTP请求总数",
    "http_request_duration_seconds": "HTTP请求持续时间",
    "http_requests_in_flight": "正在处理的HTTP请求数",
    
    # 业务指标
    "knowledge_entities_total": "知识实体总数",
    "knowledge_relations_total": "知识关系总数", 
    "documents_processed_total": "处理的文档总数",
    "search_queries_total": "搜索查询总数",
    
    # 系统指标
    "python_gc_objects_collected_total": "GC回收对象数",
    "process_resident_memory_bytes": "进程内存使用",
    "process_cpu_seconds_total": "进程CPU时间",
    
    # 数据库指标
    "database_connections_active": "活跃数据库连接数",
    "database_query_duration_seconds": "数据库查询持续时间",
    "neo4j_query_duration_seconds": "Neo4j查询持续时间",
}
```

### SLA指标
```yaml
# SLA定义
service_level_agreements:
  availability:
    target: 99.9%  # 系统可用性目标
    measurement_period: monthly
    
  response_time:
    p95_target: 2s  # 95%请求响应时间
    p99_target: 5s  # 99%请求响应时间
    measurement_period: daily
    
  error_rate:
    target: 0.1%  # 错误率目标
    measurement_period: daily
    
  throughput:
    target: 1000  # 每秒处理请求数
    measurement_period: peak_hours
```

## 告警管理

### AlertManager配置
```yaml
# alertmanager.yml
global:
  smtp_smarthost: 'localhost:587'
  smtp_from: 'alerts@knowledge-system.com'

route:
  group_by: ['alertname']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 1h
  receiver: 'web.hook'
  routes:
  - match:
      severity: critical
    receiver: 'critical-alerts'
  - match:
      severity: warning
    receiver: 'warning-alerts'

receivers:
- name: 'web.hook'
  webhook_configs:
  - url: 'http://webhook:5001/'

- name: 'critical-alerts'
  email_configs:
  - to: 'oncall@company.com'
    subject: '【紧急】知识库系统告警'
    body: |
      告警名称: {{ .GroupLabels.alertname }}
      告警级别: {{ .CommonLabels.severity }}
      告警时间: {{ .CommonAnnotations.timestamp }}
      告警描述: {{ .CommonAnnotations.description }}
  slack_configs:
  - api_url: 'https://hooks.slack.com/services/...'
    channel: '#alerts-critical'
    title: '紧急告警'

- name: 'warning-alerts'
  email_configs:
  - to: 'dev-team@company.com'
    subject: '【警告】知识库系统告警'
```

### 告警分级
```python
ALERT_LEVELS = {
    "INFO": {
        "description": "信息性告警",
        "response_time": "24小时",
        "notification": ["email"],
        "examples": ["系统启动", "配置变更"]
    },
    "WARNING": {
        "description": "警告级告警",
        "response_time": "4小时", 
        "notification": ["email", "slack"],
        "examples": ["性能下降", "资源使用率高"]
    },
    "CRITICAL": {
        "description": "严重告警",
        "response_time": "30分钟",
        "notification": ["email", "slack", "sms"],
        "examples": ["服务不可用", "数据丢失"]
    },
    "EMERGENCY": {
        "description": "紧急告警",
        "response_time": "5分钟",
        "notification": ["email", "slack", "sms", "phone"],
        "examples": ["系统完全故障", "安全事件"]
    }
}
```

## 运维手册

### 日常检查清单
```bash
#!/bin/bash
# 日常运维检查脚本

echo "=== 知识库系统日常检查 ==="
echo "检查时间: $(date)"

# 1. 服务状态检查
echo "1. 检查服务状态..."
docker-compose ps

# 2. 系统资源检查
echo "2. 检查系统资源..."
df -h
free -h
top -bn1 | head -20

# 3. 应用健康检查
echo "3. 检查应用健康状态..."
curl -s http://localhost:8000/health | jq .

# 4. 数据库连接检查
echo "4. 检查数据库连接..."
docker-compose exec postgres pg_isready
docker-compose exec neo4j cypher-shell "RETURN 1"
docker-compose exec redis redis-cli ping

# 5. 日志检查
echo "5. 检查最近错误日志..."
tail -50 /var/log/knowledge-system/error.log

# 6. 备份状态检查
echo "6. 检查备份状态..."
ls -la /backup/ | tail -10

echo "=== 检查完成 ==="
```

### 故障排查指南

#### 服务无法启动
```bash
# 1. 检查容器状态
docker-compose ps

# 2. 查看容器日志
docker-compose logs app

# 3. 检查端口占用
netstat -tlnp | grep :8000

# 4. 检查配置文件
docker-compose config

# 5. 重启服务
docker-compose restart app
```

#### 数据库连接问题
```bash
# 1. 检查数据库状态
docker-compose exec postgres pg_isready
docker-compose exec neo4j cypher-shell "RETURN 1"

# 2. 检查网络连接
docker-compose exec app ping postgres
docker-compose exec app ping neo4j

# 3. 检查配置
docker-compose exec app env | grep DATABASE
docker-compose exec app env | grep NEO4J

# 4. 重启数据库
docker-compose restart postgres neo4j
```

#### 性能问题排查
```bash
# 1. 检查系统资源
htop
iotop
nethogs

# 2. 检查应用指标
curl http://localhost:8000/metrics

# 3. 检查数据库性能
docker-compose exec postgres psql -c "SELECT * FROM pg_stat_activity;"

# 4. 检查慢查询
tail -f /var/log/postgresql/postgresql.log | grep "slow query"
```

### 扩容指南

#### 水平扩容
```bash
# 1. 扩展应用实例
docker-compose up -d --scale app=3

# 2. 配置负载均衡
# 更新nginx配置，添加新实例

# 3. 验证负载分布
for i in {1..10}; do
  curl -s http://localhost/health | jq .instance_id
done
```

#### 垂直扩容
```yaml
# docker-compose.yml
services:
  app:
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 4G
        reservations:
          cpus: '1.0'
          memory: 2G
```

### 备份和恢复

#### 自动备份脚本
```bash
#!/bin/bash
# 自动备份脚本

BACKUP_DIR="/backup/$(date +%Y%m%d_%H%M%S)"
mkdir -p $BACKUP_DIR

# 1. 数据库备份
echo "备份PostgreSQL..."
docker-compose exec -T postgres pg_dump -U postgres knowledge_db > $BACKUP_DIR/postgres.sql

echo "备份Neo4j..."
docker-compose exec -T neo4j neo4j-admin dump --database=neo4j --to=/tmp/neo4j.dump
docker cp $(docker-compose ps -q neo4j):/tmp/neo4j.dump $BACKUP_DIR/

# 2. 文件备份
echo "备份上传文件..."
tar -czf $BACKUP_DIR/uploads.tar.gz uploads/

# 3. 配置备份
echo "备份配置文件..."
cp -r config/ $BACKUP_DIR/

# 4. 压缩备份
echo "压缩备份文件..."
tar -czf $BACKUP_DIR.tar.gz -C $(dirname $BACKUP_DIR) $(basename $BACKUP_DIR)
rm -rf $BACKUP_DIR

echo "备份完成: $BACKUP_DIR.tar.gz"
```

#### 恢复脚本
```bash
#!/bin/bash
# 数据恢复脚本

BACKUP_FILE=$1
if [ -z "$BACKUP_FILE" ]; then
    echo "使用方法: $0 <backup_file>"
    exit 1
fi

# 1. 解压备份
BACKUP_DIR="/tmp/restore_$(date +%s)"
mkdir -p $BACKUP_DIR
tar -xzf $BACKUP_FILE -C $BACKUP_DIR

# 2. 停止服务
docker-compose down

# 3. 恢复数据库
echo "恢复PostgreSQL..."
docker-compose up -d postgres
sleep 10
docker-compose exec -T postgres psql -U postgres -c "DROP DATABASE IF EXISTS knowledge_db;"
docker-compose exec -T postgres psql -U postgres -c "CREATE DATABASE knowledge_db;"
docker-compose exec -T postgres psql -U postgres knowledge_db < $BACKUP_DIR/*/postgres.sql

echo "恢复Neo4j..."
docker-compose up -d neo4j
sleep 10
docker cp $BACKUP_DIR/*/neo4j.dump $(docker-compose ps -q neo4j):/tmp/
docker-compose exec neo4j neo4j-admin load --from=/tmp/neo4j.dump --database=neo4j --force

# 4. 恢复文件
echo "恢复上传文件..."
tar -xzf $BACKUP_DIR/*/uploads.tar.gz

# 5. 启动服务
docker-compose up -d

# 6. 清理
rm -rf $BACKUP_DIR

echo "恢复完成"
```

## 监控最佳实践

### 指标命名规范
```python
# 指标命名约定
METRIC_NAMING_CONVENTIONS = {
    "prefix": "knowledge_system_",  # 系统前缀
    "format": "snake_case",         # 使用下划线
    "units": {
        "time": "_seconds",         # 时间使用秒
        "size": "_bytes",          # 大小使用字节
        "rate": "_per_second",     # 速率每秒
        "count": "_total"          # 计数使用total后缀
    }
}

# 示例指标
EXAMPLE_METRICS = {
    "knowledge_system_http_requests_total": "HTTP请求总数",
    "knowledge_system_http_request_duration_seconds": "HTTP请求持续时间",
    "knowledge_system_database_connections_active": "活跃数据库连接数",
    "knowledge_system_documents_processed_total": "处理文档总数"
}
```

### 告警设计原则
1. **可操作性**: 每个告警都应该对应具体的处理动作
2. **相关性**: 告警应该与业务影响直接相关
3. **及时性**: 告警应该在问题影响用户前触发
4. **准确性**: 减少误报，提高告警质量
5. **分级性**: 根据严重程度分级处理

### 仪表板设计
1. **分层设计**: 概览 → 详细 → 调试
2. **用户导向**: 面向不同角色设计不同视图
3. **实时性**: 关键指标实时更新
4. **可读性**: 清晰的图表和标签
5. **可操作性**: 提供快速跳转和深入分析能力 