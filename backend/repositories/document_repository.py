"""文档数据仓库"""

from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, func, desc, asc, text
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime

from backend.models.knowledge import Document, DocumentChunk, KnowledgeBase, DocumentStatus, DocumentType
from backend.utils.logger import get_logger

logger = get_logger(__name__)


class DocumentRepository:
    """文档数据仓库"""
    
    def __init__(self, db: Session):
        self.db = db
    
    async def create_document(
        self,
        title: str,
        knowledge_base_id: str,
        user_id: str,
        filename: Optional[str] = None,
        file_path: Optional[str] = None,
        file_url: Optional[str] = None,
        file_size: Optional[int] = None,
        file_hash: Optional[str] = None,
        mime_type: Optional[str] = None,
        document_type: DocumentType = DocumentType.TEXT,
        content: Optional[str] = None,
        **kwargs
    ) -> Document:
        """创建文档"""
        try:
            document = Document(
                title=title,
                filename=filename,
                file_path=file_path,
                file_url=file_url,
                file_size=file_size,
                file_hash=file_hash,
                mime_type=mime_type,
                document_type=document_type,
                status=DocumentStatus.PENDING,
                knowledge_base_id=knowledge_base_id,
                user_id=user_id,
                content=content,
                **kwargs
            )
            
            self.db.add(document)
            self.db.commit()
            self.db.refresh(document)
            
            logger.info(f"Created document: {title} ({document.id})")
            return document
            
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Failed to create document {title}: {str(e)}")
            raise
    
    async def get_document_by_id(self, document_id: str) -> Optional[Document]:
        """根据ID获取文档"""
        try:
            document = self.db.query(Document).filter(
                and_(
                    Document.id == document_id,
                    Document.is_deleted == False
                )
            ).first()
            
            return document
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to get document {document_id}: {str(e)}")
            raise
    
    async def get_documents_by_knowledge_base(
        self,
        knowledge_base_id: str,
        status: Optional[DocumentStatus] = None,
        document_type: Optional[DocumentType] = None,
        limit: int = 50,
        offset: int = 0,
        order_by: str = "created_at",
        order_desc: bool = True
    ) -> List[Document]:
        """获取知识库的文档列表"""
        try:
            query = self.db.query(Document).filter(
                and_(
                    Document.knowledge_base_id == knowledge_base_id,
                    Document.is_deleted == False
                )
            )
            
            if status:
                query = query.filter(Document.status == status)
            
            if document_type:
                query = query.filter(Document.document_type == document_type)
            
            # 排序
            if hasattr(Document, order_by):
                order_column = getattr(Document, order_by)
                if order_desc:
                    query = query.order_by(desc(order_column))
                else:
                    query = query.order_by(asc(order_column))
            
            documents = query.offset(offset).limit(limit).all()
            return documents
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to get documents for knowledge base {knowledge_base_id}: {str(e)}")
            raise
    
    async def search_documents(
        self,
        query: str,
        knowledge_base_id: Optional[str] = None,
        user_id: Optional[str] = None,
        document_type: Optional[DocumentType] = None,
        status: Optional[DocumentStatus] = None,
        limit: int = 20,
        offset: int = 0
    ) -> List[Document]:
        """搜索文档"""
        try:
            search_pattern = f"%{query}%"
            
            db_query = self.db.query(Document).filter(
                and_(
                    or_(
                        Document.title.like(search_pattern),
                        Document.filename.like(search_pattern),
                        Document.content.like(search_pattern),
                        Document.summary.like(search_pattern),
                        Document.keywords.like(search_pattern)
                    ),
                    Document.is_deleted == False
                )
            )
            
            if knowledge_base_id:
                db_query = db_query.filter(Document.knowledge_base_id == knowledge_base_id)
            
            if user_id:
                db_query = db_query.filter(Document.user_id == user_id)
            
            if document_type:
                db_query = db_query.filter(Document.document_type == document_type)
            
            if status:
                db_query = db_query.filter(Document.status == status)
            
            # 排序：标题匹配优先
            db_query = db_query.order_by(
                func.case(
                    [(Document.title.like(f"%{query}%"), 1)],
                    else_=2
                ),
                desc(Document.created_at)
            )
            
            documents = db_query.offset(offset).limit(limit).all()
            return documents
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to search documents with query '{query}': {str(e)}")
            raise
    
    async def update_document(
        self,
        document_id: str,
        **kwargs
    ) -> Optional[Document]:
        """更新文档"""
        try:
            document = await self.get_document_by_id(document_id)
            if not document:
                return None
            
            # 更新字段
            for key, value in kwargs.items():
                if hasattr(document, key):
                    setattr(document, key, value)
            
            # 更新修改时间
            document.updated_at = datetime.utcnow()
            
            self.db.commit()
            self.db.refresh(document)
            
            logger.info(f"Updated document: {document_id}")
            return document
            
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Failed to update document {document_id}: {str(e)}")
            raise
    
    async def delete_document(self, document_id: str) -> bool:
        """删除文档（软删除）"""
        try:
            document = await self.get_document_by_id(document_id)
            if not document:
                return False
            
            document.is_deleted = True
            self.db.commit()
            
            logger.info(f"Deleted document: {document_id}")
            return True
            
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Failed to delete document {document_id}: {str(e)}")
            raise
    
    async def get_document_with_chunks(self, document_id: str) -> Optional[Document]:
        """获取文档及其块"""
        try:
            document = self.db.query(Document).options(
                joinedload(Document.chunks)
            ).filter(
                and_(
                    Document.id == document_id,
                    Document.is_deleted == False
                )
            ).first()
            
            return document
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to get document with chunks {document_id}: {str(e)}")
            raise
    
    async def get_documents_by_hash(self, file_hash: str) -> List[Document]:
        """根据文件哈希获取文档（用于去重）"""
        try:
            documents = self.db.query(Document).filter(
                and_(
                    Document.file_hash == file_hash,
                    Document.is_deleted == False
                )
            ).all()
            
            return documents
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to get documents by hash {file_hash}: {str(e)}")
            raise
    
    async def update_document_status(
        self,
        document_id: str,
        status: DocumentStatus,
        error_message: Optional[str] = None
    ) -> bool:
        """更新文档状态"""
        try:
            document = await self.get_document_by_id(document_id)
            if not document:
                return False
            
            document.status = status
            if error_message:
                document.error_message = error_message
            
            if status == DocumentStatus.COMPLETED:
                document.processed_at = datetime.utcnow()
            
            self.db.commit()
            
            logger.info(f"Updated document status: {document_id} -> {status}")
            return True
            
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Failed to update document status {document_id}: {str(e)}")
            raise
    
    async def get_document_statistics(
        self,
        knowledge_base_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """获取文档统计信息"""
        try:
            query = self.db.query(Document).filter(Document.is_deleted == False)
            
            if knowledge_base_id:
                query = query.filter(Document.knowledge_base_id == knowledge_base_id)
            
            if user_id:
                query = query.filter(Document.user_id == user_id)
            
            # 总文档数
            total_count = query.count()
            
            # 按状态统计
            status_stats = query.with_entities(
                Document.status,
                func.count(Document.id).label('count')
            ).group_by(Document.status).all()
            
            # 按类型统计
            type_stats = query.with_entities(
                Document.document_type,
                func.count(Document.id).label('count')
            ).group_by(Document.document_type).all()
            
            # 文件大小统计
            size_stats = query.with_entities(
                func.sum(Document.file_size).label('total_size'),
                func.avg(Document.file_size).label('avg_size'),
                func.max(Document.file_size).label('max_size')
            ).filter(Document.file_size.isnot(None)).first()
            
            return {
                'total_documents': total_count,
                'status_distribution': {row.status.value: row.count for row in status_stats},
                'type_distribution': {row.document_type.value: row.count for row in type_stats},
                'size_stats': {
                    'total_size': int(size_stats.total_size) if size_stats.total_size else 0,
                    'average_size': int(size_stats.avg_size) if size_stats.avg_size else 0,
                    'max_size': int(size_stats.max_size) if size_stats.max_size else 0
                }
            }
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to get document statistics: {str(e)}")
            raise
    
    async def get_recent_documents(
        self,
        knowledge_base_id: Optional[str] = None,
        user_id: Optional[str] = None,
        limit: int = 10
    ) -> List[Document]:
        """获取最近的文档"""
        try:
            query = self.db.query(Document).filter(Document.is_deleted == False)
            
            if knowledge_base_id:
                query = query.filter(Document.knowledge_base_id == knowledge_base_id)
            
            if user_id:
                query = query.filter(Document.user_id == user_id)
            
            documents = query.order_by(desc(Document.created_at)).limit(limit).all()
            return documents
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to get recent documents: {str(e)}")
            raise
    
    async def count_documents_by_knowledge_base(self, knowledge_base_id: str) -> int:
        """统计知识库的文档数量"""
        try:
            count = self.db.query(func.count(Document.id)).filter(
                and_(
                    Document.knowledge_base_id == knowledge_base_id,
                    Document.is_deleted == False
                )
            ).scalar()
            
            return count
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to count documents for knowledge base {knowledge_base_id}: {str(e)}")
            raise
    
    async def get_documents_by_user(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[Document]:
        """获取用户的文档列表"""
        try:
            documents = self.db.query(Document).filter(
                and_(
                    Document.user_id == user_id,
                    Document.is_deleted == False
                )
            ).order_by(desc(Document.created_at)).offset(offset).limit(limit).all()
            
            return documents
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to get documents for user {user_id}: {str(e)}")
            raise