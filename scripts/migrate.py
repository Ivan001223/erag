#!/usr/bin/env python3
"""
数据库迁移脚本

该脚本用于管理企业知识库系统的数据库架构迁移：
- 版本控制
- 架构更新
- 数据迁移
- 回滚支持
"""

import asyncio
import logging
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path

from backend.config.settings import Settings
from backend.connectors.neo4j_client import Neo4jClient
from backend.connectors.starrocks_client import StarRocksClient
from backend.utils.logger import get_logger

logger = get_logger(__name__)

class Migration:
    """
    单个迁移定义
    """
    
    def __init__(self, version: str, description: str, up_sql: List[str], down_sql: List[str]):
        self.version = version
        self.description = description
        self.up_sql = up_sql
        self.down_sql = down_sql
        self.timestamp = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "version": self.version,
            "description": self.description,
            "up_sql": self.up_sql,
            "down_sql": self.down_sql,
            "timestamp": self.timestamp.isoformat()
        }

class MigrationManager:
    """
    数据库迁移管理器
    
    负责管理数据库架构的版本控制和迁移。
    """
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.neo4j_client = None
        self.starrocks_client = None
        self.migrations_dir = Path("migrations")
        self.migrations_dir.mkdir(exist_ok=True)
    
    async def initialize_clients(self):
        """
        初始化数据库客户端
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
        
        await self.neo4j_client.connect()
        await self.starrocks_client.connect()
    
    async def create_migration_tables(self):
        """
        创建迁移历史表
        """
        # StarRocks 迁移历史表 - 保留原生SQL，因为这是DDL语句
        starrocks_migration_table = """
        CREATE TABLE IF NOT EXISTS knowledge_base.migrations (
            version VARCHAR(50) NOT NULL,
            description VARCHAR(500),
            applied_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            rollback_sql TEXT
        ) ENGINE=OLAP
        DUPLICATE KEY(version)
        DISTRIBUTED BY HASH(version) BUCKETS 1
        PROPERTIES ("replication_num" = "1")
        """
        
        # 使用SQLAlchemy方法创建数据库
        await self.starrocks_client.create_database_if_not_exists()
        await self.starrocks_client.execute(starrocks_migration_table)
        
        # Neo4j 迁移历史节点 - 保留原生Cypher，因为这是DDL语句
        neo4j_migration_constraint = """
        CREATE CONSTRAINT migration_version_unique IF NOT EXISTS 
        FOR (m:Migration) REQUIRE m.version IS UNIQUE
        """
        
        await self.neo4j_client.execute_query(neo4j_migration_constraint)
    
    async def get_applied_migrations(self) -> List[str]:
        """
        获取已应用的迁移版本列表
        """
        # 从 StarRocks 获取 - 使用SQLAlchemy方法
        result = await self.starrocks_client.get_applied_migrations()
        
        return [row[0] for row in result] if result else []
    
    def load_migrations(self) -> List[Migration]:
        """
        加载所有迁移文件
        """
        migrations = []
        
        # 预定义迁移
        predefined_migrations = self._get_predefined_migrations()
        migrations.extend(predefined_migrations)
        
        # 从文件加载自定义迁移
        for migration_file in sorted(self.migrations_dir.glob("*.json")):
            try:
                with open(migration_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    migration = Migration(
                        version=data['version'],
                        description=data['description'],
                        up_sql=data['up_sql'],
                        down_sql=data['down_sql']
                    )
                    migrations.append(migration)
            except Exception as e:
                logger.error(f"加载迁移文件 {migration_file} 失败: {e}")
        
        return sorted(migrations, key=lambda m: m.version)
    
    def _get_predefined_migrations(self) -> List[Migration]:
        """
        获取预定义的迁移
        """
        migrations = []
        
        # 迁移 v1.0.1: 添加实体置信度索引
        migrations.append(Migration(
            version="v1.0.1",
            description="添加实体置信度索引",
            up_sql=[
                "CREATE INDEX entity_confidence_index IF NOT EXISTS FOR (e:Entity) ON (e.confidence)",
                "ALTER TABLE knowledge_base.entities ADD INDEX idx_confidence (confidence)"
            ],
            down_sql=[
                "DROP INDEX entity_confidence_index IF EXISTS",
                "ALTER TABLE knowledge_base.entities DROP INDEX idx_confidence"
            ]
        ))
        
        # 迁移 v1.0.2: 添加文档处理状态
        migrations.append(Migration(
            version="v1.0.2",
            description="添加文档处理状态枚举",
            up_sql=[
                "ALTER TABLE knowledge_base.documents ADD COLUMN processing_status VARCHAR(50) DEFAULT 'pending'",
                "ALTER TABLE knowledge_base.documents ADD COLUMN error_message TEXT"
            ],
            down_sql=[
                "ALTER TABLE knowledge_base.documents DROP COLUMN processing_status",
                "ALTER TABLE knowledge_base.documents DROP COLUMN error_message"
            ]
        ))
        
        # 迁移 v1.0.3: 添加向量存储表
        migrations.append(Migration(
            version="v1.0.3",
            description="添加向量存储表",
            up_sql=[
                """
                CREATE TABLE IF NOT EXISTS knowledge_base.embeddings (
                    id VARCHAR(255) NOT NULL,
                    entity_id VARCHAR(255),
                    document_id VARCHAR(255),
                    chunk_id VARCHAR(255),
                    embedding_model VARCHAR(100),
                    vector_dimension INT,
                    vector_data TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                ) ENGINE=OLAP
                DUPLICATE KEY(id)
                DISTRIBUTED BY HASH(id) BUCKETS 10
                PROPERTIES ("replication_num" = "1")
                """
            ],
            down_sql=[
                "DROP TABLE IF EXISTS knowledge_base.embeddings"
            ]
        ))
        
        # 迁移 v1.0.4: 添加用户和权限管理
        migrations.append(Migration(
            version="v1.0.4",
            description="添加用户和权限管理",
            up_sql=[
                """
                CREATE TABLE IF NOT EXISTS knowledge_base.users (
                    id VARCHAR(255) NOT NULL,
                    username VARCHAR(100) UNIQUE,
                    email VARCHAR(255) UNIQUE,
                    password_hash VARCHAR(255),
                    role VARCHAR(50) DEFAULT 'user',
                    is_active BOOLEAN DEFAULT true,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                ) ENGINE=OLAP
                DUPLICATE KEY(id)
                DISTRIBUTED BY HASH(id) BUCKETS 5
                PROPERTIES ("replication_num" = "1")
                """,
                "CREATE CONSTRAINT user_username_unique IF NOT EXISTS FOR (u:User) REQUIRE u.username IS UNIQUE",
                "CREATE CONSTRAINT user_email_unique IF NOT EXISTS FOR (u:User) REQUIRE u.email IS UNIQUE"
            ],
            down_sql=[
                "DROP TABLE IF EXISTS knowledge_base.users",
                "DROP CONSTRAINT user_username_unique IF EXISTS",
                "DROP CONSTRAINT user_email_unique IF EXISTS"
            ]
        ))
        
        return migrations
    
    async def apply_migration(self, migration: Migration) -> bool:
        """
        应用单个迁移
        """
        logger.info(f"应用迁移 {migration.version}: {migration.description}")
        
        try:
            # 执行迁移 SQL
            for sql in migration.up_sql:
                if sql.strip().upper().startswith(('CREATE CONSTRAINT', 'CREATE INDEX', 'DROP CONSTRAINT', 'DROP INDEX')):
                    # Neo4j 语句
                    await self.neo4j_client.execute_query(sql)
                else:
                    # StarRocks 语句
                    await self.starrocks_client.execute(sql)
            
            # 记录迁移历史
            from backend.models.migration import MigrationModel
            from backend.config.database import get_async_session
            
            async with get_async_session() as session:
                new_migration = MigrationModel(
                    version=migration.version,
                    description=migration.description,
                    rollback_sql=json.dumps(migration.down_sql)
                )
                session.add(new_migration)
                await session.commit()
            
            # 在 Neo4j 中也记录 - 保留原生Cypher，因为这是数据操作语句
            await self.neo4j_client.execute_query(
                "CREATE (m:Migration {version: $version, description: $description, applied_at: datetime()})",
                {"version": migration.version, "description": migration.description}
            )
            
            logger.info(f"迁移 {migration.version} 应用成功")
            return True
        
        except Exception as e:
            logger.error(f"迁移 {migration.version} 应用失败: {e}")
            return False
    
    async def rollback_migration(self, version: str) -> bool:
        """
        回滚指定版本的迁移
        """
        logger.info(f"回滚迁移 {version}")
        
        try:
            # 获取回滚 SQL - 使用SQLAlchemy方法
            result = await self.starrocks_client.get_migration_rollback_sql(version)
            
            if not result:
                logger.error(f"未找到迁移版本 {version}")
                return False
            
            rollback_sql = json.loads(result[0][0])
            
            # 执行回滚 SQL
            for sql in rollback_sql:
                if sql.strip().upper().startswith(('CREATE CONSTRAINT', 'CREATE INDEX', 'DROP CONSTRAINT', 'DROP INDEX')):
                    # Neo4j 语句
                    await self.neo4j_client.execute_query(sql)
                else:
                    # StarRocks 语句
                    await self.starrocks_client.execute(sql)
            
            # 删除迁移记录 - 使用SQLAlchemy方法
            await self.starrocks_client.delete_migration_record(version)
            
            # 删除Neo4j中的迁移记录 - 保留原生Cypher，因为这是数据操作语句
            await self.neo4j_client.execute_query(
                "MATCH (m:Migration {version: $version}) DELETE m",
                {"version": version}
            )
            
            logger.info(f"迁移 {version} 回滚成功")
            return True
        
        except Exception as e:
            logger.error(f"迁移 {version} 回滚失败: {e}")
            return False
    
    async def migrate_up(self, target_version: Optional[str] = None) -> bool:
        """
        向上迁移到指定版本（或最新版本）
        """
        applied_migrations = await self.get_applied_migrations()
        all_migrations = self.load_migrations()
        
        pending_migrations = [
            m for m in all_migrations 
            if m.version not in applied_migrations and 
            (target_version is None or m.version <= target_version)
        ]
        
        if not pending_migrations:
            logger.info("没有待应用的迁移")
            return True
        
        logger.info(f"发现 {len(pending_migrations)} 个待应用的迁移")
        
        for migration in pending_migrations:
            success = await self.apply_migration(migration)
            if not success:
                logger.error(f"迁移过程在版本 {migration.version} 处停止")
                return False
        
        logger.info("所有迁移应用成功")
        return True
    
    async def migrate_down(self, target_version: str) -> bool:
        """
        向下迁移到指定版本
        """
        applied_migrations = await self.get_applied_migrations()
        
        migrations_to_rollback = [
            version for version in applied_migrations 
            if version > target_version
        ]
        
        migrations_to_rollback.sort(reverse=True)  # 按版本倒序回滚
        
        if not migrations_to_rollback:
            logger.info(f"当前版本已经是 {target_version} 或更低")
            return True
        
        logger.info(f"需要回滚 {len(migrations_to_rollback)} 个迁移")
        
        for version in migrations_to_rollback:
            success = await self.rollback_migration(version)
            if not success:
                logger.error(f"回滚过程在版本 {version} 处停止")
                return False
        
        logger.info(f"成功回滚到版本 {target_version}")
        return True
    
    async def get_migration_status(self) -> Dict[str, Any]:
        """
        获取迁移状态
        """
        applied_migrations = await self.get_applied_migrations()
        all_migrations = self.load_migrations()
        
        pending_migrations = [
            m.version for m in all_migrations 
            if m.version not in applied_migrations
        ]
        
        return {
            "applied_migrations": applied_migrations,
            "pending_migrations": pending_migrations,
            "current_version": applied_migrations[-1] if applied_migrations else None,
            "latest_version": all_migrations[-1].version if all_migrations else None
        }
    
    async def cleanup(self):
        """
        清理资源连接
        """
        if self.neo4j_client:
            await self.neo4j_client.close()
        if self.starrocks_client:
            await self.starrocks_client.close()

async def main():
    """
    主函数
    """
    import argparse
    
    parser = argparse.ArgumentParser(description="数据库迁移工具")
    parser.add_argument("command", choices=["up", "down", "status", "create"], help="迁移命令")
    parser.add_argument("--version", help="目标版本")
    parser.add_argument("--description", help="迁移描述（用于create命令）")
    
    args = parser.parse_args()
    
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 加载设置
    settings = Settings()
    
    # 创建迁移管理器
    manager = MigrationManager(settings)
    
    try:
        await manager.initialize_clients()
        await manager.create_migration_tables()
        
        if args.command == "up":
            success = await manager.migrate_up(args.version)
            return 0 if success else 1
        
        elif args.command == "down":
            if not args.version:
                logger.error("down 命令需要指定目标版本")
                return 1
            success = await manager.migrate_down(args.version)
            return 0 if success else 1
        
        elif args.command == "status":
            status = await manager.get_migration_status()
            print(json.dumps(status, indent=2, ensure_ascii=False))
            return 0
        
        elif args.command == "create":
            if not args.version or not args.description:
                logger.error("create 命令需要指定版本和描述")
                return 1
            
            # 创建迁移模板
            migration_template = {
                "version": args.version,
                "description": args.description,
                "up_sql": [
                    "-- 在此添加向上迁移的 SQL 语句"
                ],
                "down_sql": [
                    "-- 在此添加向下迁移的 SQL 语句"
                ]
            }
            
            migration_file = manager.migrations_dir / f"{args.version}.json"
            with open(migration_file, 'w', encoding='utf-8') as f:
                json.dump(migration_template, f, indent=2, ensure_ascii=False)
            
            logger.info(f"迁移文件已创建: {migration_file}")
            return 0
    
    except Exception as e:
        logger.error(f"迁移过程中发生错误: {e}")
        return 1
    
    finally:
        await manager.cleanup()

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)