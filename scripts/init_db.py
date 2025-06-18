#!/usr/bin/env python3
"""
数据库初始化脚本

该脚本用于初始化企业知识库系统的所有数据库组件：
- Neo4j 图数据库
- StarRocks 数据仓库
- Redis 缓存
- MinIO 对象存储
"""

import asyncio
import logging
from typing import Dict, Any

from backend.config.settings import Settings
from backend.connectors.neo4j_client import Neo4jClient
from backend.connectors.starrocks_client import StarRocksClient
from backend.connectors.redis_client import RedisClient
from backend.connectors.minio_client import MinIOClient
from backend.utils.logger import get_logger

logger = get_logger(__name__)

class DatabaseInitializer:
    """
    数据库初始化器
    
    负责初始化所有数据库组件，创建必要的表、索引和配置。
    """
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.neo4j_client = None
        self.starrocks_client = None
        self.redis_client = None
        self.minio_client = None
    
    async def initialize_all(self) -> Dict[str, bool]:
        """
        初始化所有数据库组件
        
        返回:
            Dict[str, bool]: 各组件初始化结果
        """
        results = {}
        
        logger.info("开始初始化数据库组件...")
        
        # 初始化 Neo4j
        try:
            results['neo4j'] = await self._init_neo4j()
        except Exception as e:
            logger.error(f"Neo4j 初始化失败: {e}")
            results['neo4j'] = False
        
        # 初始化 StarRocks
        try:
            results['starrocks'] = await self._init_starrocks()
        except Exception as e:
            logger.error(f"StarRocks 初始化失败: {e}")
            results['starrocks'] = False
        
        # 初始化 Redis
        try:
            results['redis'] = await self._init_redis()
        except Exception as e:
            logger.error(f"Redis 初始化失败: {e}")
            results['redis'] = False
        
        # 初始化 MinIO
        try:
            results['minio'] = await self._init_minio()
        except Exception as e:
            logger.error(f"MinIO 初始化失败: {e}")
            results['minio'] = False
        
        logger.info(f"数据库初始化完成: {results}")
        return results
    
    async def _init_neo4j(self) -> bool:
        """
        初始化 Neo4j 图数据库
        
        创建约束、索引和基础节点类型
        """
        logger.info("初始化 Neo4j 图数据库...")
        
        self.neo4j_client = Neo4jClient(
            uri=self.settings.neo4j_url,
            user=self.settings.neo4j_user,
            password=self.settings.neo4j_password
        )
        
        await self.neo4j_client.connect()
        
        # 创建约束
        constraints = [
            "CREATE CONSTRAINT entity_id_unique IF NOT EXISTS FOR (e:Entity) REQUIRE e.id IS UNIQUE",
            "CREATE CONSTRAINT document_id_unique IF NOT EXISTS FOR (d:Document) REQUIRE d.id IS UNIQUE",
            "CREATE CONSTRAINT user_id_unique IF NOT EXISTS FOR (u:User) REQUIRE u.id IS UNIQUE"
        ]
        
        for constraint in constraints:
            await self.neo4j_client.execute_query(constraint)
            logger.debug(f"创建约束: {constraint}")
        
        # 创建索引
        indexes = [
            "CREATE INDEX entity_name_index IF NOT EXISTS FOR (e:Entity) ON (e.name)",
            "CREATE INDEX entity_type_index IF NOT EXISTS FOR (e:Entity) ON (e.type)",
            "CREATE INDEX document_title_index IF NOT EXISTS FOR (d:Document) ON (d.title)",
            "CREATE INDEX relation_type_index IF NOT EXISTS FOR ()-[r:RELATES_TO]-() ON (r.type)"
        ]
        
        for index in indexes:
            await self.neo4j_client.execute_query(index)
            logger.debug(f"创建索引: {index}")
        
        logger.info("Neo4j 初始化完成")
        return True
    
    async def _init_starrocks(self) -> bool:
        """
        初始化 StarRocks 数据仓库
        
        创建数据库、表和分区
        """
        logger.info("初始化 StarRocks 数据仓库...")
        
        self.starrocks_client = StarRocksClient(
            host=self.settings.starrocks_host,
            port=self.settings.starrocks_port,
            user=self.settings.starrocks_user,
            password=self.settings.starrocks_password
        )
        
        await self.starrocks_client.connect()
        
        # 创建数据库
        # 创建数据库 - 保留原生SQL，因为这是DDL语句
        await self.starrocks_client.execute(
            "CREATE DATABASE IF NOT EXISTS knowledge_base"
        )
        
        await self.starrocks_client.execute("USE knowledge_base")
        
        # 创建文档表 - 保留原生SQL，因为这是DDL语句
        document_table_sql = """
        CREATE TABLE IF NOT EXISTS documents (
            id VARCHAR(255) NOT NULL,
            title VARCHAR(1000),
            content TEXT,
            file_path VARCHAR(500),
            file_type VARCHAR(50),
            file_size BIGINT,
            upload_time DATETIME,
            processed_time DATETIME,
            status VARCHAR(50),
            metadata JSON,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=OLAP
        DUPLICATE KEY(id)
        PARTITION BY RANGE(upload_time) (
            PARTITION p202401 VALUES [("2024-01-01"), ("2024-02-01")),
            PARTITION p202402 VALUES [("2024-02-01"), ("2024-03-01")),
            PARTITION p202403 VALUES [("2024-03-01"), ("2024-04-01"))
        )
        DISTRIBUTED BY HASH(id) BUCKETS 10
        PROPERTIES (
            "replication_num" = "1",
            "dynamic_partition.enable" = "true",
            "dynamic_partition.time_unit" = "MONTH",
            "dynamic_partition.start" = "-12",
            "dynamic_partition.end" = "3",
            "dynamic_partition.prefix" = "p",
            "dynamic_partition.buckets" = "10"
        )
        """
        
        await self.starrocks_client.execute(document_table_sql)
        
        # 创建实体表 - 保留原生SQL，因为这是DDL语句
        entity_table_sql = """
        CREATE TABLE IF NOT EXISTS entities (
            id VARCHAR(255) NOT NULL,
            name VARCHAR(500),
            type VARCHAR(100),
            description TEXT,
            confidence DOUBLE,
            source_document_id VARCHAR(255),
            properties JSON,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=OLAP
        DUPLICATE KEY(id)
        DISTRIBUTED BY HASH(id) BUCKETS 10
        PROPERTIES ("replication_num" = "1")
        """
        
        await self.starrocks_client.execute(entity_table_sql)
        
        # 创建关系表 - 保留原生SQL，因为这是DDL语句
        relation_table_sql = """
        CREATE TABLE IF NOT EXISTS relations (
            id VARCHAR(255) NOT NULL,
            source_entity_id VARCHAR(255),
            target_entity_id VARCHAR(255),
            relation_type VARCHAR(100),
            confidence DOUBLE,
            source_document_id VARCHAR(255),
            properties JSON,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=OLAP
        DUPLICATE KEY(id)
        DISTRIBUTED BY HASH(id) BUCKETS 10
        PROPERTIES ("replication_num" = "1")
        """
        
        await self.starrocks_client.execute(relation_table_sql)
        
        logger.info("StarRocks 初始化完成")
        return True
    
    async def _init_redis(self) -> bool:
        """
        初始化 Redis 缓存
        
        设置缓存策略和键空间
        """
        logger.info("初始化 Redis 缓存...")
        
        self.redis_client = RedisClient(
            host=self.settings.redis_host,
            port=self.settings.redis_port,
            password=self.settings.redis_password,
            db=self.settings.redis_db
        )
        
        await self.redis_client.connect()
        
        # 设置缓存配置
        cache_configs = {
            "cache:entity:ttl": "3600",  # 实体缓存1小时
            "cache:document:ttl": "7200",  # 文档缓存2小时
            "cache:search:ttl": "1800",  # 搜索结果缓存30分钟
            "cache:embedding:ttl": "86400"  # 向量缓存24小时
        }
        
        for key, value in cache_configs.items():
            await self.redis_client.set(key, value)
        
        logger.info("Redis 初始化完成")
        return True
    
    async def _init_minio(self) -> bool:
        """
        初始化 MinIO 对象存储
        
        创建存储桶和访问策略
        """
        logger.info("初始化 MinIO 对象存储...")
        
        self.minio_client = MinIOClient(
            endpoint=self.settings.minio_endpoint,
            access_key=self.settings.minio_access_key,
            secret_key=self.settings.minio_secret_key,
            secure=self.settings.minio_secure
        )
        
        await self.minio_client.connect()
        
        # 创建存储桶
        buckets = [
            "documents",  # 原始文档
            "processed",  # 处理后的文档
            "embeddings",  # 向量文件
            "models",  # 模型文件
            "exports"  # 导出文件
        ]
        
        for bucket in buckets:
            if not await self.minio_client.bucket_exists(bucket):
                await self.minio_client.make_bucket(bucket)
                logger.debug(f"创建存储桶: {bucket}")
        
        logger.info("MinIO 初始化完成")
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
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 加载设置
    settings = Settings()
    
    # 初始化数据库
    initializer = DatabaseInitializer(settings)
    
    try:
        results = await initializer.initialize_all()
        
        # 检查结果
        failed_components = [k for k, v in results.items() if not v]
        
        if failed_components:
            logger.error(f"以下组件初始化失败: {failed_components}")
            return 1
        else:
            logger.info("所有数据库组件初始化成功！")
            return 0
    
    except Exception as e:
        logger.error(f"数据库初始化过程中发生错误: {e}")
        return 1
    
    finally:
        await initializer.cleanup()

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)