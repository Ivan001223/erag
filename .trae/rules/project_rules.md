# 企业知识库系统 - Cursor 规则

## 项目结构

```
erag/
├── TASK_LIST.md                   # 任务跟踪和进度
├── README.md                      # 项目文档
├── docker-compose.yml             # Docker 编排
├── .env.example                   # 环境变量模板
├── requirements.txt               # Python 依赖
├── package.json                   # Node.js 依赖（前端用）
│
├── backend/                       # 后端服务
│   ├── __init__.py
│   ├── main.py                   # FastAPI 主应用
│   ├── config/                   # 配置管理
│   │   ├── __init__.py
│   │   ├── settings.py           # 设置和环境配置
│   │   └── constants.py          # 系统常量
│   │
│   ├── core/                     # 核心业务逻辑
│   │   ├── __init__.py
│   │   ├── knowledge_graph/      # 知识图谱管理
│   │   │   ├── __init__.py
│   │   │   ├── entity_extractor.py
│   │   │   ├── relation_extractor.py
│   │   │   ├── graph_builder.py
│   │   │   ├── community_detector.py
│   │   │   ├── confidence_validator.py
│   │   │   └── kg_query_engine.py
│   │   │
│   │   ├── etl/                  # ETL 和数据处理
│   │   │   ├── __init__.py
│   │   │   ├── task_generator.py
│   │   │   ├── flink_manager.py
│   │   │   ├── cdc_manager.py
│   │   │   └── data_structurer.py
│   │   │
│   │   ├── ocr/                  # OCR 处理
│   │   │   ├── __init__.py
│   │   │   ├── ocr_service.py
│   │   │   ├── document_processor.py
│   │   │   ├── table_extractor.py
│   │   │   └── quality_assurance.py
│   │   │
│   │   ├── vector/               # 向量存储和搜索
│   │   │   ├── __init__.py
│   │   │   ├── embedder.py
│   │   │   ├── vector_store.py
│   │   │   └── similarity_search.py
│   │   │
│   │   └── llm/                  # LLM 集成
│   │       ├── __init__.py
│   │       ├── llm_orchestrator.py
│   │       ├── prompt_manager.py
│   │       └── model_registry.py
│   │
│   ├── api/                      # API 端点
│   │   ├── __init__.py
│   │   ├── v1/
│   │   │   ├── __init__.py
│   │   │   ├── knowledge_routes.py
│   │   │   ├── graph_routes.py
│   │   │   ├── etl_routes.py
│   │   │   ├── ocr_routes.py
│   │   │   └── dify_routes.py
│   │   └── deps.py               # API 依赖
│   │
│   ├── models/                   # 数据模型
│   │   ├── __init__.py
│   │   ├── entity.py
│   │   ├── relation.py
│   │   ├── document.py
│   │   └── task.py
│   │
│   ├── schemas/                  # Pydantic 模式
│   │   ├── __init__.py
│   │   ├── entity_schema.py
│   │   ├── relation_schema.py
│   │   ├── query_schema.py
│   │   └── response_schema.py
│   │
│   ├── connectors/               # 外部系统连接器
│   │   ├── __init__.py
│   │   ├── starrocks_client.py
│   │   ├── neo4j_client.py
│   │   ├── flink_client.py
│   │   ├── redis_client.py
│   │   └── minio_client.py
│   │
│   ├── utils/                    # 工具函数
│   │   ├── __init__.py
│   │   ├── cache.py
│   │   ├── logger.py
│   │   ├── metrics.py
│   │   └── validators.py
│   │
│   └── tests/                    # 单元测试
│       ├── __init__.py
│       ├── test_knowledge_graph/
│       ├── test_etl/
│       ├── test_ocr/
│       └── test_api/
│
├── ocr_service/                  # 独立 OCR 服务
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py
│   └── onnx_models/              # OnnxOCR 模型
│
├── frontend/                     # Web UI (Vue.js)
│   ├── public/
│   ├── src/
│   │   ├── components/
│   │   ├── views/
│   │   ├── stores/
│   │   ├── api/
│   │   └── utils/
│   ├── package.json
│   └── vite.config.js
│
├── scripts/                      # 工具脚本
│   ├── init_db.py               # 数据库初始化
│   ├── migrate.py               # 数据库迁移
│   └── seed_data.py             # 示例数据填充
│
├── deployments/                  # 部署配置
│   ├── kubernetes/              # K8s 清单
│   │   ├── namespace.yaml
│   │   ├── configmap.yaml
│   │   ├── secrets.yaml
│   │   ├── deployments/
│   │   └── services/
│   └── docker/                  # Docker 配置
│       ├── backend.Dockerfile
│       ├── ocr.Dockerfile
│       └── frontend.Dockerfile
│
└── docs/                        # 文档
    ├── api/                     # API 文档
    ├── architecture/            # 架构图
    └── guides/                  # 用户指南
```

## 代码生成规则

### 1. 文件放置规则

- **始终**按照上述结构将文件放在正确的目录中
- **绝不**在根目录中创建文件，除了配置文件
- **始终**在新的 Python 目录中创建 `__init__.py` 文件

### 2. 命名约定

#### Python 文件

- 文件名使用下划线命名法：`entity_extractor.py`
- 类使用帕斯卡命名法：`EntityExtractor`
- 函数/方法使用下划线命名法：`extract_entities()`
- 常量使用大写下划线命名法：`MAX_RETRIES`

#### API 路由

- 所有路由使用版本前缀：`/api/v1/`
- URL 使用短横线命名法：`/api/v1/knowledge-graph/entities`
- 集合使用复数名词：`/entities`、`/relations`

### 3. 代码组织规则

#### 导入

```python
# 标准库导入优先
import os
import sys
from datetime import datetime

# 第三方导入
import numpy as np
from fastapi import FastAPI

# 本地导入
from backend.core.knowledge_graph import EntityExtractor
from backend.utils.logger import get_logger
```

#### 类结构

```python
class ServiceName:
    """
    服务的简要描述。
    
    属性:
        attribute1: 描述
        attribute2: 描述
    """
    
    def __init__(self):
        """使用必需的依赖项初始化服务。"""
        pass
    
    async def public_method(self):
        """公共方法已文档化。"""
        pass
    
    def _private_method(self):
        """私有方法以下划线开头。"""
        pass
```

### 4. API 端点规则

```python
# 在 api/v1/knowledge_routes.py 中
from fastapi import APIRouter, Depends, HTTPException
from typing import List

router = APIRouter(prefix="/knowledge", tags=["knowledge"])

@router.post("/entities", response_model=EntityResponse)
async def create_entity(
    entity: EntityCreate,
    kg_service: KnowledgeGraphService = Depends(get_kg_service)
):
    """
    在知识图谱中创建新实体。
    
    参数:
        entity: 实体创建模式
        kg_service: 注入的知识图谱服务
        
    返回:
        带有 ID 的已创建实体
    """
    pass
```

### 5. 错误处理

```python
# 在 core/exceptions.py 中使用自定义异常
class EntityNotFoundError(Exception):
    pass

class ConflictError(Exception):
    pass

# 在 API 端点中
try:
    result = await service.process()
except EntityNotFoundError:
    raise HTTPException(status_code=404, detail="实体未找到")
except ConflictError as e:
    raise HTTPException(status_code=409, detail=str(e))
```

### 6. 日志规则

```python
from backend.utils.logger import get_logger

logger = get_logger(__name__)

class Service:
    def process(self):
        logger.info(f"开始处理 {item_id}")
        try:
            # 处理
            logger.debug(f"步骤 1 完成")
        except Exception as e:
            logger.error(f"处理失败: {str(e)}", exc_info=True)
            raise
```

### 7. 测试规则

- 将测试放在 `backend/tests/` 中，镜像源结构
- 测试文件必须以 `test_` 开头
- 使用 pytest 进行测试
- 代码覆盖率目标 >80%

```python
# backend/tests/test_knowledge_graph/test_entity_extractor.py
import pytest
from backend.core.knowledge_graph.entity_extractor import EntityExtractor

class TestEntityExtractor:
    @pytest.fixture
    def extractor(self):
        return EntityExtractor()
    
    async def test_extract_entities(self, extractor):
        # 测试实现
        pass
```

### 8. 配置管理

```python
# backend/config/settings.py
from pydantic import BaseSettings

class Settings(BaseSettings):
    # 数据库
    neo4j_url: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str
    
    # StarRocks
    starrocks_host: str = "localhost"
    starrocks_port: int = 9030
    
    class Config:
        env_file = ".env"
```

### 9. 异步/等待规则

- 对所有 I/O 操作使用 `async/await`
- 不要混合同步和异步代码
- 使用 `asyncio.gather()` 进行并发操作

```python
async def process_batch(items: List[str]):
    tasks = [process_item(item) for item in items]
    results = await asyncio.gather(*tasks)
    return results
```

### 10. 文档规则

- 所有公共 API 必须有文档字符串
- 使用 Google 风格的文档字符串
- 为所有参数和返回值包含类型提示

```python
def calculate_confidence(
    entity: Entity,
    context: Dict[str, Any]
) -> float:
    """
    计算实体的置信度分数。
    
    参数:
        entity: 要评估的实体
        context: 计算的附加上下文
        
    返回:
        0 到 1 之间的置信度分数
        
    异常:
        ValueError: 如果实体无效
    """
    pass
```

## 任务管理规则

### 任务列表位置

- 主要任务列表：项目根目录中的 `TASK_LIST.md`
- 每次任务完成后更新状态
- 使用复选框进行跟踪：`- [ ]`（待定）、`- [x]`（已完成）

### 任务状态格式

```markdown
## 任务列表

### 阶段 1：基础设施设置
- [x] 初始化项目结构 (100%)
- [x] 设置 Docker 环境 (100%)
- [ ] 配置数据平台连接器 (60%)
  - [x] StarRocks 连接器
  - [x] Neo4j 连接器
  - [ ] Flink 连接器
  - [ ] MinIO 连接器
```

### 提交消息格式

```
feat(模块): 添加实体提取服务

- 实现 EntityExtractor 类
- 添加置信度评分
- 更新任务进度：实体提取 (100%)
```

## 开发工作流程

1. **开始任务之前：**
   - 检查 TASK_LIST.md 获取下一个待定任务
   - 创建功能分支：`feature/task-name`

2. **开发期间：**
   - 将文件放在正确的目录中
   - 遵循命名约定
   - 编写测试与代码

3. **完成任务后：**
   - 在 TASK_LIST.md 中更新任务状态
   - 创建描述性提交
   - 如需要则更新文档

## 常见模式

### 服务模式

```python
# backend/core/knowledge_graph/entity_service.py
class EntityService:
    def __init__(self, neo4j_client: Neo4jClient, llm_service: LLMService):
        self.neo4j = neo4j_client
        self.llm = llm_service
        self.logger = get_logger(__name__)
    
    async def create_entity(self, entity_data: Dict) -> Entity:
        # 实现
        pass
```

### 存储库模式

```python
# backend/repositories/entity_repository.py
class EntityRepository:
    def __init__(self, neo4j_client: Neo4jClient):
        self.client = neo4j_client
    
    async def find_by_id(self, entity_id: str) -> Optional[Entity]:
        # 实现
        pass
```

### 工厂模式

```python
# backend/factories/connector_factory.py
class ConnectorFactory:
    @staticmethod
    def create_connector(connector_type: str) -> BaseConnector:
        if connector_type == "neo4j":
            return Neo4jConnector()
        # 其他连接器
```

## 环境变量

必需的环境变量（放在 `.env` 中）：

```env
# 数据库
NEO4J_URL=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password

# StarRocks
STARROCKS_HOST=localhost
STARROCKS_PORT=9030
STARROCKS_USER=root
STARROCKS_PASSWORD=

# Redis
REDIS_URL=redis://localhost:6379

# MinIO
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin

# LLM
LLM_API_KEY=your_api_key
LLM_MODEL=qwen-max

# OCR
OCR_SERVICE_URL=http://localhost:8002
```

## 记住

1. **始终**在创建前检查文件放置
2. **始终**在完成任务后更新 TASK_LIST.md
3. **绝不**提交敏感数据或凭据
4. **始终**为新功能编写测试
5. **遵循**已建立的模式和约定