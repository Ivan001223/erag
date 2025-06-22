"""测试配置文件

提供测试套件的通用配置、fixtures和工具函数。
"""

import asyncio
import pytest
import pytest_asyncio
from typing import Dict, Any, AsyncGenerator, Generator
from unittest.mock import Mock, AsyncMock
from pathlib import Path
import tempfile
import shutil

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.main import app
from backend.config.settings import get_settings
from backend.config.database import get_db, Base
from backend.connectors.neo4j_client import Neo4jClient
from backend.connectors.redis_client import RedisClient
from backend.connectors.minio_client import MinIOClient
from backend.services.knowledge_service import KnowledgeService
from backend.services.llm_service import LLMService
from backend.services.vector_service import VectorService
from backend.core.base_service import service_registry


# 测试数据库配置
TEST_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop():
    """创建事件循环"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def test_settings():
    """测试设置"""
    settings = get_settings()
    settings.app_debug = True
    settings.app_env = "test"
    settings.database_url = TEST_DATABASE_URL
    return settings


@pytest.fixture(scope="session")
def test_engine(test_settings):
    """测试数据库引擎"""
    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def test_db_session(test_engine):
    """测试数据库会话"""
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    session = TestingSessionLocal()
    yield session
    session.rollback()
    session.close()


@pytest.fixture(scope="function")
def override_get_db(test_db_session):
    """覆盖数据库依赖"""
    def _override_get_db():
        try:
            yield test_db_session
        finally:
            test_db_session.close()
    
    app.dependency_overrides[get_db] = _override_get_db
    yield
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def test_client(override_get_db):
    """测试客户端"""
    with TestClient(app) as client:
        yield client


@pytest_asyncio.fixture
async def mock_neo4j_client():
    """模拟Neo4j客户端"""
    mock_client = AsyncMock(spec=Neo4jClient)
    mock_client.connect = AsyncMock()
    mock_client.close = AsyncMock()
    mock_client.verify_connectivity = AsyncMock(return_value=True)
    mock_client.run = AsyncMock(return_value=[])
    mock_client.create_node = AsyncMock(return_value={"id": "test_node_id"})
    mock_client.create_relationship = AsyncMock(return_value={"id": "test_rel_id"})
    mock_client.find_nodes = AsyncMock(return_value=[])
    mock_client.get_health_status = AsyncMock(return_value={
        "status": "healthy",
        "connected": True,
        "last_health_check": "2024-01-01T00:00:00Z"
    })
    mock_client.get_statistics = AsyncMock(return_value={
        "node_count": 0,
        "relationship_count": 0,
        "query_count": 0
    })
    yield mock_client


@pytest_asyncio.fixture
async def mock_redis_client():
    """模拟Redis客户端"""
    mock_client = AsyncMock(spec=RedisClient)
    mock_client.connect = AsyncMock()
    mock_client.close = AsyncMock()
    mock_client.ping = AsyncMock(return_value=True)
    mock_client.get = AsyncMock(return_value=None)
    mock_client.set = AsyncMock(return_value=True)
    mock_client.delete = AsyncMock(return_value=1)
    mock_client.keys = AsyncMock(return_value=[])
    mock_client.hget = AsyncMock(return_value=None)
    mock_client.hset = AsyncMock(return_value=True)
    mock_client.hgetall = AsyncMock(return_value={})
    mock_client.lrange = AsyncMock(return_value=[])
    mock_client.lpush = AsyncMock(return_value=1)
    mock_client.smembers = AsyncMock(return_value=set())
    mock_client.sadd = AsyncMock(return_value=1)
    mock_client.zrange = AsyncMock(return_value=[])
    mock_client.zadd = AsyncMock(return_value=1)
    mock_client.type = AsyncMock(return_value="string")
    mock_client.flushdb = AsyncMock(return_value=True)
    yield mock_client


@pytest_asyncio.fixture
async def mock_minio_client():
    """模拟MinIO客户端"""
    mock_client = AsyncMock(spec=MinIOClient)
    mock_client.connect = AsyncMock()
    mock_client.close = AsyncMock()
    mock_client.bucket_exists = AsyncMock(return_value=True)
    mock_client.make_bucket = AsyncMock()
    mock_client.upload_file = AsyncMock()
    mock_client.download_file = AsyncMock()
    mock_client.remove_object = AsyncMock()
    mock_client.list_objects = AsyncMock(return_value=[])
    yield mock_client


@pytest_asyncio.fixture
async def mock_llm_service():
    """模拟LLM服务"""
    mock_service = AsyncMock(spec=LLMService)
    mock_service.initialize = AsyncMock()
    mock_service.cleanup = AsyncMock()
    mock_service.generate_response = AsyncMock()
    mock_service.generate_response.return_value = Mock(
        is_success=Mock(return_value=True),
        data='{"entities": [{"name": "test_entity", "type": "PERSON"}], "relations": []}'
    )
    yield mock_service


@pytest_asyncio.fixture
async def mock_vector_service():
    """模拟向量服务"""
    mock_service = AsyncMock(spec=VectorService)
    mock_service.initialize = AsyncMock()
    mock_service.cleanup = AsyncMock()
    mock_service.create_embedding = AsyncMock(return_value=[0.1] * 768)
    mock_service.search_similar = AsyncMock(return_value=[])
    mock_service.store_embedding = AsyncMock()
    yield mock_service


@pytest_asyncio.fixture
async def knowledge_service(
    mock_neo4j_client,
    mock_redis_client,
    test_db_session,
    mock_llm_service,
    mock_vector_service
):
    """知识服务实例"""
    service = KnowledgeService(
        neo4j_client=mock_neo4j_client,
        redis_client=mock_redis_client,
        db_session=test_db_session,
        llm_service=mock_llm_service,
        vector_service=mock_vector_service
    )
    await service.initialize()
    yield service
    await service.cleanup()


@pytest.fixture
def temp_dir():
    """临时目录"""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    shutil.rmtree(temp_path)


@pytest.fixture
def sample_entity_data():
    """示例实体数据"""
    return {
        "name": "张三",
        "type": "PERSON",
        "description": "一个测试人员",
        "properties": {
            "age": 30,
            "department": "技术部"
        },
        "confidence": "HIGH"
    }


@pytest.fixture
def sample_relation_data():
    """示例关系数据"""
    return {
        "source_entity": "张三",
        "target_entity": "技术部",
        "relation_type": "WORKS_FOR",
        "properties": {
            "start_date": "2020-01-01",
            "position": "高级工程师"
        },
        "confidence": "HIGH"
    }


@pytest.fixture
def sample_document_data():
    """示例文档数据"""
    return {
        "title": "测试文档",
        "content": "这是一个测试文档的内容。张三是技术部的高级工程师。",
        "source": "test",
        "metadata": {
            "author": "测试员",
            "created_at": "2024-01-01T00:00:00Z"
        }
    }


@pytest.fixture
def auth_headers():
    """认证头"""
    return {
        "Authorization": "Bearer test_token"
    }


@pytest.fixture
def admin_auth_headers():
    """管理员认证头"""
    return {
        "Authorization": "Bearer admin_test_token"
    }


# 测试工具函数
def assert_entity_equal(actual, expected):
    """断言实体相等"""
    assert actual.name == expected["name"]
    assert actual.entity_type.value == expected["type"]
    assert actual.description == expected.get("description")
    if expected.get("properties"):
        assert actual.properties == expected["properties"]


def assert_relation_equal(actual, expected):
    """断言关系相等"""
    assert actual.relation_type.value == expected["relation_type"]
    if expected.get("properties"):
        assert actual.properties == expected["properties"]


def create_mock_response(status_code: int = 200, data: Any = None, error: str = None):
    """创建模拟响应"""
    response = Mock()
    response.status_code = status_code
    if data is not None:
        response.json.return_value = data
    if error:
        response.json.return_value = {"error": error}
    return response


# 测试数据生成器
class TestDataGenerator:
    """测试数据生成器"""
    
    @staticmethod
    def generate_entities(count: int = 10):
        """生成测试实体"""
        entities = []
        for i in range(count):
            entities.append({
                "name": f"实体_{i}",
                "type": "CONCEPT",
                "description": f"这是第{i}个测试实体",
                "properties": {"index": i}
            })
        return entities
    
    @staticmethod
    def generate_relations(entity_count: int = 10, relation_count: int = 5):
        """生成测试关系"""
        relations = []
        for i in range(relation_count):
            source_idx = i % entity_count
            target_idx = (i + 1) % entity_count
            relations.append({
                "source_entity": f"实体_{source_idx}",
                "target_entity": f"实体_{target_idx}",
                "relation_type": "RELATED_TO",
                "properties": {"weight": 0.5}
            })
        return relations
    
    @staticmethod
    def generate_documents(count: int = 5):
        """生成测试文档"""
        documents = []
        for i in range(count):
            documents.append({
                "title": f"文档_{i}",
                "content": f"这是第{i}个测试文档的内容。包含实体_{i}和实体_{i+1}。",
                "source": "test_generator",
                "metadata": {"index": i}
            })
        return documents


# 性能测试装饰器
def performance_test(max_duration_seconds: float = 1.0):
    """性能测试装饰器"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            import time
            start_time = time.time()
            result = await func(*args, **kwargs)
            duration = time.time() - start_time
            assert duration <= max_duration_seconds, f"函数执行时间 {duration:.2f}s 超过限制 {max_duration_seconds}s"
            return result
        return wrapper
    return decorator


# 数据库清理工具
@pytest.fixture
def clean_database(test_db_session):
    """清理数据库"""
    yield
    # 清理所有表
    for table in reversed(Base.metadata.sorted_tables):
        test_db_session.execute(table.delete())
    test_db_session.commit()


# 异步上下文管理器
@pytest_asyncio.fixture
async def async_test_context():
    """异步测试上下文"""
    # 设置测试环境
    test_data = {}
    
    try:
        yield test_data
    finally:
        # 清理测试数据
        test_data.clear()


# 模拟外部服务
@pytest.fixture
def mock_external_services():
    """模拟外部服务"""
    services = {
        "llm_api": Mock(),
        "vector_db": Mock(),
        "file_storage": Mock()
    }
    
    # 配置默认行为
    services["llm_api"].post.return_value = create_mock_response(
        data={"response": "模拟LLM响应"}
    )
    services["vector_db"].search.return_value = []
    services["file_storage"].upload.return_value = {"file_id": "test_file_id"}
    
    yield services


# 并发测试工具
async def run_concurrent_tasks(tasks, max_concurrent=10):
    """运行并发任务"""
    semaphore = asyncio.Semaphore(max_concurrent)
    
    async def limited_task(task):
        async with semaphore:
            return await task
    
    return await asyncio.gather(*[limited_task(task) for task in tasks])


# 测试配置验证
def validate_test_environment():
    """验证测试环境"""
    required_env_vars = ["TEST_DATABASE_URL"]
    missing_vars = []
    
    for var in required_env_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        pytest.skip(f"缺少环境变量: {', '.join(missing_vars)}")


# 测试标记
pytest_marks = {
    "unit": pytest.mark.unit,
    "integration": pytest.mark.integration,
    "performance": pytest.mark.performance,
    "slow": pytest.mark.slow,
    "external": pytest.mark.external
} 