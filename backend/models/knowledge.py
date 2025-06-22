from datetime import datetime
from typing import Optional, List, Dict, Any, Union
from enum import Enum

from sqlalchemy import Column, String, Text, Boolean, DateTime, Integer, Float, Enum as SQLEnum, JSON, ForeignKey, Index
from sqlalchemy.dialects.mysql import VARCHAR, TEXT, LONGTEXT, MEDIUMTEXT, CHAR, BIGINT
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from pydantic import Field, validator, BaseModel as PydanticBaseModel

from .base import Base, BaseModel, FullModel


class DocumentStatus(str, Enum):
    """文档状态"""
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    PROCESSED = "processed"
    INDEXED = "indexed"
    FAILED = "failed"
    DELETED = "deleted"
    ARCHIVED = "archived"


class DocumentType(str, Enum):
    """文档类型"""
    PDF = "pdf"
    WORD = "word"
    EXCEL = "excel"
    POWERPOINT = "powerpoint"
    TEXT = "text"
    MARKDOWN = "markdown"
    HTML = "html"
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    OTHER = "other"


class ChunkType(str, Enum):
    """文档块类型"""
    PARAGRAPH = "paragraph"
    SENTENCE = "sentence"
    SECTION = "section"
    CHAPTER = "chapter"
    TABLE = "table"
    IMAGE = "image"
    CODE = "code"
    FORMULA = "formula"
    HEADER = "header"
    FOOTER = "footer"
    METADATA = "metadata"


class ProcessingStage(str, Enum):
    """处理阶段"""
    UPLOAD = "upload"
    EXTRACTION = "extraction"
    CHUNKING = "chunking"
    EMBEDDING = "embedding"
    NER = "ner"
    RELATION_EXTRACTION = "relation_extraction"
    INDEXING = "indexing"
    GRAPH_BUILDING = "graph_building"
    COMPLETED = "completed"


class KnowledgeBase(Base):
    """知识库SQLAlchemy模型"""
    
    __allow_unmapped__ = True
    __tablename__ = "knowledge_bases"
    
    name: Any = Column(VARCHAR(200), nullable=False, comment="知识库名称")
    description: Any = Column(TEXT, nullable=True, comment="知识库描述")
    owner_id: Any = Column(CHAR(36), nullable=False, index=True, comment="所有者ID")
    is_public: Any = Column(Boolean, default=False, nullable=False, comment="是否公开")
    settings: Any = Column(LONGTEXT, nullable=True, comment="知识库设置(JSON)")
    meta_data: Any = Column(LONGTEXT, nullable=True, comment="元数据(JSON)")
    
    # 统计信息
    document_count: Any = Column(Integer, default=0, nullable=False, comment="文档数量")
    chunk_count: Any = Column(Integer, default=0, nullable=False, comment="文档块数量")
    total_size: Any = Column(BIGINT, default=0, nullable=False, comment="总大小(字节)")
    
    # 索引
    __table_args__ = (
        Index('idx_owner_id', 'owner_id'),
        Index('idx_is_public', 'is_public'),
        Index('idx_name', 'name'),
    )
    
    # 关联关系
    documents = relationship("Document", back_populates="knowledge_base")


class Document(Base):
    """文档SQLAlchemy模型"""
    
    __allow_unmapped__ = True
    __tablename__ = "kb_documents"
    
    knowledge_base_id: Any = Column(CHAR(36), ForeignKey('knowledge_bases.id'), nullable=False, comment="知识库ID")
    title: Any = Column(VARCHAR(500), nullable=False, comment="文档标题")
    
    # 文件信息
    filename: Any = Column(VARCHAR(500), nullable=True, comment="文件名")
    file_path: Any = Column(VARCHAR(1000), nullable=True, comment="文件路径")
    file_size: Any = Column(BIGINT, nullable=True, comment="文件大小(字节)")
    file_type: Any = Column(VARCHAR(50), nullable=True, comment="文件类型")
    mime_type: Any = Column(VARCHAR(100), nullable=True, comment="MIME类型")
    file_hash: Any = Column(VARCHAR(64), nullable=True, comment="文件哈希")
    
    # 状态信息
    status: Any = Column(VARCHAR(20), default="pending", nullable=False, comment="处理状态")
    
    # 内容信息
    content: Any = Column(LONGTEXT, nullable=True, comment="文档内容")
    summary: Any = Column(TEXT, nullable=True, comment="文档摘要")
    keywords: Any = Column(TEXT, nullable=True, comment="关键词(JSON)")
    language: Any = Column(VARCHAR(10), nullable=True, comment="语言")
    
    # 处理信息
    processed_at: Any = Column(DateTime, nullable=True, comment="处理完成时间")
    processing_time: Any = Column(Float, nullable=True, comment="处理耗时(秒)")
    error_message: Any = Column(TEXT, nullable=True, comment="错误信息")
    
    # 统计信息
    page_count: Any = Column(Integer, nullable=True, comment="页数")
    word_count: Any = Column(Integer, nullable=True, comment="字数")
    chunk_count: Any = Column(Integer, default=0, nullable=False, comment="文档块数量")
    
    # 元数据
    meta_data: Any = Column(LONGTEXT, nullable=True, comment="元数据(JSON)")
    
    # 版本信息
    version: Any = Column(Integer, default=1, nullable=False, comment="版本号")
    parent_document_id: Any = Column(CHAR(36), ForeignKey('kb_documents.id'), nullable=True, comment="父文档ID")
    
    # 索引
    __table_args__ = (
        Index('idx_document_kb_status', 'knowledge_base_id', 'status'),
        Index('idx_document_type_processed', 'file_type', 'processed_at'),
        Index('idx_document_hash', 'file_hash'),
        Index('idx_document_parent', 'parent_document_id'),
    )
    
    # 关联关系
    knowledge_base = relationship("KnowledgeBase", back_populates="documents")
    chunks = relationship("DocumentChunk", back_populates="document")


class DocumentChunk(Base):
    """文档块SQLAlchemy模型"""
    
    __allow_unmapped__ = True
    __tablename__ = "kb_document_chunks"
    
    document_id: Any = Column(CHAR(36), ForeignKey('kb_documents.id'), nullable=False, comment="文档ID")
    chunk_index: Any = Column(Integer, nullable=False, comment="块索引")
    
    # 内容信息
    content: Any = Column(TEXT, nullable=False, comment="块内容")
    content_hash: Any = Column(VARCHAR(64), nullable=True, comment="内容哈希")
    
    # 位置信息
    start_pos: Any = Column(Integer, nullable=True, comment="开始位置")
    end_pos: Any = Column(Integer, nullable=True, comment="结束位置")
    page_number: Any = Column(Integer, nullable=True, comment="页码")
    
    # 块信息
    chunk_type: Any = Column(VARCHAR(50), default="text", nullable=False, comment="块类型")
    chunk_size: Any = Column(Integer, nullable=False, comment="块大小")
    token_count: Any = Column(Integer, nullable=True, comment="Token数量")
    
    # 向量信息
    embedding_vector: Any = Column(LONGTEXT, nullable=True, comment="向量表示(JSON)")
    embedding_model: Any = Column(VARCHAR(100), nullable=True, comment="嵌入模型")
    embedding_dimension: Any = Column(Integer, nullable=True, comment="向量维度")
    
    # 处理信息
    processed_at: Any = Column(DateTime, nullable=True, comment="处理时间")
    
    # 元数据
    meta_data: Any = Column(LONGTEXT, nullable=True, comment="元数据(JSON)")
    
    # 索引
    __table_args__ = (
        Index('idx_chunk_document_index', 'document_id', 'chunk_index'),
        Index('idx_chunk_type_processed', 'chunk_type', 'processed_at'),
        Index('idx_chunk_hash', 'content_hash'),
    )
    
    # 关联关系
    document = relationship("Document", back_populates="chunks")
    
    def has_embedding(self) -> bool:
        """是否有向量表示"""
        return self.embedding_vector is not None
    
    def get_embedding(self) -> Optional[List[float]]:
        """获取向量表示"""
        if self.embedding_vector:
            import json
            return json.loads(self.embedding_vector)
        return None
    
    def set_embedding(self, vector: List[float], model: str) -> None:
        """设置向量表示"""
        import json
        self.embedding_vector = json.dumps(vector)
        self.embedding_model = model
        self.embedding_dimension = len(vector)
        self.processed_at = datetime.now()


class KnowledgeEntity(Base):
    """知识实体SQLAlchemy模型"""
    

    __allow_unmapped__ = True
    __tablename__ = "knowledge_entities"
    
    name: Any = Column(
        VARCHAR(200),
        nullable=False,
        index=True,
        comment="实体名称"
    )
    
    entity_type: Any = Column(
        VARCHAR(50),
        nullable=False,
        index=True,
        comment="实体类型"
    )
    
    description: Any = Column(
        TEXT,
        nullable=True,
        comment="实体描述"
    )
    
    aliases: Any = Column(
        TEXT,
        nullable=True,
        comment="别名列表(JSON)"
    )
    
    properties: Any = Column(
        LONGTEXT,
        nullable=True,
        comment="属性(JSON)"
    )
    
    # 统计信息
    mention_count: Any = Column(
        Integer,
        default=0,
        nullable=False,
        comment="提及次数"
    )
    
    confidence_score: Any = Column(
        Float,
        nullable=True,
        comment="置信度分数"
    )
    
    # 关联信息
    source_documents: Any = Column(
        TEXT,
        nullable=True,
        comment="来源文档ID列表(JSON)"
    )
    
    # 索引
    __table_args__ = (
        Index('idx_entity_name_type', 'name', 'entity_type'),
        Index('idx_entity_type_confidence', 'entity_type', 'confidence_score'),
    )


class KnowledgeRelation(Base):
    """知识关系SQLAlchemy模型"""
    

    __allow_unmapped__ = True
    __tablename__ = "knowledge_relations"
    
    subject_entity_id: Any = Column(
        String(36),
        ForeignKey('knowledge_entities.id'),
        nullable=False,
        index=True,
        comment="主体实体ID"
    )
    
    predicate: Any = Column(
        VARCHAR(100),
        nullable=False,
        comment="谓词/关系类型"
    )
    
    object_entity_id: Any = Column(
        String(36),
        ForeignKey('knowledge_entities.id'),
        nullable=False,
        index=True,
        comment="客体实体ID"
    )
    
    confidence_score: Any = Column(
        Float,
        nullable=True,
        comment="置信度分数"
    )
    
    properties: Any = Column(
        LONGTEXT,
        nullable=True,
        comment="关系属性(JSON)"
    )
    
    # 来源信息
    source_documents: Any = Column(
        TEXT,
        nullable=True,
        comment="来源文档ID列表(JSON)"
    )
    
    source_chunks: Any = Column(
        TEXT,
        nullable=True,
        comment="来源文档块ID列表(JSON)"
    )
    
    # 关联关系
    subject_entity = relationship(
        "KnowledgeEntity",
        foreign_keys=[subject_entity_id]
    )
    
    object_entity = relationship(
        "KnowledgeEntity",
        foreign_keys=[object_entity_id]
    )
    
    # 索引
    __table_args__ = (
        Index('idx_relation_subject_predicate', 'subject_entity_id', 'predicate'),
        Index('idx_relation_object_predicate', 'object_entity_id', 'predicate'),
        Index('idx_relation_confidence', 'confidence_score'),
    )


# Pydantic模型用于API
class KnowledgeBaseBase(BaseModel):
    """知识库基础模型"""
    
    name: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="知识库名称"
    )
    
    description: Optional[str] = Field(
        default=None,
        description="知识库描述"
    )
    
    is_public: bool = Field(
        default=False,
        description="是否公开"
    )
    
    settings: Optional[Dict[str, Any]] = Field(
        default=None,
        description="知识库设置"
    )


class KnowledgeBaseCreate(KnowledgeBaseBase):
    """创建知识库模型"""
    pass


class KnowledgeBaseUpdate(BaseModel):
    """更新知识库模型"""
    
    name: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=200,
        description="知识库名称"
    )
    
    description: Optional[str] = Field(
        default=None,
        description="知识库描述"
    )
    
    is_public: Optional[bool] = Field(
        default=None,
        description="是否公开"
    )
    
    settings: Optional[Dict[str, Any]] = Field(
        default=None,
        description="知识库设置"
    )


class KnowledgeBaseResponse(FullModel):
    """知识库响应模型"""
    
    name: str = Field(
        ...,
        description="知识库名称"
    )
    
    description: Optional[str] = Field(
        default=None,
        description="知识库描述"
    )
    
    owner_id: str = Field(
        ...,
        description="所有者ID"
    )
    
    is_public: bool = Field(
        ...,
        description="是否公开"
    )
    
    document_count: int = Field(
        default=0,
        description="文档数量"
    )
    
    chunk_count: int = Field(
        default=0,
        description="文档块数量"
    )
    
    total_size: int = Field(
        default=0,
        description="总大小(字节)"
    )
    
    settings: Optional[Dict[str, Any]] = Field(
        default=None,
        description="知识库设置"
    )


class DocumentBase(BaseModel):
    """文档基础模型"""
    
    title: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="文档标题"
    )
    
    filename: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="文件名"
    )
    
    document_type: DocumentType = Field(
        ...,
        description="文档类型"
    )
    
    knowledge_base_id: str = Field(
        ...,
        description="知识库ID"
    )


class DocumentCreate(DocumentBase):
    """创建文档模型"""
    
    file_path: Optional[str] = Field(
        default=None,
        description="文件路径"
    )
    
    file_url: Optional[str] = Field(
        default=None,
        description="文件URL"
    )
    
    file_size: int = Field(
        default=0,
        ge=0,
        description="文件大小(字节)"
    )
    
    mime_type: Optional[str] = Field(
        default=None,
        description="MIME类型"
    )
    
    content: Optional[str] = Field(
        default=None,
        description="文档内容"
    )


class DocumentUpdate(BaseModel):
    """更新文档模型"""
    
    title: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=500,
        description="文档标题"
    )
    
    status: Optional[DocumentStatus] = Field(
        default=None,
        description="文档状态"
    )
    
    processing_stage: Optional[ProcessingStage] = Field(
        default=None,
        description="处理阶段"
    )
    
    content: Optional[str] = Field(
        default=None,
        description="文档内容"
    )
    
    summary: Optional[str] = Field(
        default=None,
        description="文档摘要"
    )
    
    keywords: Optional[List[str]] = Field(
        default=None,
        description="关键词"
    )
    
    language: Optional[str] = Field(
        default=None,
        description="语言"
    )


class DocumentResponse(FullModel):
    """文档响应模型"""
    
    title: str = Field(
        ...,
        description="文档标题"
    )
    
    filename: str = Field(
        ...,
        description="文件名"
    )
    
    file_size: int = Field(
        ...,
        description="文件大小(字节)"
    )
    
    document_type: DocumentType = Field(
        ...,
        description="文档类型"
    )
    
    status: DocumentStatus = Field(
        ...,
        description="文档状态"
    )
    
    processing_stage: ProcessingStage = Field(
        ...,
        description="处理阶段"
    )
    
    knowledge_base_id: str = Field(
        ...,
        description="知识库ID"
    )
    
    user_id: str = Field(
        ...,
        description="上传用户ID"
    )
    
    summary: Optional[str] = Field(
        default=None,
        description="文档摘要"
    )
    
    keywords: Optional[List[str]] = Field(
        default=None,
        description="关键词"
    )
    
    language: Optional[str] = Field(
        default=None,
        description="语言"
    )
    
    processed_at: Optional[datetime] = Field(
        default=None,
        description="处理完成时间"
    )
    
    processing_time: Optional[float] = Field(
        default=None,
        description="处理耗时(秒)"
    )
    
    page_count: Optional[int] = Field(
        default=None,
        description="页数"
    )
    
    word_count: Optional[int] = Field(
        default=None,
        description="字数"
    )
    
    chunk_count: int = Field(
        default=0,
        description="文档块数量"
    )
    
    error_message: Optional[str] = Field(
        default=None,
        description="错误信息"
    )


class DocumentChunkBase(BaseModel):
    """文档块基础模型"""
    
    document_id: str = Field(
        ...,
        description="文档ID"
    )
    
    chunk_index: int = Field(
        ...,
        ge=0,
        description="块索引"
    )
    
    chunk_type: ChunkType = Field(
        default=ChunkType.PARAGRAPH,
        description="块类型"
    )
    
    content: str = Field(
        ...,
        min_length=1,
        description="块内容"
    )


class DocumentChunkCreate(DocumentChunkBase):
    """创建文档块模型"""
    
    start_position: Optional[int] = Field(
        default=None,
        description="开始位置"
    )
    
    end_position: Optional[int] = Field(
        default=None,
        description="结束位置"
    )
    
    page_number: Optional[int] = Field(
        default=None,
        description="页码"
    )
    
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="元数据"
    )


class DocumentChunkResponse(FullModel):
    """文档块响应模型"""
    
    document_id: str = Field(
        ...,
        description="文档ID"
    )
    
    chunk_index: int = Field(
        ...,
        description="块索引"
    )
    
    chunk_type: ChunkType = Field(
        ...,
        description="块类型"
    )
    
    content: str = Field(
        ...,
        description="块内容"
    )
    
    start_position: Optional[int] = Field(
        default=None,
        description="开始位置"
    )
    
    end_position: Optional[int] = Field(
        default=None,
        description="结束位置"
    )
    
    page_number: Optional[int] = Field(
        default=None,
        description="页码"
    )
    
    word_count: int = Field(
        default=0,
        description="字数"
    )
    
    char_count: int = Field(
        default=0,
        description="字符数"
    )
    
    embedding_model: Optional[str] = Field(
        default=None,
        description="向量模型"
    )
    
    embedding_dimension: Optional[int] = Field(
        default=None,
        description="向量维度"
    )
    
    processed_at: Optional[datetime] = Field(
        default=None,
        description="处理时间"
    )
    
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="元数据"
    )


class KnowledgeEntityBase(BaseModel):
    """知识实体基础模型"""
    
    name: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="实体名称"
    )
    
    entity_type: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="实体类型"
    )
    
    description: Optional[str] = Field(
        default=None,
        description="实体描述"
    )
    
    aliases: Optional[List[str]] = Field(
        default=None,
        description="别名列表"
    )
    
    properties: Optional[Dict[str, Any]] = Field(
        default=None,
        description="属性"
    )


class KnowledgeEntityCreate(KnowledgeEntityBase):
    """创建知识实体模型"""
    pass


class KnowledgeEntityResponse(FullModel):
    """知识实体响应模型"""
    
    name: str = Field(
        ...,
        description="实体名称"
    )
    
    entity_type: str = Field(
        ...,
        description="实体类型"
    )
    
    description: Optional[str] = Field(
        default=None,
        description="实体描述"
    )
    
    aliases: Optional[List[str]] = Field(
        default=None,
        description="别名列表"
    )
    
    properties: Optional[Dict[str, Any]] = Field(
        default=None,
        description="属性"
    )
    
    mention_count: int = Field(
        default=0,
        description="提及次数"
    )
    
    confidence_score: Optional[float] = Field(
        default=None,
        description="置信度分数"
    )
    
    source_documents: Optional[List[str]] = Field(
        default=None,
        description="来源文档ID列表"
    )


class KnowledgeRelationBase(BaseModel):
    """知识关系基础模型"""
    
    subject_entity_id: str = Field(
        ...,
        description="主体实体ID"
    )
    
    predicate: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="谓词/关系类型"
    )
    
    object_entity_id: str = Field(
        ...,
        description="客体实体ID"
    )
    
    confidence_score: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="置信度分数"
    )
    
    properties: Optional[Dict[str, Any]] = Field(
        default=None,
        description="关系属性"
    )


# 添加缺失的模型类
class Entity(BaseModel):
    """实体模型"""
    
    model_config = {"extra": "allow"}  # 允许额外字段
    
    id: str = Field(
        ...,
        description="实体ID"
    )
    
    name: str = Field(
        ...,
        description="实体名称"
    )
    
    entity_type: str = Field(
        ...,
        description="实体类型"
    )
    
    description: Optional[str] = Field(
        default=None,
        description="实体描述"
    )
    
    properties: Optional[Dict[str, Any]] = Field(
        default=None,
        description="实体属性"
    )
    
    confidence_score: Optional[float] = Field(
        default=None,
        description="置信度分数"
    )
    
    relevance_score: Optional[float] = Field(
        default=None,
        description="相关性分数"
    )
    
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="元数据"
    )


class Relation(BaseModel):
    """关系模型"""
    
    id: str = Field(
        ...,
        description="关系ID"
    )
    
    source_entity_id: str = Field(
        ...,
        description="源实体ID"
    )
    
    target_entity_id: str = Field(
        ...,
        description="目标实体ID"
    )
    
    relation_type: str = Field(
        ...,
        description="关系类型"
    )
    
    confidence_score: Optional[float] = Field(
        default=None,
        description="置信度分数"
    )
    
    properties: Optional[Dict[str, Any]] = Field(
        default=None,
        description="关系属性"
    )
    
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="元数据"
    )
    
    # 为了向后兼容，添加字段别名
    @property
    def source_id(self) -> str:
        """源实体ID别名"""
        return self.source_entity_id
    
    @source_id.setter
    def source_id(self, value: str):
        """设置源实体ID"""
        self.source_entity_id = value
    
    @property
    def target_id(self) -> str:
        """目标实体ID别名"""
        return self.target_entity_id
    
    @target_id.setter
    def target_id(self, value: str):
        """设置目标实体ID"""
        self.target_entity_id = value
    
    @property
    def subject_id(self) -> str:
        """主体实体ID别名（兼容GraphManager）"""
        return self.source_entity_id
    
    @subject_id.setter
    def subject_id(self, value: str):
        """设置主体实体ID"""
        self.source_entity_id = value
    
    @property
    def object_id(self) -> str:
        """客体实体ID别名（兼容GraphManager）"""
        return self.target_entity_id
    
    @object_id.setter
    def object_id(self, value: str):
        """设置客体实体ID"""
        self.target_entity_id = value
    
    @property
    def confidence(self) -> Optional[float]:
        """置信度别名"""
        return self.confidence_score
    
    @confidence.setter
    def confidence(self, value: Optional[float]):
        """设置置信度"""
        self.confidence_score = value
    
    def __init__(self, **data):
        # 处理字段别名
        if 'source_id' in data:
            data['source_entity_id'] = data.pop('source_id')
        if 'target_id' in data:
            data['target_entity_id'] = data.pop('target_id')
        if 'subject_id' in data:
            data['source_entity_id'] = data.pop('subject_id')
        if 'object_id' in data:
            data['target_entity_id'] = data.pop('object_id')
        if 'confidence' in data:
            data['confidence_score'] = data.pop('confidence')
        super().__init__(**data)


class KnowledgeGraph(BaseModel):
    """知识图谱模型"""
    
    model_config = {"extra": "allow"}  # 允许额外字段
    
    id: str = Field(
        ...,
        description="知识图谱ID"
    )
    
    name: str = Field(
        ...,
        description="知识图谱名称"
    )
    
    description: Optional[str] = Field(
        default=None,
        description="知识图谱描述"
    )
    
    entities: List[Entity] = Field(
        default_factory=list,
        description="实体列表"
    )
    
    relations: List[Relation] = Field(
        default_factory=list,
        description="关系列表"
    )
    
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="元数据"
    )


class KnowledgeGraphQuery(BaseModel):
    """知识图谱查询模型"""
    
    query: str = Field(
        ...,
        description="查询语句"
    )
    
    query_type: str = Field(
        default="cypher",
        description="查询类型"
    )
    
    parameters: Optional[Dict[str, Any]] = Field(
        default=None,
        description="查询参数"
    )
    
    limit: Optional[int] = Field(
        default=100,
        description="结果限制"
    )


class SearchQuery(BaseModel):
    """搜索查询模型"""
    
    query: str = Field(
        ...,
        description="搜索查询字符串"
    )
    
    knowledge_base_id: Optional[str] = Field(
        default=None,
        description="知识库ID"
    )
    
    entity_types: Optional[List[str]] = Field(
        default=None,
        description="实体类型过滤"
    )
    
    limit: Optional[int] = Field(
        default=10,
        description="返回结果数量限制"
    )
    
    offset: Optional[int] = Field(
        default=0,
        description="结果偏移量"
    )


class KnowledgeStats(BaseModel):
    """知识库统计信息模型"""
    
    total_documents: int = Field(
        ...,
        description="文档总数"
    )
    
    total_entities: int = Field(
        ...,
        description="实体总数"
    )
    
    total_relations: int = Field(
        ...,
        description="关系总数"
    )
    
    entity_types: Dict[str, int] = Field(
        ...,
        description="实体类型统计"
    )
    
    relation_types: Dict[str, int] = Field(
        ...,
        description="关系类型统计"
    )
    
    last_updated: Optional[str] = Field(
        default=None,
        description="最后更新时间"
    )


class KnowledgeRelationCreate(KnowledgeRelationBase):
    """创建知识关系模型"""
    
    source_documents: Optional[List[str]] = Field(
        default=None,
        description="来源文档ID列表"
    )
    
    source_chunks: Optional[List[str]] = Field(
        default=None,
        description="来源文档块ID列表"
    )


class KnowledgeRelationResponse(FullModel):
    """知识关系响应模型"""
    
    subject_entity_id: str = Field(
        ...,
        description="主体实体ID"
    )
    
    predicate: str = Field(
        ...,
        description="谓词/关系类型"
    )
    
    object_entity_id: str = Field(
        ...,
        description="客体实体ID"
    )
    
    confidence_score: Optional[float] = Field(
        default=None,
        description="置信度分数"
    )
    
    properties: Optional[Dict[str, Any]] = Field(
        default=None,
        description="关系属性"
    )
    
    source_documents: Optional[List[str]] = Field(
        default=None,
        description="来源文档ID列表"
    )
    
    source_chunks: Optional[List[str]] = Field(
        default=None,
        description="来源文档块ID列表"
    )


class SearchRequest(BaseModel):
    """搜索请求模型"""
    
    query: str = Field(
        ...,
        min_length=1,
        description="搜索查询"
    )
    
    knowledge_base_id: Optional[str] = Field(
        default=None,
        description="知识库ID"
    )
    
    document_types: Optional[List[DocumentType]] = Field(
        default=None,
        description="文档类型过滤"
    )
    
    chunk_types: Optional[List[ChunkType]] = Field(
        default=None,
        description="文档块类型过滤"
    )
    
    limit: int = Field(
        default=10,
        ge=1,
        le=100,
        description="返回结果数量限制"
    )
    
    similarity_threshold: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="相似度阈值"
    )
    
    include_metadata: bool = Field(
        default=False,
        description="是否包含元数据"
    )


class SearchResult(BaseModel):
    """搜索结果模型"""
    
    chunk_id: str = Field(
        ...,
        description="文档块ID"
    )
    
    document_id: str = Field(
        ...,
        description="文档ID"
    )
    
    document_title: str = Field(
        ...,
        description="文档标题"
    )
    
    content: str = Field(
        ...,
        description="内容"
    )
    
    similarity_score: float = Field(
        ...,
        description="相似度分数"
    )
    
    chunk_type: ChunkType = Field(
        ...,
        description="块类型"
    )
    
    page_number: Optional[int] = Field(
        default=None,
        description="页码"
    )
    
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="元数据"
    )


class SearchResponse(BaseModel):
    """搜索响应模型"""
    
    query: str = Field(
        ...,
        description="搜索查询"
    )
    
    total_results: int = Field(
        ...,
        description="总结果数"
    )
    
    results: List[SearchResult] = Field(
        ...,
        description="搜索结果列表"
    )
    
    search_time: float = Field(
        ...,
        description="搜索耗时(秒)"
    )


# Create 和 Update 模型
class DocumentCreate(BaseModel):
    """文档创建模型"""
    
    title: str = Field(
        ...,
        description="文档标题"
    )
    
    content: str = Field(
        ...,
        description="文档内容"
    )
    
    knowledge_base_id: str = Field(
        ...,
        description="知识库ID"
    )
    
    file_type: Optional[str] = Field(
        default=None,
        description="文件类型"
    )
    
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="元数据"
    )


class DocumentUpdate(BaseModel):
    """文档更新模型"""
    
    title: Optional[str] = Field(
        default=None,
        description="文档标题"
    )
    
    content: Optional[str] = Field(
        default=None,
        description="文档内容"
    )
    
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="元数据"
    )


class EntityCreate(BaseModel):
    """实体创建模型"""
    
    name: str = Field(
        ...,
        description="实体名称"
    )
    
    entity_type: str = Field(
        ...,
        description="实体类型"
    )
    
    description: Optional[str] = Field(
        default=None,
        description="实体描述"
    )
    
    properties: Optional[Dict[str, Any]] = Field(
        default=None,
        description="实体属性"
    )


class EntityUpdate(BaseModel):
    """实体更新模型"""
    
    name: Optional[str] = Field(
        default=None,
        description="实体名称"
    )
    
    entity_type: Optional[str] = Field(
        default=None,
        description="实体类型"
    )
    
    description: Optional[str] = Field(
        default=None,
        description="实体描述"
    )
    
    properties: Optional[Dict[str, Any]] = Field(
        default=None,
        description="实体属性"
    )


class EntityResponse(BaseModel):
    """实体响应模型"""
    
    id: str = Field(
        ...,
        description="实体ID"
    )
    
    name: str = Field(
        ...,
        description="实体名称"
    )
    
    entity_type: str = Field(
        ...,
        description="实体类型"
    )
    
    description: Optional[str] = Field(
        default=None,
        description="实体描述"
    )
    
    properties: Optional[Dict[str, Any]] = Field(
        default=None,
        description="实体属性"
    )


class RelationCreate(BaseModel):
    """关系创建模型"""
    
    subject_entity_id: str = Field(
        ...,
        description="主体实体ID"
    )
    
    predicate: str = Field(
        ...,
        description="谓词/关系类型"
    )
    
    object_entity_id: str = Field(
        ...,
        description="客体实体ID"
    )
    
    confidence_score: Optional[float] = Field(
        default=None,
        description="置信度分数"
    )
    
    properties: Optional[Dict[str, Any]] = Field(
        default=None,
        description="关系属性"
    )


class RelationUpdate(BaseModel):
    """关系更新模型"""
    
    predicate: Optional[str] = Field(
        default=None,
        description="谓词/关系类型"
    )
    
    confidence_score: Optional[float] = Field(
        default=None,
        description="置信度分数"
    )
    
    properties: Optional[Dict[str, Any]] = Field(
        default=None,
        description="关系属性"
    )


class RelationResponse(BaseModel):
    """关系响应模型"""
    
    id: str = Field(
        ...,
        description="关系ID"
    )
    
    subject_entity_id: str = Field(
        ...,
        description="主体实体ID"
    )
    
    predicate: str = Field(
        ...,
        description="谓词/关系类型"
    )
    
    object_entity_id: str = Field(
        ...,
        description="客体实体ID"
    )
    
    confidence_score: Optional[float] = Field(
        default=None,
        description="置信度分数"
    )
    
    properties: Optional[Dict[str, Any]] = Field(
        default=None,
        description="关系属性"
    )