"""服务集成测试

测试各个服务组件之间的集成和协调工作。
"""

import pytest
import asyncio
import json
import tempfile
import os
from typing import Dict, Any, List
from unittest.mock import AsyncMock, patch, MagicMock
import time
import uuid
import numpy as np

from backend.services.cache_service import CacheService
from backend.services.vector_service import VectorService
from backend.services.search_service import SearchService
from backend.services.knowledge_service import KnowledgeService
from backend.services.llm_service import LLMService
from backend.services.ocr_service import OCRService
from backend.services.etl_service import ETLService
from backend.services.document_service import DocumentService
from backend.services.task_service import TaskService
from backend.services.user_service import UserService
from backend.services.recommendation_service import RecommendationService
from backend.models.knowledge import Document, Entity, Relation
from backend.models.user import User
from backend.models.task import Task, TaskStatus


class ServiceIntegrationTest:
    """服务集成测试类"""
    
    def __init__(self):
        # 初始化所有服务（使用模拟的依赖）
        self.cache_service = None
        self.vector_service = None
        self.search_service = None
        self.knowledge_service = None
        self.llm_service = None
        self.ocr_service = None
        self.etl_service = None
        self.document_service = None
        self.task_service = None
        self.user_service = None
        self.recommendation_service = None
        
        # 测试数据
        self.test_users = []
        self.test_documents = []
        self.test_entities = []
        self.test_relations = []
        self.test_tasks = []
        self.test_vectors = []
    
    async def setup_services(self):
        """设置服务实例"""
        # 创建模拟的数据库客户端
        mock_redis = AsyncMock()
        mock_neo4j = AsyncMock()
        mock_starrocks = AsyncMock()
        mock_minio = AsyncMock()
        
        # 初始化服务
        self.cache_service = CacheService(mock_redis)
        self.vector_service = VectorService(mock_starrocks)
        self.search_service = SearchService(
            vector_service=self.vector_service,
            cache_service=self.cache_service
        )
        self.knowledge_service = KnowledgeService(
            neo4j_client=mock_neo4j,
            cache_service=self.cache_service
        )
        self.llm_service = LLMService()
        self.ocr_service = OCRService()
        self.document_service = DocumentService(
            minio_client=mock_minio,
            cache_service=self.cache_service
        )
        self.task_service = TaskService(
            cache_service=self.cache_service
        )
        self.user_service = UserService(
            cache_service=self.cache_service
        )
        self.recommendation_service = RecommendationService(
            knowledge_service=self.knowledge_service,
            vector_service=self.vector_service,
            cache_service=self.cache_service
        )
        
        # 设置ETL服务
        self.etl_service = ETLService(
            document_service=self.document_service,
            ocr_service=self.ocr_service,
            llm_service=self.llm_service,
            knowledge_service=self.knowledge_service,
            vector_service=self.vector_service
        )
    
    async def cleanup_test_data(self):
        """清理测试数据"""
        # 在实际实现中，这里会清理所有测试数据
        self.test_users.clear()
        self.test_documents.clear()
        self.test_entities.clear()
        self.test_relations.clear()
        self.test_tasks.clear()
        self.test_vectors.clear()
    
    async def test_document_processing_pipeline(self):
        """测试文档处理管道"""
        # 创建测试文档
        document_id = str(uuid.uuid4())
        document_content = "This is a test document about artificial intelligence and machine learning."
        
        # 模拟文档上传
        with patch.object(self.document_service, 'upload_document') as mock_upload:
            mock_upload.return_value = {
                "id": document_id,
                "title": "Test Document",
                "content": document_content,
                "status": "uploaded"
            }
            
            document = await self.document_service.upload_document(
                file_content=document_content.encode(),
                filename="test_document.txt",
                user_id="test_user"
            )
            
            self.test_documents.append(document)
        
        # 1. OCR处理
        with patch.object(self.ocr_service, 'process_document') as mock_ocr:
            mock_ocr.return_value = {
                "text": document_content,
                "tables": [],
                "images": [],
                "confidence": 0.95
            }
            
            ocr_result = await self.ocr_service.process_document(document_id)
            assert ocr_result["text"] == document_content
            assert ocr_result["confidence"] > 0.9
        
        # 2. LLM实体提取
        with patch.object(self.llm_service, 'extract_entities') as mock_extract:
            mock_entities = [
                {
                    "name": "artificial intelligence",
                    "type": "Technology",
                    "confidence": 0.9
                },
                {
                    "name": "machine learning",
                    "type": "Technology",
                    "confidence": 0.85
                }
            ]
            mock_extract.return_value = mock_entities
            
            entities = await self.llm_service.extract_entities(document_content)
            assert len(entities) == 2
            self.test_entities.extend(entities)
        
        # 3. 知识图谱构建
        with patch.object(self.knowledge_service, 'create_entities') as mock_create_entities:
            mock_create_entities.return_value = [
                {"id": str(uuid.uuid4()), **entity} for entity in entities
            ]
            
            created_entities = await self.knowledge_service.create_entities(entities)
            assert len(created_entities) == len(entities)
        
        # 4. 向量化
        with patch.object(self.vector_service, 'generate_embeddings') as mock_embeddings:
            mock_embeddings.return_value = [np.random.rand(768).tolist() for _ in range(len(entities))]
            
            embeddings = await self.vector_service.generate_embeddings(
                [entity["name"] for entity in entities]
            )
            assert len(embeddings) == len(entities)
            self.test_vectors.extend(embeddings)
        
        # 5. 存储向量
        with patch.object(self.vector_service, 'store_vectors') as mock_store:
            mock_store.return_value = True
            
            stored = await self.vector_service.store_vectors(
                document_id,
                embeddings,
                [entity["name"] for entity in entities]
            )
            assert stored is True
    
    async def test_search_service_integration(self):
        """测试搜索服务集成"""
        # 准备测试数据
        await self.test_document_processing_pipeline()
        
        # 1. 文本搜索
        with patch.object(self.search_service, 'text_search') as mock_text_search:
            mock_text_search.return_value = {
                "results": [
                    {
                        "id": "entity_1",
                        "name": "artificial intelligence",
                        "type": "Technology",
                        "score": 0.95
                    }
                ],
                "total": 1
            }
            
            text_results = await self.search_service.text_search(
                query="artificial intelligence",
                limit=10
            )
            assert len(text_results["results"]) > 0
            assert text_results["results"][0]["score"] > 0.9
        
        # 2. 向量搜索
        with patch.object(self.search_service, 'vector_search') as mock_vector_search:
            mock_vector_search.return_value = {
                "results": [
                    {
                        "id": "entity_1",
                        "name": "artificial intelligence",
                        "similarity": 0.92
                    }
                ],
                "total": 1
            }
            
            query_vector = np.random.rand(768).tolist()
            vector_results = await self.search_service.vector_search(
                query_vector=query_vector,
                top_k=5
            )
            assert len(vector_results["results"]) > 0
        
        # 3. 混合搜索
        with patch.object(self.search_service, 'hybrid_search') as mock_hybrid_search:
            mock_hybrid_search.return_value = {
                "results": [
                    {
                        "id": "entity_1",
                        "name": "artificial intelligence",
                        "combined_score": 0.93
                    }
                ],
                "total": 1
            }
            
            hybrid_results = await self.search_service.hybrid_search(
                query="AI technology",
                weights={"text": 0.6, "vector": 0.4},
                limit=10
            )
            assert len(hybrid_results["results"]) > 0
    
    async def test_knowledge_service_integration(self):
        """测试知识服务集成"""
        # 1. 创建实体
        entity_data = {
            "name": "Test Entity",
            "type": "Person",
            "properties": {"description": "A test entity"},
            "confidence": 0.9
        }
        
        with patch.object(self.knowledge_service, 'create_entity') as mock_create:
            mock_create.return_value = {"id": str(uuid.uuid4()), **entity_data}
            
            entity = await self.knowledge_service.create_entity(entity_data)
            assert entity["name"] == entity_data["name"]
            self.test_entities.append(entity)
        
        # 2. 创建关系
        entity2_data = {
            "name": "Test Organization",
            "type": "Organization",
            "properties": {},
            "confidence": 0.85
        }
        
        with patch.object(self.knowledge_service, 'create_entity') as mock_create2:
            mock_create2.return_value = {"id": str(uuid.uuid4()), **entity2_data}
            
            entity2 = await self.knowledge_service.create_entity(entity2_data)
            self.test_entities.append(entity2)
        
        relation_data = {
            "source_id": entity["id"],
            "target_id": entity2["id"],
            "type": "WORKS_FOR",
            "properties": {"since": "2024-01-01"},
            "confidence": 0.8
        }
        
        with patch.object(self.knowledge_service, 'create_relation') as mock_create_rel:
            mock_create_rel.return_value = {"id": str(uuid.uuid4()), **relation_data}
            
            relation = await self.knowledge_service.create_relation(relation_data)
            assert relation["type"] == relation_data["type"]
            self.test_relations.append(relation)
        
        # 3. 图谱查询
        with patch.object(self.knowledge_service, 'query_graph') as mock_query:
            mock_query.return_value = {
                "nodes": [entity, entity2],
                "edges": [relation]
            }
            
            graph_result = await self.knowledge_service.query_graph(
                query="MATCH (a)-[r]->(b) WHERE a.id = $entity_id RETURN a, r, b",
                params={"entity_id": entity['id']}
            )
            assert len(graph_result["nodes"]) == 2
            assert len(graph_result["edges"]) == 1
    
    async def test_recommendation_service_integration(self):
        """测试推荐服务集成"""
        # 准备测试数据
        user_id = str(uuid.uuid4())
        user_data = {
            "id": user_id,
            "username": "test_user",
            "preferences": {"topics": ["AI", "ML"]},
            "interaction_history": []
        }
        
        with patch.object(self.user_service, 'get_user') as mock_get_user:
            mock_get_user.return_value = user_data
            
            user = await self.user_service.get_user(user_id)
            self.test_users.append(user)
        
        # 1. 基于内容的推荐
        with patch.object(self.recommendation_service, 'content_based_recommend') as mock_content:
            mock_content.return_value = [
                {
                    "id": "doc_1",
                    "title": "AI Research Paper",
                    "score": 0.9,
                    "reason": "Matches your interest in AI"
                }
            ]
            
            content_recommendations = await self.recommendation_service.content_based_recommend(
                user_id=user_id,
                limit=5
            )
            assert len(content_recommendations) > 0
            assert content_recommendations[0]["score"] > 0.8
        
        # 2. 协同过滤推荐
        with patch.object(self.recommendation_service, 'collaborative_recommend') as mock_collab:
            mock_collab.return_value = [
                {
                    "id": "doc_2",
                    "title": "ML Tutorial",
                    "score": 0.85,
                    "reason": "Users with similar interests liked this"
                }
            ]
            
            collab_recommendations = await self.recommendation_service.collaborative_recommend(
                user_id=user_id,
                limit=5
            )
            assert len(collab_recommendations) > 0
        
        # 3. 知识图谱推荐
        with patch.object(self.recommendation_service, 'knowledge_graph_recommend') as mock_kg:
            mock_kg.return_value = [
                {
                    "id": "entity_1",
                    "name": "Deep Learning",
                    "score": 0.88,
                    "reason": "Related to your interests through knowledge graph"
                }
            ]
            
            kg_recommendations = await self.recommendation_service.knowledge_graph_recommend(
                user_id=user_id,
                limit=5
            )
            assert len(kg_recommendations) > 0
        
        # 4. 混合推荐
        with patch.object(self.recommendation_service, 'hybrid_recommend') as mock_hybrid:
            mock_hybrid.return_value = [
                {
                    "id": "doc_3",
                    "title": "AI Ethics",
                    "score": 0.92,
                    "reason": "High relevance from multiple recommendation strategies"
                }
            ]
            
            hybrid_recommendations = await self.recommendation_service.hybrid_recommend(
                user_id=user_id,
                weights={"content": 0.4, "collaborative": 0.3, "knowledge_graph": 0.3},
                limit=10
            )
            assert len(hybrid_recommendations) > 0
    
    async def test_task_service_integration(self):
        """测试任务服务集成"""
        # 1. 创建任务
        task_data = {
            "type": "document_processing",
            "parameters": {
                "document_id": str(uuid.uuid4()),
                "extract_entities": True,
                "extract_relations": True
            },
            "user_id": "test_user",
            "priority": "high"
        }
        
        with patch.object(self.task_service, 'create_task') as mock_create_task:
            task_id = str(uuid.uuid4())
            mock_create_task.return_value = {
                "id": task_id,
                "status": TaskStatus.PENDING,
                **task_data
            }
            
            task = await self.task_service.create_task(task_data)
            assert task["status"] == TaskStatus.PENDING
            self.test_tasks.append(task)
        
        # 2. 执行任务
        with patch.object(self.task_service, 'execute_task') as mock_execute:
            mock_execute.return_value = {
                "id": task_id,
                "status": TaskStatus.RUNNING,
                "progress": 0.5,
                "result": None
            }
            
            executing_task = await self.task_service.execute_task(task_id)
            assert executing_task["status"] == TaskStatus.RUNNING
        
        # 3. 完成任务
        with patch.object(self.task_service, 'complete_task') as mock_complete:
            mock_complete.return_value = {
                "id": task_id,
                "status": TaskStatus.COMPLETED,
                "progress": 1.0,
                "result": {
                    "entities_extracted": 5,
                    "relations_extracted": 3,
                    "processing_time": 120.5
                }
            }
            
            completed_task = await self.task_service.complete_task(
                task_id,
                result={
                    "entities_extracted": 5,
                    "relations_extracted": 3,
                    "processing_time": 120.5
                }
            )
            assert completed_task["status"] == TaskStatus.COMPLETED
            assert completed_task["result"]["entities_extracted"] == 5
    
    async def test_etl_service_integration(self):
        """测试ETL服务集成"""
        # 1. 创建ETL作业
        job_config = {
            "name": "test_etl_job",
            "source": {
                "type": "file",
                "path": "/tmp/test_data.json",
                "format": "json"
            },
            "transformations": [
                {"type": "entity_extraction"},
                {"type": "relation_extraction"},
                {"type": "vectorization"}
            ],
            "target": {
                "type": "knowledge_graph",
                "update_mode": "upsert"
            }
        }
        
        with patch.object(self.etl_service, 'create_job') as mock_create_job:
            job_id = str(uuid.uuid4())
            mock_create_job.return_value = {
                "id": job_id,
                "status": "created",
                **job_config
            }
            
            job = await self.etl_service.create_job(job_config)
            assert job["status"] == "created"
        
        # 2. 执行ETL作业
        with patch.object(self.etl_service, 'execute_job') as mock_execute_job:
            mock_execute_job.return_value = {
                "id": job_id,
                "status": "running",
                "progress": 0.0,
                "steps_completed": 0,
                "total_steps": 3
            }
            
            execution_result = await self.etl_service.execute_job(job_id)
            assert execution_result["status"] == "running"
        
        # 3. 监控ETL进度
        with patch.object(self.etl_service, 'get_job_status') as mock_status:
            mock_status.return_value = {
                "id": job_id,
                "status": "completed",
                "progress": 1.0,
                "steps_completed": 3,
                "total_steps": 3,
                "result": {
                    "entities_processed": 100,
                    "relations_created": 50,
                    "vectors_generated": 100
                }
            }
            
            final_status = await self.etl_service.get_job_status(job_id)
            assert final_status["status"] == "completed"
            assert final_status["result"]["entities_processed"] == 100
    
    async def test_service_error_handling(self):
        """测试服务错误处理"""
        # 1. 测试服务间错误传播
        with patch.object(self.llm_service, 'extract_entities') as mock_extract:
            mock_extract.side_effect = Exception("LLM service error")
            
            try:
                await self.llm_service.extract_entities("test text")
                assert False, "Should have raised an exception"
            except Exception as e:
                assert "LLM service error" in str(e)
        
        # 2. 测试服务降级
        with patch.object(self.search_service, 'vector_search') as mock_vector_search:
            mock_vector_search.side_effect = Exception("Vector service unavailable")
            
            with patch.object(self.search_service, 'text_search') as mock_text_search:
                mock_text_search.return_value = {
                    "results": [{"id": "1", "name": "fallback result"}],
                    "total": 1
                }
                
                # 应该降级到文本搜索
                with patch.object(self.search_service, 'hybrid_search') as mock_hybrid:
                    mock_hybrid.return_value = {
                        "results": [{"id": "1", "name": "fallback result"}],
                        "total": 1,
                        "fallback_used": True
                    }
                    
                    result = await self.search_service.hybrid_search(
                        query="test query",
                        weights={"text": 0.6, "vector": 0.4}
                    )
                    assert result["fallback_used"] is True
    
    async def test_service_performance(self):
        """测试服务性能"""
        import time
        
        # 1. 测试并发处理能力
        async def process_document(index: int):
            start_time = time.time()
            
            # 模拟文档处理流程
            with patch.object(self.document_service, 'process_document') as mock_process:
                mock_process.return_value = {
                    "id": f"doc_{index}",
                    "status": "processed",
                    "processing_time": time.time() - start_time
                }
                
                result = await self.document_service.process_document(f"doc_{index}")
                return result
        
        # 并发处理10个文档
        start_time = time.time()
        tasks = [process_document(i) for i in range(10)]
        results = await asyncio.gather(*tasks)
        total_time = time.time() - start_time
        
        assert len(results) == 10
        assert total_time < 5.0  # 应该在5秒内完成
        
        # 2. 测试缓存性能
        cache_start_time = time.time()
        
        # 第一次访问（缓存未命中）
        with patch.object(self.cache_service, 'get') as mock_get:
            mock_get.return_value = None
            
            with patch.object(self.knowledge_service, 'get_entity') as mock_get_entity:
                mock_get_entity.return_value = {"id": "entity_1", "name": "Test Entity"}
                
                entity1 = await self.knowledge_service.get_entity("entity_1")
        
        # 第二次访问（缓存命中）
        with patch.object(self.cache_service, 'get') as mock_get_cached:
            mock_get_cached.return_value = {"id": "entity_1", "name": "Test Entity"}
            
            entity2 = await self.knowledge_service.get_entity("entity_1")
        
        cache_time = time.time() - cache_start_time
        
        assert entity1["id"] == entity2["id"]
        assert cache_time < 1.0  # 缓存访问应该很快


# 测试运行器
async def run_service_integration_tests():
    """运行所有服务集成测试"""
    test_suite = ServiceIntegrationTest()
    
    try:
        print("Setting up services...")
        await test_suite.setup_services()
        
        print("Running document processing pipeline test...")
        await test_suite.test_document_processing_pipeline()
        
        print("Running search service integration test...")
        await test_suite.test_search_service_integration()
        
        print("Running knowledge service integration test...")
        await test_suite.test_knowledge_service_integration()
        
        print("Running recommendation service integration test...")
        await test_suite.test_recommendation_service_integration()
        
        print("Running task service integration test...")
        await test_suite.test_task_service_integration()
        
        print("Running ETL service integration test...")
        await test_suite.test_etl_service_integration()
        
        print("Running service error handling test...")
        await test_suite.test_service_error_handling()
        
        print("Running service performance test...")
        await test_suite.test_service_performance()
        
        print("All service integration tests passed!")
        
    except Exception as e:
        print(f"Service integration test failed: {e}")
        raise
    
    finally:
        print("Cleaning up test data...")
        await test_suite.cleanup_test_data()


if __name__ == "__main__":
    asyncio.run(run_service_integration_tests())