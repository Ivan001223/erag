import asyncio
from typing import Dict, List, Any, Optional, Union, Tuple
from datetime import datetime, date
from decimal import Decimal

from sqlalchemy import create_engine, MetaData, Table, Column, String, Text, Integer, Float, DateTime, Boolean, JSON, Index
from sqlalchemy.dialects.mysql import VARCHAR, LONGTEXT, BIGINT, DECIMAL
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import select, insert, update, delete, func, text
from sqlalchemy.exc import SQLAlchemyError

from backend.utils.logger import get_logger
from backend.config.constants import TaskStatus, TaskType
from backend.models.database import (
    DocumentModel, DocumentChunkModel, EntityModel, RelationModel,
    TaskModel, QueryLogModel, MetricModel
)

# StarRocks专用的Base类
StarRocksBase = declarative_base()


class StarRocksDocumentModel(StarRocksBase):
    """StarRocks文档表模型"""
    __tablename__ = 'starrocks_documents'
    
    id = Column(VARCHAR(64), primary_key=True)
    title = Column(VARCHAR(500), nullable=False)
    content = Column(LONGTEXT)
    doc_type = Column(VARCHAR(50), nullable=False)
    source_path = Column(VARCHAR(1000))
    file_size = Column(BIGINT, default=0)
    page_count = Column(Integer, default=0)
    language = Column(VARCHAR(10), default='zh')
    model_metadata = Column(JSON)
    vector_status = Column(VARCHAR(20), default='pending')
    kg_status = Column(VARCHAR(20), default='pending')
    created_at = Column(DateTime, default=func.current_timestamp())
    updated_at = Column(DateTime, default=func.current_timestamp(), onupdate=func.current_timestamp())
    
    __table_args__ = (
        Index('idx_doc_type', 'doc_type'),
        Index('idx_vector_status', 'vector_status'),
        Index('idx_kg_status', 'kg_status'),
        Index('idx_created_at', 'created_at'),
        {
            'mysql_engine': 'OLAP',
            'mysql_duplicate_key': 'id',
            'mysql_distributed_by': 'HASH(id) BUCKETS 10',
            'mysql_properties': {
                'replication_num': '1',
                'storage_format': 'V2'
            }
        }
    )


class StarRocksDocumentChunkModel(StarRocksBase):
    """StarRocks文档块表模型"""
    __tablename__ = 'sr_document_chunks'
    
    id = Column(VARCHAR(64), primary_key=True)
    document_id = Column(VARCHAR(64), nullable=False)
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    chunk_size = Column(Integer, nullable=False)
    overlap_size = Column(Integer, default=0)
    model_metadata = Column(JSON)
    embedding_vector = Column(JSON)
    created_at = Column(DateTime, default=func.current_timestamp())
    
    __table_args__ = (
        Index('idx_document_id', 'document_id'),
        Index('idx_chunk_index', 'chunk_index'),
        Index('idx_created_at', 'created_at'),
        {
            'mysql_engine': 'OLAP',
            'mysql_duplicate_key': 'id',
            'mysql_distributed_by': 'HASH(id) BUCKETS 10',
            'mysql_properties': {
                'replication_num': '1',
                'storage_format': 'V2'
            }
        }
    )


class StarRocksEntityModel(StarRocksBase):
    """StarRocks实体表模型"""
    __tablename__ = 'entities'
    
    id = Column(VARCHAR(64), primary_key=True)
    name = Column(VARCHAR(500), nullable=False)
    entity_type = Column(VARCHAR(50), nullable=False)
    description = Column(Text)
    properties = Column(JSON)
    confidence = Column(DECIMAL(3, 2), default=0.0)
    source_documents = Column(JSON)
    created_at = Column(DateTime, default=func.current_timestamp())
    updated_at = Column(DateTime, default=func.current_timestamp(), onupdate=func.current_timestamp())
    
    __table_args__ = (
        Index('idx_name', 'name'),
        Index('idx_entity_type', 'entity_type'),
        Index('idx_confidence', 'confidence'),
        Index('idx_created_at', 'created_at'),
        {
            'mysql_engine': 'OLAP',
            'mysql_duplicate_key': 'id',
            'mysql_distributed_by': 'HASH(id) BUCKETS 10',
            'mysql_properties': {
                'replication_num': '1',
                'storage_format': 'V2'
            }
        }
    )


class StarRocksRelationModel(StarRocksBase):
    """StarRocks关系表模型"""
    __tablename__ = 'relations'
    
    id = Column(VARCHAR(64), primary_key=True)
    source_entity_id = Column(VARCHAR(64), nullable=False)
    target_entity_id = Column(VARCHAR(64), nullable=False)
    relation_type = Column(VARCHAR(50), nullable=False)
    description = Column(Text)
    properties = Column(JSON)
    confidence = Column(DECIMAL(3, 2), default=0.0)
    source_documents = Column(JSON)
    created_at = Column(DateTime, default=func.current_timestamp())
    updated_at = Column(DateTime, default=func.current_timestamp(), onupdate=func.current_timestamp())
    
    __table_args__ = (
        Index('idx_source_entity', 'source_entity_id'),
        Index('idx_target_entity', 'target_entity_id'),
        Index('idx_relation_type', 'relation_type'),
        Index('idx_confidence', 'confidence'),
        Index('idx_created_at', 'created_at'),
        {
            'mysql_engine': 'OLAP',
            'mysql_duplicate_key': 'id',
            'mysql_distributed_by': 'HASH(id) BUCKETS 10',
            'mysql_properties': {
                'replication_num': '1',
                'storage_format': 'V2'
            }
        }
    )


class StarRocksTaskModel(StarRocksBase):
    """StarRocks任务表模型"""
    __tablename__ = 'tasks'
    
    id = Column(VARCHAR(64), primary_key=True)
    task_type = Column(VARCHAR(50), nullable=False)
    status = Column(VARCHAR(20), nullable=False, default='pending')
    input_data = Column(JSON)
    output_data = Column(JSON)
    error_message = Column(Text)
    progress = Column(Integer, default=0)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    created_at = Column(DateTime, default=func.current_timestamp())
    updated_at = Column(DateTime, default=func.current_timestamp(), onupdate=func.current_timestamp())
    
    __table_args__ = (
        Index('idx_task_type', 'task_type'),
        Index('idx_status', 'status'),
        Index('idx_created_at', 'created_at'),
        {
            'mysql_engine': 'OLAP',
            'mysql_duplicate_key': 'id',
            'mysql_distributed_by': 'HASH(id) BUCKETS 10',
            'mysql_properties': {
                'replication_num': '1',
                'storage_format': 'V2'
            }
        }
    )


class StarRocksMigrationsModel(StarRocksBase):
    """StarRocks迁移表模型"""
    __tablename__ = 'migrations'
    
    version = Column(VARCHAR(50), primary_key=True)
    description = Column(VARCHAR(500))
    rollback_sql = Column(LONGTEXT)
    applied_at = Column(DateTime, default=func.current_timestamp())
    
    __table_args__ = (
        Index('idx_applied_at', 'applied_at'),
        {
            'mysql_engine': 'OLAP',
            'mysql_duplicate_key': 'version',
            'mysql_distributed_by': 'HASH(version) BUCKETS 10',
            'mysql_properties': {
                'replication_num': '1',
                'storage_format': 'V2'
            }
        }
    )


class StarRocksQueryLogModel(StarRocksBase):
    """StarRocks查询日志表模型"""
    __tablename__ = 'query_logs'
    
    id = Column(VARCHAR(64), primary_key=True)
    user_id = Column(VARCHAR(64))
    query_text = Column(Text, nullable=False)
    query_type = Column(VARCHAR(50), nullable=False)
    response_data = Column(JSON)
    execution_time_ms = Column(Integer)
    result_count = Column(Integer, default=0)
    success = Column(Boolean, default=True)
    error_message = Column(Text)
    created_at = Column(DateTime, default=func.current_timestamp())
    
    __table_args__ = (
        Index('idx_user_id', 'user_id'),
        Index('idx_query_type', 'query_type'),
        Index('idx_success', 'success'),
        Index('idx_created_at', 'created_at'),
        {
            'mysql_engine': 'OLAP',
            'mysql_duplicate_key': 'id',
            'mysql_distributed_by': 'HASH(id) BUCKETS 10',
            'mysql_properties': {
                'replication_num': '1',
                'storage_format': 'V2'
            }
        }
    )


class StarRocksMetricModel(StarRocksBase):
    """StarRocks指标表模型"""
    __tablename__ = 'metrics'
    
    id = Column(VARCHAR(64), primary_key=True)
    metric_name = Column(VARCHAR(100), nullable=False)
    metric_value = Column(DECIMAL(15, 4), nullable=False)
    metric_type = Column(VARCHAR(50), nullable=False)
    tags = Column(JSON)
    timestamp = Column(DateTime, default=func.current_timestamp())
    
    __table_args__ = (
        Index('idx_metric_name', 'metric_name'),
        Index('idx_metric_type', 'metric_type'),
        Index('idx_timestamp', 'timestamp'),
        {
            'mysql_engine': 'OLAP',
            'mysql_duplicate_key': 'id',
            'mysql_distributed_by': 'HASH(id) BUCKETS 10',
            'mysql_properties': {
                'replication_num': '1',
                'storage_format': 'V2'
            }
        }
    )


class StarRocksClient:
    """StarRocks SQLAlchemy 客户端"""
    
    def __init__(
        self,
        host: str,
        port: int,
        user: str,
        password: str,
        database: str = "information_schema",
        charset: str = "utf8mb4",
        pool_size: int = 10,
        max_overflow: int = 20,
        pool_recycle: int = 3600,
        connect_timeout: int = 10
    ):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database = database
        self.charset = charset
        self.logger = get_logger(__name__)
        
        # 构建数据库URL
        self.database_url = (
            f"mysql+aiomysql://{user}:{password}@{host}:{port}/{database}"
            f"?charset={charset}"
        )
        
        # 创建异步引擎
        self.engine = create_async_engine(
            self.database_url,
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_recycle=pool_recycle,
            connect_args={
                "connect_timeout": connect_timeout,
                "autocommit": True
            },
            echo=False
        )
        
        # 创建会话工厂
        self.async_session = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
    
    async def connect(self) -> None:
        """建立连接并初始化架构"""
        try:
            # 使用SQLAlchemy的select语句进行连接测试
            async with self.async_session() as session:
                from sqlalchemy import select, literal
                result = await session.execute(select(literal(1)))
                result.fetchone()
            
            self.logger.info(f"StarRocks 连接成功: {self.host}:{self.port}")
            
            # 初始化架构
            await self._initialize_schema()
            
        except Exception as e:
            self.logger.error(f"StarRocks 连接失败: {str(e)}")
            raise
    
    async def close(self) -> None:
        """关闭连接"""
        await self.engine.dispose()
        self.logger.info("StarRocks 连接已关闭")
    
    async def _initialize_schema(self) -> None:
        """初始化数据库架构"""
        try:
            # 创建知识库数据库 - 这里保留原生SQL因为CREATE DATABASE语句在SQLAlchemy中没有直接对应
            async with self.engine.begin() as conn:
                await conn.execute(text("CREATE DATABASE IF NOT EXISTS knowledge_base"))
            
            # 更新连接到知识库数据库
            knowledge_base_url = (
                f"mysql+aiomysql://{self.user}:{self.password}@{self.host}:{self.port}/knowledge_base"
                f"?charset={self.charset}"
            )
            
            # 创建新的引擎连接到knowledge_base
            self.engine = create_async_engine(
                knowledge_base_url,
                pool_size=10,
                max_overflow=20,
                pool_recycle=3600,
                connect_args={"autocommit": True},
                echo=False
            )
            
            # 更新会话工厂
            self.async_session = async_sessionmaker(
                self.engine,
                class_=AsyncSession,
                expire_on_commit=False
            )
            
            # 创建所有表
            async with self.engine.begin() as conn:
                # 由于StarRocks的特殊语法，我们仍需要使用原生SQL创建表
                await self._create_starrocks_tables(conn)
            
            self.logger.info("StarRocks 架构初始化完成")
            
        except Exception as e:
            self.logger.error(f"初始化架构失败: {str(e)}")
            raise
    
    async def _create_starrocks_tables(self, conn) -> None:
        """创建StarRocks特定的表结构"""
        tables_sql = {
            "documents": """
                CREATE TABLE IF NOT EXISTS documents (
                    id VARCHAR(64) NOT NULL,
                    title VARCHAR(500) NOT NULL,
                    content LONGTEXT,
                    doc_type VARCHAR(50) NOT NULL,
                    source_path VARCHAR(1000),
                    file_size BIGINT DEFAULT 0,
                    page_count INT DEFAULT 0,
                    language VARCHAR(10) DEFAULT 'zh',
                    metadata JSON,
                    vector_status VARCHAR(20) DEFAULT 'pending',
                    kg_status VARCHAR(20) DEFAULT 'pending',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    INDEX idx_doc_type (doc_type),
                    INDEX idx_vector_status (vector_status),
                    INDEX idx_kg_status (kg_status),
                    INDEX idx_created_at (created_at)
                ) ENGINE=OLAP
                DUPLICATE KEY(id)
                DISTRIBUTED BY HASH(id) BUCKETS 10
                PROPERTIES (
                    "replication_num" = "1",
                    "storage_format" = "V2"
                )
            """,
            
                    "sr_document_chunks": """
            CREATE TABLE IF NOT EXISTS sr_document_chunks (
                    id VARCHAR(64) NOT NULL,
                    document_id VARCHAR(64) NOT NULL,
                    chunk_index INT NOT NULL,
                    content TEXT NOT NULL,
                    chunk_size INT NOT NULL,
                    overlap_size INT DEFAULT 0,
                    metadata JSON,
                    embedding_vector JSON,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_document_id (document_id),
                    INDEX idx_chunk_index (chunk_index),
                    INDEX idx_created_at (created_at)
                ) ENGINE=OLAP
                DUPLICATE KEY(id)
                DISTRIBUTED BY HASH(id) BUCKETS 10
                PROPERTIES (
                    "replication_num" = "1",
                    "storage_format" = "V2"
                )
            """,
            
            "entities": """
                CREATE TABLE IF NOT EXISTS entities (
                    id VARCHAR(64) NOT NULL,
                    name VARCHAR(500) NOT NULL,
                    entity_type VARCHAR(50) NOT NULL,
                    description TEXT,
                    properties JSON,
                    confidence DECIMAL(3,2) DEFAULT 0.0,
                    source_documents JSON,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    INDEX idx_name (name),
                    INDEX idx_entity_type (entity_type),
                    INDEX idx_confidence (confidence),
                    INDEX idx_created_at (created_at)
                ) ENGINE=OLAP
                DUPLICATE KEY(id)
                DISTRIBUTED BY HASH(id) BUCKETS 10
                PROPERTIES (
                    "replication_num" = "1",
                    "storage_format" = "V2"
                )
            """,
            
            "relations": """
                CREATE TABLE IF NOT EXISTS relations (
                    id VARCHAR(64) NOT NULL,
                    source_entity_id VARCHAR(64) NOT NULL,
                    target_entity_id VARCHAR(64) NOT NULL,
                    relation_type VARCHAR(50) NOT NULL,
                    description TEXT,
                    properties JSON,
                    confidence DECIMAL(3,2) DEFAULT 0.0,
                    source_documents JSON,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    INDEX idx_source_entity (source_entity_id),
                    INDEX idx_target_entity (target_entity_id),
                    INDEX idx_relation_type (relation_type),
                    INDEX idx_confidence (confidence),
                    INDEX idx_created_at (created_at)
                ) ENGINE=OLAP
                DUPLICATE KEY(id)
                DISTRIBUTED BY HASH(id) BUCKETS 10
                PROPERTIES (
                    "replication_num" = "1",
                    "storage_format" = "V2"
                )
            """,
            
            "tasks": """
                CREATE TABLE IF NOT EXISTS tasks (
                    id VARCHAR(64) NOT NULL,
                    task_type VARCHAR(50) NOT NULL,
                    status VARCHAR(20) NOT NULL DEFAULT 'pending',
                    input_data JSON,
                    output_data JSON,
                    error_message TEXT,
                    progress INT DEFAULT 0,
                    started_at DATETIME,
                    completed_at DATETIME,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    INDEX idx_task_type (task_type),
                    INDEX idx_status (status),
                    INDEX idx_created_at (created_at)
                ) ENGINE=OLAP
                DUPLICATE KEY(id)
                DISTRIBUTED BY HASH(id) BUCKETS 10
                PROPERTIES (
                    "replication_num" = "1",
                    "storage_format" = "V2"
                )
            """,
            
            "query_logs": """
                CREATE TABLE IF NOT EXISTS query_logs (
                    id VARCHAR(64) NOT NULL,
                    user_id VARCHAR(64),
                    query_text TEXT NOT NULL,
                    query_type VARCHAR(50) NOT NULL,
                    response_data JSON,
                    execution_time_ms INT,
                    result_count INT DEFAULT 0,
                    success BOOLEAN DEFAULT TRUE,
                    error_message TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_user_id (user_id),
                    INDEX idx_query_type (query_type),
                    INDEX idx_success (success),
                    INDEX idx_created_at (created_at)
                ) ENGINE=OLAP
                DUPLICATE KEY(id)
                DISTRIBUTED BY HASH(id) BUCKETS 10
                PROPERTIES (
                    "replication_num" = "1",
                    "storage_format" = "V2"
                )
            """,
            
            "metrics": """
                CREATE TABLE IF NOT EXISTS metrics (
                    id VARCHAR(64) NOT NULL,
                    metric_name VARCHAR(100) NOT NULL,
                    metric_value DECIMAL(15,4) NOT NULL,
                    metric_type VARCHAR(50) NOT NULL,
                    tags JSON,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_metric_name (metric_name),
                    INDEX idx_metric_type (metric_type),
                    INDEX idx_timestamp (timestamp)
                ) ENGINE=OLAP
                DUPLICATE KEY(id)
                DISTRIBUTED BY HASH(id) BUCKETS 10
                PROPERTIES (
                    "replication_num" = "1",
                    "storage_format" = "V2"
                )
            """
        }
        
        for table_name, create_sql in tables_sql.items():
            try:
                await conn.execute(text(create_sql))
                self.logger.info(f"表 {table_name} 创建成功")
            except Exception as e:
                self.logger.error(f"创建表 {table_name} 失败: {str(e)}")
    
    # 文档相关操作
    async def insert_document(
        self,
        doc_id: str,
        title: str,
        content: str,
        doc_type: str,
        source_path: Optional[str] = None,
        file_size: int = 0,
        page_count: int = 0,
        language: str = "zh",
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """插入文档"""
        try:
            async with self.async_session() as session:
                stmt = insert(StarRocksDocumentModel).values(
                    id=doc_id,
                    title=title,
                    content=content,
                    doc_type=doc_type,
                    source_path=source_path,
                    file_size=file_size,
                    page_count=page_count,
                    language=language,
                    model_metadata=metadata
                )
                await session.execute(stmt)
                await session.commit()
                return True
        except Exception as e:
            self.logger.error(f"插入文档失败: {str(e)}")
            return False
    
    async def get_document_by_id(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """根据ID获取文档"""
        try:
            async with self.async_session() as session:
                stmt = select(StarRocksDocumentModel).where(StarRocksDocumentModel.id == doc_id)
                result = await session.execute(stmt)
                document = result.scalar_one_or_none()
                
                if document:
                    return {
                        "id": document.id,
                        "title": document.title,
                        "content": document.content,
                        "doc_type": document.doc_type,
                        "source_path": document.source_path,
                        "file_size": document.file_size,
                        "page_count": document.page_count,
                        "language": document.language,
                        "metadata": document.model_metadata,
                        "vector_status": document.vector_status,
                        "kg_status": document.kg_status,
                        "created_at": document.created_at,
                        "updated_at": document.updated_at
                    }
                return None
        except Exception as e:
            self.logger.error(f"获取文档失败: {str(e)}")
            return None
    
    async def search_documents(
        self,
        keyword: Optional[str] = None,
        doc_type: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """搜索文档"""
        try:
            async with self.async_session() as session:
                stmt = select(
                    StarRocksDocumentModel.id,
                    StarRocksDocumentModel.title,
                    StarRocksDocumentModel.doc_type,
                    StarRocksDocumentModel.source_path,
                    StarRocksDocumentModel.file_size,
                    StarRocksDocumentModel.page_count,
                    StarRocksDocumentModel.language,
                    StarRocksDocumentModel.created_at,
                    StarRocksDocumentModel.updated_at
                )
                
                if keyword:
                    stmt = stmt.where(
                        (StarRocksDocumentModel.title.like(f"%{keyword}%")) |
                        (StarRocksDocumentModel.content.like(f"%{keyword}%"))
                    )
                
                if doc_type:
                    stmt = stmt.where(StarRocksDocumentModel.doc_type == doc_type)
                
                stmt = stmt.order_by(StarRocksDocumentModel.created_at.desc())
                stmt = stmt.limit(limit).offset(offset)
                
                result = await session.execute(stmt)
                documents = result.fetchall()
                
                return [
                    {
                        "id": doc.id,
                        "title": doc.title,
                        "doc_type": doc.doc_type,
                        "source_path": doc.source_path,
                        "file_size": doc.file_size,
                        "page_count": doc.page_count,
                        "language": doc.language,
                        "created_at": doc.created_at,
                        "updated_at": doc.updated_at
                    }
                    for doc in documents
                ]
        except Exception as e:
            self.logger.error(f"搜索文档失败: {str(e)}")
            return []
    
    # 实体相关操作
    async def insert_entity(
        self,
        entity_id: str,
        name: str,
        entity_type: str,
        description: Optional[str] = None,
        properties: Optional[Dict[str, Any]] = None,
        confidence: float = 0.0,
        source_documents: Optional[List[str]] = None
    ) -> bool:
        """插入实体"""
        try:
            async with self.async_session() as session:
                stmt = insert(StarRocksEntityModel).values(
                    id=entity_id,
                    name=name,
                    entity_type=entity_type,
                    description=description,
                    properties=properties,
                    confidence=confidence,
                    source_documents=source_documents
                )
                await session.execute(stmt)
                await session.commit()
                return True
        except Exception as e:
            self.logger.error(f"插入实体失败: {str(e)}")
            return False
    
    async def get_entities_by_type(
        self,
        entity_type: str,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """根据类型获取实体"""
        try:
            async with self.async_session() as session:
                stmt = select(StarRocksEntityModel).where(
                    StarRocksEntityModel.entity_type == entity_type
                ).order_by(
                    StarRocksEntityModel.confidence.desc(),
                    StarRocksEntityModel.created_at.desc()
                ).limit(limit).offset(offset)
                
                result = await session.execute(stmt)
                entities = result.scalars().all()
                
                return [
                    {
                        "id": entity.id,
                        "name": entity.name,
                        "entity_type": entity.entity_type,
                        "description": entity.description,
                        "properties": entity.properties,
                        "confidence": entity.confidence,
                        "source_documents": entity.source_documents,
                        "created_at": entity.created_at,
                        "updated_at": entity.updated_at
                    }
                    for entity in entities
                ]
        except Exception as e:
            self.logger.error(f"获取实体失败: {str(e)}")
            return []
    
    # 任务相关操作
    async def create_task(
        self,
        task_id: str,
        task_type: TaskType,
        input_data: Dict[str, Any]
    ) -> bool:
        """创建任务"""
        try:
            async with self.async_session() as session:
                stmt = insert(StarRocksTaskModel).values(
                    id=task_id,
                    task_type=task_type.value,
                    status=TaskStatus.PENDING.value,
                    input_data=input_data
                )
                await session.execute(stmt)
                await session.commit()
                return True
        except Exception as e:
            self.logger.error(f"创建任务失败: {str(e)}")
            return False
    
    async def update_task_status(
        self,
        task_id: str,
        status: TaskStatus,
        output_data: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
        progress: Optional[int] = None
    ) -> bool:
        """更新任务状态"""
        try:
            async with self.async_session() as session:
                update_values = {
                    "status": status.value,
                    "updated_at": func.now()
                }
                
                if output_data is not None:
                    update_values["output_data"] = output_data
                
                if error_message is not None:
                    update_values["error_message"] = error_message
                
                if progress is not None:
                    update_values["progress"] = progress
                
                if status == TaskStatus.RUNNING:
                    update_values["started_at"] = func.now()
                elif status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
                    update_values["completed_at"] = func.now()
                
                stmt = update(StarRocksTaskModel).where(
                    StarRocksTaskModel.id == task_id
                ).values(**update_values)
                
                result = await session.execute(stmt)
                await session.commit()
                return result.rowcount > 0
        except Exception as e:
            self.logger.error(f"更新任务状态失败: {str(e)}")
            return False
    
    async def get_task_by_id(self, task_id: str) -> Optional[Dict[str, Any]]:
        """根据ID获取任务"""
        try:
            async with self.async_session() as session:
                stmt = select(StarRocksTaskModel).where(StarRocksTaskModel.id == task_id)
                result = await session.execute(stmt)
                task = result.scalar_one_or_none()
                
                if task:
                    return {
                        "id": task.id,
                        "task_type": task.task_type,
                        "status": task.status,
                        "input_data": task.input_data,
                        "output_data": task.output_data,
                        "error_message": task.error_message,
                        "progress": task.progress,
                        "started_at": task.started_at,
                        "completed_at": task.completed_at,
                        "created_at": task.created_at,
                        "updated_at": task.updated_at
                    }
                return None
        except Exception as e:
            self.logger.error(f"获取任务失败: {str(e)}")
            return None
    
    # 查询日志相关操作
    async def insert_query_log(
        self,
        query_id: str,
        user_id: Optional[str],
        query_text: str,
        query_type: str,
        response_data: Optional[Dict[str, Any]] = None,
        execution_time_ms: Optional[int] = None,
        result_count: int = 0,
        success: bool = True,
        error_message: Optional[str] = None
    ) -> bool:
        """插入查询日志"""
        try:
            async with self.async_session() as session:
                stmt = insert(StarRocksQueryLogModel).values(
                    id=query_id,
                    user_id=user_id,
                    query_text=query_text,
                    query_type=query_type,
                    response_data=response_data,
                    execution_time_ms=execution_time_ms,
                    result_count=result_count,
                    success=success,
                    error_message=error_message
                )
                await session.execute(stmt)
                await session.commit()
                return True
        except Exception as e:
            self.logger.error(f"插入查询日志失败: {str(e)}")
            return False
    
    async def update_query_log(
        self,
        query_id: str,
        response_data: Optional[Dict[str, Any]] = None,
        execution_time_ms: Optional[int] = None,
        result_count: Optional[int] = None,
        success: Optional[bool] = None,
        error_message: Optional[str] = None
    ) -> bool:
        """更新查询日志"""
        try:
            async with self.async_session() as session:
                update_values = {}
                
                if response_data is not None:
                    update_values["response_data"] = response_data
                
                if execution_time_ms is not None:
                    update_values["execution_time_ms"] = execution_time_ms
                
                if result_count is not None:
                    update_values["result_count"] = result_count
                
                if success is not None:
                    update_values["success"] = success
                
                if error_message is not None:
                    update_values["error_message"] = error_message
                
                if update_values:
                    stmt = update(StarRocksQueryLogModel).where(
                        StarRocksQueryLogModel.id == query_id
                    ).values(**update_values)
                    
                    result = await session.execute(stmt)
                    await session.commit()
                    return result.rowcount > 0
                
                return True
        except Exception as e:
            self.logger.error(f"更新查询日志失败: {str(e)}")
            return False
    
    # 指标相关操作
    async def insert_metric(
        self,
        metric_id: str,
        metric_name: str,
        metric_value: float,
        metric_type: str,
        tags: Optional[Dict[str, Any]] = None
    ) -> bool:
        """插入指标"""
        try:
            async with self.async_session() as session:
                stmt = insert(StarRocksMetricModel).values(
                    id=metric_id,
                    metric_name=metric_name,
                    metric_value=metric_value,
                    metric_type=metric_type,
                    tags=tags
                )
                await session.execute(stmt)
                await session.commit()
                return True
        except Exception as e:
            self.logger.error(f"插入指标失败: {str(e)}")
            return False
    
    async def get_database_stats(self) -> Dict[str, Any]:
        """获取数据库统计信息"""
        stats = {}
        
        # 定义表模型映射
        table_models = {
            "documents": StarRocksDocumentModel,
            "sr_document_chunks": StarRocksDocumentChunkModel,
            "entities": StarRocksEntityModel,
            "relations": StarRocksRelationModel,
            "tasks": StarRocksTaskModel,
            "query_logs": StarRocksQueryLogModel,
            "metrics": StarRocksMetricModel
        }
        
        try:
            async with self.async_session() as session:
                for table_name, model in table_models.items():
                    try:
                        stmt = select(func.count()).select_from(model)
                        result = await session.execute(stmt)
                        count = result.scalar()
                        stats[f"{table_name}_count"] = count or 0
                    except Exception as e:
                        self.logger.error(f"获取表 {table_name} 统计失败: {str(e)}")
                        stats[f"{table_name}_count"] = 0
        except Exception as e:
            self.logger.error(f"获取数据库统计失败: {str(e)}")
        
        return stats
    
    async def health_check(self) -> bool:
        """健康检查"""
        try:
            async with self.async_session() as session:
                from sqlalchemy import select, literal
                result = await session.execute(select(literal(1).label('health')))
                row = result.fetchone()
                return row is not None and row[0] == 1
        except Exception as e:
            self.logger.error(f"StarRocks 健康检查失败: {str(e)}")
            return False
    
    # 批量操作方法
    async def bulk_insert_entities(self, entities: List[Dict[str, Any]]) -> bool:
        """批量插入实体"""
        try:
            async with self.async_session() as session:
                stmt = insert(StarRocksEntityModel)
                await session.execute(stmt, entities)
                await session.commit()
                return True
        except Exception as e:
            self.logger.error(f"批量插入实体失败: {str(e)}")
            return False
    
    async def bulk_insert_relations(self, relations: List[Dict[str, Any]]) -> bool:
        """批量插入关系"""
        try:
            async with self.async_session() as session:
                stmt = insert(StarRocksRelationModel)
                await session.execute(stmt, relations)
                await session.commit()
                return True
        except Exception as e:
            self.logger.error(f"批量插入关系失败: {str(e)}")
            return False
    
    async def truncate_table(self, table_name: str) -> bool:
        """清空表数据"""
        try:
            # TRUNCATE语句在SQLAlchemy中没有直接对应，保留原生SQL
            async with self.async_session() as session:
                await session.execute(text(f"TRUNCATE TABLE {table_name}"))
                await session.commit()
                return True
        except Exception as e:
            self.logger.error(f"清空表 {table_name} 失败: {str(e)}")
            return False
    
    async def create_database_if_not_exists(self) -> bool:
        """创建数据库（如果不存在）"""
        try:
            # CREATE DATABASE语句在SQLAlchemy中没有直接对应，保留原生SQL
            async with self.async_session() as session:
                await session.execute(text("CREATE DATABASE IF NOT EXISTS knowledge_base"))
                await session.commit()
                return True
        except Exception as e:
            self.logger.error(f"创建数据库失败: {str(e)}")
            return False
    
    async def get_applied_migrations(self) -> List[List[str]]:
        """获取已应用的迁移版本列表"""
        try:
            async with self.async_session() as session:
                result = await session.execute(
                    select(StarRocksMigrationsModel.version)
                    .order_by(StarRocksMigrationsModel.applied_at)
                )
                return [[row[0]] for row in result.fetchall()]
        except Exception as e:
            self.logger.error(f"获取迁移版本失败: {str(e)}")
            return []
    
    async def get_migration_rollback_sql(self, version: str) -> List[List[str]]:
        """获取迁移的回滚SQL"""
        try:
            async with self.async_session() as session:
                result = await session.execute(
                    select(StarRocksMigrationsModel.rollback_sql)
                    .where(StarRocksMigrationsModel.version == version)
                )
                row = result.fetchone()
                return [[row[0]]] if row else []
        except Exception as e:
            self.logger.error(f"获取回滚SQL失败: {str(e)}")
            return []
    
    async def delete_migration_record(self, version: str) -> bool:
        """删除迁移记录"""
        try:
            async with self.async_session() as session:
                await session.execute(
                    delete(StarRocksMigrationsModel)
                    .where(StarRocksMigrationsModel.version == version)
                )
                await session.commit()
                return True
        except Exception as e:
            self.logger.error(f"删除迁移记录失败: {str(e)}")
            return False