from sqlalchemy import Column, String, Text, Float, DateTime, ForeignKey, Index, Integer, Boolean, JSON
from sqlalchemy.dialects.mysql import VARCHAR, TEXT, CHAR, DECIMAL
from typing import Any
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from backend.models.base import Base


class GraphModel(Base):
    """知识图谱表模型"""

    __allow_unmapped__ = True
    __tablename__ = 'graphs'
    
    name: Any = Column(VARCHAR(255), nullable=False, comment='图名称')
    description: Any = Column(TEXT, comment='图描述')
    meta_data: Any = Column(JSON, comment='元数据JSON')
    
    # 索引
    __table_args__ = (
        Index('idx_name', 'name'),
        Index('idx_created_at', 'created_at'),
    )
    
    # 关系
    entities = relationship("GraphEntityModel", back_populates="graph", cascade="all, delete-orphan")
    relations = relationship("GraphRelationModel", back_populates="graph", cascade="all, delete-orphan")
    statistics = relationship("GraphStatisticsModel", back_populates="graph", cascade="all, delete-orphan")


class GraphEntityModel(Base):
    """知识图谱实体表模型"""

    __allow_unmapped__ = True
    __tablename__ = 'graph_entities'
    
    name: Any = Column(VARCHAR(255), nullable=False, comment='实体名称')
    entity_type: Any = Column(VARCHAR(100), nullable=False, comment='实体类型')
    properties: Any = Column(TEXT, comment='属性JSON')
    meta_data: Any = Column(TEXT, comment='元数据JSON')
    graph_id: Any = Column(CHAR(36), ForeignKey('graphs.id'), nullable=False, comment='图ID')
    
    # 索引
    __table_args__ = (
        Index('idx_graph_id', 'graph_id'),
        Index('idx_name', 'name'),
        Index('idx_entity_type', 'entity_type'),
        Index('idx_created_at', 'created_at'),
    )
    
    # 关系
    graph = relationship("GraphModel", back_populates="entities")
    source_relations = relationship("GraphRelationModel", foreign_keys="GraphRelationModel.source_id", back_populates="source_entity")
    target_relations = relationship("GraphRelationModel", foreign_keys="GraphRelationModel.target_id", back_populates="target_entity")


class GraphRelationModel(Base):
    """知识图谱关系表模型"""

    __allow_unmapped__ = True
    __tablename__ = 'graph_relations'
    
    source_id: Any = Column(CHAR(36), ForeignKey('graph_entities.id'), nullable=False, comment='源实体ID')
    target_id: Any = Column(CHAR(36), ForeignKey('graph_entities.id'), nullable=False, comment='目标实体ID')
    relation_type: Any = Column(VARCHAR(100), nullable=False, comment='关系类型')
    properties: Any = Column(TEXT, comment='属性JSON')
    meta_data: Any = Column(TEXT, comment='元数据JSON')
    confidence: Any = Column(DECIMAL(3, 2), default=1.0, comment='置信度')
    graph_id: Any = Column(CHAR(36), ForeignKey('graphs.id'), nullable=False, comment='图ID')
    
    # 索引
    __table_args__ = (
        Index('idx_graph_id', 'graph_id'),
        Index('idx_source_id', 'source_id'),
        Index('idx_target_id', 'target_id'),
        Index('idx_relation_type', 'relation_type'),
        Index('idx_confidence', 'confidence'),
        Index('idx_created_at', 'created_at'),
    )
    
    # 关系
    graph = relationship("GraphModel", back_populates="relations")
    source_entity = relationship("GraphEntityModel", foreign_keys=[source_id], back_populates="source_relations")
    target_entity = relationship("GraphEntityModel", foreign_keys=[target_id], back_populates="target_relations")


class GraphStatisticsModel(Base):
    """知识图谱统计表模型"""

    __allow_unmapped__ = True
    __tablename__ = 'graph_statistics'
    
    graph_id: Any = Column(CHAR(36), ForeignKey('graphs.id'), nullable=False, comment='图ID')
    entity_count: Any = Column(Integer, default=0, comment='实体数量')
    relation_count: Any = Column(Integer, default=0, comment='关系数量')
    node_degree_avg: Any = Column(DECIMAL(10, 2), default=0.00, comment='平均节点度')
    clustering_coefficient: Any = Column(DECIMAL(5, 4), default=0.0000, comment='聚类系数')
    diameter: Any = Column(Integer, default=0, comment='图直径')
    density: Any = Column(DECIMAL(10, 8), default=0.00000000, comment='图密度')
    computed_at: Any = Column(DateTime, default=func.current_timestamp(), comment='计算时间')
    
    # 索引
    __table_args__ = (
        Index('idx_graph_id', 'graph_id'),
        Index('idx_computed_at', 'computed_at'),
    )
    
    # 关系
    graph = relationship("GraphModel", back_populates="statistics")