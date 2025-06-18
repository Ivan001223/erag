"""数据库集成测试

测试Neo4j、StarRocks、Redis、MinIO等数据库组件之间的集成。
"""

import pytest
import asyncio
import json
import tempfile
import os
from typing import Dict, Any, List
from unittest.mock import AsyncMock, patch
import time
import uuid

from backend.connectors.neo4j_client import Neo4jClient
from backend.connectors.starrocks_client import StarRocksClient
from backend.connectors.redis_client import RedisClient
from backend.connectors.minio_client import MinIOClient
from backend.models.knowledge import Entity, Relation, Document
from backend.services.cache_service import CacheService
from backend.services.vector_service import VectorService


class DatabaseIntegrationTest:
    """数据库集成测试类"""
    
    def __init__(self):
        self.neo4j_client = None
        self.starrocks_client = None
        self.redis_client = None
        self.minio_client = None
        self.cache_service = None
        self.vector_service = None
        
        # 测试数据
        self.test_entities = []
        self.test_relations = []
        self.test_documents = []
        self.test_vectors = []
        self.test_cache_keys = []
        self.test_buckets = []
    
    async def setup_clients(self):
        """设置数据库客户端"""
        # 在实际测试中，这些应该连接到测试数据库
        self.neo4j_client = Neo4jClient(
            uri="bolt://localhost:7687",
            user="neo4j",
            password="test_password"
        )
        
        self.starrocks_client = StarRocksClient(
            host="localhost",
            port=9030,
            user="root",
            password="test_password",
            database="test_erag"
        )
        
        self.redis_client = RedisClient(
            host="localhost",
            port=6379,
            db=1  # 使用测试数据库
        )
        
        self.minio_client = MinIOClient(
            endpoint="localhost:9000",
            access_key="test_access_key",
            secret_key="test_secret_key",
            secure=False
        )
        
        # 初始化服务
        self.cache_service = CacheService(self.redis_client)
        self.vector_service = VectorService(self.starrocks_client)
        
        # 连接到数据库
        await self.neo4j_client.connect()
        await self.starrocks_client.connect()
        await self.redis_client.connect()
        await self.minio_client.connect()
    
    async def cleanup_test_data(self):
        """清理测试数据"""
        try:
            # 清理Neo4j测试数据
            for entity in self.test_entities:
                await self.neo4j_client.delete_node(entity["id"])
            
            for relation in self.test_relations:
                await self.neo4j_client.delete_relationship(relation["id"])
            
            # 清理StarRocks测试数据 - 使用SQLAlchemy方法
            for doc in self.test_documents:
                await self.starrocks_client.delete_document(doc["id"])
            
            for vector in self.test_vectors:
                await self.vector_service.delete_vector(vector["id"])
            
            # 清理Redis缓存
            for key in self.test_cache_keys:
                await self.redis_client.delete(key)
            
            # 清理MinIO存储桶
            for bucket in self.test_buckets:
                try:
                    objects = await self.minio_client.list_objects(bucket)
                    for obj in objects:
                        await self.minio_client.remove_object(bucket, obj.object_name)
                    await self.minio_client.remove_bucket(bucket)
                except Exception:
                    pass  # 忽略清理错误
        
        except Exception as e:
            print(f"Cleanup error: {e}")
        
        finally:
            # 关闭连接
            if self.neo4j_client:
                await self.neo4j_client.close()
            if self.starrocks_client:
                await self.starrocks_client.close()
            if self.redis_client:
                await self.redis_client.close()
            if self.minio_client:
                await self.minio_client.close()
    
    async def test_cross_database_entity_storage(self):
        """测试跨数据库实体存储"""
        entity_id = str(uuid.uuid4())
        entity_data = {
            "id": entity_id,
            "name": "Test Entity",
            "type": "Person",
            "properties": {
                "description": "A test entity for database integration",
                "created_at": "2024-01-27T10:00:00Z"
            },
            "confidence": 0.9
        }
        
        # 1. 在Neo4j中创建实体节点
        await self.neo4j_client.create_node(
            "Entity",
            entity_data
        )
        self.test_entities.append(entity_data)
        
        # 2. 在StarRocks中存储实体元数据
        from backend.models.entity import EntityModel
        from backend.database.session import get_async_session
        
        async with get_async_session() as session:
            entity = EntityModel(
                id=entity_id,
                name=entity_data["name"],
                type=entity_data["type"],
                properties=json.dumps(entity_data["properties"]),
                confidence=entity_data["confidence"],
                created_at=entity_data["properties"]["created_at"]
            )
            session.add(entity)
            await session.commit()
        
        # 3. 在Redis中缓存实体
        cache_key = f"entity:{entity_id}"
        await self.cache_service.set(cache_key, entity_data, ttl=3600)
        self.test_cache_keys.append(cache_key)
        
        # 4. 验证数据一致性
        # 从Neo4j查询
        neo4j_result = await self.neo4j_client.run_query(
            "MATCH (e:Entity {id: $id}) RETURN e",
            {"id": entity_id}
        )
        assert len(neo4j_result) == 1
        assert neo4j_result[0]["e"]["name"] == entity_data["name"]
        
        # 从StarRocks查询
        # 使用SQLAlchemy方法查询实体
        starrocks_result = await self.starrocks_client.get_entity_by_id(entity_id)
        starrocks_result = [starrocks_result] if starrocks_result else []
        assert len(starrocks_result) == 1
        assert starrocks_result[0]["name"] == entity_data["name"]
        
        # 从Redis查询
        cached_entity = await self.cache_service.get(cache_key)
        assert cached_entity is not None
        assert cached_entity["name"] == entity_data["name"]
    
    async def test_cross_database_relation_storage(self):
        """测试跨数据库关系存储"""
        # 首先创建两个实体
        entity1_id = str(uuid.uuid4())
        entity2_id = str(uuid.uuid4())
        
        entity1_data = {
            "id": entity1_id,
            "name": "John Smith",
            "type": "Person",
            "properties": {},
            "confidence": 0.9
        }
        
        entity2_data = {
            "id": entity2_id,
            "name": "Microsoft",
            "type": "Organization",
            "properties": {},
            "confidence": 0.95
        }
        
        # 在Neo4j中创建实体
        await self.neo4j_client.create_node("Entity", entity1_data)
        await self.neo4j_client.create_node("Entity", entity2_data)
        self.test_entities.extend([entity1_data, entity2_data])
        
        # 创建关系
        relation_id = str(uuid.uuid4())
        relation_data = {
            "id": relation_id,
            "source_id": entity1_id,
            "target_id": entity2_id,
            "type": "WORKS_FOR",
            "properties": {
                "since": "2020-01-01",
                "position": "Software Engineer"
            },
            "confidence": 0.85
        }
        
        # 1. 在Neo4j中创建关系
        await self.neo4j_client.create_relationship(
            entity1_id,
            entity2_id,
            "WORKS_FOR",
            relation_data["properties"]
        )
        self.test_relations.append(relation_data)
        
        # 2. 在StarRocks中存储关系元数据
        from backend.models.relation import RelationModel
        from backend.database.session import get_async_session
        
        async with get_async_session() as session:
            relation = RelationModel(
                id=relation_id,
                source_id=entity1_id,
                target_id=entity2_id,
                type=relation_data["type"],
                properties=json.dumps(relation_data["properties"]),
                confidence=relation_data["confidence"],
                created_at="2024-01-27T10:00:00Z"
            )
            session.add(relation)
            await session.commit()
        
        # 3. 验证关系查询
        # Neo4j路径查询
        path_result = await self.neo4j_client.run_query(
            """
            MATCH (a:Entity {id: $source_id})-[r:WORKS_FOR]->(b:Entity {id: $target_id})
            RETURN a, r, b
            """,
            {"source_id": entity1_id, "target_id": entity2_id}
        )
        assert len(path_result) == 1
        
        # StarRocks关系分析
        relation_stats = await self.starrocks_client.execute(
            """
            SELECT type, COUNT(*) as count, AVG(confidence) as avg_confidence
            FROM relations
            WHERE source_id = %s OR target_id = %s
            GROUP BY type
            """,
            (entity1_id, entity1_id)
        )
        assert len(relation_stats) > 0
    
    async def test_document_vector_integration(self):
        """测试文档和向量集成存储"""
        document_id = str(uuid.uuid4())
        document_content = "This is a test document for vector integration testing."
        
        # 1. 在MinIO中存储原始文档
        bucket_name = "test-documents"
        await self.minio_client.make_bucket(bucket_name)
        self.test_buckets.append(bucket_name)
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as tmp_file:
            tmp_file.write(document_content)
            tmp_file_path = tmp_file.name
        
        try:
            await self.minio_client.fput_object(
                bucket_name,
                f"{document_id}.txt",
                tmp_file_path
            )
            
            # 2. 在StarRocks中存储文档元数据
            document_data = {
                "id": document_id,
                "title": "Test Document",
                "content": document_content,
                "file_path": f"s3://{bucket_name}/{document_id}.txt",
                "created_at": "2024-01-27T10:00:00Z",
                "status": "processed"
            }
            
            from backend.models.database import DocumentModel
            from backend.database.session import get_async_session
            
            async with get_async_session() as session:
                document = DocumentModel(
                    id=document_id,
                    title=document_data["title"],
                    content=document_data["content"],
                    file_path=document_data["file_path"],
                    created_at=document_data["created_at"],
                    status=document_data["status"]
                )
                session.add(document)
                await session.commit()
            self.test_documents.append(document_data)
            
            # 3. 生成并存储向量
            # 模拟向量生成
            import numpy as np
            vector = np.random.rand(768).tolist()  # 模拟768维向量
            
            vector_data = {
                "id": str(uuid.uuid4()),
                "document_id": document_id,
                "vector": vector,
                "metadata": {
                    "chunk_index": 0,
                    "chunk_text": document_content[:100]
                }
            }
            
            await self.vector_service.store_vector(
                vector_data["id"],
                vector,
                vector_data["metadata"]
            )
            self.test_vectors.append(vector_data)
            
            # 4. 验证集成查询
            # 从MinIO获取文档
            retrieved_content = await self.minio_client.get_object(
                bucket_name,
                f"{document_id}.txt"
            )
            assert retrieved_content.decode('utf-8') == document_content
            
            # 从StarRocks查询文档元数据
            # 使用SQLAlchemy方法查询文档
            doc_result = await self.starrocks_client.get_document_by_id(document_id)
            doc_result = [doc_result] if doc_result else []
            assert len(doc_result) == 1
            assert doc_result[0]["title"] == document_data["title"]
            
            # 向量相似性搜索
            similar_vectors = await self.vector_service.similarity_search(
                vector,
                top_k=5
            )
            assert len(similar_vectors) > 0
            
        finally:
            os.unlink(tmp_file_path)
    
    async def test_cache_consistency(self):
        """测试缓存一致性"""
        # 创建测试数据
        entity_id = str(uuid.uuid4())
        entity_data = {
            "id": entity_id,
            "name": "Cache Test Entity",
            "type": "TestType",
            "properties": {"test": True},
            "confidence": 0.8
        }
        
        # 1. 在主数据库中创建数据
        await self.neo4j_client.create_node("Entity", entity_data)
        self.test_entities.append(entity_data)
        
        # 2. 缓存数据
        cache_key = f"entity:{entity_id}"
        await self.cache_service.set(cache_key, entity_data, ttl=60)
        self.test_cache_keys.append(cache_key)
        
        # 3. 验证缓存命中
        cached_data = await self.cache_service.get(cache_key)
        assert cached_data is not None
        assert cached_data["name"] == entity_data["name"]
        
        # 4. 更新主数据库
        updated_data = entity_data.copy()
        updated_data["name"] = "Updated Cache Test Entity"
        
        await self.neo4j_client.update_node(entity_id, {"name": updated_data["name"]})
        
        # 5. 使缓存失效
        await self.cache_service.delete(cache_key)
        
        # 6. 重新缓存更新后的数据
        await self.cache_service.set(cache_key, updated_data, ttl=60)
        
        # 7. 验证缓存更新
        updated_cached_data = await self.cache_service.get(cache_key)
        assert updated_cached_data["name"] == updated_data["name"]
    
    async def test_transaction_consistency(self):
        """测试跨数据库事务一致性"""
        entity_id = str(uuid.uuid4())
        entity_data = {
            "id": entity_id,
            "name": "Transaction Test Entity",
            "type": "TestType",
            "properties": {},
            "confidence": 0.9
        }
        
        try:
            # 模拟分布式事务
            # 1. 开始事务
            neo4j_tx = await self.neo4j_client.begin_transaction()
            
            # 2. 在Neo4j中创建实体
            await neo4j_tx.run(
                "CREATE (e:Entity {id: $id, name: $name, type: $type})",
                entity_data
            )
            
            # 3. 在StarRocks中创建记录
            from backend.models.entity import EntityModel
            from backend.database.session import get_async_session
            
            async with get_async_session() as session:
                entity = EntityModel(
                    id=entity_id,
                    name=entity_data["name"],
                    type=entity_data["type"],
                    confidence=entity_data["confidence"]
                )
                session.add(entity)
                await session.commit()
            
            # 4. 提交事务
            await neo4j_tx.commit()
            
            # 5. 验证数据一致性
            neo4j_result = await self.neo4j_client.run_query(
                "MATCH (e:Entity {id: $id}) RETURN e",
                {"id": entity_id}
            )
            assert len(neo4j_result) == 1
            
            # 使用SQLAlchemy方法查询实体
            starrocks_result = await self.starrocks_client.get_entity_by_id(entity_id)
            starrocks_result = [starrocks_result] if starrocks_result else []
            assert len(starrocks_result) == 1
            
            self.test_entities.append(entity_data)
            
        except Exception as e:
            # 回滚事务
            if 'neo4j_tx' in locals():
                await neo4j_tx.rollback()
            
            # 清理StarRocks数据 - 使用SQLAlchemy方法
            await self.starrocks_client.delete_entity(entity_id)
            
            raise e
    
    async def test_performance_under_load(self):
        """测试负载下的数据库性能"""
        import asyncio
        import time
        
        # 并发创建多个实体
        async def create_test_entity(index: int):
            entity_id = str(uuid.uuid4())
            entity_data = {
                "id": entity_id,
                "name": f"Load Test Entity {index}",
                "type": "LoadTest",
                "properties": {"index": index},
                "confidence": 0.8
            }
            
            # 并发写入多个数据库
            tasks = [
                self.neo4j_client.create_node("Entity", entity_data),
                self._insert_entity_with_sqlalchemy(entity_id, entity_data),
                self.cache_service.set(f"entity:{entity_id}", entity_data, ttl=300)
            ]
            
            await asyncio.gather(*tasks)
        self.test_entities.append(entity_data)
        return entity_id
    
    async def _insert_entity_with_sqlalchemy(self, entity_id: str, entity_data: dict):
        """使用SQLAlchemy插入实体的辅助方法"""
        from backend.models.entity import EntityModel
        from backend.database.session import get_async_session
        
        async with get_async_session() as session:
            entity = EntityModel(
                id=entity_id,
                name=entity_data["name"],
                type=entity_data["type"],
                confidence=entity_data["confidence"]
            )
            session.add(entity)
            await session.commit()
        
        # 测试并发写入
        start_time = time.time()
        
        tasks = [create_test_entity(i) for i in range(20)]
        entity_ids = await asyncio.gather(*tasks)
        
        write_time = time.time() - start_time
        
        # 测试并发读取
        async def read_test_entity(entity_id: str):
            tasks = [
                self.neo4j_client.run_query(
                    "MATCH (e:Entity {id: $id}) RETURN e",
                    {"id": entity_id}
                ),
                self.starrocks_client.get_entity_by_id(entity_id),
                self.cache_service.get(f"entity:{entity_id}")
            ]
            
            results = await asyncio.gather(*tasks)
            return all(len(result) > 0 if isinstance(result, list) else result is not None for result in results)
        
        start_time = time.time()
        
        read_tasks = [read_test_entity(entity_id) for entity_id in entity_ids]
        read_results = await asyncio.gather(*read_tasks)
        
        read_time = time.time() - start_time
        
        # 验证性能指标
        assert write_time < 10.0  # 20个实体写入应在10秒内完成
        assert read_time < 5.0    # 20个实体读取应在5秒内完成
        assert all(read_results)  # 所有读取都应成功
        
        print(f"Write performance: {len(entity_ids)/write_time:.2f} entities/second")
        print(f"Read performance: {len(entity_ids)/read_time:.2f} entities/second")


# 测试运行器
async def run_database_integration_tests():
    """运行所有数据库集成测试"""
    test_suite = DatabaseIntegrationTest()
    
    try:
        print("Setting up database clients...")
        await test_suite.setup_clients()
        
        print("Running cross-database entity storage test...")
        await test_suite.test_cross_database_entity_storage()
        
        print("Running cross-database relation storage test...")
        await test_suite.test_cross_database_relation_storage()
        
        print("Running document vector integration test...")
        await test_suite.test_document_vector_integration()
        
        print("Running cache consistency test...")
        await test_suite.test_cache_consistency()
        
        print("Running transaction consistency test...")
        await test_suite.test_transaction_consistency()
        
        print("Running performance under load test...")
        await test_suite.test_performance_under_load()
        
        print("All database integration tests passed!")
        
    except Exception as e:
        print(f"Database integration test failed: {e}")
        raise
    
    finally:
        print("Cleaning up test data...")
        await test_suite.cleanup_test_data()


if __name__ == "__main__":
    asyncio.run(run_database_integration_tests())