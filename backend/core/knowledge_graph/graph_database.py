from typing import List, Dict, Any, Optional, Tuple, Set, Union
from dataclasses import dataclass, field
from enum import Enum
import asyncio
import logging
from datetime import datetime, timedelta
from collections import defaultdict
import json
import sqlite3
import aiosqlite
from contextlib import asynccontextmanager
import pickle
import hashlib
from concurrent.futures import ThreadPoolExecutor
import threading
from sqlalchemy import select, insert, update, delete, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.models.knowledge import Entity, Relation, KnowledgeGraph
from backend.models.knowledge_graph_models import GraphModel, GraphEntityModel, GraphRelationModel, GraphStatisticsModel
from backend.api.deps import CacheManager
from backend.config.database import get_async_session

logger = logging.getLogger(__name__)

class DatabaseType(Enum):
    """数据库类型"""
    SQLITE = "sqlite"
    NEO4J = "neo4j"
    MEMORY = "memory"

class IndexType(Enum):
    """索引类型"""
    BTREE = "btree"
    HASH = "hash"
    FULLTEXT = "fulltext"

class TransactionIsolation(Enum):
    """事务隔离级别"""
    READ_UNCOMMITTED = "read_uncommitted"
    READ_COMMITTED = "read_committed"
    REPEATABLE_READ = "repeatable_read"
    SERIALIZABLE = "serializable"

@dataclass
class DatabaseConfig:
    """数据库配置"""
    db_type: DatabaseType = DatabaseType.SQLITE
    connection_string: str = "knowledge_graph.db"
    max_connections: int = 10
    connection_timeout: int = 30
    enable_wal: bool = True
    enable_foreign_keys: bool = True
    cache_size: int = 10000
    page_size: int = 4096
    auto_vacuum: bool = True
    enable_indexes: bool = True
    backup_interval: int = 3600  # 秒
    
@dataclass
class QueryResult:
    """查询结果"""
    success: bool
    data: Any = None
    error: Optional[str] = None
    execution_time: float = 0.0
    rows_affected: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class TransactionContext:
    """事务上下文"""
    transaction_id: str
    isolation_level: TransactionIsolation
    start_time: datetime
    operations: List[Dict[str, Any]] = field(default_factory=list)
    is_active: bool = True
    
class GraphDatabase:
    """图数据库接口"""
    
    def __init__(self, config: DatabaseConfig, cache_manager: CacheManager = None):
        self.config = config
        self.cache_manager = cache_manager
        self._connection_pool = []
        self._pool_lock = threading.Lock()
        self._executor = ThreadPoolExecutor(max_workers=4)
        self._transactions = {}
        self._indexes = set()
        self._is_initialized = False
        
    async def initialize(self):
        """初始化数据库"""
        try:
            if self.config.db_type == DatabaseType.SQLITE:
                await self._initialize_sqlite()
            elif self.config.db_type == DatabaseType.MEMORY:
                await self._initialize_memory()
            else:
                raise ValueError(f"不支持的数据库类型: {self.config.db_type}")
            
            # 创建表结构
            await self._create_tables()
            
            # 创建索引
            if self.config.enable_indexes:
                await self._create_indexes()
            
            self._is_initialized = True
            logger.info(f"图数据库初始化完成: {self.config.db_type.value}")
            
        except Exception as e:
            logger.error(f"图数据库初始化失败: {str(e)}")
            raise
    
    async def _initialize_sqlite(self):
        """初始化SQLite数据库"""
        # 创建连接池
        for _ in range(self.config.max_connections):
            conn = await aiosqlite.connect(
                self.config.connection_string,
                timeout=self.config.connection_timeout
            )
            
            # 配置SQLite
            if self.config.enable_wal:
                await conn.execute("PRAGMA journal_mode=WAL")
            
            if self.config.enable_foreign_keys:
                await conn.execute("PRAGMA foreign_keys=ON")
            
            # 验证配置值为整数，防止SQL注入
            cache_size = int(self.config.cache_size)
            page_size = int(self.config.page_size)
            
            await conn.execute("PRAGMA cache_size=?", (cache_size,))
            await conn.execute("PRAGMA page_size=?", (page_size,))
            
            if self.config.auto_vacuum:
                await conn.execute("PRAGMA auto_vacuum=INCREMENTAL")
            
            await conn.commit()
            self._connection_pool.append(conn)
    
    async def _initialize_memory(self):
        """初始化内存数据库"""
        self._memory_entities = {}
        self._memory_relations = {}
        self._memory_graphs = {}
        
    async def _create_tables(self):
        """创建表结构"""
        if self.config.db_type == DatabaseType.SQLITE:
            await self._create_sqlite_tables()
    
    async def _create_sqlite_tables(self):
        """创建SQLite表结构"""
        async with self._get_connection() as conn:
            # 实体表
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS entities (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    entity_type TEXT NOT NULL,
                    properties TEXT,
                    metadata TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    graph_id TEXT,
                    FOREIGN KEY (graph_id) REFERENCES graphs(id)
                )
            """)
            
            # 关系表
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS relations (
                    id TEXT PRIMARY KEY,
                    source_id TEXT NOT NULL,
                    target_id TEXT NOT NULL,
                    relation_type TEXT NOT NULL,
                    properties TEXT,
                    metadata TEXT,
                    confidence REAL DEFAULT 1.0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    graph_id TEXT,
                    FOREIGN KEY (source_id) REFERENCES entities(id),
                    FOREIGN KEY (target_id) REFERENCES entities(id),
                    FOREIGN KEY (graph_id) REFERENCES graphs(id)
                )
            """)
            
            # 图表
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS graphs (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    metadata TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 图统计表
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS graph_statistics (
                    graph_id TEXT PRIMARY KEY,
                    num_entities INTEGER DEFAULT 0,
                    num_relations INTEGER DEFAULT 0,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (graph_id) REFERENCES graphs(id)
                )
            """)
            
            await conn.commit()
    
    async def _create_indexes(self):
        """创建索引"""
        if self.config.db_type == DatabaseType.SQLITE:
            await self._create_sqlite_indexes()
    
    async def _create_sqlite_indexes(self):
        """创建SQLite索引"""
        async with self._get_connection() as conn:
            indexes = [
                "CREATE INDEX IF NOT EXISTS idx_entities_name ON entities(name)",
                "CREATE INDEX IF NOT EXISTS idx_entities_type ON entities(entity_type)",
                "CREATE INDEX IF NOT EXISTS idx_entities_graph ON entities(graph_id)",
                "CREATE INDEX IF NOT EXISTS idx_relations_source ON relations(source_id)",
                "CREATE INDEX IF NOT EXISTS idx_relations_target ON relations(target_id)",
                "CREATE INDEX IF NOT EXISTS idx_relations_type ON relations(relation_type)",
                "CREATE INDEX IF NOT EXISTS idx_relations_graph ON relations(graph_id)",
                "CREATE INDEX IF NOT EXISTS idx_relations_confidence ON relations(confidence)"
            ]
            
            for index_sql in indexes:
                await conn.execute(index_sql)
                self._indexes.add(index_sql.split()[-1])  # 提取索引名
            
            await conn.commit()
    
    @asynccontextmanager
    async def _get_connection(self):
        """获取数据库连接"""
        if self.config.db_type == DatabaseType.SQLITE:
            with self._pool_lock:
                if self._connection_pool:
                    conn = self._connection_pool.pop()
                else:
                    conn = await aiosqlite.connect(
                        self.config.connection_string,
                        timeout=self.config.connection_timeout
                    )
            
            try:
                yield conn
            finally:
                with self._pool_lock:
                    if len(self._connection_pool) < self.config.max_connections:
                        self._connection_pool.append(conn)
                    else:
                        await conn.close()
        else:
            yield None
    
    async def create_graph(self, graph: KnowledgeGraph) -> QueryResult:
        """创建图"""
        try:
            start_time = datetime.now()
            
            if self.config.db_type == DatabaseType.SQLITE:
                result = await self._create_graph_sqlite(graph)
            elif self.config.db_type == DatabaseType.MEMORY:
                result = await self._create_graph_memory(graph)
            else:
                return QueryResult(
                    success=False,
                    error=f"不支持的数据库类型: {self.config.db_type}"
                )
            
            result.execution_time = (datetime.now() - start_time).total_seconds()
            
            # 缓存结果
            if self.cache_manager and result.success:
                await self.cache_manager.set(
                    f"graph:{graph.id}",
                    graph,
                    ttl=3600
                )
            
            return result
            
        except Exception as e:
            logger.error(f"创建图失败: {str(e)}")
            return QueryResult(
                success=False,
                error=str(e)
            )
    
    async def _create_graph_sqlite(self, graph: KnowledgeGraph) -> QueryResult:
        """在SQLite中创建图"""
        async with get_async_session() as session:
            try:
                # 插入图记录
                graph_stmt = insert(GraphModel).values(
                    id=graph.id,
                    name=graph.name,
                    description=graph.description,
                    metadata=json.dumps(graph.metadata) if graph.metadata else None
                )
                graph_stmt = graph_stmt.on_duplicate_key_update(
                    name=graph_stmt.inserted.name,
                    description=graph_stmt.inserted.description,
                    metadata=graph_stmt.inserted.metadata
                )
                await session.execute(graph_stmt)
                
                # 插入实体
                for entity in graph.entities:
                    entity_stmt = insert(GraphEntityModel).values(
                        id=entity.id,
                        name=entity.name,
                        entity_type=entity.entity_type,
                        properties=json.dumps(entity.properties) if entity.properties else None,
                        metadata=json.dumps(entity.metadata) if entity.metadata else None,
                        graph_id=graph.id
                    )
                    entity_stmt = entity_stmt.on_duplicate_key_update(
                        name=entity_stmt.inserted.name,
                        entity_type=entity_stmt.inserted.entity_type,
                        properties=entity_stmt.inserted.properties,
                        metadata=entity_stmt.inserted.metadata
                    )
                    await session.execute(entity_stmt)
                
                # 插入关系
                for relation in graph.relations:
                    relation_stmt = insert(GraphRelationModel).values(
                        id=relation.id,
                        source_id=relation.source_id,
                        target_id=relation.target_id,
                        relation_type=relation.relation_type,
                        properties=json.dumps(relation.properties) if relation.properties else None,
                        metadata=json.dumps(relation.metadata) if relation.metadata else None,
                        confidence=relation.confidence,
                        graph_id=graph.id
                    )
                    relation_stmt = relation_stmt.on_duplicate_key_update(
                        source_id=relation_stmt.inserted.source_id,
                        target_id=relation_stmt.inserted.target_id,
                        relation_type=relation_stmt.inserted.relation_type,
                        properties=relation_stmt.inserted.properties,
                        metadata=relation_stmt.inserted.metadata,
                        confidence=relation_stmt.inserted.confidence
                    )
                    await session.execute(relation_stmt)
                
                # 更新统计信息
                stats_stmt = insert(GraphStatisticsModel).values(
                    graph_id=graph.id,
                    num_entities=len(graph.entities),
                    num_relations=len(graph.relations)
                )
                stats_stmt = stats_stmt.on_duplicate_key_update(
                    num_entities=stats_stmt.inserted.num_entities,
                    num_relations=stats_stmt.inserted.num_relations
                )
                await session.execute(stats_stmt)
                
                await session.commit()
                
                return QueryResult(
                    success=True,
                    rows_affected=len(graph.entities) + len(graph.relations) + 1
                )
            except Exception as e:
                await session.rollback()
                raise e
    
    async def _create_graph_memory(self, graph: KnowledgeGraph) -> QueryResult:
        """在内存中创建图"""
        self._memory_graphs[graph.id] = graph
        
        for entity in graph.entities:
            self._memory_entities[entity.id] = entity
        
        for relation in graph.relations:
            self._memory_relations[relation.id] = relation
        
        return QueryResult(
            success=True,
            rows_affected=len(graph.entities) + len(graph.relations) + 1
        )
    
    async def save_graph(self, graph: KnowledgeGraph) -> QueryResult:
        """保存知识图谱"""
        try:
            if self.config.db_type == DatabaseType.SQLITE:
                return await self._save_graph_sqlalchemy(graph)
            elif self.config.db_type == DatabaseType.MEMORY:
                return await self._save_graph_memory(graph)
            else:
                return QueryResult(
                    success=False,
                    error=f"不支持的数据库类型: {self.config.db_type}"
                )
        except Exception as e:
            logger.error(f"保存图失败: {str(e)}")
            return QueryResult(
                success=False,
                error=str(e)
            )
    
    async def _save_graph_sqlalchemy(self, graph: KnowledgeGraph) -> QueryResult:
        """使用SQLAlchemy保存图"""
        async with get_async_session() as session:
            try:
                # 保存或更新图信息
                graph_stmt = select(GraphModel).where(GraphModel.id == graph.id)
                existing_graph = await session.execute(graph_stmt)
                existing_graph = existing_graph.scalar_one_or_none()
                
                if existing_graph:
                    # 更新现有图
                    existing_graph.name = graph.name
                    existing_graph.description = graph.description
                    existing_graph.metadata = json.dumps(graph.metadata) if graph.metadata else None
                else:
                    # 创建新图
                    new_graph = GraphModel(
                        id=graph.id,
                        name=graph.name,
                        description=graph.description,
                        metadata=json.dumps(graph.metadata) if graph.metadata else None
                    )
                    session.add(new_graph)
                
                # 保存实体
                for entity in graph.entities:
                    entity_stmt = select(GraphEntityModel).where(GraphEntityModel.id == entity.id)
                    existing_entity = await session.execute(entity_stmt)
                    existing_entity = existing_entity.scalar_one_or_none()
                    
                    if existing_entity:
                        # 更新现有实体
                        existing_entity.name = entity.name
                        existing_entity.entity_type = entity.entity_type
                        existing_entity.properties = json.dumps(entity.properties) if entity.properties else None
                        existing_entity.metadata = json.dumps(entity.metadata) if entity.metadata else None
                    else:
                        # 创建新实体
                        new_entity = GraphEntityModel(
                            id=entity.id,
                            name=entity.name,
                            entity_type=entity.entity_type,
                            properties=json.dumps(entity.properties) if entity.properties else None,
                            metadata=json.dumps(entity.metadata) if entity.metadata else None,
                            graph_id=graph.id
                        )
                        session.add(new_entity)
                
                # 保存关系
                for relation in graph.relations:
                    relation_stmt = select(GraphRelationModel).where(GraphRelationModel.id == relation.id)
                    existing_relation = await session.execute(relation_stmt)
                    existing_relation = existing_relation.scalar_one_or_none()
                    
                    if existing_relation:
                        # 更新现有关系
                        existing_relation.source_id = relation.source_id
                        existing_relation.target_id = relation.target_id
                        existing_relation.relation_type = relation.relation_type
                        existing_relation.properties = json.dumps(relation.properties) if relation.properties else None
                        existing_relation.metadata = json.dumps(relation.metadata) if relation.metadata else None
                        existing_relation.confidence = relation.confidence
                    else:
                        # 创建新关系
                        new_relation = GraphRelationModel(
                            id=relation.id,
                            source_id=relation.source_id,
                            target_id=relation.target_id,
                            relation_type=relation.relation_type,
                            properties=json.dumps(relation.properties) if relation.properties else None,
                            metadata=json.dumps(relation.metadata) if relation.metadata else None,
                            confidence=relation.confidence,
                            graph_id=graph.id
                        )
                        session.add(new_relation)
                
                # 更新统计信息
                stats_stmt = select(GraphStatisticsModel).where(GraphStatisticsModel.graph_id == graph.id)
                existing_stats = await session.execute(stats_stmt)
                existing_stats = existing_stats.scalar_one_or_none()
                
                if existing_stats:
                    existing_stats.num_entities = len(graph.entities)
                    existing_stats.num_relations = len(graph.relations)
                    existing_stats.last_updated = func.now()
                else:
                    new_stats = GraphStatisticsModel(
                        graph_id=graph.id,
                        num_entities=len(graph.entities),
                        num_relations=len(graph.relations)
                    )
                    session.add(new_stats)
                
                await session.commit()
                
                return QueryResult(
                    success=True,
                    rows_affected=len(graph.entities) + len(graph.relations) + 1
                )
                
            except Exception as e:
                await session.rollback()
                raise e

    async def load_graph(self, graph_id: str) -> QueryResult:
        """加载知识图谱"""
        try:
            if self.config.db_type == DatabaseType.SQLITE:
                return await self._load_graph_sqlalchemy(graph_id)
            elif self.config.db_type == DatabaseType.MEMORY:
                return await self._load_graph_memory(graph_id)
            else:
                return QueryResult(
                    success=False,
                    error=f"不支持的数据库类型: {self.config.db_type}"
                )
        except Exception as e:
            logger.error(f"加载图失败: {str(e)}")
            return QueryResult(
                success=False,
                error=str(e)
            )

    async def _load_graph_sqlalchemy(self, graph_id: str) -> QueryResult:
        """使用SQLAlchemy加载图"""
        async with get_async_session() as session:
            # 获取图信息
            graph_stmt = select(GraphModel).where(GraphModel.id == graph_id)
            graph_result = await session.execute(graph_stmt)
            graph_row = graph_result.scalar_one_or_none()
            
            if not graph_row:
                return QueryResult(
                    success=False,
                    error=f"图不存在: {graph_id}"
                )
            
            # 获取实体
            entities = []
            entities_stmt = select(GraphEntityModel).where(GraphEntityModel.graph_id == graph_id)
            entities_result = await session.execute(entities_stmt)
            
            for entity_row in entities_result.scalars():
                entity = Entity(
                    id=entity_row.id,
                    name=entity_row.name,
                    entity_type=entity_row.entity_type,
                    properties=json.loads(entity_row.properties) if entity_row.properties else {},
                    metadata=json.loads(entity_row.metadata) if entity_row.metadata else {}
                )
                entities.append(entity)
            
            # 获取关系
            relations = []
            relations_stmt = select(GraphRelationModel).where(GraphRelationModel.graph_id == graph_id)
            relations_result = await session.execute(relations_stmt)
            
            for relation_row in relations_result.scalars():
                relation = Relation(
                    id=relation_row.id,
                    source_id=relation_row.source_id,
                    target_id=relation_row.target_id,
                    relation_type=relation_row.relation_type,
                    properties=json.loads(relation_row.properties) if relation_row.properties else {},
                    metadata=json.loads(relation_row.metadata) if relation_row.metadata else {},
                    confidence=relation_row.confidence
                )
                relations.append(relation)
            
            # 构建知识图谱对象
            graph = KnowledgeGraph(
                id=graph_row.id,
                name=graph_row.name,
                description=graph_row.description,
                entities=entities,
                relations=relations,
                metadata=json.loads(graph_row.metadata) if graph_row.metadata else {}
            )
            
            return QueryResult(
                success=True,
                data=graph
            )

    async def _load_graph_memory(self, graph_id: str) -> QueryResult:
        """从内存获取图"""
        graph = self._memory_graphs.get(graph_id)
        if not graph:
            return QueryResult(
                success=False,
                error=f"图不存在: {graph_id}"
            )
        
        return QueryResult(
            success=True,
            data=graph
        )
    
    async def add_entity(self, graph_id: str, entity: Entity) -> QueryResult:
        """添加实体"""
        try:
            start_time = datetime.now()
            
            if self.config.db_type == DatabaseType.SQLITE:
                result = await self._add_entity_sqlite(graph_id, entity)
            elif self.config.db_type == DatabaseType.MEMORY:
                result = await self._add_entity_memory(graph_id, entity)
            else:
                return QueryResult(
                    success=False,
                    error=f"不支持的数据库类型: {self.config.db_type}"
                )
            
            result.execution_time = (datetime.now() - start_time).total_seconds()
            
            # 清除相关缓存
            if self.cache_manager and result.success:
                await self.cache_manager.delete(f"graph:{graph_id}")
                await self.cache_manager.delete(f"entity:{entity.id}")
            
            return result
            
        except Exception as e:
            logger.error(f"添加实体失败: {str(e)}")
            return QueryResult(
                success=False,
                error=str(e)
            )
    
    async def _add_entity_sqlite(self, graph_id: str, entity: Entity) -> QueryResult:
        """在SQLite中添加实体"""
        async with get_async_session() as session:
            try:
                # 插入或替换实体
                entity_stmt = insert(GraphEntityModel).values(
                    id=entity.id,
                    name=entity.name,
                    entity_type=entity.entity_type,
                    properties=json.dumps(entity.properties) if entity.properties else None,
                    metadata=json.dumps(entity.metadata) if entity.metadata else None,
                    graph_id=graph_id
                )
                entity_stmt = entity_stmt.on_duplicate_key_update(
                    name=entity_stmt.inserted.name,
                    entity_type=entity_stmt.inserted.entity_type,
                    properties=entity_stmt.inserted.properties,
                    metadata=entity_stmt.inserted.metadata
                )
                await session.execute(entity_stmt)
                
                # 更新统计信息
                stats_stmt = update(GraphStatisticsModel).where(
                    GraphStatisticsModel.graph_id == graph_id
                ).values(
                    num_entities=GraphStatisticsModel.num_entities + 1,
                    last_updated=func.current_timestamp()
                )
                await session.execute(stats_stmt)
                
                await session.commit()
                
                return QueryResult(
                    success=True,
                    rows_affected=1
                )
            except Exception as e:
                await session.rollback()
                raise e
    
    async def _add_entity_memory(self, graph_id: str, entity: Entity) -> QueryResult:
        """在内存中添加实体"""
        self._memory_entities[entity.id] = entity
        
        # 更新图中的实体列表
        if graph_id in self._memory_graphs:
            graph = self._memory_graphs[graph_id]
            if entity not in graph.entities:
                graph.entities.append(entity)
        
        return QueryResult(
            success=True,
            rows_affected=1
        )
    
    async def add_relation(self, graph_id: str, relation: Relation) -> QueryResult:
        """添加关系"""
        try:
            start_time = datetime.now()
            
            if self.config.db_type == DatabaseType.SQLITE:
                result = await self._add_relation_sqlite(graph_id, relation)
            elif self.config.db_type == DatabaseType.MEMORY:
                result = await self._add_relation_memory(graph_id, relation)
            else:
                return QueryResult(
                    success=False,
                    error=f"不支持的数据库类型: {self.config.db_type}"
                )
            
            result.execution_time = (datetime.now() - start_time).total_seconds()
            
            # 清除相关缓存
            if self.cache_manager and result.success:
                await self.cache_manager.delete(f"graph:{graph_id}")
                await self.cache_manager.delete(f"relation:{relation.id}")
            
            return result
            
        except Exception as e:
            logger.error(f"添加关系失败: {str(e)}")
            return QueryResult(
                success=False,
                error=str(e)
            )
    
    async def _add_relation_sqlite(self, graph_id: str, relation: Relation) -> QueryResult:
        """在SQLite中添加关系"""
        async with get_async_session() as session:
            try:
                # 插入或替换关系
                relation_stmt = insert(GraphRelationModel).values(
                    id=relation.id,
                    source_id=relation.source_id,
                    target_id=relation.target_id,
                    relation_type=relation.relation_type,
                    properties=json.dumps(relation.properties) if relation.properties else None,
                    metadata=json.dumps(relation.metadata) if relation.metadata else None,
                    confidence=relation.confidence,
                    graph_id=graph_id
                )
                relation_stmt = relation_stmt.on_duplicate_key_update(
                    source_id=relation_stmt.inserted.source_id,
                    target_id=relation_stmt.inserted.target_id,
                    relation_type=relation_stmt.inserted.relation_type,
                    properties=relation_stmt.inserted.properties,
                    metadata=relation_stmt.inserted.metadata,
                    confidence=relation_stmt.inserted.confidence
                )
                await session.execute(relation_stmt)
                
                # 更新统计信息
                stats_stmt = update(GraphStatisticsModel).where(
                    GraphStatisticsModel.graph_id == graph_id
                ).values(
                    num_relations=GraphStatisticsModel.num_relations + 1,
                    last_updated=func.current_timestamp()
                )
                await session.execute(stats_stmt)
                
                await session.commit()
                
                return QueryResult(
                    success=True,
                    rows_affected=1
                )
            except Exception as e:
                await session.rollback()
                raise e
    
    async def _add_relation_memory(self, graph_id: str, relation: Relation) -> QueryResult:
        """在内存中添加关系"""
        self._memory_relations[relation.id] = relation
        
        # 更新图中的关系列表
        if graph_id in self._memory_graphs:
            graph = self._memory_graphs[graph_id]
            if relation not in graph.relations:
                graph.relations.append(relation)
        
        return QueryResult(
            success=True,
            rows_affected=1
        )
    
    async def search_entities(
        self,
        graph_id: str,
        query: str = None,
        entity_type: str = None,
        limit: int = 100
    ) -> QueryResult:
        """搜索实体"""
        try:
            if self.config.db_type == DatabaseType.SQLITE:
                return await self._search_entities_sqlalchemy(graph_id, query, entity_type, limit)
            elif self.config.db_type == DatabaseType.MEMORY:
                return await self._search_entities_memory(graph_id, query, entity_type, limit)
            else:
                return QueryResult(
                    success=False,
                    error=f"不支持的数据库类型: {self.config.db_type}"
                )
        except Exception as e:
            logger.error(f"搜索实体失败: {str(e)}")
            return QueryResult(
                success=False,
                error=str(e)
            )
    
    async def _search_entities_sqlalchemy(
        self,
        graph_id: str,
        query: str,
        entity_type: str,
        limit: int
    ) -> QueryResult:
        """使用SQLAlchemy搜索实体"""
        async with get_async_session() as session:
            # 构建查询条件
            conditions = [GraphEntityModel.graph_id == graph_id]
            
            if query:
                conditions.append(GraphEntityModel.name.like(f"%{query}%"))
            
            if entity_type:
                conditions.append(GraphEntityModel.entity_type == entity_type)
            
            # 执行查询
            stmt = select(GraphEntityModel).where(and_(*conditions)).limit(limit)
            result = await session.execute(stmt)
            
            entities = []
            for row in result.scalars():
                entity = Entity(
                    id=row.id,
                    name=row.name,
                    entity_type=row.entity_type,
                    properties=json.loads(row.properties) if row.properties else {},
                    metadata=json.loads(row.metadata) if row.metadata else {}
                )
                entities.append(entity)
            
            return QueryResult(
                success=True,
                data=entities
            )

    async def _search_entities_memory(
        self,
        graph_id: str,
        query: str,
        entity_type: str,
        limit: int
    ) -> QueryResult:
        """在内存中搜索实体"""
        entities = []
        
        if graph_id in self._memory_graphs:
            graph = self._memory_graphs[graph_id]
            
            for entity in graph.entities:
                # 应用过滤条件
                if query and query.lower() not in entity.name.lower():
                    continue
                
                if entity_type and entity.entity_type != entity_type:
                    continue
                
                entities.append(entity)
                
                if len(entities) >= limit:
                    break
        
        return QueryResult(
            success=True,
            data=entities
        )
    
    async def get_entity_neighbors(
        self,
        graph_id: str,
        entity_id: str,
        relation_types: List[str] = None,
        max_depth: int = 1
    ) -> QueryResult:
        """获取实体邻居"""
        try:
            start_time = datetime.now()
            
            if self.config.db_type == DatabaseType.SQLITE:
                result = await self._get_entity_neighbors_sqlite(graph_id, entity_id, relation_types, max_depth)
            elif self.config.db_type == DatabaseType.MEMORY:
                result = await self._get_entity_neighbors_memory(graph_id, entity_id, relation_types, max_depth)
            else:
                return QueryResult(
                    success=False,
                    error=f"不支持的数据库类型: {self.config.db_type}"
                )
            
            result.execution_time = (datetime.now() - start_time).total_seconds()
            return result
            
        except Exception as e:
            logger.error(f"获取实体邻居失败: {str(e)}")
            return QueryResult(
                success=False,
                error=str(e)
            )
    
    async def _get_entity_neighbors_sqlite(
        self,
        graph_id: str,
        entity_id: str,
        relation_types: List[str],
        max_depth: int
    ) -> QueryResult:
        """在SQLite中获取实体邻居"""
        async with get_async_session() as session:
            try:
                neighbors = set()
                current_entities = {entity_id}
                
                for depth in range(max_depth):
                    if not current_entities:
                        break
                    
                    next_entities = set()
                    
                    for current_entity in current_entities:
                        # 查找出边
                        outbound_query = select(GraphRelationModel.target_id).where(
                            and_(
                                GraphRelationModel.graph_id == graph_id,
                                GraphRelationModel.source_id == current_entity
                            )
                        )
                        
                        if relation_types:
                            outbound_query = outbound_query.where(
                                GraphRelationModel.relation_type.in_(relation_types)
                            )
                        
                        result = await session.execute(outbound_query)
                        for row in result:
                            target_id = row[0]
                            if target_id not in neighbors and target_id != entity_id:
                                neighbors.add(target_id)
                                next_entities.add(target_id)
                        
                        # 查找入边
                        inbound_query = select(GraphRelationModel.source_id).where(
                            and_(
                                GraphRelationModel.graph_id == graph_id,
                                GraphRelationModel.target_id == current_entity
                            )
                        )
                        
                        if relation_types:
                            inbound_query = inbound_query.where(
                                GraphRelationModel.relation_type.in_(relation_types)
                            )
                        
                        result = await session.execute(inbound_query)
                        for row in result:
                            source_id = row[0]
                            if source_id not in neighbors and source_id != entity_id:
                                neighbors.add(source_id)
                                next_entities.add(source_id)
                    
                    current_entities = next_entities
                
                # 获取邻居实体详细信息
                neighbor_entities = []
                if neighbors:
                    entities_query = select(
                        GraphEntityModel.id,
                        GraphEntityModel.name,
                        GraphEntityModel.entity_type,
                        GraphEntityModel.properties,
                        GraphEntityModel.metadata
                    ).where(GraphEntityModel.id.in_(list(neighbors)))
                    
                    result = await session.execute(entities_query)
                    for row in result:
                        entity = Entity(
                            id=row[0],
                            name=row[1],
                            entity_type=row[2],
                            properties=json.loads(row[3]) if row[3] else {},
                            metadata=json.loads(row[4]) if row[4] else {}
                        )
                        neighbor_entities.append(entity)
                
                return QueryResult(
                    success=True,
                    data=neighbor_entities
                )
            except Exception as e:
                raise e
    
    async def _get_entity_neighbors_memory(
        self,
        graph_id: str,
        entity_id: str,
        relation_types: List[str],
        max_depth: int
    ) -> QueryResult:
        """在内存中获取实体邻居"""
        if graph_id not in self._memory_graphs:
            return QueryResult(
                success=False,
                error=f"图不存在: {graph_id}"
            )
        
        graph = self._memory_graphs[graph_id]
        neighbors = set()
        current_entities = {entity_id}
        
        for depth in range(max_depth):
            if not current_entities:
                break
            
            next_entities = set()
            
            for relation in graph.relations:
                if relation_types and relation.relation_type not in relation_types:
                    continue
                
                if relation.source_id in current_entities:
                    if relation.target_id not in neighbors and relation.target_id != entity_id:
                        neighbors.add(relation.target_id)
                        next_entities.add(relation.target_id)
                
                if relation.target_id in current_entities:
                    if relation.source_id not in neighbors and relation.source_id != entity_id:
                        neighbors.add(relation.source_id)
                        next_entities.add(relation.source_id)
            
            current_entities = next_entities
        
        # 获取邻居实体
        neighbor_entities = []
        for entity in graph.entities:
            if entity.id in neighbors:
                neighbor_entities.append(entity)
        
        return QueryResult(
            success=True,
            data=neighbor_entities
        )
    
    async def delete_entity(self, graph_id: str, entity_id: str) -> QueryResult:
        """删除实体"""
        try:
            start_time = datetime.now()
            
            if self.config.db_type == DatabaseType.SQLITE:
                result = await self._delete_entity_sqlite(graph_id, entity_id)
            elif self.config.db_type == DatabaseType.MEMORY:
                result = await self._delete_entity_memory(graph_id, entity_id)
            else:
                return QueryResult(
                    success=False,
                    error=f"不支持的数据库类型: {self.config.db_type}"
                )
            
            result.execution_time = (datetime.now() - start_time).total_seconds()
            
            # 清除相关缓存
            if self.cache_manager and result.success:
                await self.cache_manager.delete(f"graph:{graph_id}")
                await self.cache_manager.delete(f"entity:{entity_id}")
            
            return result
            
        except Exception as e:
            logger.error(f"删除实体失败: {str(e)}")
            return QueryResult(
                success=False,
                error=str(e)
            )
    
    async def _delete_entity_sqlite(self, graph_id: str, entity_id: str) -> QueryResult:
        """在SQLite中删除实体"""
        async with get_async_session() as session:
            try:
                # 删除相关关系
                relations_stmt = delete(GraphRelationModel).where(
                    and_(
                        GraphRelationModel.graph_id == graph_id,
                        or_(
                            GraphRelationModel.source_id == entity_id,
                            GraphRelationModel.target_id == entity_id
                        )
                    )
                )
                await session.execute(relations_stmt)
                
                # 删除实体
                entity_stmt = delete(GraphEntityModel).where(
                    and_(
                        GraphEntityModel.graph_id == graph_id,
                        GraphEntityModel.id == entity_id
                    )
                )
                result = await session.execute(entity_stmt)
                rows_affected = result.rowcount
                
                # 更新统计信息
                if rows_affected > 0:
                    stats_stmt = update(GraphStatisticsModel).where(
                        GraphStatisticsModel.graph_id == graph_id
                    ).values(
                        num_entities=GraphStatisticsModel.num_entities - 1,
                        last_updated=func.current_timestamp()
                    )
                    await session.execute(stats_stmt)
                
                await session.commit()
                
                return QueryResult(
                    success=True,
                    rows_affected=rows_affected
                )
            except Exception as e:
                await session.rollback()
                raise e
    
    async def _delete_entity_memory(self, graph_id: str, entity_id: str) -> QueryResult:
        """在内存中删除实体"""
        if graph_id not in self._memory_graphs:
            return QueryResult(
                success=False,
                error=f"图不存在: {graph_id}"
            )
        
        graph = self._memory_graphs[graph_id]
        
        # 删除实体
        entity_found = False
        graph.entities = [e for e in graph.entities if e.id != entity_id]
        
        if entity_id in self._memory_entities:
            del self._memory_entities[entity_id]
            entity_found = True
        
        # 删除相关关系
        relations_to_remove = []
        for relation in graph.relations:
            if relation.source_id == entity_id or relation.target_id == entity_id:
                relations_to_remove.append(relation)
        
        for relation in relations_to_remove:
            graph.relations.remove(relation)
            if relation.id in self._memory_relations:
                del self._memory_relations[relation.id]
        
        return QueryResult(
            success=True,
            rows_affected=1 if entity_found else 0
        )
    
    async def get_graph_statistics(self, graph_id: str) -> QueryResult:
        """获取图统计信息"""
        try:
            if self.config.db_type == DatabaseType.SQLITE:
                return await self._get_graph_statistics_sqlalchemy(graph_id)
            elif self.config.db_type == DatabaseType.MEMORY:
                return await self._get_graph_statistics_memory(graph_id)
            else:
                return QueryResult(
                    success=False,
                    error=f"不支持的数据库类型: {self.config.db_type}"
                )
        except Exception as e:
            logger.error(f"获取图统计信息失败: {str(e)}")
            return QueryResult(
                success=False,
                error=str(e)
            )
    
    async def _get_graph_statistics_sqlalchemy(self, graph_id: str) -> QueryResult:
        """使用SQLAlchemy获取图统计信息"""
        async with get_async_session() as session:
            # 获取基本统计信息
            stats_stmt = select(GraphStatisticsModel).where(GraphStatisticsModel.graph_id == graph_id)
            stats_result = await session.execute(stats_stmt)
            stats_row = stats_result.scalar_one_or_none()
            
            if not stats_row:
                # 重新计算统计信息
                entities_count_stmt = select(func.count(GraphEntityModel.id)).where(GraphEntityModel.graph_id == graph_id)
                entities_result = await session.execute(entities_count_stmt)
                num_entities = entities_result.scalar()
                
                relations_count_stmt = select(func.count(GraphRelationModel.id)).where(GraphRelationModel.graph_id == graph_id)
                relations_result = await session.execute(relations_count_stmt)
                num_relations = relations_result.scalar()
                
                # 更新统计信息
                new_stats = GraphStatisticsModel(
                    graph_id=graph_id,
                    num_entities=num_entities,
                    num_relations=num_relations
                )
                session.add(new_stats)
                await session.commit()
            else:
                num_entities = stats_row.num_entities
                num_relations = stats_row.num_relations
            
            # 获取实体类型分布
            entity_types_stmt = select(
                GraphEntityModel.entity_type,
                func.count(GraphEntityModel.id)
            ).where(
                GraphEntityModel.graph_id == graph_id
            ).group_by(GraphEntityModel.entity_type)
            
            entity_types_result = await session.execute(entity_types_stmt)
            entity_types = {row[0]: row[1] for row in entity_types_result}
            
            # 获取关系类型分布
            relation_types_stmt = select(
                GraphRelationModel.relation_type,
                func.count(GraphRelationModel.id)
            ).where(
                GraphRelationModel.graph_id == graph_id
            ).group_by(GraphRelationModel.relation_type)
            
            relation_types_result = await session.execute(relation_types_stmt)
            relation_types = {row[0]: row[1] for row in relation_types_result}
            
            statistics = {
                "num_entities": num_entities,
                "num_relations": num_relations,
                "entity_types": entity_types,
                "relation_types": relation_types,
                "density": num_relations / (num_entities * (num_entities - 1)) if num_entities > 1 else 0
            }
            
            return QueryResult(
                success=True,
                data=statistics
            )
    
    async def _get_graph_statistics_memory(self, graph_id: str) -> QueryResult:
        """在内存中获取图统计信息"""
        if graph_id not in self._memory_graphs:
            return QueryResult(
                success=False,
                error=f"图不存在: {graph_id}"
            )
        
        graph = self._memory_graphs[graph_id]
        
        # 计算实体类型分布
        entity_types = defaultdict(int)
        for entity in graph.entities:
            entity_types[entity.entity_type] += 1
        
        # 计算关系类型分布
        relation_types = defaultdict(int)
        for relation in graph.relations:
            relation_types[relation.relation_type] += 1
        
        num_entities = len(graph.entities)
        num_relations = len(graph.relations)
        
        statistics = {
            "num_entities": num_entities,
            "num_relations": num_relations,
            "entity_types": dict(entity_types),
            "relation_types": dict(relation_types),
            "density": (2 * num_relations) / (num_entities * (num_entities - 1)) if num_entities > 1 else 0
        }
        
        return QueryResult(
            success=True,
            data=statistics
        )
    
    async def backup_graph(self, graph_id: str, backup_path: str) -> QueryResult:
        """备份图"""
        try:
            start_time = datetime.now()
            
            # 获取图数据
            graph_result = await self.get_graph(graph_id)
            if not graph_result.success:
                return graph_result
            
            # 序列化图数据
            graph_data = {
                "graph": graph_result.data.__dict__,
                "timestamp": datetime.now().isoformat(),
                "version": "1.0"
            }
            
            # 写入备份文件
            with open(backup_path, 'w', encoding='utf-8') as f:
                json.dump(graph_data, f, indent=2, ensure_ascii=False, default=str)
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            return QueryResult(
                success=True,
                execution_time=execution_time,
                metadata={"backup_path": backup_path}
            )
            
        except Exception as e:
            logger.error(f"备份图失败: {str(e)}")
            return QueryResult(
                success=False,
                error=str(e)
            )
    
    async def restore_graph(self, backup_path: str) -> QueryResult:
        """恢复图"""
        try:
            start_time = datetime.now()
            
            # 读取备份文件
            with open(backup_path, 'r', encoding='utf-8') as f:
                graph_data = json.load(f)
            
            # 重建图对象
            graph_dict = graph_data["graph"]
            
            entities = []
            for entity_dict in graph_dict.get("entities", []):
                entity = Entity(**entity_dict)
                entities.append(entity)
            
            relations = []
            for relation_dict in graph_dict.get("relations", []):
                relation = Relation(**relation_dict)
                relations.append(relation)
            
            graph = KnowledgeGraph(
                id=graph_dict["id"],
                name=graph_dict["name"],
                description=graph_dict.get("description"),
                entities=entities,
                relations=relations,
                metadata=graph_dict.get("metadata", {})
            )
            
            # 创建图
            result = await self.create_graph(graph)
            result.execution_time = (datetime.now() - start_time).total_seconds()
            
            return result
            
        except Exception as e:
            logger.error(f"恢复图失败: {str(e)}")
            return QueryResult(
                success=False,
                error=str(e)
            )
    
    async def cleanup(self):
        """清理资源"""
        try:
            # 关闭连接池
            with self._pool_lock:
                for conn in self._connection_pool:
                    await conn.close()
                self._connection_pool.clear()
            
            # 关闭线程池
            if self._executor:
                self._executor.shutdown(wait=True)
            
            # 清理内存数据
            if hasattr(self, '_memory_entities'):
                self._memory_entities.clear()
            if hasattr(self, '_memory_relations'):
                self._memory_relations.clear()
            if hasattr(self, '_memory_graphs'):
                self._memory_graphs.clear()
            
            logger.info("图数据库资源清理完成")
            
        except Exception as e:
            logger.error(f"图数据库资源清理失败: {str(e)}")