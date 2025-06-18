"""向量数据仓库"""

from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc, text
from sqlalchemy.exc import SQLAlchemyError
import json

from backend.models.knowledge import DocumentChunk
from backend.utils.logger import get_logger

logger = get_logger(__name__)


class VectorRepository:
    """向量数据仓库"""
    
    def __init__(self, db: Session):
        self.db = db
    
    async def create_chunk(
        self,
        document_id: str,
        content: str,
        chunk_index: int,
        start_pos: int = 0,
        end_pos: Optional[int] = None,
        chunk_type: str = "text",
        metadata: Optional[Dict[str, Any]] = None,
        embedding: Optional[List[float]] = None
    ) -> DocumentChunk:
        """创建文档块"""
        try:
            chunk = DocumentChunk(
                document_id=document_id,
                content=content,
                chunk_index=chunk_index,
                start_pos=start_pos,
                end_pos=end_pos or len(content),
                chunk_type=chunk_type,
                metadata=json.dumps(metadata) if metadata else None,
                embedding=json.dumps(embedding) if embedding else None,
                token_count=len(content.split()) if content else 0
            )
            
            self.db.add(chunk)
            self.db.commit()
            self.db.refresh(chunk)
            
            logger.info(f"Created chunk: {document_id}[{chunk_index}] ({chunk.id})")
            return chunk
            
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Failed to create chunk for document {document_id}: {str(e)}")
            raise
    
    async def get_chunk_by_id(self, chunk_id: str) -> Optional[DocumentChunk]:
        """根据ID获取文档块"""
        try:
            chunk = self.db.query(DocumentChunk).filter(
                and_(
                    DocumentChunk.id == chunk_id,
                    DocumentChunk.is_deleted == False
                )
            ).first()
            
            return chunk
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to get chunk {chunk_id}: {str(e)}")
            raise
    
    async def get_chunks_by_document(
        self,
        document_id: str,
        limit: int = 100,
        offset: int = 0
    ) -> List[DocumentChunk]:
        """获取文档的所有块"""
        try:
            chunks = self.db.query(DocumentChunk).filter(
                and_(
                    DocumentChunk.document_id == document_id,
                    DocumentChunk.is_deleted == False
                )
            ).order_by(DocumentChunk.chunk_index).offset(offset).limit(limit).all()
            
            return chunks
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to get chunks for document {document_id}: {str(e)}")
            raise
    
    async def search_chunks_by_text(
        self,
        query: str,
        document_ids: Optional[List[str]] = None,
        limit: int = 20,
        offset: int = 0
    ) -> List[DocumentChunk]:
        """根据文本内容搜索块"""
        try:
            search_pattern = f"%{query}%"
            
            db_query = self.db.query(DocumentChunk).filter(
                and_(
                    DocumentChunk.content.like(search_pattern),
                    DocumentChunk.is_deleted == False
                )
            )
            
            if document_ids:
                db_query = db_query.filter(DocumentChunk.document_id.in_(document_ids))
            
            # 排序：内容匹配度
            db_query = db_query.order_by(
                func.case(
                    [(DocumentChunk.content.like(f"%{query}%"), 1)],
                    else_=2
                ),
                DocumentChunk.chunk_index
            )
            
            chunks = db_query.offset(offset).limit(limit).all()
            return chunks
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to search chunks with query '{query}': {str(e)}")
            raise
    
    async def update_chunk_embedding(
        self,
        chunk_id: str,
        embedding: List[float]
    ) -> bool:
        """更新块的向量嵌入"""
        try:
            chunk = await self.get_chunk_by_id(chunk_id)
            if not chunk:
                return False
            
            chunk.embedding = json.dumps(embedding)
            self.db.commit()
            
            logger.info(f"Updated embedding for chunk: {chunk_id}")
            return True
            
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Failed to update embedding for chunk {chunk_id}: {str(e)}")
            raise
    
    async def batch_update_embeddings(
        self,
        chunk_embeddings: List[Tuple[str, List[float]]]
    ) -> int:
        """批量更新块的向量嵌入"""
        try:
            updated_count = 0
            
            for chunk_id, embedding in chunk_embeddings:
                chunk = await self.get_chunk_by_id(chunk_id)
                if chunk:
                    chunk.embedding = json.dumps(embedding)
                    updated_count += 1
            
            self.db.commit()
            
            logger.info(f"Batch updated embeddings for {updated_count} chunks")
            return updated_count
            
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Failed to batch update embeddings: {str(e)}")
            raise
    
    async def get_chunks_without_embeddings(
        self,
        limit: int = 100
    ) -> List[DocumentChunk]:
        """获取没有向量嵌入的块"""
        try:
            chunks = self.db.query(DocumentChunk).filter(
                and_(
                    or_(
                        DocumentChunk.embedding.is_(None),
                        DocumentChunk.embedding == ''
                    ),
                    DocumentChunk.is_deleted == False
                )
            ).order_by(DocumentChunk.created_at).limit(limit).all()
            
            return chunks
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to get chunks without embeddings: {str(e)}")
            raise
    
    async def delete_chunk(self, chunk_id: str) -> bool:
        """删除块（软删除）"""
        try:
            chunk = await self.get_chunk_by_id(chunk_id)
            if not chunk:
                return False
            
            chunk.is_deleted = True
            self.db.commit()
            
            logger.info(f"Deleted chunk: {chunk_id}")
            return True
            
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Failed to delete chunk {chunk_id}: {str(e)}")
            raise
    
    async def delete_chunks_by_document(self, document_id: str) -> int:
        """删除文档的所有块"""
        try:
            chunks = await self.get_chunks_by_document(document_id)
            deleted_count = 0
            
            for chunk in chunks:
                chunk.is_deleted = True
                deleted_count += 1
            
            self.db.commit()
            
            logger.info(f"Deleted {deleted_count} chunks for document: {document_id}")
            return deleted_count
            
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Failed to delete chunks for document {document_id}: {str(e)}")
            raise
    
    async def get_chunk_statistics(
        self,
        document_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """获取块统计信息"""
        try:
            query = self.db.query(DocumentChunk).filter(DocumentChunk.is_deleted == False)
            
            if document_id:
                query = query.filter(DocumentChunk.document_id == document_id)
            
            # 总块数
            total_count = query.count()
            
            # 有嵌入的块数
            embedded_count = query.filter(
                and_(
                    DocumentChunk.embedding.isnot(None),
                    DocumentChunk.embedding != ''
                )
            ).count()
            
            # 按类型统计
            type_stats = query.with_entities(
                DocumentChunk.chunk_type,
                func.count(DocumentChunk.id).label('count')
            ).group_by(DocumentChunk.chunk_type).all()
            
            # 内容长度统计
            length_stats = query.with_entities(
                func.avg(func.length(DocumentChunk.content)).label('avg_length'),
                func.min(func.length(DocumentChunk.content)).label('min_length'),
                func.max(func.length(DocumentChunk.content)).label('max_length')
            ).first()
            
            # Token统计
            token_stats = query.with_entities(
                func.sum(DocumentChunk.token_count).label('total_tokens'),
                func.avg(DocumentChunk.token_count).label('avg_tokens')
            ).filter(DocumentChunk.token_count.isnot(None)).first()
            
            return {
                'total_chunks': total_count,
                'embedded_chunks': embedded_count,
                'embedding_coverage': embedded_count / total_count if total_count > 0 else 0,
                'chunk_types': {row.chunk_type: row.count for row in type_stats},
                'content_length': {
                    'average': int(length_stats.avg_length) if length_stats.avg_length else 0,
                    'minimum': int(length_stats.min_length) if length_stats.min_length else 0,
                    'maximum': int(length_stats.max_length) if length_stats.max_length else 0
                },
                'token_stats': {
                    'total_tokens': int(token_stats.total_tokens) if token_stats.total_tokens else 0,
                    'average_tokens': int(token_stats.avg_tokens) if token_stats.avg_tokens else 0
                }
            }
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to get chunk statistics: {str(e)}")
            raise
    
    async def update_chunk(
        self,
        chunk_id: str,
        **kwargs
    ) -> Optional[DocumentChunk]:
        """更新块"""
        try:
            chunk = await self.get_chunk_by_id(chunk_id)
            if not chunk:
                return None
            
            # 处理JSON字段
            if 'metadata' in kwargs and kwargs['metadata'] is not None:
                kwargs['metadata'] = json.dumps(kwargs['metadata'])
            
            if 'embedding' in kwargs and kwargs['embedding'] is not None:
                kwargs['embedding'] = json.dumps(kwargs['embedding'])
            
            # 更新字段
            for key, value in kwargs.items():
                if hasattr(chunk, key):
                    setattr(chunk, key, value)
            
            # 重新计算token数量
            if 'content' in kwargs:
                chunk.token_count = len(kwargs['content'].split()) if kwargs['content'] else 0
            
            self.db.commit()
            self.db.refresh(chunk)
            
            logger.info(f"Updated chunk: {chunk_id}")
            return chunk
            
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Failed to update chunk {chunk_id}: {str(e)}")
            raise
    
    async def get_similar_chunks_by_content(
        self,
        content: str,
        document_ids: Optional[List[str]] = None,
        similarity_threshold: float = 0.8,
        limit: int = 10
    ) -> List[DocumentChunk]:
        """根据内容相似度获取相似块（简单文本匹配）"""
        try:
            # 简单的文本相似度匹配，实际应用中可以使用更复杂的算法
            words = content.lower().split()
            if not words:
                return []
            
            # 构建搜索条件
            conditions = []
            for word in words[:5]:  # 限制关键词数量
                conditions.append(DocumentChunk.content.like(f"%{word}%"))
            
            query = self.db.query(DocumentChunk).filter(
                and_(
                    or_(*conditions),
                    DocumentChunk.is_deleted == False
                )
            )
            
            if document_ids:
                query = query.filter(DocumentChunk.document_id.in_(document_ids))
            
            chunks = query.limit(limit).all()
            return chunks
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to get similar chunks: {str(e)}")
            raise
    
    async def count_chunks_by_document(self, document_id: str) -> int:
        """统计文档的块数量"""
        try:
            count = self.db.query(func.count(DocumentChunk.id)).filter(
                and_(
                    DocumentChunk.document_id == document_id,
                    DocumentChunk.is_deleted == False
                )
            ).scalar()
            
            return count
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to count chunks for document {document_id}: {str(e)}")
            raise