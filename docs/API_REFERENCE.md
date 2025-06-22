# API 参考文档

## 概述

智能知识库系统提供了完整的RESTful API，支持知识管理、搜索、用户认证等功能。

### 基础信息
- **Base URL**: `https://api.knowledge-system.com`
- **API版本**: `v1`
- **认证方式**: Bearer Token (JWT)
- **数据格式**: JSON
- **字符编码**: UTF-8

### 通用响应格式
```json
{
  "success": true,
  "data": {},
  "message": "操作成功",
  "timestamp": "2024-01-15T10:30:00Z",
  "request_id": "req_123456789"
}
```

### 错误响应格式
```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "输入参数验证失败",
    "details": {
      "field": "name",
      "reason": "字段不能为空"
    }
  },
  "timestamp": "2024-01-15T10:30:00Z",
  "request_id": "req_123456789"
}
```

## 认证接口

### 用户登录
获取访问令牌进行API认证。

```http
POST /auth/login
Content-Type: application/json

{
  "username": "admin",
  "password": "password"
}
```

**响应示例**:
```json
{
  "success": true,
  "data": {
    "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "token_type": "bearer",
    "expires_in": 1800,
    "user": {
      "id": "user_123",
      "username": "admin",
      "roles": ["admin"],
      "permissions": ["*"]
    }
  }
}
```

### 刷新令牌
使用刷新令牌获取新的访问令牌。

```http
POST /auth/refresh
Authorization: Bearer <refresh_token>
```

### 用户注销
撤销当前访问令牌。

```http
POST /auth/logout
Authorization: Bearer <access_token>
```

## 实体管理

### 创建实体
创建新的知识实体。

```http
POST /api/v1/entities
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "name": "张三",
  "entity_type": "PERSON",
  "description": "高级软件工程师",
  "properties": {
    "department": "技术部",
    "level": "P7",
    "email": "zhangsan@company.com"
  },
  "confidence": "HIGH"
}
```

**参数说明**:
- `name` (string, required): 实体名称
- `entity_type` (string, required): 实体类型，可选值: PERSON, ORGANIZATION, LOCATION, CONCEPT, EVENT, PRODUCT
- `description` (string, optional): 实体描述
- `properties` (object, optional): 实体属性键值对
- `confidence` (string, optional): 置信度，可选值: LOW, MEDIUM, HIGH

**响应示例**:
```json
{
  "success": true,
  "data": {
    "id": "entity_123456",
    "name": "张三",
    "entity_type": "PERSON",
    "description": "高级软件工程师",
    "properties": {
      "department": "技术部",
      "level": "P7",
      "email": "zhangsan@company.com"
    },
    "confidence": "HIGH",
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-15T10:30:00Z"
  }
}
```

### 获取实体详情
根据ID获取实体详细信息。

```http
GET /api/v1/entities/{entity_id}
Authorization: Bearer <access_token>
```

### 更新实体
更新现有实体信息。

```http
PUT /api/v1/entities/{entity_id}
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "description": "资深软件工程师",
  "properties": {
    "level": "P8"
  }
}
```

### 删除实体
删除指定实体。

```http
DELETE /api/v1/entities/{entity_id}
Authorization: Bearer <access_token>
```

### 搜索实体
根据条件搜索实体。

```http
GET /api/v1/entities/search?q=张三&entity_type=PERSON&limit=20&offset=0
Authorization: Bearer <access_token>
```

**查询参数**:
- `q` (string, optional): 搜索关键词
- `entity_type` (string, optional): 实体类型过滤
- `confidence` (string, optional): 置信度过滤
- `limit` (integer, optional): 返回数量限制，默认20，最大100
- `offset` (integer, optional): 偏移量，默认0

**响应示例**:
```json
{
  "success": true,
  "data": {
    "entities": [
      {
        "id": "entity_123456",
        "name": "张三",
        "entity_type": "PERSON",
        "description": "高级软件工程师",
        "score": 0.95
      }
    ],
    "total": 1,
    "limit": 20,
    "offset": 0
  }
}
```

### 获取实体关系
获取实体的关联关系。

```http
GET /api/v1/entities/{entity_id}/relations?direction=both&limit=50
Authorization: Bearer <access_token>
```

**查询参数**:
- `direction` (string, optional): 关系方向，可选值: incoming, outgoing, both，默认both
- `relation_type` (string, optional): 关系类型过滤
- `limit` (integer, optional): 返回数量限制，默认50

## 关系管理

### 创建关系
创建实体间的关系。

```http
POST /api/v1/relations
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "source_entity_id": "entity_123456",
  "target_entity_id": "entity_789012",
  "relation_type": "WORKS_FOR",
  "properties": {
    "start_date": "2020-01-01",
    "position": "高级工程师"
  },
  "confidence": "HIGH"
}
```

**参数说明**:
- `source_entity_id` (string, required): 源实体ID
- `target_entity_id` (string, required): 目标实体ID
- `relation_type` (string, required): 关系类型
- `properties` (object, optional): 关系属性
- `confidence` (string, optional): 置信度

### 获取关系详情
```http
GET /api/v1/relations/{relation_id}
Authorization: Bearer <access_token>
```

### 更新关系
```http
PUT /api/v1/relations/{relation_id}
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "properties": {
    "position": "资深工程师"
  }
}
```

### 删除关系
```http
DELETE /api/v1/relations/{relation_id}
Authorization: Bearer <access_token>
```

## 文档管理

### 上传文档
上传文档文件进行处理。

```http
POST /api/v1/documents
Authorization: Bearer <access_token>
Content-Type: multipart/form-data

file: <document_file>
title: "技术规范文档"
category: "技术文档"
description: "系统架构技术规范"
```

**参数说明**:
- `file` (file, required): 文档文件，支持PDF、DOC、DOCX、TXT等格式
- `title` (string, optional): 文档标题
- `category` (string, optional): 文档分类
- `description` (string, optional): 文档描述

**响应示例**:
```json
{
  "success": true,
  "data": {
    "id": "doc_123456",
    "title": "技术规范文档",
    "filename": "tech_spec.pdf",
    "size": 1024000,
    "category": "技术文档",
    "description": "系统架构技术规范",
    "status": "uploaded",
    "created_at": "2024-01-15T10:30:00Z"
  }
}
```

### 获取文档列表
```http
GET /api/v1/documents?category=技术文档&status=processed&limit=20&offset=0
Authorization: Bearer <access_token>
```

### 获取文档详情
```http
GET /api/v1/documents/{document_id}
Authorization: Bearer <access_token>
```

### 提取文档知识
从文档中提取实体和关系。

```http
POST /api/v1/documents/{document_id}/extract
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "extract_entities": true,
  "extract_relations": true,
  "auto_save": true
}
```

**响应示例**:
```json
{
  "success": true,
  "data": {
    "task_id": "task_123456",
    "status": "processing",
    "estimated_time": 300
  }
}
```

### 获取提取结果
```http
GET /api/v1/documents/{document_id}/extract/{task_id}
Authorization: Bearer <access_token>
```

## 搜索接口

### 综合搜索
执行综合搜索，包括实体、关系和文档。

```http
GET /api/v1/search?q=人工智能&type=all&limit=20
Authorization: Bearer <access_token>
```

**查询参数**:
- `q` (string, required): 搜索关键词
- `type` (string, optional): 搜索类型，可选值: entities, relations, documents, all，默认all
- `limit` (integer, optional): 返回数量限制
- `include_similarity` (boolean, optional): 是否包含相似度分数

### 语义搜索
基于向量相似度的语义搜索。

```http
POST /api/v1/search/semantic
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "query": "机器学习算法",
  "top_k": 10,
  "threshold": 0.7,
  "entity_types": ["CONCEPT", "TECHNOLOGY"]
}
```

### 图谱查询
使用Cypher语言查询知识图谱。

```http
POST /api/v1/search/graph
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "cypher": "MATCH (p:PERSON)-[r:WORKS_FOR]->(o:ORGANIZATION) WHERE p.name CONTAINS '张' RETURN p, r, o LIMIT 10",
  "parameters": {}
}
```

## 知识图谱

### 获取图谱统计
```http
GET /api/v1/graph/stats
Authorization: Bearer <access_token>
```

**响应示例**:
```json
{
  "success": true,
  "data": {
    "node_count": 10000,
    "relationship_count": 25000,
    "entity_types": {
      "PERSON": 3000,
      "ORGANIZATION": 1500,
      "CONCEPT": 4000,
      "LOCATION": 1500
    },
    "relation_types": {
      "WORKS_FOR": 2500,
      "LOCATED_IN": 3000,
      "RELATED_TO": 15000,
      "PART_OF": 4500
    }
  }
}
```

### 获取子图
获取指定实体周围的子图。

```http
GET /api/v1/graph/subgraph/{entity_id}?depth=2&limit=100
Authorization: Bearer <access_token>
```

### 路径查询
查找两个实体间的路径。

```http
GET /api/v1/graph/path?source={source_id}&target={target_id}&max_depth=5
Authorization: Bearer <access_token>
```

## 用户管理

### 获取用户信息
```http
GET /api/v1/users/me
Authorization: Bearer <access_token>
```

### 更新用户信息
```http
PUT /api/v1/users/me
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "email": "new_email@company.com",
  "display_name": "新昵称"
}
```

### 修改密码
```http
POST /api/v1/users/me/change-password
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "current_password": "old_password",
  "new_password": "new_password"
}
```

## 系统管理

### 健康检查
```http
GET /health
```

**响应示例**:
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00Z",
  "version": "2.0.0",
  "uptime": 86400
}
```

### 详细健康状态
```http
GET /health/detailed
Authorization: Bearer <access_token>
```

### 系统指标
```http
GET /metrics
Authorization: Bearer <access_token>
```

### 备份管理
```http
# 创建备份
POST /admin/backup
Authorization: Bearer <admin_token>
Content-Type: application/json

{
  "backup_type": "full",
  "description": "定期备份",
  "compression": true
}

# 获取备份列表
GET /admin/backups
Authorization: Bearer <admin_token>

# 恢复备份
POST /admin/restore
Authorization: Bearer <admin_token>
Content-Type: application/json

{
  "backup_id": "backup_20240115_103000",
  "dry_run": false
}
```

## 错误代码

### 通用错误代码
- `400` - VALIDATION_ERROR: 请求参数验证失败
- `401` - UNAUTHORIZED: 未授权访问
- `403` - FORBIDDEN: 权限不足
- `404` - NOT_FOUND: 资源不存在
- `409` - CONFLICT: 资源冲突
- `429` - RATE_LIMIT_EXCEEDED: 请求频率超限
- `500` - INTERNAL_ERROR: 服务器内部错误

### 业务错误代码
- `E001` - ENTITY_NOT_FOUND: 实体不存在
- `E002` - ENTITY_ALREADY_EXISTS: 实体已存在
- `E003` - INVALID_ENTITY_TYPE: 无效的实体类型
- `R001` - RELATION_NOT_FOUND: 关系不存在
- `R002` - INVALID_RELATION_TYPE: 无效的关系类型
- `D001` - DOCUMENT_PROCESSING_FAILED: 文档处理失败
- `D002` - UNSUPPORTED_FILE_FORMAT: 不支持的文件格式
- `S001` - SEARCH_TIMEOUT: 搜索超时
- `S002` - INVALID_CYPHER_QUERY: 无效的Cypher查询

## 限流规则

### 默认限流配置
- **默认用户**: 60 requests/minute, 1000 requests/hour
- **高级用户**: 300 requests/minute, 5000 requests/hour  
- **管理员**: 1000 requests/minute, 20000 requests/hour

### 限流响应头
```http
X-RateLimit-Remaining-Minute: 45
X-RateLimit-Remaining-Hour: 850
X-RateLimit-Remaining-Day: 8500
X-RateLimit-Reset: 1642248600
```

## SDK和示例

### Python SDK
```python
from knowledge_system_client import KnowledgeClient

# 初始化客户端
client = KnowledgeClient(
    base_url="https://api.knowledge-system.com",
    token="your_access_token"
)

# 创建实体
entity = client.entities.create({
    "name": "张三",
    "entity_type": "PERSON",
    "description": "高级工程师"
})

# 搜索实体
results = client.entities.search(q="张三", entity_type="PERSON")

# 上传文档
document = client.documents.upload(
    file_path="./document.pdf",
    title="技术文档"
)

# 提取知识
task = client.documents.extract_knowledge(document.id)
```

### JavaScript SDK
```javascript
import { KnowledgeClient } from '@knowledge-system/client';

const client = new KnowledgeClient({
  baseURL: 'https://api.knowledge-system.com',
  token: 'your_access_token'
});

// 创建实体
const entity = await client.entities.create({
  name: '张三',
  entity_type: 'PERSON',
  description: '高级工程师'
});

// 搜索实体
const results = await client.entities.search({
  q: '张三',
  entity_type: 'PERSON'
});
```

## 最佳实践

### 认证和安全
1. 使用HTTPS进行所有API调用
2. 定期轮换访问令牌
3. 不要在客户端代码中硬编码令牌
4. 实施适当的权限控制

### 性能优化
1. 使用分页避免大量数据传输
2. 利用缓存减少重复请求
3. 批量操作代替单个请求
4. 合理设置请求超时时间

### 错误处理
1. 检查响应状态码和错误信息
2. 实施指数退避重试策略
3. 记录详细的错误日志
4. 为用户提供友好的错误提示

### 数据质量
1. 验证输入数据的完整性
2. 使用合适的置信度级别
3. 定期清理和更新数据
4. 监控数据质量指标 