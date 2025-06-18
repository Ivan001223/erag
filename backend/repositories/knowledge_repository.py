"""知识库数据仓库"""

from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, func, desc, asc
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime

from backend.models.knowledge import KnowledgeBase, Document, DocumentChunk
from backend.utils.logger import get_logger

logger = get_logger(__name__)


class KnowledgeRepository:
    """知识库数据仓库"""
    
    def __init__(self, db: Session):
        self.db = db
    
    async def create_knowledge_base(
        self,
        name: str,
        description: str,
        owner_id: str,
        is_public: bool = False,
        settings: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> KnowledgeBase:
        """创建知识库"""
        try:
            import json
            
            knowledge_base = KnowledgeBase(
                name=name,
                description=description,
                owner_id=owner_id,
                is_public=is_public,
                settings=json.dumps(settings) if settings else None,
                metadata=json.dumps(metadata) if metadata else None,
                document_count=0,
                chunk_count=0,
                total_size=0
            )
            
            self.db.add(knowledge_base)
            self.db.commit()
            self.db.refresh(knowledge_base)
            
            logger.info(f"Created knowledge base: {name} ({knowledge_base.id})")
            return knowledge_base
            
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Failed to create knowledge base {name}: {str(e)}")
            raise
    
    async def get_knowledge_base_by_id(self, kb_id: str) -> Optional[KnowledgeBase]:
        """根据ID获取知识库"""
        try:
            kb = self.db.query(KnowledgeBase).filter(
                and_(
                    KnowledgeBase.id == kb_id,
                    KnowledgeBase.is_deleted == False
                )
            ).first()
            
            return kb
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to get knowledge base {kb_id}: {str(e)}")
            raise
    
    async def get_knowledge_base_by_name(
        self, 
        name: str, 
        owner_id: Optional[str] = None
    ) -> Optional[KnowledgeBase]:
        """根据名称获取知识库"""
        try:
            query = self.db.query(KnowledgeBase).filter(
                and_(
                    KnowledgeBase.name == name,
                    KnowledgeBase.is_deleted == False
                )
            )
            
            if owner_id:
                query = query.filter(KnowledgeBase.owner_id == owner_id)
            
            kb = query.first()
            return kb
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to get knowledge base by name {name}: {str(e)}")
            raise
    
    async def get_knowledge_bases_by_owner(
        self,
        owner_id: str,
        include_public: bool = True,
        limit: int = 50,
        offset: int = 0,
        order_by: str = "created_at",
        order_desc: bool = True
    ) -> List[KnowledgeBase]:
        """获取用户的知识库列表"""
        try:
            query = self.db.query(KnowledgeBase).filter(
                KnowledgeBase.is_deleted == False
            )
            
            if include_public:
                query = query.filter(
                    or_(
                        KnowledgeBase.owner_id == owner_id,
                        KnowledgeBase.is_public == True
                    )
                )
            else:
                query = query.filter(KnowledgeBase.owner_id == owner_id)
            
            # 排序
            if hasattr(KnowledgeBase, order_by):
                order_column = getattr(KnowledgeBase, order_by)
                if order_desc:
                    query = query.order_by(desc(order_column))
                else:
                    query = query.order_by(asc(order_column))
            
            kbs = query.offset(offset).limit(limit).all()
            return kbs
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to get knowledge bases for owner {owner_id}: {str(e)}")
            raise
    
    async def get_public_knowledge_bases(
        self,
        limit: int = 50,
        offset: int = 0
    ) -> List[KnowledgeBase]:
        """获取公开的知识库列表"""
        try:
            kbs = self.db.query(KnowledgeBase).filter(
                and_(
                    KnowledgeBase.is_public == True,
                    KnowledgeBase.is_deleted == False
                )
            ).order_by(desc(KnowledgeBase.created_at)).offset(offset).limit(limit).all()
            
            return kbs
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to get public knowledge bases: {str(e)}")
            raise
    
    async def search_knowledge_bases(
        self,
        query: str,
        owner_id: Optional[str] = None,
        include_public: bool = True,
        limit: int = 20,
        offset: int = 0
    ) -> List[KnowledgeBase]:
        """搜索知识库"""
        try:
            search_pattern = f"%{query}%"
            
            db_query = self.db.query(KnowledgeBase).filter(
                and_(
                    or_(
                        KnowledgeBase.name.like(search_pattern),
                        KnowledgeBase.description.like(search_pattern)
                    ),
                    KnowledgeBase.is_deleted == False
                )
            )
            
            # 权限过滤
            if owner_id and include_public:
                db_query = db_query.filter(
                    or_(
                        KnowledgeBase.owner_id == owner_id,
                        KnowledgeBase.is_public == True
                    )
                )
            elif owner_id:
                db_query = db_query.filter(KnowledgeBase.owner_id == owner_id)
            elif include_public:
                db_query = db_query.filter(KnowledgeBase.is_public == True)
            
            # 排序：名称匹配优先
            db_query = db_query.order_by(
                func.case(
                    [(KnowledgeBase.name.like(f"%{query}%"), 1)],
                    else_=2
                ),
                desc(KnowledgeBase.created_at)
            )
            
            kbs = db_query.offset(offset).limit(limit).all()
            return kbs
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to search knowledge bases with query '{query}': {str(e)}")
            raise
    
    async def update_knowledge_base(
        self,
        kb_id: str,
        **kwargs
    ) -> Optional[KnowledgeBase]:
        """更新知识库"""
        try:
            kb = await self.get_knowledge_base_by_id(kb_id)
            if not kb:
                return None
            
            # 处理JSON字段
            if 'settings' in kwargs and kwargs['settings'] is not None:
                import json
                kwargs['settings'] = json.dumps(kwargs['settings'])
            
            if 'metadata' in kwargs and kwargs['metadata'] is not None:
                import json
                kwargs['metadata'] = json.dumps(kwargs['metadata'])
            
            # 更新字段
            for key, value in kwargs.items():
                if hasattr(kb, key):
                    setattr(kb, key, value)
            
            # 更新修改时间
            kb.updated_at = datetime.utcnow()
            
            self.db.commit()
            self.db.refresh(kb)
            
            logger.info(f"Updated knowledge base: {kb_id}")
            return kb
            
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Failed to update knowledge base {kb_id}: {str(e)}")
            raise
    
    async def delete_knowledge_base(self, kb_id: str) -> bool:
        """删除知识库（软删除）"""
        try:
            kb = await self.get_knowledge_base_by_id(kb_id)
            if not kb:
                return False
            
            kb.is_deleted = True
            self.db.commit()
            
            logger.info(f"Deleted knowledge base: {kb_id}")
            return True
            
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Failed to delete knowledge base {kb_id}: {str(e)}")
            raise
    
    async def get_knowledge_base_with_documents(
        self, 
        kb_id: str,
        include_chunks: bool = False
    ) -> Optional[KnowledgeBase]:
        """获取知识库及其文档"""
        try:
            query = self.db.query(KnowledgeBase).options(
                joinedload(KnowledgeBase.documents)
            )
            
            if include_chunks:
                query = query.options(
                    joinedload(KnowledgeBase.documents).joinedload(Document.chunks)
                )
            
            kb = query.filter(
                and_(
                    KnowledgeBase.id == kb_id,
                    KnowledgeBase.is_deleted == False
                )
            ).first()
            
            return kb
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to get knowledge base with documents {kb_id}: {str(e)}")
            raise
    
    async def update_knowledge_base_statistics(self, kb_id: str) -> bool:
        """更新知识库统计信息"""
        try:
            # 统计文档数量
            doc_count = self.db.query(func.count(Document.id)).filter(
                and_(
                    Document.knowledge_base_id == kb_id,
                    Document.is_deleted == False
                )
            ).scalar()
            
            # 统计块数量
            chunk_count = self.db.query(func.count(DocumentChunk.id)).join(
                Document, DocumentChunk.document_id == Document.id
            ).filter(
                and_(
                    Document.knowledge_base_id == kb_id,
                    Document.is_deleted == False,
                    DocumentChunk.is_deleted == False
                )
            ).scalar()
            
            # 统计总大小
            total_size = self.db.query(func.sum(Document.file_size)).filter(
                and_(
                    Document.knowledge_base_id == kb_id,
                    Document.is_deleted == False,
                    Document.file_size.isnot(None)
                )
            ).scalar() or 0
            
            # 更新知识库
            kb = await self.get_knowledge_base_by_id(kb_id)
            if kb:
                kb.document_count = doc_count
                kb.chunk_count = chunk_count
                kb.total_size = int(total_size)
                kb.updated_at = datetime.utcnow()
                
                self.db.commit()
                
                logger.info(f"Updated statistics for knowledge base {kb_id}: {doc_count} docs, {chunk_count} chunks, {total_size} bytes")
                return True
            
            return False
            
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Failed to update statistics for knowledge base {kb_id}: {str(e)}")
            raise
    
    async def get_knowledge_base_statistics(self, kb_id: str) -> Dict[str, Any]:
        """获取知识库详细统计信息"""
        try:
            kb = await self.get_knowledge_base_by_id(kb_id)
            if not kb:
                return {}
            
            # 文档状态统计
            doc_status_stats = self.db.query(
                Document.status,
                func.count(Document.id).label('count')
            ).filter(
                and_(
                    Document.knowledge_base_id == kb_id,
                    Document.is_deleted == False
                )
            ).group_by(Document.status).all()
            
            # 文档类型统计
            doc_type_stats = self.db.query(
                Document.document_type,
                func.count(Document.id).label('count')
            ).filter(
                and_(
                    Document.knowledge_base_id == kb_id,
                    Document.is_deleted == False
                )
            ).group_by(Document.document_type).all()
            
            # 最近活动
            recent_docs = self.db.query(Document).filter(
                and_(
                    Document.knowledge_base_id == kb_id,
                    Document.is_deleted == False
                )
            ).order_by(desc(Document.created_at)).limit(5).all()
            
            return {
                'basic_stats': {
                    'document_count': kb.document_count,
                    'chunk_count': kb.chunk_count,
                    'total_size': kb.total_size
                },
                'document_status': {row.status.value: row.count for row in doc_status_stats},
                'document_types': {row.document_type.value: row.count for row in doc_type_stats},
                'recent_documents': [
                    {
                        'id': doc.id,
                        'title': doc.title,
                        'created_at': doc.created_at.isoformat(),
                        'status': doc.status.value
                    } for doc in recent_docs
                ]
            }
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to get statistics for knowledge base {kb_id}: {str(e)}")
            raise
    
    async def check_knowledge_base_access(
        self, 
        kb_id: str, 
        user_id: str
    ) -> bool:
        """检查用户是否有访问知识库的权限"""
        try:
            kb = self.db.query(KnowledgeBase).filter(
                and_(
                    KnowledgeBase.id == kb_id,
                    KnowledgeBase.is_deleted == False,
                    or_(
                        KnowledgeBase.owner_id == user_id,
                        KnowledgeBase.is_public == True
                    )
                )
            ).first()
            
            return kb is not None
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to check access for knowledge base {kb_id}: {str(e)}")
            raise
    
    async def get_popular_knowledge_bases(
        self, 
        limit: int = 10
    ) -> List[KnowledgeBase]:
        """获取热门知识库（按文档数量排序）"""
        try:
            kbs = self.db.query(KnowledgeBase).filter(
                and_(
                    KnowledgeBase.is_public == True,
                    KnowledgeBase.is_deleted == False
                )
            ).order_by(
                desc(KnowledgeBase.document_count),
                desc(KnowledgeBase.created_at)
            ).limit(limit).all()
            
            return kbs
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to get popular knowledge bases: {str(e)}")
            raise