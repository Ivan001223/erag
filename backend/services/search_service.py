"""搜索服务"""

import asyncio
from datetime import datetime
from typing import List, Optional, Dict, Any, Union
from uuid import uuid4
import json

from ..config import get_settings
from ..config.constants import ChunkType, DocumentStatus
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from ..connectors import Neo4jClient, RedisClient
from ..models import (
    Document, DocumentChunk, Entity, Relation,
    SearchQuery, SearchResult, APIResponse, PaginatedResponse, ErrorResponse
)
from ..utils import get_logger
from .vector_service import VectorService
from .llm_service import LLMService


class SearchService:
    """搜索服务"""
    
    def __init__(
        self,
        neo4j_client: Neo4jClient,
        redis_client: RedisClient,
        db_session: Session,
        vector_service: VectorService,
        llm_service: LLMService
    ):
        self.neo4j = neo4j_client
        self.redis = redis_client
        self.db = db_session
        self.vector_service = vector_service
        self.llm_service = llm_service
        self.settings = get_settings()
        self.logger = get_logger(__name__)
    
    async def search(
        self,
        query: SearchQuery,
        user_id: Optional[str] = None
    ) -> APIResponse[SearchResult]:
        """综合搜索"""
        try:
            search_id = str(uuid4())
            start_time = datetime.now()
            
            # 记录搜索查询
            await self._log_search_query(query, user_id, search_id)
            
            # 根据搜索类型执行不同的搜索策略
            if query.search_type == "semantic":
                result = await self._semantic_search(query, search_id)
            elif query.search_type == "keyword":
                result = await self._keyword_search(query, search_id)
            elif query.search_type == "hybrid":
                result = await self._hybrid_search(query, search_id)
            elif query.search_type == "knowledge_graph":
                result = await self._knowledge_graph_search(query, search_id)
            else:
                # 默认使用混合搜索
                result = await self._hybrid_search(query, search_id)
            
            # 计算搜索耗时
            search_time = (datetime.now() - start_time).total_seconds()
            result.search_time = search_time
            result.search_id = search_id
            
            # 记录搜索结果
            await self._log_search_result(search_id, result, user_id)
            
            self.logger.info(
                f"Search completed: {search_id}, query: {query.query[:50]}..., "
                f"results: {len(result.documents + result.chunks + result.entities)}, "
                f"time: {search_time:.3f}s"
            )
            
            return APIResponse(
                status="success",
                message="Search completed successfully",
                data=result
            )
            
        except Exception as e:
            self.logger.error(f"Error in search: {str(e)}")
            return ErrorResponse(
                message=f"Search failed: {str(e)}",
                error_code="SEARCH_FAILED"
            )
    
    async def suggest(
        self,
        query: str,
        limit: int = 10
    ) -> APIResponse[List[str]]:
        """搜索建议"""
        try:
            suggestions = []
            
            # 从缓存获取热门搜索词
            popular_queries = await self._get_popular_queries(limit // 2)
            suggestions.extend(popular_queries)
            
            # 基于查询前缀匹配
            if query.strip():
                prefix_matches = await self._get_prefix_matches(query, limit - len(suggestions))
                suggestions.extend(prefix_matches)
            
            # 去重并限制数量
            suggestions = list(dict.fromkeys(suggestions))[:limit]
            
            return APIResponse(
                status="success",
                message="Suggestions retrieved successfully",
                data=suggestions
            )
            
        except Exception as e:
            self.logger.error(f"Error getting suggestions: {str(e)}")
            return ErrorResponse(
                message=f"Failed to get suggestions: {str(e)}",
                error_code="SUGGESTION_FAILED"
            )
    
    async def get_search_history(
        self,
        user_id: str,
        limit: int = 20
    ) -> APIResponse[List[Dict[str, Any]]]:
        """获取搜索历史"""
        try:
            # 使用SQLAlchemy ORM查询
            from backend.models.database import QueryLogModel
            from sqlalchemy import desc
            
            query = self.db.query(QueryLogModel).filter(
                QueryLogModel.user_id == user_id
            ).order_by(desc(QueryLogModel.created_at)).limit(limit)
            
            result = query.all()
            
            history = []
            for row in result or []:
                history.append({
                    "query": row["query"],
                    "search_type": row["search_type"],
                    "created_at": row["created_at"],
                    "result_count": row["result_count"]
                })
            
            return APIResponse(
                status="success",
                message="Search history retrieved successfully",
                data=history
            )
            
        except Exception as e:
            self.logger.error(f"Error getting search history: {str(e)}")
            return ErrorResponse(
                message=f"Failed to get search history: {str(e)}",
                error_code="HISTORY_FAILED"
            )
    
    async def get_trending_queries(
        self,
        limit: int = 10,
        time_range: str = "24h"
    ) -> APIResponse[List[Dict[str, Any]]]:
        """获取热门搜索"""
        try:
            # 根据时间范围构建查询条件
            if time_range == "1h":
                time_condition = "created_at >= NOW() - INTERVAL 1 HOUR"
            elif time_range == "24h":
                time_condition = "created_at >= NOW() - INTERVAL 1 DAY"
            elif time_range == "7d":
                time_condition = "created_at >= NOW() - INTERVAL 7 DAY"
            else:
                time_condition = "created_at >= NOW() - INTERVAL 1 DAY"
            
            # 使用SQLAlchemy ORM查询
            from backend.models.database import QueryLogModel
            from sqlalchemy import func, desc, and_
            from datetime import datetime, timedelta
            
            # 根据时间范围设置过滤条件
            if time_range == "week":
                time_filter = QueryLogModel.created_at >= datetime.now() - timedelta(days=7)
            else:
                time_filter = QueryLogModel.created_at >= datetime.now() - timedelta(days=1)
            
            query = self.db.query(
                QueryLogModel.query,
                func.count().label('search_count'),
                func.avg(QueryLogModel.result_count).label('avg_results'),
                func.max(QueryLogModel.created_at).label('last_searched')
            ).filter(time_filter).group_by(
                QueryLogModel.query
            ).having(
                func.count() > 1
            ).order_by(
                desc('search_count'), desc('last_searched')
            ).limit(limit)
            
            result = query.all()
            
            trending = []
            for row in result or []:
                trending.append({
                    "query": row["query"],
                    "search_count": row["search_count"],
                    "avg_results": float(row["avg_results"]),
                    "last_searched": row["last_searched"]
                })
            
            return APIResponse(
                status="success",
                message="Trending queries retrieved successfully",
                data=trending
            )
            
        except Exception as e:
            self.logger.error(f"Error getting trending queries: {str(e)}")
            return ErrorResponse(
                message=f"Failed to get trending queries: {str(e)}",
                error_code="TRENDING_FAILED"
            )
    
    # 私有方法
    
    async def _semantic_search(
        self,
        query: SearchQuery,
        search_id: str
    ) -> SearchResult:
        """语义搜索"""
        # 生成查询向量
        query_vector = await self.vector_service.encode_text(query.query)
        
        # 搜索文档块
        chunks = []
        if "chunks" in query.include_types:
            chunk_results = await self.vector_service.search_similar_chunks(
                query_vector,
                limit=query.limit,
                threshold=query.similarity_threshold,
                filters=query.filters
            )
            
            for chunk_id, score in chunk_results:
                chunk = await self._get_chunk_by_id(chunk_id)
                if chunk:
                    chunk.relevance_score = score
                    chunks.append(chunk)
        
        # 搜索实体
        entities = []
        if "entities" in query.include_types:
            entity_results = await self.vector_service.search_similar_entities(
                query_vector,
                limit=query.limit,
                threshold=query.similarity_threshold
            )
            
            for entity_id, score in entity_results:
                entity = await self._get_entity_by_id(entity_id)
                if entity:
                    entity.relevance_score = score
                    entities.append(entity)
        
        # 获取相关文档
        documents = []
        if "documents" in query.include_types:
            document_ids = list(set(chunk.document_id for chunk in chunks))
            for doc_id in document_ids[:query.limit]:
                document = await self._get_document_by_id(doc_id)
                if document:
                    # 计算文档相关性（基于其块的平均分数）
                    doc_chunks = [c for c in chunks if c.document_id == doc_id]
                    if doc_chunks:
                        document.relevance_score = sum(c.relevance_score for c in doc_chunks) / len(doc_chunks)
                        documents.append(document)
        
        return SearchResult(
            query=query.query,
            search_type="semantic",
            documents=documents,
            chunks=chunks,
            entities=entities,
            relations=[],
            total_results=len(documents) + len(chunks) + len(entities)
        )
    
    async def _keyword_search(
        self,
        query: SearchQuery,
        search_id: str
    ) -> SearchResult:
        """关键词搜索"""
        documents = []
        chunks = []
        entities = []
        
        # 搜索文档
        if "documents" in query.include_types:
            # 使用SQLAlchemy ORM查询文档
            from backend.models.database import DocumentModel
            from sqlalchemy import and_, desc, func
            
            doc_query = self.db.query(DocumentModel).filter(
                and_(
                    DocumentModel.vector_status == 'processed',
                    DocumentModel.is_deleted == False,
                    func.match(DocumentModel.title, DocumentModel.content).against(
                        query.query, func.in_natural_language_mode()
                    )
                )
            ).order_by(
                desc(func.match(DocumentModel.title, DocumentModel.content).against(
                    query.query, func.in_natural_language_mode()
                ))
            ).limit(query.limit)
            
            result = doc_query.all()
            
            for row in result or []:
                document = Document(**row)
                document.relevance_score = float(row["relevance"])
                documents.append(document)
        
        # 搜索文档块
        if "chunks" in query.include_types:
            # 使用SQLAlchemy ORM查询文档块
            from backend.models.database import DocumentChunkModel
            from sqlalchemy import and_, desc, func
            
            chunk_query = self.db.query(DocumentChunkModel).filter(
                and_(
                    DocumentChunkModel.is_deleted == False,
                    func.match(DocumentChunkModel.content).against(
                        query.query, func.in_natural_language_mode()
                    )
                )
            ).order_by(
                desc(func.match(DocumentChunkModel.content).against(
                    query.query, func.in_natural_language_mode()
                ))
            ).limit(query.limit)
            
            result = chunk_query.all()
            
            for row in result or []:
                chunk = DocumentChunk(**row)
                chunk.relevance_score = float(row["relevance"])
                chunks.append(chunk)
        
        # 搜索实体
        if "entities" in query.include_types:
            # 使用SQLAlchemy ORM查询实体
            from backend.models.knowledge_graph_models import EntityModel
            from sqlalchemy import and_, desc, func
            
            entity_query = self.db.query(EntityModel).filter(
                and_(
                    EntityModel.is_deleted == False,
                    func.match(EntityModel.name, EntityModel.description).against(
                        query.query, func.in_natural_language_mode()
                    )
                )
            ).order_by(
                desc(func.match(EntityModel.name, EntityModel.description).against(
                    query.query, func.in_natural_language_mode()
                ))
            ).limit(query.limit)
            
            result = await self.starrocks.execute_query(
                entity_query, 
                (query.query, query.query, query.limit)
            )
            
            for row in result or []:
                entity = Entity(**row)
                entity.relevance_score = float(row["relevance"])
                entities.append(entity)
        
        return SearchResult(
            query=query.query,
            search_type="keyword",
            documents=documents,
            chunks=chunks,
            entities=entities,
            relations=[],
            total_results=len(documents) + len(chunks) + len(entities)
        )
    
    async def _hybrid_search(
        self,
        query: SearchQuery,
        search_id: str
    ) -> SearchResult:
        """混合搜索(语义 + 关键词)"""
        # 并行执行语义搜索和关键词搜索
        semantic_query = SearchQuery(
            query=query.query,
            search_type="semantic",
            include_types=query.include_types,
            limit=query.limit,
            similarity_threshold=query.similarity_threshold,
            filters=query.filters
        )
        
        keyword_query = SearchQuery(
            query=query.query,
            search_type="keyword",
            include_types=query.include_types,
            limit=query.limit,
            filters=query.filters
        )
        
        semantic_result, keyword_result = await asyncio.gather(
            self._semantic_search(semantic_query, search_id),
            self._keyword_search(keyword_query, search_id)
        )
        
        # 合并和重新排序结果
        merged_result = self._merge_search_results(
            semantic_result, 
            keyword_result, 
            query.limit
        )
        
        merged_result.search_type = "hybrid"
        return merged_result
    
    async def _knowledge_graph_search(
        self,
        query: SearchQuery,
        search_id: str
    ) -> SearchResult:
        """知识图谱搜索"""
        entities = []
        relations = []
        
        # 首先进行实体搜索
        entity_query = """
            MATCH (e:Entity)
            WHERE e.name CONTAINS $query OR e.description CONTAINS $query
            RETURN e
            ORDER BY e.confidence DESC
            LIMIT $limit
        """
        
        entity_results = await self.neo4j.execute_query(
            entity_query,
            {"query": query.query, "limit": query.limit}
        )
        
        entity_ids = []
        for record in entity_results:
            entity_data = dict(record["e"])
            entity = Entity(**entity_data)
            entities.append(entity)
            entity_ids.append(entity.id)
        
        # 搜索实体间的关系
        if entity_ids and "relations" in query.include_types:
            relation_query = """
                MATCH (e1:Entity)-[r:RELATION]->(e2:Entity)
                WHERE e1.id IN $entity_ids OR e2.id IN $entity_ids
                RETURN r, e1.id as source_id, e2.id as target_id
                LIMIT $limit
            """
            
            relation_results = await self.neo4j.execute_query(
                relation_query,
                {"entity_ids": entity_ids, "limit": query.limit}
            )
            
            for record in relation_results:
                relation_data = dict(record["r"])
                relation_data["source_entity_id"] = record["source_id"]
                relation_data["target_entity_id"] = record["target_id"]
                relation = Relation(**relation_data)
                relations.append(relation)
        
        # 获取相关文档块
        chunks = []
        if "chunks" in query.include_types and entity_ids:
            chunk_query = """
                SELECT DISTINCT dc.* 
                FROM document_chunks dc
                JOIN chunk_entities ce ON dc.id = ce.chunk_id
                WHERE ce.entity_id IN ({})
                  AND dc.deleted_at IS NULL
                ORDER BY dc.created_at DESC
                LIMIT ?
            """.format(",".join(["?"] * len(entity_ids)))
            
            params = entity_ids + [query.limit]
            result = await self.starrocks.execute_query(chunk_query, params)
            
            for row in result or []:
                chunk = DocumentChunk(**row)
                chunks.append(chunk)
        
        return SearchResult(
            query=query.query,
            search_type="knowledge_graph",
            documents=[],
            chunks=chunks,
            entities=entities,
            relations=relations,
            total_results=len(chunks) + len(entities) + len(relations)
        )
    
    def _merge_search_results(
        self,
        semantic_result: SearchResult,
        keyword_result: SearchResult,
        limit: int
    ) -> SearchResult:
        """合并搜索结果"""
        # 合并文档
        documents = {}
        for doc in semantic_result.documents:
            documents[doc.id] = doc
            doc.relevance_score = doc.relevance_score * 0.7  # 语义搜索权重
        
        for doc in keyword_result.documents:
            if doc.id in documents:
                # 合并分数
                documents[doc.id].relevance_score += doc.relevance_score * 0.3  # 关键词搜索权重
            else:
                doc.relevance_score = doc.relevance_score * 0.3
                documents[doc.id] = doc
        
        # 合并文档块
        chunks = {}
        for chunk in semantic_result.chunks:
            chunks[chunk.id] = chunk
            chunk.relevance_score = chunk.relevance_score * 0.7
        
        for chunk in keyword_result.chunks:
            if chunk.id in chunks:
                chunks[chunk.id].relevance_score += chunk.relevance_score * 0.3
            else:
                chunk.relevance_score = chunk.relevance_score * 0.3
                chunks[chunk.id] = chunk
        
        # 合并实体
        entities = {}
        for entity in semantic_result.entities:
            entities[entity.id] = entity
            entity.relevance_score = entity.relevance_score * 0.7
        
        for entity in keyword_result.entities:
            if entity.id in entities:
                entities[entity.id].relevance_score += entity.relevance_score * 0.3
            else:
                entity.relevance_score = entity.relevance_score * 0.3
                entities[entity.id] = entity
        
        # 排序并限制结果数量
        sorted_documents = sorted(
            documents.values(),
            key=lambda x: x.relevance_score,
            reverse=True
        )[:limit]
        
        sorted_chunks = sorted(
            chunks.values(),
            key=lambda x: x.relevance_score,
            reverse=True
        )[:limit]
        
        sorted_entities = sorted(
            entities.values(),
            key=lambda x: x.relevance_score,
            reverse=True
        )[:limit]
        
        return SearchResult(
            query=semantic_result.query,
            search_type="hybrid",
            documents=sorted_documents,
            chunks=sorted_chunks,
            entities=sorted_entities,
            relations=[],
            total_results=len(sorted_documents) + len(sorted_chunks) + len(sorted_entities)
        )
    
    async def _get_document_by_id(self, document_id: str) -> Optional[Document]:
        """根据ID获取文档"""
        try:
            from backend.models.database import DocumentModel
            from sqlalchemy import select
            
            stmt = select(DocumentModel).where(
                DocumentModel.id == document_id,
                DocumentModel.deleted_at.is_(None)
            ).limit(1)
            
            result = await self.db.fetch_one(stmt)
            if result:
                # 将SQLAlchemy结果转换为字典
                doc_dict = {column.name: getattr(result, column.name) for column in DocumentModel.__table__.columns}
                return Document(**doc_dict)
            return None
        except Exception as e:
            self.logger.error(f"Get document by ID failed: {str(e)}")
            return None
    
    async def _get_chunk_by_id(self, chunk_id: str) -> Optional[DocumentChunk]:
        """根据ID获取文档块"""
        try:
            from backend.models.database import DocumentChunkModel
            from sqlalchemy import select
            
            stmt = select(DocumentChunkModel).where(
                DocumentChunkModel.id == chunk_id,
                DocumentChunkModel.deleted_at.is_(None)
            ).limit(1)
            
            result = await self.db.fetch_one(stmt)
            if result:
                # 将SQLAlchemy结果转换为字典
                chunk_dict = {column.name: getattr(result, column.name) for column in DocumentChunkModel.__table__.columns}
                return DocumentChunk(**chunk_dict)
            return None
        except Exception as e:
            self.logger.error(f"Get chunk by ID failed: {str(e)}")
            return None
    
    async def _get_entity_by_id(self, entity_id: str) -> Optional[Entity]:
        """根据ID获取实体"""
        try:
            from backend.models.database import EntityModel
            from sqlalchemy import select
            
            stmt = select(EntityModel).where(
                EntityModel.id == entity_id,
                EntityModel.deleted_at.is_(None)
            ).limit(1)
            
            result = await self.db.fetch_one(stmt)
            if result:
                # 将SQLAlchemy结果转换为字典
                entity_dict = {column.name: getattr(result, column.name) for column in EntityModel.__table__.columns}
                return Entity(**entity_dict)
            return None
        except Exception as e:
            self.logger.error(f"Get entity by ID failed: {str(e)}")
            return None
    
    async def _log_search_query(
        self,
        query: SearchQuery,
        user_id: Optional[str],
        search_id: str
    ) -> None:
        """记录搜索查询"""
        try:
            log_data = {
                "id": search_id,
                "user_id": user_id,
                "query": query.query,
                "search_type": query.search_type,
                "include_types": json.dumps(query.include_types),
                "filters": json.dumps(query.filters) if query.filters else None,
                "limit": query.limit,
                "similarity_threshold": query.similarity_threshold,
                "created_at": datetime.now()
            }
            
            await self.starrocks.insert_query_log(log_data)
            
        except Exception as e:
            self.logger.error(f"Error logging search query: {str(e)}")
    
    async def _log_search_result(
        self,
        search_id: str,
        result: SearchResult,
        user_id: Optional[str]
    ) -> None:
        """记录搜索结果"""
        try:
            # 更新查询日志
            update_data = {
                "result_count": result.total_results,
                "search_time": result.search_time,
                "updated_at": datetime.now()
            }
            
            await self.starrocks.update_query_log(search_id, update_data)
            
            # 缓存搜索结果（短期）
            await self.redis.set(
                f"search_result:{search_id}",
                result.json(),
                expire=300  # 5分钟
            )
            
        except Exception as e:
            self.logger.error(f"Error logging search result: {str(e)}")
    
    async def _get_popular_queries(self, limit: int) -> List[str]:
        """获取热门搜索词"""
        try:
            # 从Redis缓存获取
            cached_queries = await self.redis.get("popular_queries")
            if cached_queries:
                queries = json.loads(cached_queries)
                return queries[:limit]
            
            # 使用SQLAlchemy ORM查询热门查询
            from backend.models.database import QueryLogModel
            from sqlalchemy import func, desc
            from datetime import datetime, timedelta
            
            query = self.db.query(
                QueryLogModel.query,
                func.count().label('search_count')
            ).filter(
                QueryLogModel.created_at >= datetime.now() - timedelta(days=7)
            ).group_by(
                QueryLogModel.query
            ).having(
                func.count() > 2
            ).order_by(
                desc('search_count')
            ).limit(limit * 2)
            
            result = query.all()
            
            queries = [row["query"] for row in result] if result else []
            
            # 缓存结果
            await self.redis.set(
                "popular_queries",
                json.dumps(queries),
                expire=3600  # 1小时
            )
            
            return queries[:limit]
            
        except Exception as e:
            self.logger.error(f"Error getting popular queries: {str(e)}")
            return []
    
    async def _get_prefix_matches(self, prefix: str, limit: int) -> List[str]:
        """获取前缀匹配的查询"""
        try:
            # 使用SQLAlchemy ORM查询前缀匹配
            from backend.models.database import QueryLogModel
            from sqlalchemy import desc, distinct
            from datetime import datetime, timedelta
            
            query = self.db.query(
                distinct(QueryLogModel.query)
            ).filter(
                QueryLogModel.query.like(f"{prefix}%"),
                QueryLogModel.created_at >= datetime.now() - timedelta(days=30)
            ).order_by(
                desc(QueryLogModel.created_at)
            ).limit(limit)
            
            result = await self.starrocks.execute_query(
                query, 
                (f"{prefix}%", limit)
            )
            
            return [row["query"] for row in result] if result else []
            
        except Exception as e:
            self.logger.error(f"Error getting prefix matches: {str(e)}")
            return []