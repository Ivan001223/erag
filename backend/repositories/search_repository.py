from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import select, and_, or_, func, desc, text, case
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta

from .base_repository import BaseRepository
from ..models.database_models import (
    DocumentModel, DocumentChunkModel, EntityModel, 
    QueryLogModel, MetricModel
)
from ..utils.logger import get_logger

logger = get_logger(__name__)


class SearchRepository(BaseRepository[QueryLogModel]):
    """搜索仓储类"""
    
    def __init__(self, db_session: Optional[AsyncSession] = None):
        super().__init__(QueryLogModel, db_session)
    
    async def log_search_query(
        self,
        query: str,
        search_type: str,
        user_id: Optional[str] = None,
        search_id: Optional[str] = None,
        result_count: int = 0,
        search_time: float = 0.0,
        filters: Optional[Dict[str, Any]] = None
    ) -> Optional[QueryLogModel]:
        """记录搜索查询"""
        return await self.create(
            query=query,
            search_type=search_type,
            user_id=user_id,
            search_id=search_id,
            result_count=result_count,
            search_time=search_time,
            filters=filters or {},
            ip_address=None,  # 可以从请求中获取
            user_agent=None   # 可以从请求中获取
        )
    
    async def get_search_history(
        self,
        user_id: str,
        limit: int = 20,
        offset: int = 0
    ) -> List[QueryLogModel]:
        """获取用户搜索历史"""
        return await self.get_all(
            user_id=user_id,
            limit=limit,
            offset=offset,
            order_by='-created_at'
        )
    
    async def get_trending_queries(
        self,
        time_range: str = "24h",
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """获取热门搜索查询"""
        try:
            async with self.get_session() as session:
                # 计算时间范围
                now = datetime.utcnow()
                if time_range == "1h":
                    start_time = now - timedelta(hours=1)
                elif time_range == "24h":
                    start_time = now - timedelta(days=1)
                elif time_range == "7d":
                    start_time = now - timedelta(days=7)
                else:
                    start_time = now - timedelta(days=1)
                
                # 构建查询
                stmt = (
                    select(
                        QueryLogModel.query,
                        func.count(QueryLogModel.id).label('search_count'),
                        func.avg(QueryLogModel.result_count).label('avg_results'),
                        func.max(QueryLogModel.created_at).label('last_searched')
                    )
                    .where(QueryLogModel.created_at >= start_time)
                    .group_by(QueryLogModel.query)
                    .having(func.count(QueryLogModel.id) > 1)
                    .order_by(
                        desc(func.count(QueryLogModel.id)),
                        desc(func.max(QueryLogModel.created_at))
                    )
                    .limit(limit)
                )
                
                result = await session.execute(stmt)
                rows = result.fetchall()
                
                trending = []
                for row in rows:
                    trending.append({
                        'query': row.query,
                        'search_count': row.search_count,
                        'avg_results': float(row.avg_results or 0),
                        'last_searched': row.last_searched
                    })
                
                return trending
        except Exception as e:
            self.logger.error(f"Failed to get trending queries: {str(e)}")
            return []
    
    async def get_search_suggestions(
        self,
        query_prefix: str,
        limit: int = 10
    ) -> List[str]:
        """获取搜索建议"""
        try:
            async with self.get_session() as session:
                # 查找以指定前缀开头的查询
                stmt = (
                    select(QueryLogModel.query)
                    .where(QueryLogModel.query.like(f"{query_prefix}%"))
                    .group_by(QueryLogModel.query)
                    .order_by(desc(func.count(QueryLogModel.id)))
                    .limit(limit)
                )
                
                result = await session.execute(stmt)
                suggestions = [row.query for row in result.fetchall()]
                
                return suggestions
        except Exception as e:
            self.logger.error(f"Failed to get search suggestions: {str(e)}")
            return []
    
    async def search_documents(
        self,
        query: str,
        knowledge_base_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 20,
        offset: int = 0
    ) -> List[DocumentModel]:
        """搜索文档（使用全文搜索）"""
        try:
            async with self.get_session() as session:
                # 构建基础查询
                stmt = select(DocumentModel).where(
                    and_(
                        or_(
                            DocumentModel.title.like(f"%{query}%"),
                            DocumentModel.content.like(f"%{query}%"),
                            DocumentModel.summary.like(f"%{query}%"),
                            DocumentModel.keywords.like(f"%{query}%")
                        ),
                        DocumentModel.is_deleted == False
                    )
                )
                
                # 添加过滤条件
                if knowledge_base_id:
                    stmt = stmt.where(DocumentModel.knowledge_base_id == knowledge_base_id)
                
                if status:
                    stmt = stmt.where(DocumentModel.status == status)
                
                # 排序：标题匹配优先
                stmt = stmt.order_by(
                    case(
                        [(DocumentModel.title.like(f"%{query}%"), 1)],
                        else_=2
                    ),
                    desc(DocumentModel.created_at)
                )
                
                # 分页
                stmt = stmt.offset(offset).limit(limit)
                
                result = await session.execute(stmt)
                return result.scalars().all()
        except Exception as e:
            self.logger.error(f"Failed to search documents: {str(e)}")
            return []
    
    async def search_chunks(
        self,
        query: str,
        document_id: Optional[str] = None,
        knowledge_base_id: Optional[str] = None,
        limit: int = 20,
        offset: int = 0
    ) -> List[DocumentChunkModel]:
        """搜索文档块"""
        try:
            async with self.get_session() as session:
                # 构建基础查询
                stmt = select(DocumentChunkModel).where(
                    and_(
                        or_(
                            DocumentChunkModel.content.like(f"%{query}%"),
                            DocumentChunkModel.summary.like(f"%{query}%")
                        ),
                        DocumentChunkModel.is_deleted == False
                    )
                )
                
                # 添加过滤条件
                if document_id:
                    stmt = stmt.where(DocumentChunkModel.document_id == document_id)
                
                if knowledge_base_id:
                    stmt = stmt.where(DocumentChunkModel.knowledge_base_id == knowledge_base_id)
                
                # 排序
                stmt = stmt.order_by(desc(DocumentChunkModel.created_at))
                
                # 分页
                stmt = stmt.offset(offset).limit(limit)
                
                result = await session.execute(stmt)
                return result.scalars().all()
        except Exception as e:
            self.logger.error(f"Failed to search chunks: {str(e)}")
            return []
    
    async def search_entities(
        self,
        query: str,
        entity_type: Optional[str] = None,
        knowledge_base_id: Optional[str] = None,
        limit: int = 20,
        offset: int = 0
    ) -> List[EntityModel]:
        """搜索实体"""
        try:
            async with self.get_session() as session:
                # 构建基础查询
                stmt = select(EntityModel).where(
                    and_(
                        or_(
                            EntityModel.name.like(f"%{query}%"),
                            EntityModel.description.like(f"%{query}%")
                        ),
                        EntityModel.is_deleted == False
                    )
                )
                
                # 添加过滤条件
                if entity_type:
                    stmt = stmt.where(EntityModel.type == entity_type)
                
                if knowledge_base_id:
                    stmt = stmt.where(EntityModel.knowledge_base_id == knowledge_base_id)
                
                # 排序：名称匹配优先
                stmt = stmt.order_by(
                    case(
                        [(EntityModel.name.like(f"%{query}%"), 1)],
                        else_=2
                    ),
                    desc(EntityModel.confidence),
                    desc(EntityModel.created_at)
                )
                
                # 分页
                stmt = stmt.offset(offset).limit(limit)
                
                result = await session.execute(stmt)
                return result.scalars().all()
        except Exception as e:
            self.logger.error(f"Failed to search entities: {str(e)}")
            return []
    
    async def get_search_statistics(
        self,
        user_id: Optional[str] = None,
        time_range: str = "24h"
    ) -> Dict[str, Any]:
        """获取搜索统计信息"""
        try:
            async with self.get_session() as session:
                # 计算时间范围
                now = datetime.utcnow()
                if time_range == "1h":
                    start_time = now - timedelta(hours=1)
                elif time_range == "24h":
                    start_time = now - timedelta(days=1)
                elif time_range == "7d":
                    start_time = now - timedelta(days=7)
                else:
                    start_time = now - timedelta(days=1)
                
                base_query = select(QueryLogModel).where(
                    QueryLogModel.created_at >= start_time
                )
                
                if user_id:
                    base_query = base_query.where(QueryLogModel.user_id == user_id)
                
                # 总搜索次数
                total_stmt = select(func.count(QueryLogModel.id)).select_from(base_query.subquery())
                total_result = await session.execute(total_stmt)
                total_searches = total_result.scalar() or 0
                
                # 按搜索类型统计
                type_stmt = (
                    select(
                        QueryLogModel.search_type,
                        func.count(QueryLogModel.id).label('count')
                    )
                    .where(QueryLogModel.created_at >= start_time)
                    .group_by(QueryLogModel.search_type)
                )
                
                if user_id:
                    type_stmt = type_stmt.where(QueryLogModel.user_id == user_id)
                
                type_result = await session.execute(type_stmt)
                type_stats = dict(type_result.fetchall())
                
                # 平均搜索时间
                avg_time_stmt = select(func.avg(QueryLogModel.search_time)).where(
                    QueryLogModel.created_at >= start_time
                )
                
                if user_id:
                    avg_time_stmt = avg_time_stmt.where(QueryLogModel.user_id == user_id)
                
                avg_time_result = await session.execute(avg_time_stmt)
                avg_search_time = avg_time_result.scalar() or 0
                
                # 平均结果数
                avg_results_stmt = select(func.avg(QueryLogModel.result_count)).where(
                    QueryLogModel.created_at >= start_time
                )
                
                if user_id:
                    avg_results_stmt = avg_results_stmt.where(QueryLogModel.user_id == user_id)
                
                avg_results_result = await session.execute(avg_results_stmt)
                avg_result_count = avg_results_result.scalar() or 0
                
                return {
                    'total_searches': total_searches,
                    'type_distribution': type_stats,
                    'average_search_time': round(float(avg_search_time), 3),
                    'average_result_count': round(float(avg_result_count), 2),
                    'time_range': time_range
                }
        except Exception as e:
            self.logger.error(f"Failed to get search statistics: {str(e)}")
            return {
                'total_searches': 0,
                'type_distribution': {},
                'average_search_time': 0,
                'average_result_count': 0,
                'time_range': time_range
            }
    
    async def get_popular_search_terms(
        self,
        time_range: str = "7d",
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """获取热门搜索词"""
        try:
            async with self.get_session() as session:
                # 计算时间范围
                now = datetime.now()
                if time_range == "1h":
                    start_time = now - timedelta(hours=1)
                elif time_range == "24h":
                    start_time = now - timedelta(days=1)
                elif time_range == "7d":
                    start_time = now - timedelta(days=7)
                elif time_range == "30d":
                    start_time = now - timedelta(days=30)
                else:
                    start_time = now - timedelta(days=7)
                
                # 查询热门搜索词
                stmt = (
                    select(
                        QueryLogModel.query,
                        func.count(QueryLogModel.id).label('frequency'),
                        func.avg(QueryLogModel.result_count).label('avg_results'),
                        func.avg(QueryLogModel.search_time).label('avg_time')
                    )
                    .where(QueryLogModel.created_at >= start_time)
                    .group_by(QueryLogModel.query)
                    .order_by(desc(func.count(QueryLogModel.id)))
                    .limit(limit)
                )
                
                result = await session.execute(stmt)
                rows = result.fetchall()
                
                popular_terms = []
                for row in rows:
                    popular_terms.append({
                        'query': row.query,
                        'frequency': row.frequency,
                        'avg_results': round(float(row.avg_results or 0), 2),
                        'avg_time': round(float(row.avg_time or 0), 3)
                    })
                
                return popular_terms
        except Exception as e:
            self.logger.error(f"Failed to get popular search terms: {str(e)}")
            return []