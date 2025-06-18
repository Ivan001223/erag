#!/usr/bin/env python3
"""
示例数据填充脚本

该脚本用于为企业知识库系统填充示例数据：
- 示例文档
- 示例实体和关系
- 测试用户
- 示例配置
"""

import asyncio
import logging
import json
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Any
from pathlib import Path

from backend.config.settings import Settings
from backend.connectors.neo4j_client import Neo4jClient
from backend.connectors.starrocks_client import StarRocksClient
from backend.connectors.redis_client import RedisClient
from backend.connectors.minio_client import MinIOClient
from backend.utils.logger import get_logger

logger = get_logger(__name__)

class DataSeeder:
    """
    数据填充器
    
    负责生成和插入示例数据到各个数据存储系统。
    """
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.neo4j_client = None
        self.starrocks_client = None
        self.redis_client = None
        self.minio_client = None
    
    async def initialize_clients(self):
        """
        初始化所有数据库客户端
        """
        self.neo4j_client = Neo4jClient(
            uri=self.settings.neo4j_url,
            user=self.settings.neo4j_user,
            password=self.settings.neo4j_password
        )
        
        self.starrocks_client = StarRocksClient(
            host=self.settings.starrocks_host,
            port=self.settings.starrocks_port,
            user=self.settings.starrocks_user,
            password=self.settings.starrocks_password
        )
        
        self.redis_client = RedisClient(
            host=self.settings.redis_host,
            port=self.settings.redis_port,
            password=self.settings.redis_password,
            db=self.settings.redis_db
        )
        
        self.minio_client = MinIOClient(
            endpoint=self.settings.minio_endpoint,
            access_key=self.settings.minio_access_key,
            secret_key=self.settings.minio_secret_key,
            secure=self.settings.minio_secure
        )
        
        await self.neo4j_client.connect()
        await self.starrocks_client.connect()
        await self.redis_client.connect()
        await self.minio_client.connect()
    
    async def seed_all(self, clear_existing: bool = False) -> Dict[str, bool]:
        """
        填充所有示例数据
        
        参数:
            clear_existing: 是否清除现有数据
        
        返回:
            Dict[str, bool]: 各组件填充结果
        """
        results = {}
        
        logger.info("开始填充示例数据...")
        
        if clear_existing:
            await self._clear_existing_data()
        
        # 填充用户数据
        try:
            results['users'] = await self._seed_users()
        except Exception as e:
            logger.error(f"用户数据填充失败: {e}")
            results['users'] = False
        
        # 填充文档数据
        try:
            results['documents'] = await self._seed_documents()
        except Exception as e:
            logger.error(f"文档数据填充失败: {e}")
            results['documents'] = False
        
        # 填充实体和关系数据
        try:
            results['entities'] = await self._seed_entities_and_relations()
        except Exception as e:
            logger.error(f"实体关系数据填充失败: {e}")
            results['entities'] = False
        
        # 填充缓存数据
        try:
            results['cache'] = await self._seed_cache_data()
        except Exception as e:
            logger.error(f"缓存数据填充失败: {e}")
            results['cache'] = False
        
        # 填充对象存储数据
        try:
            results['storage'] = await self._seed_storage_data()
        except Exception as e:
            logger.error(f"存储数据填充失败: {e}")
            results['storage'] = False
        
        logger.info(f"示例数据填充完成: {results}")
        return results
    
    async def _clear_existing_data(self):
        """
        清除现有数据
        """
        logger.info("清除现有数据...")
        
        # 清除 Neo4j 数据
        await self.neo4j_client.execute_query("MATCH (n) DETACH DELETE n")
        
        # 清除 StarRocks 数据 - 使用SQLAlchemy方法
        tables = ['documents', 'entities', 'relations', 'users', 'embeddings']
        for table in tables:
            try:
                await self.starrocks_client.truncate_table(table)
            except Exception as e:
                logger.warning(f"清除表 {table} 失败: {e}")
        
        # 清除 Redis 数据
        await self.redis_client.flushdb()
        
        logger.info("现有数据清除完成")
    
    async def _seed_users(self) -> bool:
        """
        填充用户数据
        """
        logger.info("填充用户数据...")
        
        users = [
            {
                "id": str(uuid.uuid4()),
                "username": "admin",
                "email": "admin@example.com",
                "password_hash": "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj3QJgusgqSK",  # password: admin123
                "role": "admin",
                "is_active": True
            },
            {
                "id": str(uuid.uuid4()),
                "username": "analyst",
                "email": "analyst@example.com",
                "password_hash": "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj3QJgusgqSK",  # password: analyst123
                "role": "analyst",
                "is_active": True
            },
            {
                "id": str(uuid.uuid4()),
                "username": "viewer",
                "email": "viewer@example.com",
                "password_hash": "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj3QJgusgqSK",  # password: viewer123
                "role": "viewer",
                "is_active": True
            }
        ]
        
        # 插入到 StarRocks
        from backend.models.user import UserModel
        from backend.config.database import get_async_session
        
        async with get_async_session() as session:
            for user in users:
                new_user = UserModel(
                    id=user['id'],
                    username=user['username'],
                    email=user['email'],
                    password_hash=user['password_hash'],
                    role=user['role'],
                    is_active=user['is_active']
                )
                session.add(new_user)
            await session.commit()
        
        # 插入到 Neo4j
        for user in users:
            await self.neo4j_client.execute_query(
                """
                CREATE (u:User {
                    id: $id,
                    username: $username,
                    email: $email,
                    role: $role,
                    is_active: $is_active,
                    created_at: datetime()
                })
                """,
                user
            )
        
        logger.info(f"已创建 {len(users)} 个用户")
        return True
    
    async def _seed_documents(self) -> bool:
        """
        填充文档数据
        """
        logger.info("填充文档数据...")
        
        documents = [
            {
                "id": str(uuid.uuid4()),
                "title": "企业数字化转型白皮书",
                "content": "数字化转型是企业在数字经济时代的必然选择。本文档详细介绍了数字化转型的核心要素、实施路径和最佳实践。",
                "file_path": "/documents/digital_transformation.pdf",
                "file_type": "pdf",
                "file_size": 2048576,
                "status": "processed",
                "metadata": json.dumps({
                    "author": "技术部",
                    "department": "IT",
                    "tags": ["数字化", "转型", "战略"]
                })
            },
            {
                "id": str(uuid.uuid4()),
                "title": "人工智能技术应用指南",
                "content": "人工智能技术在企业中的应用越来越广泛。本指南涵盖了机器学习、深度学习、自然语言处理等核心技术的应用场景。",
                "file_path": "/documents/ai_application_guide.docx",
                "file_type": "docx",
                "file_size": 1536000,
                "status": "processed",
                "metadata": json.dumps({
                    "author": "AI团队",
                    "department": "研发",
                    "tags": ["人工智能", "机器学习", "应用"]
                })
            },
            {
                "id": str(uuid.uuid4()),
                "title": "数据安全管理规范",
                "content": "数据安全是企业信息化建设的重要组成部分。本规范详细说明了数据分类、访问控制、加密传输等安全措施。",
                "file_path": "/documents/data_security_policy.pdf",
                "file_type": "pdf",
                "file_size": 1024000,
                "status": "processed",
                "metadata": json.dumps({
                    "author": "安全部",
                    "department": "信息安全",
                    "tags": ["数据安全", "规范", "管理"]
                })
            },
            {
                "id": str(uuid.uuid4()),
                "title": "云计算架构设计方案",
                "content": "云计算为企业提供了灵活、可扩展的IT基础设施。本方案介绍了混合云架构的设计原则和实施步骤。",
                "file_path": "/documents/cloud_architecture.pptx",
                "file_type": "pptx",
                "file_size": 3072000,
                "status": "processing",
                "metadata": json.dumps({
                    "author": "架构师",
                    "department": "技术架构",
                    "tags": ["云计算", "架构", "设计"]
                })
            }
        ]
        
        # 插入到 StarRocks
        from backend.models.document import DocumentModel
        from backend.config.database import get_async_session
        
        async with get_async_session() as session:
            for doc in documents:
                upload_time = datetime.now() - timedelta(days=30, hours=12)
                processed_time = upload_time + timedelta(hours=2) if doc['status'] == 'processed' else None
                
                new_document = DocumentModel(
                    id=doc['id'],
                    title=doc['title'],
                    content=doc['content'],
                    file_path=doc['file_path'],
                    file_type=doc['file_type'],
                    file_size=doc['file_size'],
                    upload_time=upload_time,
                    processed_time=processed_time,
                    status=doc['status'],
                    metadata=doc['metadata']
                )
                session.add(new_document)
            await session.commit()
        
        # 插入到 Neo4j
        for doc in documents:
            await self.neo4j_client.execute_query(
                """
                CREATE (d:Document {
                    id: $id,
                    title: $title,
                    file_path: $file_path,
                    file_type: $file_type,
                    status: $status,
                    created_at: datetime()
                })
                """,
                {
                    "id": doc['id'],
                    "title": doc['title'],
                    "file_path": doc['file_path'],
                    "file_type": doc['file_type'],
                    "status": doc['status']
                }
            )
        
        logger.info(f"已创建 {len(documents)} 个文档")
        return True
    
    async def _seed_entities_and_relations(self) -> bool:
        """
        填充实体和关系数据
        """
        logger.info("填充实体和关系数据...")
        
        # 获取文档ID
        from backend.models.document import DocumentModel
        from sqlalchemy import select
        from backend.core.database import get_async_session
        
        async with get_async_session() as session:
            doc_query = select(DocumentModel.id).limit(1)
            result = await session.execute(doc_query)
            doc_row = result.first()
            doc_id = doc_row[0] if doc_row else str(uuid.uuid4())
        
        entities = [
            {
                "id": str(uuid.uuid4()),
                "name": "数字化转型",
                "type": "概念",
                "description": "企业利用数字技术改变业务模式和运营方式的过程",
                "confidence": 0.95,
                "source_document_id": doc_id,
                "properties": json.dumps({
                    "category": "战略概念",
                    "importance": "高"
                })
            },
            {
                "id": str(uuid.uuid4()),
                "name": "人工智能",
                "type": "技术",
                "description": "模拟人类智能的计算机系统和技术",
                "confidence": 0.98,
                "source_document_id": doc_id,
                "properties": json.dumps({
                    "category": "核心技术",
                    "maturity": "成熟"
                })
            },
            {
                "id": str(uuid.uuid4()),
                "name": "机器学习",
                "type": "技术",
                "description": "让计算机系统自动学习和改进的技术方法",
                "confidence": 0.92,
                "source_document_id": doc_id,
                "properties": json.dumps({
                    "category": "AI子技术",
                    "applications": ["预测", "分类", "聚类"]
                })
            },
            {
                "id": str(uuid.uuid4()),
                "name": "云计算",
                "type": "技术",
                "description": "通过网络提供可扩展的计算资源和服务",
                "confidence": 0.96,
                "source_document_id": doc_id,
                "properties": json.dumps({
                    "category": "基础设施",
                    "deployment_models": ["公有云", "私有云", "混合云"]
                })
            },
            {
                "id": str(uuid.uuid4()),
                "name": "数据安全",
                "type": "概念",
                "description": "保护数据免受未授权访问、使用、披露、破坏的措施",
                "confidence": 0.94,
                "source_document_id": doc_id,
                "properties": json.dumps({
                    "category": "安全概念",
                    "priority": "最高"
                })
            }
        ]
        
        # 插入实体到 StarRocks
        from backend.models.knowledge import EntityModel
        from backend.config.database import get_async_session
        
        async with get_async_session() as session:
            for entity in entities:
                new_entity = EntityModel(
                    id=entity['id'],
                    name=entity['name'],
                    entity_type=entity['type'],
                    description=entity['description'],
                    confidence=entity['confidence'],
                    source_documents=entity['source_document_id'],
                    properties=entity['properties']
                )
                session.add(new_entity)
            await session.commit()
        
        # 插入实体到 Neo4j
        for entity in entities:
            await self.neo4j_client.execute_query(
                """
                CREATE (e:Entity {
                    id: $id,
                    name: $name,
                    type: $type,
                    description: $description,
                    confidence: $confidence,
                    created_at: datetime()
                })
                """,
                entity
            )
        
        # 创建关系
        relations = [
            {
                "id": str(uuid.uuid4()),
                "source_entity_id": entities[1]['id'],  # 人工智能
                "target_entity_id": entities[2]['id'],  # 机器学习
                "relation_type": "包含",
                "confidence": 0.90,
                "source_document_id": doc_id,
                "properties": json.dumps({"relationship_strength": "强"})
            },
            {
                "id": str(uuid.uuid4()),
                "source_entity_id": entities[0]['id'],  # 数字化转型
                "target_entity_id": entities[1]['id'],  # 人工智能
                "relation_type": "依赖",
                "confidence": 0.85,
                "source_document_id": doc_id,
                "properties": json.dumps({"dependency_type": "技术支撑"})
            },
            {
                "id": str(uuid.uuid4()),
                "source_entity_id": entities[0]['id'],  # 数字化转型
                "target_entity_id": entities[3]['id'],  # 云计算
                "relation_type": "依赖",
                "confidence": 0.88,
                "source_document_id": doc_id,
                "properties": json.dumps({"dependency_type": "基础设施"})
            },
            {
                "id": str(uuid.uuid4()),
                "source_entity_id": entities[3]['id'],  # 云计算
                "target_entity_id": entities[4]['id'],  # 数据安全
                "relation_type": "关联",
                "confidence": 0.82,
                "source_document_id": doc_id,
                "properties": json.dumps({"association_type": "安全考虑"})
            }
        ]
        
        # 插入关系到 StarRocks
        from backend.models.knowledge import RelationModel
        from backend.config.database import get_async_session
        
        async with get_async_session() as session:
            for relation in relations:
                new_relation = RelationModel(
                    id=relation['id'],
                    source_entity_id=relation['source_entity_id'],
                    target_entity_id=relation['target_entity_id'],
                    relation_type=relation['relation_type'],
                    confidence=relation['confidence'],
                    source_documents=relation['source_document_id'],
                    properties=relation['properties']
                )
                session.add(new_relation)
            await session.commit()
        
        # 插入关系到 Neo4j
        for relation in relations:
            await self.neo4j_client.execute_query(
                """
                MATCH (source:Entity {id: $source_id}), (target:Entity {id: $target_id})
                CREATE (source)-[r:RELATES_TO {
                    id: $id,
                    type: $relation_type,
                    confidence: $confidence,
                    created_at: datetime()
                }]->(target)
                """,
                {
                    "id": relation['id'],
                    "source_id": relation['source_entity_id'],
                    "target_id": relation['target_entity_id'],
                    "relation_type": relation['relation_type'],
                    "confidence": relation['confidence']
                }
            )
        
        logger.info(f"已创建 {len(entities)} 个实体和 {len(relations)} 个关系")
        return True
    
    async def _seed_cache_data(self) -> bool:
        """
        填充缓存数据
        """
        logger.info("填充缓存数据...")
        
        # 缓存一些常用的搜索结果
        cache_data = {
            "search:数字化转型": json.dumps({
                "results": [
                    {"id": "1", "title": "数字化转型白皮书", "score": 0.95},
                    {"id": "2", "title": "企业数字化实践", "score": 0.88}
                ],
                "total": 2,
                "cached_at": datetime.now().isoformat()
            }),
            "search:人工智能": json.dumps({
                "results": [
                    {"id": "2", "title": "AI应用指南", "score": 0.98},
                    {"id": "3", "title": "机器学习实践", "score": 0.92}
                ],
                "total": 2,
                "cached_at": datetime.now().isoformat()
            }),
            "config:system": json.dumps({
                "max_upload_size": 100 * 1024 * 1024,  # 100MB
                "supported_formats": ["pdf", "docx", "txt", "md"],
                "embedding_model": "text-embedding-ada-002",
                "chunk_size": 1000,
                "chunk_overlap": 200
            })
        }
        
        for key, value in cache_data.items():
            await self.redis_client.set(key, value, ex=3600)  # 1小时过期
        
        logger.info(f"已缓存 {len(cache_data)} 条数据")
        return True
    
    async def _seed_storage_data(self) -> bool:
        """
        填充对象存储数据
        """
        logger.info("填充对象存储数据...")
        
        # 创建示例文件
        sample_files = {
            "documents/sample.txt": "这是一个示例文档，用于测试文档上传和处理功能。",
            "processed/sample_processed.json": json.dumps({
                "document_id": "sample",
                "entities": ["示例", "文档", "测试"],
                "processed_at": datetime.now().isoformat()
            }),
            "models/config.json": json.dumps({
                "model_name": "text-embedding-ada-002",
                "dimension": 1536,
                "max_tokens": 8191
            })
        }
        
        for file_path, content in sample_files.items():
            bucket, object_name = file_path.split('/', 1)
            
            # 确保存储桶存在
            if not await self.minio_client.bucket_exists(bucket):
                await self.minio_client.make_bucket(bucket)
            
            # 上传文件
            await self.minio_client.put_object(
                bucket, object_name, content.encode('utf-8'), len(content.encode('utf-8'))
            )
        
        logger.info(f"已上传 {len(sample_files)} 个示例文件")
        return True
    
    async def cleanup(self):
        """
        清理资源连接
        """
        if self.neo4j_client:
            await self.neo4j_client.close()
        if self.starrocks_client:
            await self.starrocks_client.close()
        if self.redis_client:
            await self.redis_client.close()
        if self.minio_client:
            await self.minio_client.close()

async def main():
    """
    主函数
    """
    import argparse
    
    parser = argparse.ArgumentParser(description="示例数据填充工具")
    parser.add_argument("--clear", action="store_true", help="清除现有数据")
    parser.add_argument("--component", choices=["users", "documents", "entities", "cache", "storage"], 
                       help="只填充指定组件的数据")
    
    args = parser.parse_args()
    
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 加载设置
    settings = Settings()
    
    # 创建数据填充器
    seeder = DataSeeder(settings)
    
    try:
        await seeder.initialize_clients()
        
        if args.component:
            # 填充指定组件
            if args.component == "users":
                success = await seeder._seed_users()
            elif args.component == "documents":
                success = await seeder._seed_documents()
            elif args.component == "entities":
                success = await seeder._seed_entities_and_relations()
            elif args.component == "cache":
                success = await seeder._seed_cache_data()
            elif args.component == "storage":
                success = await seeder._seed_storage_data()
            
            return 0 if success else 1
        else:
            # 填充所有数据
            results = await seeder.seed_all(clear_existing=args.clear)
            
            failed_components = [k for k, v in results.items() if not v]
            
            if failed_components:
                logger.error(f"以下组件数据填充失败: {failed_components}")
                return 1
            else:
                logger.info("所有示例数据填充成功！")
                return 0
    
    except Exception as e:
        logger.error(f"数据填充过程中发生错误: {e}")
        return 1
    
    finally:
        await seeder.cleanup()

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)