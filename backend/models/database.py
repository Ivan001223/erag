from typing import Optional, List, Dict, Any, Union
from enum import Enum
from datetime import datetime

from sqlalchemy import Column, String, Text, Boolean, DateTime, Integer, Float, Enum as SQLEnum, JSON, ForeignKey, Index, ARRAY
from sqlalchemy.dialects.mysql import VARCHAR, TEXT, LONGTEXT, MEDIUMTEXT, BIGINT, CHAR, DECIMAL
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql import func
from pydantic import BaseModel as PydanticBaseModel

from .base import Base


class DocumentModel(Base):
    """文档表模型"""

    __allow_unmapped__ = True
    __tablename__ = 'base_documents'
    
    title: Any = Column(VARCHAR(500), nullable=False, comment='文档标题')
    content: Any = Column(LONGTEXT, comment='文档内容')
    doc_type: Any = Column(VARCHAR(50), nullable=False, comment='文档类型')
    source_path: Any = Column(VARCHAR(1000), comment='源文件路径')
    file_size: Any = Column(BIGINT, default=0, comment='文件大小')
    page_count: Any = Column(Integer, default=0, comment='页数')
    language: Any = Column(VARCHAR(10), default='zh', comment='语言')
    meta_data: Any = Column(JSON, comment='元数据')
    vector_status: Any = Column(VARCHAR(20), default='pending', comment='向量化状态')
    kg_status: Any = Column(VARCHAR(20), default='pending', comment='知识图谱状态')
    
    # 索引
    __table_args__ = (
        Index('idx_doc_type', 'doc_type'),
        Index('idx_vector_status', 'vector_status'),
        Index('idx_kg_status', 'kg_status'),
        Index('idx_created_at', 'created_at'),
    )
    
    # 关系
    chunks = relationship("DocumentChunkModel", back_populates="document", cascade="all, delete-orphan")


class DocumentChunkModel(Base):
    """文档块表模型"""

    __allow_unmapped__ = True
    __tablename__ = 'base_document_chunks'
    
    document_id: Any = Column(CHAR(36), ForeignKey('base_documents.id'), nullable=False, comment='文档ID')
    chunk_index: Any = Column(Integer, nullable=False, comment='块索引')
    content: Any = Column(TEXT, nullable=False, comment='块内容')
    chunk_size: Any = Column(Integer, nullable=False, comment='块大小')
    overlap_size: Any = Column(Integer, default=0, comment='重叠大小')
    meta_data: Any = Column(JSON, comment='元数据')
    embedding_vector: Any = Column(JSON, comment='嵌入向量')
    
    # 索引
    __table_args__ = (
        Index('idx_document_id', 'document_id'),
        Index('idx_chunk_index', 'chunk_index'),
        Index('idx_created_at', 'created_at'),
    )
    
    # 关系
    document = relationship("DocumentModel", back_populates="chunks")


class EntityModel(Base):
    """实体表模型"""

    __allow_unmapped__ = True
    __tablename__ = 'entities'
    
    name: Any = Column(VARCHAR(255), nullable=False, comment='实体名称')
    entity_type: Any = Column(VARCHAR(100), nullable=False, comment='实体类型')
    description: Any = Column(TEXT, comment='实体描述')
    properties: Any = Column(JSON, comment='实体属性')
    confidence: Any = Column(DECIMAL(3, 2), default=0.0, comment='置信度')
    source_documents: Any = Column(JSON, comment='来源文档')
    
    # 索引
    __table_args__ = (
        Index('idx_name', 'name'),
        Index('idx_entity_type', 'entity_type'),
        Index('idx_confidence', 'confidence'),
        Index('idx_created_at', 'created_at'),
    )
    
    # 关系
    source_relations = relationship("RelationModel", foreign_keys="RelationModel.source_id", back_populates="source_entity")
    target_relations = relationship("RelationModel", foreign_keys="RelationModel.target_id", back_populates="target_entity")


class RelationModel(Base):
    """关系表模型"""

    __allow_unmapped__ = True
    __tablename__ = 'relations'
    
    source_id: Any = Column(CHAR(36), ForeignKey('entities.id'), nullable=False, comment='源实体ID')
    target_id: Any = Column(CHAR(36), ForeignKey('entities.id'), nullable=False, comment='目标实体ID')
    relation_type: Any = Column(VARCHAR(100), nullable=False, comment='关系类型')
    properties: Any = Column(JSON, comment='关系属性')
    confidence: Any = Column(DECIMAL(3, 2), default=0.0, comment='置信度')
    source_documents: Any = Column(JSON, comment='来源文档')
    
    # 索引
    __table_args__ = (
        Index('idx_source_id', 'source_id'),
        Index('idx_target_id', 'target_id'),
        Index('idx_relation_type', 'relation_type'),
        Index('idx_confidence', 'confidence'),
        Index('idx_created_at', 'created_at'),
    )
    
    # 关系
    source_entity = relationship("EntityModel", foreign_keys=[source_id], back_populates="source_relations")
    target_entity = relationship("EntityModel", foreign_keys=[target_id], back_populates="target_relations")


class TaskModel(Base):
    """任务表模型"""

    __allow_unmapped__ = True
    __tablename__ = 'tasks'
    
    task_type: Any = Column(VARCHAR(50), nullable=False, comment='任务类型')
    status: Any = Column(VARCHAR(50), nullable=False, comment='任务状态')
    input_data: Any = Column(JSON, comment='输入数据')
    output_data: Any = Column(JSON, comment='输出数据')
    error_message: Any = Column(TEXT, comment='错误信息')
    progress: Any = Column(DECIMAL(5, 2), default=0.0, comment='进度')
    priority: Any = Column(Integer, default=0, comment='优先级')
    
    # 索引
    __table_args__ = (
        Index('idx_task_type', 'task_type'),
        Index('idx_status', 'status'),
        Index('idx_priority', 'priority'),
        Index('idx_created_at', 'created_at'),
    )


class QueryLogModel(Base):
    """查询日志表模型"""

    __allow_unmapped__ = True
    __tablename__ = 'query_logs'
    
    user_id: Any = Column(VARCHAR(64), comment='用户ID')
    query: Any = Column(TEXT, nullable=False, comment='查询内容')
    search_type: Any = Column(VARCHAR(50), comment='搜索类型')
    result_count: Any = Column(Integer, default=0, comment='结果数量')
    response_time: Any = Column(DECIMAL(10, 3), comment='响应时间')
    meta_data: Any = Column(JSON, comment='元数据')
    
    # 索引
    __table_args__ = (
        Index('idx_user_id', 'user_id'),
        Index('idx_search_type', 'search_type'),
        Index('idx_created_at', 'created_at'),
    )


class MetricModel(Base):
    """指标表模型"""

    __allow_unmapped__ = True
    __tablename__ = 'metrics'
    
    metric_name: Any = Column(VARCHAR(100), nullable=False, comment='指标名称')
    metric_value: Any = Column(DECIMAL(15, 4), nullable=False, comment='指标值')
    metric_type: Any = Column(VARCHAR(50), comment='指标类型')
    tags: Any = Column(JSON, comment='标签')
    
    # 索引
    __table_args__ = (
        Index('idx_metric_name', 'metric_name'),
        Index('idx_metric_type', 'metric_type'),
        Index('idx_created_at', 'created_at'),
    )


class VectorModel(Base):
    """向量表模型"""

    __allow_unmapped__ = True
    __tablename__ = 'vectors'
    
    text: Any = Column(TEXT, comment='文本内容')
    vector: Any = Column(JSON, comment='向量数据')
    model: Any = Column(VARCHAR(100), comment='模型名称')
    vector_type: Any = Column(VARCHAR(50), comment='向量类型')
    dimension: Any = Column(Integer, comment='向量维度')
    source_id: Any = Column(VARCHAR(255), comment='来源ID')
    source_type: Any = Column(VARCHAR(100), comment='来源类型')
    chunk_index: Any = Column(Integer, comment='块索引')
    page_number: Any = Column(Integer, comment='页码')
    language: Any = Column(VARCHAR(10), comment='语言')
    meta_data: Any = Column(JSON, comment='元数据')
    
    # 索引
    __table_args__ = (
        Index('idx_source_id', 'source_id'),
        Index('idx_source_type', 'source_type'),
        Index('idx_model', 'model'),
        Index('idx_vector_type', 'vector_type'),
        Index('idx_created_at', 'created_at'),
    )


class ConfigModel(Base):
    """配置表模型"""

    __allow_unmapped__ = True
    __tablename__ = 'configs'
    
    config_key: Any = Column(VARCHAR(255), nullable=False, comment='配置键')
    value: Any = Column(TEXT, comment='配置值')
    data_type: Any = Column(VARCHAR(50), comment='数据类型')
    config_type: Any = Column(VARCHAR(50), comment='配置类型')
    scope: Any = Column(VARCHAR(50), comment='作用域')
    scope_id: Any = Column(VARCHAR(255), comment='作用域ID')
    description: Any = Column(TEXT, comment='描述')
    default_value: Any = Column(TEXT, comment='默认值')
    validation_rules: Any = Column(JSON, comment='验证规则')
    is_sensitive: Any = Column(Boolean, default=False, comment='是否敏感')
    is_readonly: Any = Column(Boolean, default=False, comment='是否只读')
    status: Any = Column(VARCHAR(50), default='active', comment='状态')
    version: Any = Column(Integer, default=1, comment='版本')
    created_by: Any = Column(VARCHAR(255), comment='创建者')
    updated_by: Any = Column(VARCHAR(255), comment='更新者')
    tags: Any = Column(JSON, comment='标签')
    meta_data: Any = Column(JSON, comment='元数据')
    
    # 索引
    __table_args__ = (
        Index('uk_config', 'config_key', 'scope', 'scope_id', unique=True),
        Index('idx_config_type', 'config_type'),
        Index('idx_scope', 'scope'),
        Index('idx_status', 'status'),
    )


class ConfigHistoryModel(Base):
    """配置历史表模型"""

    __allow_unmapped__ = True
    __tablename__ = 'config_history'
    
    config_key: Any = Column(VARCHAR(255), nullable=False, comment='配置键')
    old_value: Any = Column(TEXT, comment='旧值')
    new_value: Any = Column(TEXT, comment='新值')
    scope: Any = Column(VARCHAR(50), comment='作用域')
    scope_id: Any = Column(VARCHAR(255), comment='作用域ID')
    change_type: Any = Column(VARCHAR(50), comment='变更类型')
    changed_by: Any = Column(VARCHAR(255), comment='变更者')
    change_reason: Any = Column(TEXT, comment='变更原因')
    timestamp: Any = Column(DateTime, default=func.now(), comment='时间戳')
    meta_data: Any = Column(JSON, comment='元数据')
    
    # 索引
    __table_args__ = (
        Index('idx_config_key', 'config_key'),
        Index('idx_timestamp', 'timestamp'),
        Index('idx_changed_by', 'changed_by'),
    )


class ConfigTemplateModel(Base):
    """配置模板表模型"""

    __allow_unmapped__ = True
    __tablename__ = 'config_templates'
    
    name: Any = Column(VARCHAR(255), nullable=False, comment='模板名称')
    description: Any = Column(TEXT, comment='模板描述')
    template_data: Any = Column(JSON, comment='模板数据')
    category: Any = Column(VARCHAR(100), comment='分类')
    version: Any = Column(VARCHAR(50), comment='版本')
    is_default: Any = Column(Boolean, default=False, comment='是否默认')
    
    # 索引
    __table_args__ = (
        Index('idx_name', 'name'),
        Index('idx_category', 'category'),
        Index('idx_version', 'version'),
    )


class ETLJobModel(Base):
    """ETL作业表模型"""

    __allow_unmapped__ = True
    __tablename__ = 'etl_jobs'
    
    name: Any = Column(VARCHAR(255), nullable=False, comment='作业名称')
    description: Any = Column(TEXT, comment='作业描述')
    job_type: Any = Column(VARCHAR(50), comment='作业类型')
    source_config: Any = Column(JSON, comment='源配置')
    target_config: Any = Column(JSON, comment='目标配置')
    steps_config: Any = Column(JSON, comment='步骤配置')
    schedule_config: Any = Column(VARCHAR(255), comment='调度配置')
    config: Any = Column(JSON, comment='配置')
    status: Any = Column(VARCHAR(50), comment='状态')
    priority: Any = Column(Integer, comment='优先级')
    created_by: Any = Column(VARCHAR(255), comment='创建者')
    start_time: Any = Column(DateTime, comment='开始时间')
    end_time: Any = Column(DateTime, comment='结束时间')
    last_run_time: Any = Column(DateTime, comment='最后运行时间')
    next_run_time: Any = Column(DateTime, comment='下次运行时间')
    run_count: Any = Column(Integer, default=0, comment='运行次数')
    success_count: Any = Column(Integer, default=0, comment='成功次数')
    failure_count: Any = Column(Integer, default=0, comment='失败次数')
    error_message: Any = Column(TEXT, comment='错误信息')
    metrics: Any = Column(JSON, comment='指标')
    
    # 索引
    __table_args__ = (
        Index('idx_name', 'name'),
        Index('idx_job_type', 'job_type'),
        Index('idx_status', 'status'),
        Index('idx_created_by', 'created_by'),
    )
    
    # 关系
    job_runs = relationship("ETLJobRunModel", back_populates="job", cascade="all, delete-orphan")


class ETLJobRunModel(Base):
    """ETL作业运行记录表模型"""

    __allow_unmapped__ = True
    __tablename__ = 'etl_job_runs'
    
    job_id: Any = Column(CHAR(36), ForeignKey('etl_jobs.id'), nullable=False, comment='作业ID')
    run_number: Any = Column(Integer, comment='运行编号')
    status: Any = Column(VARCHAR(50), comment='状态')
    start_time: Any = Column(DateTime, comment='开始时间')
    end_time: Any = Column(DateTime, comment='结束时间')
    duration_seconds: Any = Column(Integer, comment='持续时间(秒)')
    records_processed: Any = Column(Integer, default=0, comment='处理记录数')
    records_success: Any = Column(Integer, default=0, comment='成功记录数')
    records_failed: Any = Column(Integer, default=0, comment='失败记录数')
    error_message: Any = Column(TEXT, comment='错误信息')
    step_results: Any = Column(JSON, comment='步骤结果')
    metrics: Any = Column(JSON, comment='指标')
    logs: Any = Column(JSON, comment='日志')
    
    # 索引
    __table_args__ = (
        Index('idx_job_id', 'job_id'),
        Index('idx_status', 'status'),
        Index('idx_start_time', 'start_time'),
    )
    
    # 关系
    job = relationship("ETLJobModel", back_populates="job_runs")


class ETLMetricModel(Base):
    """ETL指标表模型"""

    __allow_unmapped__ = True
    __tablename__ = 'etl_metrics'
    
    job_id: Any = Column(CHAR(36), comment='作业ID')
    run_id: Any = Column(CHAR(36), comment='运行ID')
    metric_name: Any = Column(VARCHAR(100), comment='指标名称')
    metric_value: Any = Column(DECIMAL(15, 4), comment='指标值')
    metric_type: Any = Column(VARCHAR(50), comment='指标类型')
    timestamp: Any = Column(DateTime, default=func.now(), comment='时间戳')
    tags: Any = Column(JSON, comment='标签')
    
    # 索引
    __table_args__ = (
        Index('idx_job_id', 'job_id'),
        Index('idx_run_id', 'run_id'),
        Index('idx_metric_name', 'metric_name'),
        Index('idx_timestamp', 'timestamp'),
    )