"""关系数据仓库"""

from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc
from sqlalchemy.exc import SQLAlchemyError

from backend.models.knowledge import KnowledgeRelation, KnowledgeEntity
from backend.utils.logger import get_logger

logger = get_logger(__name__)


class RelationRepository:
    """关系数据仓库"""
    
    def __init__(self, db: Session):
        self.db = db
    
    async def create_relation(
        self,
        source_entity_id: str,
        target_entity_id: str,
        relation_type: str,
        description: Optional[str] = None,
        properties: Optional[Dict[str, Any]] = None,
        confidence_score: Optional[float] = None,
        source_documents: Optional[List[str]] = None
    ) -> KnowledgeRelation:
        """创建关系"""
        try:
            import json
            
            relation = KnowledgeRelation(
                source_entity_id=source_entity_id,
                target_entity_id=target_entity_id,
                relation_type=relation_type,
                description=description,
                properties=json.dumps(properties) if properties else None,
                confidence_score=confidence_score,
                source_documents=json.dumps(source_documents) if source_documents else None,
                mention_count=1
            )
            
            self.db.add(relation)
            self.db.commit()
            self.db.refresh(relation)
            
            logger.info(f"Created relation: {source_entity_id} -> {target_entity_id} ({relation.id})")
            return relation
            
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Failed to create relation {source_entity_id} -> {target_entity_id}: {str(e)}")
            raise
    
    async def get_relation_by_id(self, relation_id: str) -> Optional[KnowledgeRelation]:
        """根据ID获取关系"""
        try:
            relation = self.db.query(KnowledgeRelation).filter(
                and_(
                    KnowledgeRelation.id == relation_id,
                    KnowledgeRelation.is_deleted == False
                )
            ).first()
            
            return relation
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to get relation {relation_id}: {str(e)}")
            raise
    
    async def get_relations_by_entity(
        self,
        entity_id: str,
        direction: str = "both",  # "outgoing", "incoming", "both"
        relation_type: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[KnowledgeRelation]:
        """获取实体的关系"""
        try:
            query = self.db.query(KnowledgeRelation).filter(
                KnowledgeRelation.is_deleted == False
            )
            
            # 根据方向过滤
            if direction == "outgoing":
                query = query.filter(KnowledgeRelation.source_entity_id == entity_id)
            elif direction == "incoming":
                query = query.filter(KnowledgeRelation.target_entity_id == entity_id)
            else:  # both
                query = query.filter(
                    or_(
                        KnowledgeRelation.source_entity_id == entity_id,
                        KnowledgeRelation.target_entity_id == entity_id
                    )
                )
            
            # 关系类型过滤
            if relation_type:
                query = query.filter(KnowledgeRelation.relation_type == relation_type)
            
            # 排序
            query = query.order_by(
                desc(KnowledgeRelation.confidence_score),
                desc(KnowledgeRelation.mention_count),
                desc(KnowledgeRelation.created_at)
            )
            
            relations = query.offset(offset).limit(limit).all()
            return relations
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to get relations for entity {entity_id}: {str(e)}")
            raise
    
    async def get_relation_by_entities(
        self,
        source_entity_id: str,
        target_entity_id: str,
        relation_type: Optional[str] = None
    ) -> Optional[KnowledgeRelation]:
        """根据实体对获取关系"""
        try:
            query = self.db.query(KnowledgeRelation).filter(
                and_(
                    KnowledgeRelation.source_entity_id == source_entity_id,
                    KnowledgeRelation.target_entity_id == target_entity_id,
                    KnowledgeRelation.is_deleted == False
                )
            )
            
            if relation_type:
                query = query.filter(KnowledgeRelation.relation_type == relation_type)
            
            relation = query.first()
            return relation
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to get relation between {source_entity_id} and {target_entity_id}: {str(e)}")
            raise
    
    async def search_relations(
        self,
        query: str,
        relation_type: Optional[str] = None,
        limit: int = 20,
        offset: int = 0
    ) -> List[KnowledgeRelation]:
        """搜索关系"""
        try:
            search_pattern = f"%{query}%"
            
            db_query = self.db.query(KnowledgeRelation).filter(
                and_(
                    or_(
                        KnowledgeRelation.relation_type.like(search_pattern),
                        KnowledgeRelation.description.like(search_pattern)
                    ),
                    KnowledgeRelation.is_deleted == False
                )
            )
            
            if relation_type:
                db_query = db_query.filter(KnowledgeRelation.relation_type == relation_type)
            
            # 排序
            db_query = db_query.order_by(
                func.case(
                    [(KnowledgeRelation.relation_type == query, 1)],
                    else_=func.case(
                        [(KnowledgeRelation.relation_type.like(f"{query}%"), 2)],
                        else_=3
                    )
                ),
                desc(KnowledgeRelation.confidence_score),
                desc(KnowledgeRelation.created_at)
            )
            
            relations = db_query.offset(offset).limit(limit).all()
            return relations
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to search relations with query '{query}': {str(e)}")
            raise
    
    async def update_relation(
        self,
        relation_id: str,
        **kwargs
    ) -> Optional[KnowledgeRelation]:
        """更新关系"""
        try:
            relation = await self.get_relation_by_id(relation_id)
            if not relation:
                return None
            
            # 处理JSON字段
            if 'properties' in kwargs and kwargs['properties'] is not None:
                import json
                kwargs['properties'] = json.dumps(kwargs['properties'])
            
            if 'source_documents' in kwargs and kwargs['source_documents'] is not None:
                import json
                kwargs['source_documents'] = json.dumps(kwargs['source_documents'])
            
            # 更新字段
            for key, value in kwargs.items():
                if hasattr(relation, key):
                    setattr(relation, key, value)
            
            self.db.commit()
            self.db.refresh(relation)
            
            logger.info(f"Updated relation: {relation_id}")
            return relation
            
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Failed to update relation {relation_id}: {str(e)}")
            raise
    
    async def delete_relation(self, relation_id: str) -> bool:
        """删除关系（软删除）"""
        try:
            relation = await self.get_relation_by_id(relation_id)
            if not relation:
                return False
            
            relation.is_deleted = True
            self.db.commit()
            
            logger.info(f"Deleted relation: {relation_id}")
            return True
            
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Failed to delete relation {relation_id}: {str(e)}")
            raise
    
    async def get_relations_by_type(
        self, 
        relation_type: str, 
        limit: int = 100,
        offset: int = 0
    ) -> List[KnowledgeRelation]:
        """根据类型获取关系列表"""
        try:
            relations = self.db.query(KnowledgeRelation).filter(
                and_(
                    KnowledgeRelation.relation_type == relation_type,
                    KnowledgeRelation.is_deleted == False
                )
            ).order_by(
                desc(KnowledgeRelation.confidence_score),
                desc(KnowledgeRelation.mention_count)
            ).offset(offset).limit(limit).all()
            
            return relations
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to get relations by type {relation_type}: {str(e)}")
            raise
    
    async def increment_mention_count(self, relation_id: str) -> bool:
        """增加关系提及次数"""
        try:
            relation = await self.get_relation_by_id(relation_id)
            if not relation:
                return False
            
            relation.mention_count += 1
            self.db.commit()
            
            return True
            
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Failed to increment mention count for relation {relation_id}: {str(e)}")
            raise
    
    async def get_entity_graph(
        self,
        entity_id: str,
        max_depth: int = 2,
        relation_types: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """获取实体的关系图"""
        try:
            # 获取直接关系
            query = self.db.query(KnowledgeRelation).filter(
                and_(
                    or_(
                        KnowledgeRelation.source_entity_id == entity_id,
                        KnowledgeRelation.target_entity_id == entity_id
                    ),
                    KnowledgeRelation.is_deleted == False
                )
            )
            
            if relation_types:
                query = query.filter(KnowledgeRelation.relation_type.in_(relation_types))
            
            direct_relations = query.all()
            
            # 构建图结构
            nodes = set([entity_id])
            edges = []
            
            for relation in direct_relations:
                nodes.add(relation.source_entity_id)
                nodes.add(relation.target_entity_id)
                edges.append({
                    'id': relation.id,
                    'source': relation.source_entity_id,
                    'target': relation.target_entity_id,
                    'type': relation.relation_type,
                    'confidence': relation.confidence_score,
                    'description': relation.description
                })
            
            # 如果需要更深层次，递归获取
            if max_depth > 1:
                # 这里可以实现递归逻辑，暂时只返回直接关系
                pass
            
            return {
                'nodes': list(nodes),
                'edges': edges,
                'center_node': entity_id
            }
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to get entity graph for {entity_id}: {str(e)}")
            raise
    
    async def get_relation_statistics(self) -> Dict[str, Any]:
        """获取关系统计信息"""
        try:
            # 总关系数
            total_count = self.db.query(func.count(KnowledgeRelation.id)).filter(
                KnowledgeRelation.is_deleted == False
            ).scalar()
            
            # 按类型统计
            type_stats = self.db.query(
                KnowledgeRelation.relation_type,
                func.count(KnowledgeRelation.id).label('count')
            ).filter(
                KnowledgeRelation.is_deleted == False
            ).group_by(KnowledgeRelation.relation_type).all()
            
            # 置信度统计
            confidence_stats = self.db.query(
                func.avg(KnowledgeRelation.confidence_score).label('avg_confidence'),
                func.min(KnowledgeRelation.confidence_score).label('min_confidence'),
                func.max(KnowledgeRelation.confidence_score).label('max_confidence')
            ).filter(
                and_(
                    KnowledgeRelation.is_deleted == False,
                    KnowledgeRelation.confidence_score.isnot(None)
                )
            ).first()
            
            return {
                'total_relations': total_count,
                'relation_types': {row.relation_type: row.count for row in type_stats},
                'confidence_stats': {
                    'average': float(confidence_stats.avg_confidence) if confidence_stats.avg_confidence else 0,
                    'minimum': float(confidence_stats.min_confidence) if confidence_stats.min_confidence else 0,
                    'maximum': float(confidence_stats.max_confidence) if confidence_stats.max_confidence else 0
                }
            }
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to get relation statistics: {str(e)}")
            raise