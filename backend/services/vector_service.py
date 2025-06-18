from typing import List, Dict, Any, Optional, Tuple, Union
from datetime import datetime
import asyncio
import json
import numpy as np
from enum import Enum
import hashlib
import uuid

from backend.connectors.redis_client import RedisClient
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from backend.models.base import BaseModel
from backend.utils.logger import get_logger

logger = get_logger(__name__)


class VectorModel(str, Enum):
    """向量模型枚举"""
    OPENAI_ADA_002 = "text-embedding-ada-002"
    OPENAI_3_SMALL = "text-embedding-3-small"
    OPENAI_3_LARGE = "text-embedding-3-large"
    SENTENCE_TRANSFORMERS = "sentence-transformers"
    BGE_LARGE_ZH = "bge-large-zh"
    BGE_BASE_ZH = "bge-base-zh"
    BGE_SMALL_ZH = "bge-small-zh"
    M3E_BASE = "m3e-base"
    M3E_LARGE = "m3e-large"
    COHERE_EMBED = "embed-english-v3.0"
    HUGGINGFACE_BGE = "BAAI/bge-large-en-v1.5"


class VectorType(str, Enum):
    """向量类型枚举"""
    DOCUMENT = "document"
    CHUNK = "chunk"
    QUERY = "query"
    ENTITY = "entity"
    RELATION = "relation"
    SUMMARY = "summary"


class SimilarityMetric(str, Enum):
    """相似度度量枚举"""
    COSINE = "cosine"
    EUCLIDEAN = "euclidean"
    DOT_PRODUCT = "dot_product"
    MANHATTAN = "manhattan"


class VectorMetadata(BaseModel):
    """向量元数据模型"""
    id: str
    text: str
    model: VectorModel
    vector_type: VectorType
    dimension: int
    source_id: str  # 来源文档/实体ID
    source_type: str  # 来源类型
    chunk_index: Optional[int] = None
    page_number: Optional[int] = None
    language: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    metadata: Dict[str, Any] = {}


class VectorSearchResult(BaseModel):
    """向量搜索结果模型"""
    id: str
    score: float
    metadata: VectorMetadata
    text: str
    vector: Optional[List[float]] = None


class VectorSearchRequest(BaseModel):
    """向量搜索请求模型"""
    query: str
    query_vector: Optional[List[float]] = None
    model: VectorModel
    vector_types: List[VectorType] = [VectorType.CHUNK]
    top_k: int = 10
    similarity_threshold: float = 0.7
    similarity_metric: SimilarityMetric = SimilarityMetric.COSINE
    filters: Dict[str, Any] = {}
    include_vector: bool = False


class VectorBatch(BaseModel):
    """向量批处理模型"""
    texts: List[str]
    metadatas: List[VectorMetadata]
    vectors: Optional[List[List[float]]] = None


class VectorStats(BaseModel):
    """向量统计信息模型"""
    total_vectors: int
    vectors_by_type: Dict[VectorType, int]
    vectors_by_model: Dict[VectorModel, int]
    average_dimension: float
    storage_size_mb: float
    last_updated: datetime


class VectorService:
    """向量服务"""
    
    def __init__(self, redis_client: RedisClient, db: Session):
        self.redis = redis_client
        self.db = db
        self.embedding_models: Dict[VectorModel, Any] = {}
        self.model_dimensions: Dict[VectorModel, int] = {
            VectorModel.OPENAI_ADA_002: 1536,
            VectorModel.OPENAI_3_SMALL: 1536,
            VectorModel.OPENAI_3_LARGE: 3072,
            VectorModel.BGE_LARGE_ZH: 1024,
            VectorModel.BGE_BASE_ZH: 768,
            VectorModel.BGE_SMALL_ZH: 512,
            VectorModel.M3E_BASE: 768,
            VectorModel.M3E_LARGE: 1024,
            VectorModel.COHERE_EMBED: 1024,
            VectorModel.HUGGINGFACE_BGE: 1024
        }
        
    async def initialize(self):
        """初始化向量服务"""
        try:
            # 初始化嵌入模型
            await self._initialize_embedding_models()
            
            # 创建向量表
            await self._create_vector_tables()
            
            logger.info("Vector service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize vector service: {str(e)}")
            raise
    
    async def embed_text(
        self,
        text: str,
        model: VectorModel = VectorModel.BGE_LARGE_ZH
    ) -> List[float]:
        """文本向量化"""
        try:
            # 检查缓存
            cache_key = self._get_embedding_cache_key(text, model)
            cached_vector = await self.redis.get(cache_key)
            
            if cached_vector:
                return json.loads(cached_vector)
            
            # 生成向量
            vector = await self._generate_embedding(text, model)
            
            # 缓存向量
            await self.redis.setex(
                cache_key,
                86400,  # 24小时缓存
                json.dumps(vector)
            )
            
            return vector
            
        except Exception as e:
            logger.error(f"Text embedding failed: {str(e)}")
            raise
    
    async def embed_batch(
        self,
        texts: List[str],
        model: VectorModel = VectorModel.BGE_LARGE_ZH
    ) -> List[List[float]]:
        """批量文本向量化"""
        try:
            vectors = []
            uncached_texts = []
            uncached_indices = []
            
            # 检查缓存
            for i, text in enumerate(texts):
                cache_key = self._get_embedding_cache_key(text, model)
                cached_vector = await self.redis.get(cache_key)
                
                if cached_vector:
                    vectors.append(json.loads(cached_vector))
                else:
                    vectors.append(None)
                    uncached_texts.append(text)
                    uncached_indices.append(i)
            
            # 批量生成未缓存的向量
            if uncached_texts:
                uncached_vectors = await self._generate_embeddings_batch(uncached_texts, model)
                
                # 填充结果并缓存
                for i, vector in enumerate(uncached_vectors):
                    idx = uncached_indices[i]
                    vectors[idx] = vector
                    
                    # 缓存向量
                    cache_key = self._get_embedding_cache_key(uncached_texts[i], model)
                    await self.redis.setex(
                        cache_key,
                        86400,
                        json.dumps(vector)
                    )
            
            return vectors
            
        except Exception as e:
            logger.error(f"Batch embedding failed: {str(e)}")
            raise
    
    async def store_vector(
        self,
        text: str,
        vector: List[float],
        metadata: VectorMetadata
    ) -> str:
        """存储向量"""
        try:
            # 生成向量ID
            vector_id = metadata.id or str(uuid.uuid4())
            
            # 存储到StarRocks
            await self._store_vector_to_db(vector_id, text, vector, metadata)
            
            # 更新缓存
            await self._update_vector_cache(vector_id, metadata)
            
            logger.info(f"Vector stored successfully: {vector_id}")
            return vector_id
            
        except Exception as e:
            logger.error(f"Vector storage failed: {str(e)}")
            raise
    
    async def store_vectors_batch(
        self,
        batch: VectorBatch
    ) -> List[str]:
        """批量存储向量"""
        try:
            if not batch.vectors:
                # 如果没有提供向量，先生成
                model = batch.metadatas[0].model if batch.metadatas else VectorModel.BGE_LARGE_ZH
                batch.vectors = await self.embed_batch(batch.texts, model)
            
            vector_ids = []
            
            # 批量存储
            for i, (text, vector, metadata) in enumerate(zip(batch.texts, batch.vectors, batch.metadatas)):
                vector_id = metadata.id or str(uuid.uuid4())
                vector_ids.append(vector_id)
                
                # 更新元数据
                metadata.id = vector_id
                if not metadata.created_at:
                    metadata.created_at = datetime.now()
                metadata.updated_at = datetime.now()
            
            # 批量存储到数据库
            await self._store_vectors_batch_to_db(vector_ids, batch.texts, batch.vectors, batch.metadatas)
            
            # 更新缓存
            for vector_id, metadata in zip(vector_ids, batch.metadatas):
                await self._update_vector_cache(vector_id, metadata)
            
            logger.info(f"Batch stored {len(vector_ids)} vectors successfully")
            return vector_ids
            
        except Exception as e:
            logger.error(f"Batch vector storage failed: {str(e)}")
            raise
    
    async def search_vectors(
        self,
        request: VectorSearchRequest
    ) -> List[VectorSearchResult]:
        """向量搜索"""
        try:
            # 生成查询向量
            if not request.query_vector:
                request.query_vector = await self.embed_text(request.query, request.model)
            
            # 执行搜索
            results = await self._search_vectors_in_db(request)
            
            # 计算相似度分数
            scored_results = []
            for result in results:
                score = self._calculate_similarity(
                    request.query_vector,
                    result["vector"],
                    request.similarity_metric
                )
                
                if score >= request.similarity_threshold:
                    search_result = VectorSearchResult(
                        id=result["id"],
                        score=score,
                        metadata=VectorMetadata(**result["metadata"]),
                        text=result["text"],
                        vector=result["vector"] if request.include_vector else None
                    )
                    scored_results.append(search_result)
            
            # 按分数排序
            scored_results.sort(key=lambda x: x.score, reverse=True)
            
            # 返回top_k结果
            return scored_results[:request.top_k]
            
        except Exception as e:
            logger.error(f"Vector search failed: {str(e)}")
            raise
    
    async def search_similar_vectors(
        self,
        vector_id: str,
        top_k: int = 10,
        similarity_threshold: float = 0.7,
        vector_types: Optional[List[VectorType]] = None
    ) -> List[VectorSearchResult]:
        """搜索相似向量"""
        try:
            # 获取目标向量
            target_vector_data = await self._get_vector_by_id(vector_id)
            if not target_vector_data:
                raise ValueError(f"Vector not found: {vector_id}")
            
            # 构建搜索请求
            request = VectorSearchRequest(
                query="",
                query_vector=target_vector_data["vector"],
                model=VectorModel(target_vector_data["metadata"]["model"]),
                vector_types=vector_types or [VectorType.CHUNK],
                top_k=top_k + 1,  # +1 因为会包含自己
                similarity_threshold=similarity_threshold
            )
            
            # 执行搜索
            results = await self.search_vectors(request)
            
            # 过滤掉自己
            filtered_results = [r for r in results if r.id != vector_id]
            
            return filtered_results[:top_k]
            
        except Exception as e:
            logger.error(f"Similar vector search failed: {str(e)}")
            raise
    
    async def get_vector(
        self,
        vector_id: str,
        include_vector: bool = False
    ) -> Optional[VectorSearchResult]:
        """获取向量"""
        try:
            vector_data = await self._get_vector_by_id(vector_id)
            if not vector_data:
                return None
            
            return VectorSearchResult(
                id=vector_data["id"],
                score=1.0,
                metadata=VectorMetadata(**vector_data["metadata"]),
                text=vector_data["text"],
                vector=vector_data["vector"] if include_vector else None
            )
            
        except Exception as e:
            logger.error(f"Get vector failed: {str(e)}")
            raise
    
    async def update_vector(
        self,
        vector_id: str,
        text: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """更新向量"""
        try:
            # 获取现有向量
            existing_vector = await self._get_vector_by_id(vector_id)
            if not existing_vector:
                return False
            
            # 准备更新数据
            update_data = {}
            
            if text is not None:
                # 重新生成向量
                model = VectorModel(existing_vector["metadata"]["model"])
                new_vector = await self.embed_text(text, model)
                update_data["text"] = text
                update_data["vector"] = new_vector
            
            if metadata is not None:
                # 合并元数据
                existing_metadata = existing_vector["metadata"]
                existing_metadata.update(metadata)
                existing_metadata["updated_at"] = datetime.now().isoformat()
                update_data["metadata"] = existing_metadata
            
            # 更新数据库
            await self._update_vector_in_db(vector_id, update_data)
            
            # 清除缓存
            await self._clear_vector_cache(vector_id)
            
            logger.info(f"Vector updated successfully: {vector_id}")
            return True
            
        except Exception as e:
            logger.error(f"Vector update failed: {str(e)}")
            raise
    
    async def delete_vector(self, vector_id: str) -> bool:
        """删除向量"""
        try:
            # 从数据库删除
            deleted = await self._delete_vector_from_db(vector_id)
            
            if deleted:
                # 清除缓存
                await self._clear_vector_cache(vector_id)
                logger.info(f"Vector deleted successfully: {vector_id}")
            
            return deleted
            
        except Exception as e:
            logger.error(f"Vector deletion failed: {str(e)}")
            raise
    
    async def delete_vectors_by_source(
        self,
        source_id: str,
        source_type: str
    ) -> int:
        """根据来源删除向量"""
        try:
            # 获取要删除的向量ID列表
            vector_ids = await self._get_vector_ids_by_source(source_id, source_type)
            
            if not vector_ids:
                return 0
            
            # 批量删除
            deleted_count = await self._delete_vectors_batch_from_db(vector_ids)
            
            # 清除缓存
            for vector_id in vector_ids:
                await self._clear_vector_cache(vector_id)
            
            logger.info(f"Deleted {deleted_count} vectors for source {source_id}")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Batch vector deletion failed: {str(e)}")
            raise
    
    async def get_vector_stats(self) -> VectorStats:
        """获取向量统计信息"""
        try:
            # 检查缓存
            cache_key = "vector_stats"
            cached_stats = await self.redis.get(cache_key)
            
            if cached_stats:
                return VectorStats(**json.loads(cached_stats))
            
            # 从数据库获取统计信息
            stats_data = await self._get_vector_stats_from_db()
            
            stats = VectorStats(
                total_vectors=stats_data["total_vectors"],
                vectors_by_type=stats_data["vectors_by_type"],
                vectors_by_model=stats_data["vectors_by_model"],
                average_dimension=stats_data["average_dimension"],
                storage_size_mb=stats_data["storage_size_mb"],
                last_updated=datetime.now()
            )
            
            # 缓存统计信息
            await self.redis.setex(
                cache_key,
                300,  # 5分钟缓存
                stats.json()
            )
            
            return stats
            
        except Exception as e:
            logger.error(f"Get vector stats failed: {str(e)}")
            raise
    
    async def get_available_models(self) -> List[Dict[str, Any]]:
        """获取可用的向量模型"""
        models = []
        
        for model in VectorModel:
            model_info = {
                "name": model.value,
                "dimension": self.model_dimensions.get(model, 0),
                "available": model in self.embedding_models,
                "type": "local" if model in [VectorModel.BGE_LARGE_ZH, VectorModel.BGE_BASE_ZH, VectorModel.BGE_SMALL_ZH, VectorModel.M3E_BASE, VectorModel.M3E_LARGE] else "api"
            }
            models.append(model_info)
        
        return models
    
    def _get_embedding_cache_key(self, text: str, model: VectorModel) -> str:
        """生成嵌入缓存键"""
        text_hash = hashlib.md5(text.encode()).hexdigest()
        return f"embedding:{model.value}:{text_hash}"
    
    def _calculate_similarity(
        self,
        vector1: List[float],
        vector2: List[float],
        metric: SimilarityMetric
    ) -> float:
        """计算向量相似度"""
        try:
            v1 = np.array(vector1)
            v2 = np.array(vector2)
            
            if metric == SimilarityMetric.COSINE:
                # 余弦相似度
                dot_product = np.dot(v1, v2)
                norm1 = np.linalg.norm(v1)
                norm2 = np.linalg.norm(v2)
                return float(dot_product / (norm1 * norm2))
                
            elif metric == SimilarityMetric.DOT_PRODUCT:
                # 点积
                return float(np.dot(v1, v2))
                
            elif metric == SimilarityMetric.EUCLIDEAN:
                # 欧几里得距离（转换为相似度）
                distance = np.linalg.norm(v1 - v2)
                return float(1 / (1 + distance))
                
            elif metric == SimilarityMetric.MANHATTAN:
                # 曼哈顿距离（转换为相似度）
                distance = np.sum(np.abs(v1 - v2))
                return float(1 / (1 + distance))
                
            else:
                raise ValueError(f"Unsupported similarity metric: {metric}")
                
        except Exception as e:
            logger.error(f"Similarity calculation failed: {str(e)}")
            return 0.0
    
    async def _generate_embedding(self, text: str, model: VectorModel) -> List[float]:
        """生成单个文本的嵌入向量"""
        try:
            if model in self.embedding_models:
                # 使用本地模型
                embedding_model = self.embedding_models[model]
                # TODO: 实现具体的嵌入生成逻辑
                # vector = embedding_model.encode(text)
                # return vector.tolist()
                
                # 模拟向量生成
                dimension = self.model_dimensions[model]
                vector = np.random.random(dimension).tolist()
                return vector
            else:
                # 使用API模型
                return await self._generate_embedding_via_api(text, model)
                
        except Exception as e:
            logger.error(f"Embedding generation failed: {str(e)}")
            raise
    
    async def _generate_embeddings_batch(
        self,
        texts: List[str],
        model: VectorModel
    ) -> List[List[float]]:
        """批量生成嵌入向量"""
        try:
            if model in self.embedding_models:
                # 使用本地模型批量处理
                embedding_model = self.embedding_models[model]
                # TODO: 实现具体的批量嵌入生成逻辑
                # vectors = embedding_model.encode(texts)
                # return [vector.tolist() for vector in vectors]
                
                # 模拟批量向量生成
                dimension = self.model_dimensions[model]
                vectors = [np.random.random(dimension).tolist() for _ in texts]
                return vectors
            else:
                # 使用API模型批量处理
                return await self._generate_embeddings_batch_via_api(texts, model)
                
        except Exception as e:
            logger.error(f"Batch embedding generation failed: {str(e)}")
            raise
    
    async def _generate_embedding_via_api(
        self,
        text: str,
        model: VectorModel
    ) -> List[float]:
        """通过API生成嵌入向量"""
        try:
            # TODO: 实现OpenAI、Cohere等API调用
            # 这里是模拟实现
            dimension = self.model_dimensions[model]
            vector = np.random.random(dimension).tolist()
            return vector
            
        except Exception as e:
            logger.error(f"API embedding generation failed: {str(e)}")
            raise
    
    async def _generate_embeddings_batch_via_api(
        self,
        texts: List[str],
        model: VectorModel
    ) -> List[List[float]]:
        """通过API批量生成嵌入向量"""
        try:
            # TODO: 实现API批量调用
            dimension = self.model_dimensions[model]
            vectors = [np.random.random(dimension).tolist() for _ in texts]
            return vectors
            
        except Exception as e:
            logger.error(f"API batch embedding generation failed: {str(e)}")
            raise
    
    async def _initialize_embedding_models(self):
        """初始化嵌入模型"""
        try:
            # TODO: 初始化本地嵌入模型
            # 例如：sentence-transformers, BGE, M3E等
            
            # 模拟初始化
            self.embedding_models[VectorModel.BGE_LARGE_ZH] = "mock_bge_large"
            self.embedding_models[VectorModel.BGE_BASE_ZH] = "mock_bge_base"
            self.embedding_models[VectorModel.M3E_BASE] = "mock_m3e_base"
            
            logger.info("Embedding models initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize embedding models: {str(e)}")
            raise
    
    async def _create_vector_tables(self):
        """创建向量表"""
        try:
            from backend.models.database import VectorModel
            from backend.config.database import engine
            from sqlalchemy import text
            
            # 使用SQLAlchemy创建表
            async with engine.begin() as conn:
                await conn.run_sync(VectorModel.metadata.create_all)
            
            logger.info("Vector tables created successfully")
            
        except Exception as e:
            logger.error(f"Failed to create vector tables: {str(e)}")
            raise
    
    async def _store_vector_to_db(
        self,
        vector_id: str,
        text: str,
        vector: List[float],
        metadata: VectorMetadata
    ):
        """存储向量到数据库"""
        try:
            async with get_async_session() as session:
                new_vector = VectorModel(
                    id=vector_id,
                    text=text,
                    vector=vector,
                    model=metadata.model.value,
                    vector_type=metadata.vector_type.value,
                    dimension=metadata.dimension,
                    source_id=metadata.source_id,
                    source_type=metadata.source_type,
                    chunk_index=metadata.chunk_index,
                    page_number=metadata.page_number,
                    language=metadata.language,
                    metadata=json.dumps(metadata.metadata),
                    created_at=metadata.created_at,
                    updated_at=metadata.updated_at
                )
                
                session.add(new_vector)
                await session.commit()
            
        except Exception as e:
            logger.error(f"Failed to store vector to database: {str(e)}")
            raise
    
    async def _store_vectors_batch_to_db(
        self,
        vector_ids: List[str],
        texts: List[str],
        vectors: List[List[float]],
        metadatas: List[VectorMetadata]
    ):
        """批量存储向量到数据库"""
        try:
            async with get_async_session() as session:
                new_vectors = []
                for vector_id, text, vector, metadata in zip(vector_ids, texts, vectors, metadatas):
                    new_vector = VectorModel(
                        id=vector_id,
                        text=text,
                        vector=vector,
                        model=metadata.model.value,
                        vector_type=metadata.vector_type.value,
                        dimension=metadata.dimension,
                        source_id=metadata.source_id,
                        source_type=metadata.source_type,
                        chunk_index=metadata.chunk_index,
                        page_number=metadata.page_number,
                        language=metadata.language,
                        metadata=json.dumps(metadata.metadata),
                        created_at=metadata.created_at,
                        updated_at=metadata.updated_at
                    )
                    new_vectors.append(new_vector)
                
                session.add_all(new_vectors)
                await session.commit()
            
        except Exception as e:
            logger.error(f"Failed to batch store vectors to database: {str(e)}")
            raise
    
    async def _search_vectors_in_db(
        self,
        request: VectorSearchRequest
    ) -> List[Dict[str, Any]]:
        """在数据库中搜索向量"""
        try:
            # 构建查询条件
            where_conditions = []
            params = []
            
            # 向量类型过滤
            if request.vector_types:
                type_placeholders = ",".join(["%s"] * len(request.vector_types))
                where_conditions.append(f"vector_type IN ({type_placeholders})")
                params.extend([vt.value for vt in request.vector_types])
            
            # 其他过滤条件
            for key, value in request.filters.items():
                if key in ["source_id", "source_type", "language", "model"]:
                    where_conditions.append(f"{key} = %s")
                    params.append(value)
            
            where_clause = "WHERE " + " AND ".join(where_conditions) if where_conditions else ""
            
            # TODO: 实现向量相似度搜索
            # 这里是简化的查询，实际应该使用向量数据库的相似度搜索功能
            async with get_async_session() as session:
                query_stmt = select(VectorModel)
                
                # 添加过滤条件
                if request.vector_types:
                    query_stmt = query_stmt.where(VectorModel.vector_type.in_([vt.value for vt in request.vector_types]))
                
                for key, value in request.filters.items():
                    if key in ["source_id", "source_type", "language", "model"]:
                        query_stmt = query_stmt.where(getattr(VectorModel, key) == value)
                
                query_stmt = query_stmt.limit(request.top_k * 2)
                
                result = await session.execute(query_stmt)
                results = result.scalars().all()
            
            # 转换结果格式
            formatted_results = []
            for row in results:
                result = {
                    "id": row.id,
                    "text": row.text,
                    "vector": row.vector,
                    "metadata": {
                        "id": row.id,
                        "text": row.text,
                        "model": row.model,
                        "vector_type": row.vector_type,
                        "dimension": row.dimension,
                        "source_id": row.source_id,
                        "source_type": row.source_type,
                        "chunk_index": row.chunk_index,
                        "page_number": row.page_number,
                        "language": row.language,
                        "metadata": json.loads(row.metadata) if row.metadata else {},
                        "created_at": row.created_at,
                        "updated_at": row.updated_at
                    }
                }
                formatted_results.append(result)
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"Vector search in database failed: {str(e)}")
            raise
    
    async def _get_vector_by_id(self, vector_id: str) -> Optional[Dict[str, Any]]:
        """根据ID获取向量"""
        try:
            async with get_async_session() as session:
                query_stmt = select(VectorModel).where(VectorModel.id == vector_id)
                result = await session.execute(query_stmt)
                vector_row = result.scalar_one_or_none()
            
            if not vector_row:
                return None
            
            return {
                "id": vector_row.id,
                "text": vector_row.text,
                "vector": vector_row.vector,
                "metadata": {
                    "id": vector_row.id,
                    "text": vector_row.text,
                    "model": vector_row.model,
                    "vector_type": vector_row.vector_type,
                    "dimension": vector_row.dimension,
                    "source_id": vector_row.source_id,
                    "source_type": vector_row.source_type,
                    "chunk_index": vector_row.chunk_index,
                    "page_number": vector_row.page_number,
                    "language": vector_row.language,
                    "metadata": json.loads(vector_row.metadata) if vector_row.metadata else {},
                    "created_at": vector_row.created_at,
                    "updated_at": vector_row.updated_at
                }
            }
            
        except Exception as e:
            logger.error(f"Get vector by ID failed: {str(e)}")
            raise
    
    async def _update_vector_in_db(self, vector_id: str, update_data: Dict[str, Any]):
        """更新数据库中的向量"""
        try:
            set_clauses = []
            params = []
            
            for key, value in update_data.items():
                if key == "metadata":
                    set_clauses.append("metadata = %s")
                    params.append(json.dumps(value))
                else:
                    set_clauses.append(f"{key} = %s")
                    params.append(value)
            
            set_clauses.append("updated_at = %s")
            params.append(datetime.now())
            params.append(vector_id)
            
            async with get_async_session() as session:
                update_stmt = update(VectorModel).where(VectorModel.id == vector_id)
                update_values = {}
                
                for key, value in updates.items():
                    if hasattr(VectorModel, key):
                        update_values[key] = value
                
                update_values['updated_at'] = datetime.now()
                update_stmt = update_stmt.values(**update_values)
                
                await session.execute(update_stmt)
                await session.commit()
            
        except Exception as e:
            logger.error(f"Update vector in database failed: {str(e)}")
            raise
    
    async def _delete_vector_from_db(self, vector_id: str) -> bool:
        """从数据库删除向量"""
        try:
            async with get_async_session() as session:
                delete_stmt = delete(VectorModel).where(VectorModel.id == vector_id)
                result = await session.execute(delete_stmt)
                await session.commit()
                return result.rowcount > 0
            
        except Exception as e:
            logger.error(f"Delete vector from database failed: {str(e)}")
            raise
    
    async def _delete_vectors_batch_from_db(self, vector_ids: List[str]) -> int:
        """批量从数据库删除向量"""
        try:
            if not vector_ids:
                return 0
            
            async with get_async_session() as session:
                delete_stmt = delete(VectorModel).where(VectorModel.id.in_(vector_ids))
                result = await session.execute(delete_stmt)
                await session.commit()
                return result.rowcount
            
        except Exception as e:
            logger.error(f"Batch delete vectors from database failed: {str(e)}")
            raise
    
    async def _get_vector_ids_by_source(
        self, source_id: str, source_type: str
    ) -> List[str]:
        """根据来源获取向量ID列表"""
        try:
            from backend.models.database import VectorModel
            from sqlalchemy import select
            
            async with get_async_session() as session:
                stmt = select(VectorModel.id).where(
                    VectorModel.source_id == source_id,
                    VectorModel.source_type == source_type
                )
                
                result = await session.execute(stmt)
                return [row[0] for row in result.fetchall()]
            
        except Exception as e:
            logger.error(f"Get vector IDs by source failed: {str(e)}")
            raise
    
    async def _get_vector_stats_from_db(self) -> Dict[str, Any]:
        """从数据库获取向量统计信息"""
        try:
            from backend.models.database import VectorModel
            from sqlalchemy import select, func
            
            async with get_async_session() as session:
                # 总向量数
                total_stmt = select(func.count(VectorModel.id))
                total_result = await session.execute(total_stmt)
                total_vectors = total_result.scalar() or 0
                
                # 按类型统计
                type_stmt = select(VectorModel.vector_type, func.count(VectorModel.id)).group_by(VectorModel.vector_type)
                type_results = await session.execute(type_stmt)
                vectors_by_type = {row[0]: row[1] for row in type_results.fetchall()}
                
                # 按模型统计
                model_stmt = select(VectorModel.model, func.count(VectorModel.id)).group_by(VectorModel.model)
                model_results = await session.execute(model_stmt)
                vectors_by_model = {row[0]: row[1] for row in model_results.fetchall()}
                
                # 平均维度
                dim_stmt = select(func.avg(VectorModel.dimension))
                dim_result = await session.execute(dim_stmt)
                average_dimension = float(dim_result.scalar()) if dim_result.scalar() else 0.0
            
            # 存储大小（估算）
            storage_size_mb = total_vectors * average_dimension * 4 / (1024 * 1024)  # 假设每个float 4字节
            
            return {
                "total_vectors": total_vectors,
                "vectors_by_type": vectors_by_type,
                "vectors_by_model": vectors_by_model,
                "average_dimension": average_dimension,
                "storage_size_mb": storage_size_mb
            }
            
        except Exception as e:
            logger.error(f"Get vector stats from database failed: {str(e)}")
            raise
    
    async def _update_vector_cache(self, vector_id: str, metadata: VectorMetadata):
        """更新向量缓存"""
        try:
            cache_key = f"vector_meta:{vector_id}"
            await self.redis.setex(
                cache_key,
                3600,  # 1小时缓存
                metadata.json()
            )
            
        except Exception as e:
            logger.error(f"Update vector cache failed: {str(e)}")
    
    async def _clear_vector_cache(self, vector_id: str):
        """清除向量缓存"""
        try:
            cache_key = f"vector_meta:{vector_id}"
            await self.redis.delete(cache_key)
            
        except Exception as e:
            logger.error(f"Clear vector cache failed: {str(e)}")