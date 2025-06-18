"""pytest配置文件

提供测试夹具和配置，用于整个测试套件。
"""

import os
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock
from typing import Generator, AsyncGenerator
from fastapi.testclient import TestClient
from httpx import AsyncClient

# 设置测试环境变量
os.environ["TESTING"] = "true"
os.environ["SECRET_KEY"] = "test-secret-key"
os.environ["NEO4J_PASSWORD"] = "test_password"
os.environ["LLM_API_KEY"] = "test-api-key"

from backend.main import app
from backend.config.settings import Settings
from backend.connectors.neo4j_client import Neo4jClient
from backend.connectors.redis_client import RedisClient
from backend.connectors.starrocks_client import StarRocksClient
from backend.connectors.minio_client import MinIOClient
from backend.core.llm.llm_orchestrator import LLMOrchestrator
from backend.core.vector.embedder import Embedder
from backend.core.ocr.ocr_service import OCRService


@pytest.fixture(scope="session")
def event_loop():
    """创建事件循环"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def test_settings() -> Settings:
    """测试设置"""
    return Settings(
        app_debug=True,
        secret_key="test-secret-key",
        neo4j_password="test_password",
        llm_api_key="test-api-key",
        redis_db=1,  # 使用不同的Redis数据库
        mysql_database="test_erag_metadata",
        starrocks_database="test_knowledge_base",
        minio_bucket_name="test-knowledge-base"
    )


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    """测试客户端"""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """异步测试客户端"""
    async with AsyncClient(app=app, base_url="http://testserver") as ac:
        yield ac


@pytest.fixture
def mock_neo4j_client():
    """模拟Neo4j客户端"""
    mock_client = Mock(spec=Neo4jClient)
    mock_client.execute_query = AsyncMock(return_value=[])
    mock_client.create_node = AsyncMock(return_value={"id": "test_id"})
    mock_client.create_relationship = AsyncMock(return_value={"id": "rel_id"})
    mock_client.find_nodes = AsyncMock(return_value=[])
    mock_client.close = AsyncMock()
    return mock_client


@pytest.fixture
def mock_redis_client():
    """模拟Redis客户端"""
    mock_client = Mock(spec=RedisClient)
    mock_client.get = AsyncMock(return_value=None)
    mock_client.set = AsyncMock(return_value=True)
    mock_client.delete = AsyncMock(return_value=True)
    mock_client.exists = AsyncMock(return_value=False)
    mock_client.close = AsyncMock()
    return mock_client


@pytest.fixture
def mock_starrocks_client():
    """模拟StarRocks客户端"""
    mock_client = Mock(spec=StarRocksClient)
    mock_client.execute_query = AsyncMock(return_value=[])
    mock_client.insert_data = AsyncMock(return_value=True)
    mock_client.create_table = AsyncMock(return_value=True)
    mock_client.close = AsyncMock()
    return mock_client


@pytest.fixture
def mock_minio_client():
    """模拟MinIO客户端"""
    mock_client = Mock(spec=MinIOClient)
    mock_client.upload_file = AsyncMock(return_value="test_object_name")
    mock_client.download_file = AsyncMock(return_value=b"test_content")
    mock_client.delete_file = AsyncMock(return_value=True)
    mock_client.file_exists = AsyncMock(return_value=False)
    return mock_client


@pytest.fixture
def mock_llm_orchestrator():
    """模拟LLM编排器"""
    mock_orchestrator = Mock(spec=LLMOrchestrator)
    mock_orchestrator.generate = AsyncMock(return_value={
        "content": "Mock LLM response",
        "model": "mock-model",
        "usage": {"prompt_tokens": 10, "completion_tokens": 20}
    })
    mock_orchestrator.generate_stream = AsyncMock()
    return mock_orchestrator


@pytest.fixture
def mock_embedder():
    """模拟嵌入器"""
    mock_embedder = Mock(spec=Embedder)
    mock_embedder.embed_text = AsyncMock(return_value=[0.1, 0.2, 0.3, 0.4])
    mock_embedder.embed_documents = AsyncMock(return_value=[[0.1, 0.2, 0.3, 0.4]])
    return mock_embedder


@pytest.fixture
def mock_ocr_service():
    """模拟OCR服务"""
    mock_service = Mock(spec=OCRService)
    mock_service.process_document = AsyncMock(return_value={
        "text": "Mock OCR text",
        "tables": [],
        "images": [],
        "metadata": {"pages": 1}
    })
    return mock_service


@pytest.fixture
def sample_document_data():
    """示例文档数据"""
    return {
        "title": "测试文档",
        "content": "这是一个测试文档的内容。包含一些示例文本用于测试。",
        "file_type": "text",
        "file_size": 1024,
        "metadata": {
            "author": "测试用户",
            "created_at": "2024-01-01T00:00:00Z"
        }
    }


@pytest.fixture
def sample_entity_data():
    """示例实体数据"""
    return {
        "name": "苹果公司",
        "entity_type": "ORG",
        "properties": {
            "industry": "科技",
            "founded": "1976",
            "founder": "史蒂夫·乔布斯"
        },
        "confidence": 0.95
    }


@pytest.fixture
def sample_relation_data():
    """示例关系数据"""
    return {
        "source_entity": "史蒂夫·乔布斯",
        "target_entity": "苹果公司",
        "relation_type": "创立",
        "properties": {
            "year": "1976"
        },
        "confidence": 0.90
    }


@pytest.fixture
def sample_user_data():
    """示例用户数据"""
    return {
        "username": "test_user",
        "email": "test@example.com",
        "full_name": "测试用户",
        "role": "user",
        "is_active": True
    }


@pytest.fixture(autouse=True)
def cleanup_test_data():
    """自动清理测试数据"""
    yield
    # 测试后清理逻辑可以在这里添加
    pass


# 测试标记
pytestmark = pytest.mark.asyncio