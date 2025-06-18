"""API集成测试

测试各个API端点之间的集成和协调工作。
"""

import pytest
import asyncio
from httpx import AsyncClient
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
import json
import tempfile
import os
from typing import Dict, Any

from backend.main import app
from backend.models.knowledge import Document, Entity, Relation
from backend.models.user import User
from backend.models.task import Task, TaskStatus


class APIIntegrationTest:
    """API集成测试类"""
    
    def __init__(self):
        self.client = TestClient(app)
        self.base_url = "http://testserver"
        self.test_user_id = "test_user_123"
        self.test_document_id = None
        self.test_entity_ids = []
        self.test_relation_ids = []
    
    async def setup_test_data(self):
        """设置测试数据"""
        # 创建测试用户
        user_data = {
            "username": "test_user",
            "email": "test@example.com",
            "full_name": "Test User",
            "role": "user"
        }
        
        response = self.client.post("/api/v1/users/", json=user_data)
        assert response.status_code == 201
        self.test_user_id = response.json()["id"]
    
    async def cleanup_test_data(self):
        """清理测试数据"""
        # 清理创建的测试数据
        if self.test_document_id:
            self.client.delete(f"/api/v1/documents/{self.test_document_id}")
        
        for entity_id in self.test_entity_ids:
            self.client.delete(f"/api/v1/graph/entities/{entity_id}")
        
        for relation_id in self.test_relation_ids:
            self.client.delete(f"/api/v1/graph/relations/{relation_id}")
        
        if self.test_user_id:
            self.client.delete(f"/api/v1/users/{self.test_user_id}")
    
    def test_document_processing_workflow(self):
        """测试完整的文档处理工作流"""
        # 1. 上传文档
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_file:
            tmp_file.write(b"Test document content for integration testing")
            tmp_file_path = tmp_file.name
        
        try:
            with open(tmp_file_path, "rb") as f:
                files = {"file": ("test_document.pdf", f, "application/pdf")}
                data = {"user_id": self.test_user_id}
                response = self.client.post("/api/v1/documents/upload", files=files, data=data)
            
            assert response.status_code == 201
            document_data = response.json()
            self.test_document_id = document_data["id"]
            
            # 2. 检查文档状态
            response = self.client.get(f"/api/v1/documents/{self.test_document_id}")
            assert response.status_code == 200
            assert response.json()["status"] in ["processing", "completed"]
            
            # 3. 触发OCR处理
            response = self.client.post(f"/api/v1/ocr/process", json={
                "document_id": self.test_document_id,
                "options": {"extract_tables": True, "quality_check": True}
            })
            assert response.status_code == 200
            task_id = response.json()["task_id"]
            
            # 4. 检查OCR任务状态
            response = self.client.get(f"/api/v1/ocr/status/{task_id}")
            assert response.status_code == 200
            
            # 5. 等待处理完成（模拟）
            import time
            time.sleep(2)
            
            # 6. 获取OCR结果
            response = self.client.get(f"/api/v1/documents/{self.test_document_id}/content")
            assert response.status_code == 200
            
        finally:
            os.unlink(tmp_file_path)
    
    def test_knowledge_graph_workflow(self):
        """测试知识图谱构建工作流"""
        # 1. 创建实体
        entity_data = {
            "name": "Test Entity",
            "type": "Person",
            "properties": {"description": "A test entity for integration testing"},
            "confidence": 0.9
        }
        
        response = self.client.post("/api/v1/graph/entities", json=entity_data)
        assert response.status_code == 201
        entity1_id = response.json()["id"]
        self.test_entity_ids.append(entity1_id)
        
        # 2. 创建第二个实体
        entity_data2 = {
            "name": "Test Organization",
            "type": "Organization",
            "properties": {"description": "A test organization"},
            "confidence": 0.8
        }
        
        response = self.client.post("/api/v1/graph/entities", json=entity_data2)
        assert response.status_code == 201
        entity2_id = response.json()["id"]
        self.test_entity_ids.append(entity2_id)
        
        # 3. 创建关系
        relation_data = {
            "source_id": entity1_id,
            "target_id": entity2_id,
            "type": "WORKS_FOR",
            "properties": {"since": "2024-01-01"},
            "confidence": 0.85
        }
        
        response = self.client.post("/api/v1/graph/relations", json=relation_data)
        assert response.status_code == 201
        relation_id = response.json()["id"]
        self.test_relation_ids.append(relation_id)
        
        # 4. 查询图谱
        query_data = {
            "query": "MATCH (a)-[r]->(b) WHERE a.id = $entity_id RETURN a, r, b",
            "params": {"entity_id": entity1_id},
            "limit": 10
        }
        
        response = self.client.post("/api/v1/graph/query", json=query_data)
        assert response.status_code == 200
        results = response.json()
        assert len(results["nodes"]) >= 2
        assert len(results["edges"]) >= 1
        
        # 5. 测试推理
        reasoning_data = {
            "entity_id": entity1_id,
            "reasoning_type": "path",
            "max_depth": 3
        }
        
        response = self.client.post("/api/v1/graph/reasoning", json=reasoning_data)
        assert response.status_code == 200
    
    def test_search_integration(self):
        """测试搜索功能集成"""
        # 1. 创建一些测试数据
        self.test_knowledge_graph_workflow()
        
        # 2. 文本搜索
        search_data = {
            "query": "Test Entity",
            "search_type": "text",
            "limit": 10
        }
        
        response = self.client.post("/api/v1/search/", json=search_data)
        assert response.status_code == 200
        results = response.json()
        assert len(results["results"]) > 0
        
        # 3. 向量搜索
        vector_search_data = {
            "query": "Find similar entities to Test Entity",
            "search_type": "vector",
            "limit": 5
        }
        
        response = self.client.post("/api/v1/search/", json=vector_search_data)
        assert response.status_code == 200
        
        # 4. 混合搜索
        hybrid_search_data = {
            "query": "Test Entity Organization",
            "search_type": "hybrid",
            "limit": 10,
            "weights": {"text": 0.6, "vector": 0.4}
        }
        
        response = self.client.post("/api/v1/search/", json=hybrid_search_data)
        assert response.status_code == 200
    
    def test_llm_integration(self):
        """测试LLM集成功能"""
        # 1. 测试实体提取
        text_data = {
            "text": "John Smith works at Microsoft as a software engineer. He lives in Seattle.",
            "extract_entities": True,
            "extract_relations": True
        }
        
        response = self.client.post("/api/v1/llm/extract", json=text_data)
        assert response.status_code == 200
        extraction_result = response.json()
        assert "entities" in extraction_result
        assert "relations" in extraction_result
        
        # 2. 测试问答
        qa_data = {
            "question": "Who works at Microsoft?",
            "context": "John Smith works at Microsoft as a software engineer.",
            "use_knowledge_graph": True
        }
        
        response = self.client.post("/api/v1/llm/qa", json=qa_data)
        assert response.status_code == 200
        qa_result = response.json()
        assert "answer" in qa_result
        assert "confidence" in qa_result
        
        # 3. 测试摘要生成
        summary_data = {
            "text": "This is a long document about artificial intelligence and machine learning. " * 10,
            "max_length": 100,
            "style": "concise"
        }
        
        response = self.client.post("/api/v1/llm/summarize", json=summary_data)
        assert response.status_code == 200
        summary_result = response.json()
        assert "summary" in summary_result
    
    def test_etl_integration(self):
        """测试ETL集成功能"""
        # 1. 创建ETL作业
        job_data = {
            "name": "test_etl_job",
            "source_type": "file",
            "source_config": {
                "file_path": "/tmp/test_data.json",
                "format": "json"
            },
            "target_type": "knowledge_graph",
            "target_config": {
                "entity_extraction": True,
                "relation_extraction": True
            },
            "schedule": "manual"
        }
        
        response = self.client.post("/api/v1/etl/jobs", json=job_data)
        assert response.status_code == 201
        job_id = response.json()["id"]
        
        # 2. 启动ETL作业
        response = self.client.post(f"/api/v1/etl/jobs/{job_id}/start")
        assert response.status_code == 200
        
        # 3. 检查作业状态
        response = self.client.get(f"/api/v1/etl/jobs/{job_id}/status")
        assert response.status_code == 200
        status = response.json()
        assert "status" in status
        
        # 4. 获取作业日志
        response = self.client.get(f"/api/v1/etl/jobs/{job_id}/logs")
        assert response.status_code == 200
    
    def test_user_workflow_integration(self):
        """测试用户工作流集成"""
        # 1. 用户登录
        login_data = {
            "username": "test_user",
            "password": "test_password"
        }
        
        response = self.client.post("/api/v1/auth/login", json=login_data)
        # 注意：这里可能返回401，因为我们没有实际的认证系统
        
        # 2. 获取用户信息
        response = self.client.get(f"/api/v1/users/{self.test_user_id}")
        assert response.status_code == 200
        user_info = response.json()
        assert user_info["id"] == self.test_user_id
        
        # 3. 更新用户偏好
        preferences_data = {
            "language": "zh-CN",
            "theme": "dark",
            "notifications": True
        }
        
        response = self.client.put(f"/api/v1/users/{self.test_user_id}/preferences", json=preferences_data)
        assert response.status_code == 200
        
        # 4. 获取用户活动历史
        response = self.client.get(f"/api/v1/users/{self.test_user_id}/activities")
        assert response.status_code == 200
    
    def test_error_handling_integration(self):
        """测试错误处理集成"""
        # 1. 测试无效的文档ID
        response = self.client.get("/api/v1/documents/invalid_id")
        assert response.status_code == 404
        
        # 2. 测试无效的实体数据
        invalid_entity_data = {
            "name": "",  # 空名称
            "type": "InvalidType",
            "confidence": 1.5  # 超出范围
        }
        
        response = self.client.post("/api/v1/graph/entities", json=invalid_entity_data)
        assert response.status_code == 422
        
        # 3. 测试无效的查询
        invalid_query_data = {
            "query": "INVALID CYPHER QUERY",
            "limit": -1
        }
        
        response = self.client.post("/api/v1/graph/query", json=invalid_query_data)
        assert response.status_code == 400
        
        # 4. 测试权限错误
        response = self.client.delete("/api/v1/users/admin_user")
        # 应该返回403或401，取决于认证实现
        assert response.status_code in [401, 403]
    
    def test_performance_integration(self):
        """测试性能相关的集成"""
        import time
        
        # 1. 测试批量操作性能
        start_time = time.time()
        
        entities_data = []
        for i in range(10):
            entities_data.append({
                "name": f"Batch Entity {i}",
                "type": "TestEntity",
                "properties": {"batch_id": "test_batch"},
                "confidence": 0.8
            })
        
        response = self.client.post("/api/v1/graph/entities/batch", json={"entities": entities_data})
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        assert response.status_code == 201
        assert processing_time < 5.0  # 应该在5秒内完成
        
        # 清理批量创建的实体
        batch_entities = response.json()["entities"]
        for entity in batch_entities:
            self.test_entity_ids.append(entity["id"])
        
        # 2. 测试并发查询
        import threading
        
        def concurrent_query():
            query_data = {
                "query": "MATCH (n:TestEntity) RETURN count(n) as count",
                "limit": 1
            }
            response = self.client.post("/api/v1/graph/query", json=query_data)
            return response.status_code == 200
        
        threads = []
        results = []
        
        for _ in range(5):
            thread = threading.Thread(target=lambda: results.append(concurrent_query()))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # 所有并发查询都应该成功
        assert all(results)


# 测试运行器
def run_integration_tests():
    """运行所有集成测试"""
    test_suite = APIIntegrationTest()
    
    try:
        # 设置测试数据
        asyncio.run(test_suite.setup_test_data())
        
        # 运行测试
        print("Running document processing workflow test...")
        test_suite.test_document_processing_workflow()
        
        print("Running knowledge graph workflow test...")
        test_suite.test_knowledge_graph_workflow()
        
        print("Running search integration test...")
        test_suite.test_search_integration()
        
        print("Running LLM integration test...")
        test_suite.test_llm_integration()
        
        print("Running ETL integration test...")
        test_suite.test_etl_integration()
        
        print("Running user workflow integration test...")
        test_suite.test_user_workflow_integration()
        
        print("Running error handling integration test...")
        test_suite.test_error_handling_integration()
        
        print("Running performance integration test...")
        test_suite.test_performance_integration()
        
        print("All integration tests passed!")
        
    except Exception as e:
        print(f"Integration test failed: {e}")
        raise
    
    finally:
        # 清理测试数据
        asyncio.run(test_suite.cleanup_test_data())


if __name__ == "__main__":
    run_integration_tests()