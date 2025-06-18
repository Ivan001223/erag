"""实体数据仓库"""

from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc
from sqlalchemy.exc import SQLAlchemyError

from backend.models.knowledge import KnowledgeEntity
from backend.utils.logger import get_logger

logger = get_logger(__name__)


class EntityRepository:
    """实体数据仓库"""
    
    def __init__(self, db: Session):
        self.db = db
    
    async def create_entity(
        self,
        name: str,
        entity_type: str,
        description: Optional[str] = None,
        aliases: Optional[List[str]] = None,
        properties: Optional[Dict[str, Any]] = None,
        confidence_score: Optional[float] = None,
        source_documents: Optional[List[str]] = None
    ) -> KnowledgeEntity:
        """创建实体"""
        try:
            import json
            
            entity = KnowledgeEntity(
                name=name,
                entity_type=entity_type,
                description=description,
                aliases=json.dumps(aliases) if aliases else None,
                properties=json.dumps(properties) if properties else None,
                confidence_score=confidence_score,
                source_documents=json.dumps(source_documents) if source_documents else None,
                mention_count=1
            )
            
            self.db.add(entity)
            self.db.commit()
            self.db.refresh(entity)
            
            logger.info(f"Created entity: {name} ({entity.id})")
            return entity
            
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Failed to create entity {name}: {str(e)}")
            raise
    
    async def get_entity_by_id(self, entity_id: str) -> Optional[KnowledgeEntity]:
        """根据ID获取实体"""
        try:
            entity = self.db.query(KnowledgeEntity).filter(
                and_(
                    KnowledgeEntity.id == entity_id,
                    KnowledgeEntity.is_deleted == False
                )
            ).first()
            
            return entity
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to get entity {entity_id}: {str(e)}")
            raise
    
    async def get_entity_by_name(
        self, 
        name: str, 
        entity_type: Optional[str] = None
    ) -> Optional[KnowledgeEntity]:
        """根据名称获取实体"""
        try:
            query = self.db.query(KnowledgeEntity).filter(
                and_(
                    KnowledgeEntity.name == name,
                    KnowledgeEntity.is_deleted == False
                )
            )
            
            if entity_type:
                query = query.filter(KnowledgeEntity.entity_type == entity_type)
            
            entity = query.first()
            return entity
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to get entity by name {name}: {str(e)}")
            raise
    
    async def search_entities(
        self,
        query: str,
        entity_type: Optional[str] = None,
        limit: int = 20,
        offset: int = 0
    ) -> List[KnowledgeEntity]:
        """搜索实体"""
        try:
            search_pattern = f"%{query}%"
            
            db_query = self.db.query(KnowledgeEntity).filter(
                and_(
                    or_(
                        KnowledgeEntity.name.like(search_pattern),
                        KnowledgeEntity.description.like(search_pattern)
                    ),
                    KnowledgeEntity.is_deleted == False
                )
            )
            
            if entity_type:
                db_query = db_query.filter(KnowledgeEntity.entity_type == entity_type)
            
            # 排序：精确匹配优先，然后按置信度和创建时间
            db_query = db_query.order_by(
                func.case(
                    [(KnowledgeEntity.name == query, 1)],
                    else_=func.case(
                        [(KnowledgeEntity.name.like(f"{query}%"), 2)],
                        else_=3
                    )
                ),
                desc(KnowledgeEntity.confidence_score),
                desc(KnowledgeEntity.created_at)
            )
            
            entities = db_query.offset(offset).limit(limit).all()
            return entities
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to search entities with query '{query}': {str(e)}")
            raise
    
    async def update_entity(
        self,
        entity_id: str,
        **kwargs
    ) -> Optional[KnowledgeEntity]:
        """更新实体"""
        try:
            entity = await self.get_entity_by_id(entity_id)
            if not entity:
                return None
            
            # 处理JSON字段
            if 'aliases' in kwargs and kwargs['aliases'] is not None:
                import json
                kwargs['aliases'] = json.dumps(kwargs['aliases'])
            
            if 'properties' in kwargs and kwargs['properties'] is not None:
                import json
                kwargs['properties'] = json.dumps(kwargs['properties'])
            
            if 'source_documents' in kwargs and kwargs['source_documents'] is not None:
                import json
                kwargs['source_documents'] = json.dumps(kwargs['source_documents'])
            
            # 更新字段
            for key, value in kwargs.items():
                if hasattr(entity, key):
                    setattr(entity, key, value)
            
            self.db.commit()
            self.db.refresh(entity)
            
            logger.info(f"Updated entity: {entity_id}")
            return entity
            
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Failed to update entity {entity_id}: {str(e)}")
            raise
    
    async def delete_entity(self, entity_id: str) -> bool:
        """删除实体（软删除）"""
        try:
            entity = await self.get_entity_by_id(entity_id)
            if not entity:
                return False
            
            entity.is_deleted = True
            self.db.commit()
            
            logger.info(f"Deleted entity: {entity_id}")
            return True
            
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Failed to delete entity {entity_id}: {str(e)}")
            raise
    
    async def get_entities_by_type(
        self, 
        entity_type: str, 
        limit: int = 100,
        offset: int = 0
    ) -> List[KnowledgeEntity]:
        """根据类型获取实体列表"""
        try:
            entities = self.db.query(KnowledgeEntity).filter(
                and_(
                    KnowledgeEntity.entity_type == entity_type,
                    KnowledgeEntity.is_deleted == False
                )
            ).order_by(
                desc(KnowledgeEntity.confidence_score),
                desc(KnowledgeEntity.mention_count)
            ).offset(offset).limit(limit).all()
            
            return entities
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to get entities by type {entity_type}: {str(e)}")
            raise
    
    async def increment_mention_count(self, entity_id: str) -> bool:
        """增加实体提及次数"""
        try:
            entity = await self.get_entity_by_id(entity_id)
            if not entity:
                return False
            
            entity.mention_count += 1
            self.db.commit()
            
            return True
            
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Failed to increment mention count for entity {entity_id}: {str(e)}")
            raise
    
    async def get_entity_statistics(self) -> Dict[str, Any]:
        """获取实体统计信息"""
        try:
            # 总实体数
            total_count = self.db.query(func.count(KnowledgeEntity.id)).filter(
                KnowledgeEntity.is_deleted == False
            ).scalar()
            
            # 按类型统计
            type_stats = self.db.query(
                KnowledgeEntity.entity_type,
                func.count(KnowledgeEntity.id).label('count')
            ).filter(
                KnowledgeEntity.is_deleted == False
            ).group_by(KnowledgeEntity.entity_type).all()
            
            # 置信度统计
            confidence_stats = self.db.query(
                func.avg(KnowledgeEntity.confidence_score).label('avg_confidence'),
                func.min(KnowledgeEntity.confidence_score).label('min_confidence'),
                func.max(KnowledgeEntity.confidence_score).label('max_confidence')
            ).filter(
                and_(
                    KnowledgeEntity.is_deleted == False,
                    KnowledgeEntity.confidence_score.isnot(None)
                )
            ).first()
            
            return {
                'total_entities': total_count,
                'entity_types': {row.entity_type: row.count for row in type_stats},
                'confidence_stats': {
                    'average': float(confidence_stats.avg_confidence) if confidence_stats.avg_confidence else 0,
                    'minimum': float(confidence_stats.min_confidence) if confidence_stats.min_confidence else 0,
                    'maximum': float(confidence_stats.max_confidence) if confidence_stats.max_confidence else 0
                }
            }
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to get entity statistics: {str(e)}")
            raise