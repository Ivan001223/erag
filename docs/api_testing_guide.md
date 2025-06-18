# API 测试指南

本文档提供了企业知识库系统 API 的详细测试指南，包括测试环境设置、API 端点测试和自动化测试流程。

## 目录

1. [测试环境设置](#测试环境设置)
2. [API 端点测试](#api-端点测试)
3. [集成测试](#集成测试)
4. [性能测试](#性能测试)
5. [安全测试](#安全测试)
6. [自动化测试](#自动化测试)
7. [测试数据管理](#测试数据管理)
8. [故障排除](#故障排除)

## 测试环境设置

### 1. 环境准备

```bash
# 安装测试依赖
pip install pytest pytest-asyncio httpx pytest-mock pytest-cov

# 设置环境变量
export ENVIRONMENT=test
export DATABASE_URL=postgresql://test_user:test_pass@localhost:5432/test_db
export REDIS_URL=redis://localhost:6379/1
export NEO4J_URI=bolt://localhost:7687
export NEO4J_USER=neo4j
export NEO4J_PASSWORD=test_password
```

### 2. 测试数据库设置

```python
# tests/conftest.py
import pytest
import asyncio
from httpx import AsyncClient
from backend.api.main import app
from backend.core.database import get_database
from backend.core.config import settings

@pytest.fixture(scope="session")
def event_loop():
    """创建事件循环"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
async def client():
    """创建测试客户端"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

@pytest.fixture
async def test_db():
    """创建测试数据库"""
    # 设置测试数据库
    db = await get_database()
    yield db
    # 清理测试数据
    await db.execute("TRUNCATE TABLE users, documents, tasks CASCADE")
```

## API 端点测试

### 1. 用户管理 API

#### 用户注册

```python
# tests/test_api/test_users.py
import pytest
from httpx import AsyncClient

class TestUserAPI:
    """用户 API 测试"""
    
    async def test_user_registration(self, client: AsyncClient):
        """测试用户注册"""
        user_data = {
            "username": "testuser",
            "email": "test@example.com",
            "password": "securepassword123",
            "full_name": "Test User"
        }
        
        response = await client.post("/api/v1/users/register", json=user_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["username"] == user_data["username"]
        assert data["email"] == user_data["email"]
        assert "password" not in data  # 密码不应该返回
        assert "id" in data
        assert "created_at" in data
    
    async def test_user_login(self, client: AsyncClient):
        """测试用户登录"""
        # 先注册用户
        await self.test_user_registration(client)
        
        login_data = {
            "username": "testuser",
            "password": "securepassword123"
        }
        
        response = await client.post("/api/v1/users/login", json=login_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "token_type" in data
        assert data["token_type"] == "bearer"
    
    async def test_get_user_profile(self, client: AsyncClient, auth_headers):
        """测试获取用户资料"""
        response = await client.get("/api/v1/users/me", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert "username" in data
        assert "email" in data
        assert "preferences" in data
```

#### 认证测试

```python
@pytest.fixture
async def auth_headers(client: AsyncClient):
    """获取认证头"""
    # 注册并登录用户
    user_data = {
        "username": "authuser",
        "email": "auth@example.com",
        "password": "authpassword123"
    }
    
    await client.post("/api/v1/users/register", json=user_data)
    
    login_response = await client.post("/api/v1/users/login", json={
        "username": user_data["username"],
        "password": user_data["password"]
    })
    
    token = login_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
```

### 2. 文档管理 API

```python
# tests/test_api/test_documents.py
class TestDocumentAPI:
    """文档 API 测试"""
    
    async def test_upload_document(self, client: AsyncClient, auth_headers):
        """测试文档上传"""
        # 准备测试文件
        file_content = b"This is a test document about artificial intelligence."
        files = {
            "file": ("test.txt", file_content, "text/plain")
        }
        data = {
            "title": "AI Test Document",
            "description": "A test document for AI processing",
            "tags": "ai,test,document"
        }
        
        response = await client.post(
            "/api/v1/documents/upload",
            files=files,
            data=data,
            headers=auth_headers
        )
        
        assert response.status_code == 201
        result = response.json()
        assert result["title"] == data["title"]
        assert result["status"] == "uploaded"
        assert "id" in result
        assert "file_path" in result
        
        return result["id"]
    
    async def test_get_document(self, client: AsyncClient, auth_headers):
        """测试获取文档"""
        # 先上传文档
        doc_id = await self.test_upload_document(client, auth_headers)
        
        response = await client.get(
            f"/api/v1/documents/{doc_id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == doc_id
        assert "title" in data
        assert "content" in data
        assert "metadata" in data
    
    async def test_list_documents(self, client: AsyncClient, auth_headers):
        """测试文档列表"""
        # 上传几个文档
        await self.test_upload_document(client, auth_headers)
        
        response = await client.get(
            "/api/v1/documents/",
            params={"page": 1, "size": 10},
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "size" in data
        assert len(data["items"]) > 0
    
    async def test_delete_document(self, client: AsyncClient, auth_headers):
        """测试删除文档"""
        # 先上传文档
        doc_id = await self.test_upload_document(client, auth_headers)
        
        response = await client.delete(
            f"/api/v1/documents/{doc_id}",
            headers=auth_headers
        )
        
        assert response.status_code == 204
        
        # 验证文档已删除
        get_response = await client.get(
            f"/api/v1/documents/{doc_id}",
            headers=auth_headers
        )
        assert get_response.status_code == 404
```

### 3. 搜索 API

```python
# tests/test_api/test_search.py
class TestSearchAPI:
    """搜索 API 测试"""
    
    async def test_text_search(self, client: AsyncClient, auth_headers):
        """测试文本搜索"""
        search_data = {
            "query": "artificial intelligence",
            "search_type": "text",
            "limit": 10,
            "filters": {
                "content_type": ["document", "entity"],
                "date_range": {
                    "start": "2024-01-01",
                    "end": "2024-12-31"
                }
            }
        }
        
        response = await client.post(
            "/api/v1/search/",
            json=search_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert "total" in data
        assert "query_time" in data
        assert "search_type" in data
        
        # 验证结果格式
        if data["results"]:
            result = data["results"][0]
            assert "id" in result
            assert "title" in result or "name" in result
            assert "score" in result
            assert "type" in result
    
    async def test_vector_search(self, client: AsyncClient, auth_headers):
        """测试向量搜索"""
        search_data = {
            "query": "machine learning algorithms",
            "search_type": "vector",
            "limit": 5,
            "similarity_threshold": 0.7
        }
        
        response = await client.post(
            "/api/v1/search/vector",
            json=search_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        
        # 验证相似度分数
        for result in data["results"]:
            assert result["score"] >= search_data["similarity_threshold"]
    
    async def test_hybrid_search(self, client: AsyncClient, auth_headers):
        """测试混合搜索"""
        search_data = {
            "query": "deep learning neural networks",
            "search_type": "hybrid",
            "weights": {
                "text": 0.4,
                "vector": 0.6
            },
            "limit": 10
        }
        
        response = await client.post(
            "/api/v1/search/hybrid",
            json=search_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert data["search_type"] == "hybrid"
```

### 4. 知识图谱 API

```python
# tests/test_api/test_knowledge_graph.py
class TestKnowledgeGraphAPI:
    """知识图谱 API 测试"""
    
    async def test_get_entity(self, client: AsyncClient, auth_headers):
        """测试获取实体"""
        entity_id = "test_entity_id"
        
        response = await client.get(
            f"/api/v1/knowledge/entities/{entity_id}",
            headers=auth_headers
        )
        
        if response.status_code == 200:
            data = response.json()
            assert "id" in data
            assert "name" in data
            assert "type" in data
            assert "properties" in data
            assert "relations" in data
    
    async def test_create_entity(self, client: AsyncClient, auth_headers):
        """测试创建实体"""
        entity_data = {
            "name": "Test Entity",
            "type": "Concept",
            "properties": {
                "description": "A test entity for API testing",
                "category": "test",
                "confidence": 0.95
            },
            "aliases": ["Test", "Testing Entity"]
        }
        
        response = await client.post(
            "/api/v1/knowledge/entities/",
            json=entity_data,
            headers=auth_headers
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == entity_data["name"]
        assert data["type"] == entity_data["type"]
        assert "id" in data
        
        return data["id"]
    
    async def test_create_relation(self, client: AsyncClient, auth_headers):
        """测试创建关系"""
        # 先创建两个实体
        entity1_id = await self.test_create_entity(client, auth_headers)
        entity2_id = await self.test_create_entity(client, auth_headers)
        
        relation_data = {
            "source_id": entity1_id,
            "target_id": entity2_id,
            "relation_type": "RELATED_TO",
            "properties": {
                "strength": 0.8,
                "context": "test relationship"
            }
        }
        
        response = await client.post(
            "/api/v1/knowledge/relations/",
            json=relation_data,
            headers=auth_headers
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["source_id"] == entity1_id
        assert data["target_id"] == entity2_id
        assert data["relation_type"] == "RELATED_TO"
    
    async def test_graph_query(self, client: AsyncClient, auth_headers):
        """测试图查询"""
        query_data = {
            "query_type": "path",
            "parameters": {
                "start_entity": "entity_1",
                "end_entity": "entity_2",
                "max_depth": 3,
                "relation_types": ["RELATED_TO", "PART_OF"]
            }
        }
        
        response = await client.post(
            "/api/v1/knowledge/query",
            json=query_data,
            headers=auth_headers
        )
        
        if response.status_code == 200:
            data = response.json()
            assert "paths" in data or "results" in data
            assert "query_time" in data
```

### 5. 任务管理 API

```python
# tests/test_api/test_tasks.py
class TestTaskAPI:
    """任务 API 测试"""
    
    async def test_create_task(self, client: AsyncClient, auth_headers):
        """测试创建任务"""
        task_data = {
            "type": "document_processing",
            "parameters": {
                "document_id": "test_doc_id",
                "extract_entities": True,
                "extract_relations": True
            },
            "priority": "normal",
            "scheduled_at": "2024-01-01T12:00:00Z"
        }
        
        response = await client.post(
            "/api/v1/tasks/",
            json=task_data,
            headers=auth_headers
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["type"] == task_data["type"]
        assert data["status"] == "pending"
        assert "id" in data
        
        return data["id"]
    
    async def test_get_task_status(self, client: AsyncClient, auth_headers):
        """测试获取任务状态"""
        task_id = await self.test_create_task(client, auth_headers)
        
        response = await client.get(
            f"/api/v1/tasks/{task_id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == task_id
        assert "status" in data
        assert "progress" in data
        assert "created_at" in data
    
    async def test_list_tasks(self, client: AsyncClient, auth_headers):
        """测试任务列表"""
        response = await client.get(
            "/api/v1/tasks/",
            params={
                "status": "pending",
                "page": 1,
                "size": 10
            },
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
```

## 集成测试

### 1. 端到端工作流测试

```python
# tests/test_integration/test_workflows.py
class TestWorkflows:
    """工作流集成测试"""
    
    async def test_document_processing_workflow(self, client: AsyncClient, auth_headers):
        """测试文档处理完整工作流"""
        # 1. 上传文档
        file_content = b"Machine learning is a subset of artificial intelligence."
        files = {"file": ("ml.txt", file_content, "text/plain")}
        data = {"title": "ML Introduction"}
        
        upload_response = await client.post(
            "/api/v1/documents/upload",
            files=files,
            data=data,
            headers=auth_headers
        )
        assert upload_response.status_code == 201
        doc_id = upload_response.json()["id"]
        
        # 2. 等待处理任务创建
        await asyncio.sleep(1)
        
        # 3. 检查任务状态
        tasks_response = await client.get(
            "/api/v1/tasks/",
            params={"document_id": doc_id},
            headers=auth_headers
        )
        assert tasks_response.status_code == 200
        tasks = tasks_response.json()["items"]
        assert len(tasks) > 0
        
        # 4. 等待任务完成
        task_id = tasks[0]["id"]
        for _ in range(30):  # 最多等待30秒
            task_response = await client.get(
                f"/api/v1/tasks/{task_id}",
                headers=auth_headers
            )
            task_data = task_response.json()
            if task_data["status"] == "completed":
                break
            await asyncio.sleep(1)
        
        assert task_data["status"] == "completed"
        
        # 5. 验证知识图谱更新
        search_response = await client.post(
            "/api/v1/search/",
            json={"query": "machine learning", "search_type": "text"},
            headers=auth_headers
        )
        assert search_response.status_code == 200
        search_results = search_response.json()
        assert len(search_results["results"]) > 0
```

## 性能测试

### 1. 负载测试

```python
# tests/test_performance/test_load.py
import asyncio
import time
from concurrent.futures import ThreadPoolExecutor

class TestPerformance:
    """性能测试"""
    
    async def test_concurrent_searches(self, client: AsyncClient, auth_headers):
        """测试并发搜索性能"""
        search_queries = [
            "artificial intelligence",
            "machine learning",
            "deep learning",
            "neural networks",
            "data science"
        ]
        
        async def perform_search(query):
            start_time = time.time()
            response = await client.post(
                "/api/v1/search/",
                json={"query": query, "search_type": "text"},
                headers=auth_headers
            )
            end_time = time.time()
            return {
                "query": query,
                "status_code": response.status_code,
                "response_time": end_time - start_time
            }
        
        # 并发执行搜索
        tasks = [perform_search(query) for query in search_queries * 10]  # 50个并发请求
        results = await asyncio.gather(*tasks)
        
        # 验证性能指标
        success_count = sum(1 for r in results if r["status_code"] == 200)
        avg_response_time = sum(r["response_time"] for r in results) / len(results)
        
        assert success_count >= len(results) * 0.95  # 95% 成功率
        assert avg_response_time < 2.0  # 平均响应时间小于2秒
    
    async def test_upload_performance(self, client: AsyncClient, auth_headers):
        """测试文档上传性能"""
        file_sizes = [1024, 10240, 102400, 1048576]  # 1KB, 10KB, 100KB, 1MB
        
        for size in file_sizes:
            file_content = b"x" * size
            files = {"file": (f"test_{size}.txt", file_content, "text/plain")}
            
            start_time = time.time()
            response = await client.post(
                "/api/v1/documents/upload",
                files=files,
                data={"title": f"Test {size} bytes"},
                headers=auth_headers
            )
            end_time = time.time()
            
            assert response.status_code == 201
            upload_time = end_time - start_time
            
            # 验证上传时间合理（根据文件大小）
            max_time = max(5.0, size / 100000)  # 基于文件大小的动态阈值
            assert upload_time < max_time
```

## 安全测试

### 1. 认证和授权测试

```python
# tests/test_security/test_auth.py
class TestSecurity:
    """安全测试"""
    
    async def test_unauthorized_access(self, client: AsyncClient):
        """测试未授权访问"""
        protected_endpoints = [
            "/api/v1/documents/",
            "/api/v1/search/",
            "/api/v1/knowledge/entities/",
            "/api/v1/tasks/",
            "/api/v1/users/me"
        ]
        
        for endpoint in protected_endpoints:
            response = await client.get(endpoint)
            assert response.status_code == 401
    
    async def test_invalid_token(self, client: AsyncClient):
        """测试无效令牌"""
        invalid_headers = {"Authorization": "Bearer invalid_token"}
        
        response = await client.get(
            "/api/v1/users/me",
            headers=invalid_headers
        )
        assert response.status_code == 401
    
    async def test_sql_injection_protection(self, client: AsyncClient, auth_headers):
        """测试SQL注入防护"""
        malicious_queries = [
            "'; DROP TABLE users; --",
            "' OR '1'='1",
            "'; SELECT * FROM users; --"
        ]
        
        for query in malicious_queries:
            response = await client.post(
                "/api/v1/search/",
                json={"query": query, "search_type": "text"},
                headers=auth_headers
            )
            # 应该正常处理，不应该导致错误
            assert response.status_code in [200, 400]  # 200正常或400参数错误
    
    async def test_xss_protection(self, client: AsyncClient, auth_headers):
        """测试XSS防护"""
        xss_payload = "<script>alert('xss')</script>"
        
        # 尝试在文档标题中注入XSS
        file_content = b"Test content"
        files = {"file": ("test.txt", file_content, "text/plain")}
        data = {"title": xss_payload}
        
        response = await client.post(
            "/api/v1/documents/upload",
            files=files,
            data=data,
            headers=auth_headers
        )
        
        if response.status_code == 201:
            doc_data = response.json()
            # 验证XSS payload被正确转义或过滤
            assert "<script>" not in doc_data["title"]
```

## 自动化测试

### 1. CI/CD 集成

```yaml
# .github/workflows/api-tests.yml
name: API Tests

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:13
        env:
          POSTGRES_PASSWORD: test_password
          POSTGRES_DB: test_db
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
      
      redis:
        image: redis:6
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
      
      neo4j:
        image: neo4j:4.4
        env:
          NEO4J_AUTH: neo4j/test_password
        options: >-
          --health-cmd "cypher-shell -u neo4j -p test_password 'RETURN 1'"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.9'
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install -r requirements-test.txt
    
    - name: Run API tests
      env:
        DATABASE_URL: postgresql://postgres:test_password@localhost:5432/test_db
        REDIS_URL: redis://localhost:6379/1
        NEO4J_URI: bolt://localhost:7687
        NEO4J_USER: neo4j
        NEO4J_PASSWORD: test_password
      run: |
        pytest tests/test_api/ -v --cov=backend --cov-report=xml
    
    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
```

### 2. 测试报告生成

```python
# tests/conftest.py
import pytest
import json
from datetime import datetime

@pytest.fixture(scope="session", autouse=True)
def test_report():
    """生成测试报告"""
    yield
    
    # 测试完成后生成报告
    report_data = {
        "timestamp": datetime.now().isoformat(),
        "test_summary": {
            "total_tests": pytest.test_results.total,
            "passed": pytest.test_results.passed,
            "failed": pytest.test_results.failed,
            "skipped": pytest.test_results.skipped
        },
        "coverage": {
            "percentage": pytest.coverage_percentage,
            "missing_lines": pytest.missing_lines
        }
    }
    
    with open("test_report.json", "w") as f:
        json.dump(report_data, f, indent=2)
```

## 测试数据管理

### 1. 测试数据工厂

```python
# tests/factories.py
import factory
from factory import fuzzy
from datetime import datetime, timedelta

class UserFactory(factory.Factory):
    """用户测试数据工厂"""
    class Meta:
        model = dict
    
    username = factory.Sequence(lambda n: f"user{n}")
    email = factory.LazyAttribute(lambda obj: f"{obj.username}@example.com")
    full_name = factory.Faker('name')
    password = "testpassword123"
    is_active = True
    created_at = factory.LazyFunction(datetime.now)

class DocumentFactory(factory.Factory):
    """文档测试数据工厂"""
    class Meta:
        model = dict
    
    title = factory.Faker('sentence', nb_words=4)
    content = factory.Faker('text', max_nb_chars=1000)
    file_type = fuzzy.FuzzyChoice(['pdf', 'txt', 'docx', 'md'])
    size = fuzzy.FuzzyInteger(1000, 1000000)
    language = 'zh-CN'
    status = 'uploaded'
    created_at = factory.LazyFunction(datetime.now)

class TaskFactory(factory.Factory):
    """任务测试数据工厂"""
    class Meta:
        model = dict
    
    type = fuzzy.FuzzyChoice(['document_processing', 'entity_extraction', 'relation_extraction'])
    status = 'pending'
    priority = fuzzy.FuzzyChoice(['low', 'normal', 'high', 'urgent'])
    parameters = factory.LazyFunction(lambda: {})
    created_at = factory.LazyFunction(datetime.now)
```

### 2. 测试数据清理

```python
# tests/utils/cleanup.py
import asyncio
from backend.core.database import get_database
from backend.core.redis import get_redis
from backend.core.neo4j import get_neo4j

async def cleanup_test_data():
    """清理测试数据"""
    # 清理关系数据库
    db = await get_database()
    await db.execute("DELETE FROM tasks WHERE created_at < NOW() - INTERVAL '1 hour'")
    await db.execute("DELETE FROM documents WHERE title LIKE 'Test%'")
    await db.execute("DELETE FROM users WHERE username LIKE 'testuser%'")
    
    # 清理Redis缓存
    redis = await get_redis()
    await redis.flushdb()
    
    # 清理Neo4j测试节点
    neo4j = await get_neo4j()
    await neo4j.run("MATCH (n:TestEntity) DETACH DELETE n")
    await neo4j.run("MATCH (n:TestRelation) DELETE n")

@pytest.fixture(autouse=True)
async def auto_cleanup():
    """自动清理测试数据"""
    yield
    await cleanup_test_data()
```

## 故障排除

### 1. 常见问题

#### 数据库连接问题
```bash
# 检查数据库连接
psql -h localhost -U test_user -d test_db -c "SELECT 1;"

# 检查Redis连接
redis-cli -h localhost -p 6379 ping

# 检查Neo4j连接
cypher-shell -a bolt://localhost:7687 -u neo4j -p test_password "RETURN 1;"
```

#### 认证问题
```python
# 调试认证问题
import jwt
from backend.core.security import SECRET_KEY

# 解码JWT令牌
token = "your_jwt_token_here"
try:
    payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
    print(f"Token payload: {payload}")
except jwt.ExpiredSignatureError:
    print("Token has expired")
except jwt.InvalidTokenError:
    print("Invalid token")
```

#### 性能问题
```python
# 性能分析
import cProfile
import pstats

def profile_api_call():
    # 你的API调用代码
    pass

# 运行性能分析
cProfile.run('profile_api_call()', 'profile_stats')
stats = pstats.Stats('profile_stats')
stats.sort_stats('cumulative').print_stats(10)
```

### 2. 调试技巧

```python
# 启用详细日志
import logging
logging.basicConfig(level=logging.DEBUG)

# 使用pytest调试
pytest tests/test_api/test_users.py::TestUserAPI::test_user_registration -v -s --pdb

# 使用断点调试
import pdb; pdb.set_trace()
```

### 3. 监控和指标

```python
# 添加测试指标收集
import time
import psutil

class TestMetrics:
    def __init__(self):
        self.start_time = time.time()
        self.start_memory = psutil.Process().memory_info().rss
    
    def end_test(self):
        end_time = time.time()
        end_memory = psutil.Process().memory_info().rss
        
        return {
            "duration": end_time - self.start_time,
            "memory_used": end_memory - self.start_memory,
            "cpu_percent": psutil.cpu_percent()
        }
```

## 总结

本测试指南提供了全面的API测试策略，包括：

1. **单元测试**：测试各个API端点的基本功能
2. **集成测试**：测试端到端工作流程
3. **性能测试**：验证系统在负载下的表现
4. **安全测试**：确保系统安全性
5. **自动化测试**：CI/CD集成和持续测试

通过遵循这些测试实践，可以确保API的质量、性能和安全性，为用户提供稳定可靠的服务。