"""向量存储

提供向量数据的存储、检索和管理功能，支持多种向量数据库。
"""
# TODO: 添加Starrocks向量存储、检索和管理功能。


import asyncio
import json
import time
import uuid
from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, List, Optional, Union, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime

import numpy as np
import faiss
import chromadb
from chromadb.config import Settings
try:
    import weaviate
    from weaviate.client import Client as WeaviateClient
    WEAVIATE_AVAILABLE = True
except ImportError:
    WEAVIATE_AVAILABLE = False

try:
    import pinecone
    PINECONE_AVAILABLE = True
except ImportError:
    PINECONE_AVAILABLE = False
from qdrant_client import QdrantClient
from qdrant_client.http import models

try:
    from pymilvus import connections, Collection, CollectionSchema, FieldSchema, DataType, utility
    MILVUS_AVAILABLE = True
except ImportError:
    MILVUS_AVAILABLE = False

from backend.utils.logger import get_logger
from .embedder import EmbeddingResult

logger = get_logger(__name__)


class VectorStoreType(Enum):
    """向量存储类型"""
    FAISS = "faiss"
    CHROMA = "chroma"
    WEAVIATE = "weaviate"
    PINECONE = "pinecone"
    QDRANT = "qdrant"
    MILVUS = "milvus"
    ELASTICSEARCH = "elasticsearch"
    MEMORY = "memory"


class IndexType(Enum):
    """索引类型"""
    FLAT = "flat"  # 暴力搜索
    IVF_FLAT = "ivf_flat"  # 倒排文件索引
    IVF_PQ = "ivf_pq"  # 乘积量化
    HNSW = "hnsw"  # 分层导航小世界
    LSH = "lsh"  # 局部敏感哈希
    ANNOY = "annoy"  # Spotify的近似最近邻


class DistanceMetric(Enum):
    """距离度量"""
    COSINE = "cosine"
    EUCLIDEAN = "euclidean"
    DOT_PRODUCT = "dot_product"
    MANHATTAN = "manhattan"
    HAMMING = "hamming"


@dataclass
class VectorStoreConfig:
    """向量存储配置"""
    store_type: VectorStoreType
    dimension: int
    index_type: IndexType = IndexType.HNSW
    distance_metric: DistanceMetric = DistanceMetric.COSINE
    
    # 连接配置
    host: str = "localhost"
    port: int = 6333
    api_key: Optional[str] = None
    environment: Optional[str] = None
    
    # 索引配置
    nlist: int = 100  # IVF索引的聚类中心数
    m: int = 8  # PQ编码的子向量数
    ef_construction: int = 200  # HNSW构建时的候选数
    ef_search: int = 100  # HNSW搜索时的候选数
    max_connections: int = 16  # HNSW每个节点的最大连接数
    
    # 存储配置
    collection_name: str = "vectors"
    persist_directory: Optional[str] = None
    batch_size: int = 1000
    
    # 性能配置
    enable_gpu: bool = False
    num_threads: int = 4
    cache_size: int = 1000000  # 缓存大小（字节）
    
    # 备份配置
    enable_backup: bool = True
    backup_interval: int = 3600  # 秒
    max_backups: int = 5


@dataclass
class VectorDocument:
    """向量文档"""
    id: str
    vector: np.ndarray
    text: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "vector": self.vector.tolist(),
            "text": self.text,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "VectorDocument":
        """从字典创建"""
        return cls(
            id=data["id"],
            vector=np.array(data["vector"]),
            text=data["text"],
            metadata=data.get("metadata", {}),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"])
        )
    
    @classmethod
    def from_embedding_result(cls, result: EmbeddingResult, doc_id: Optional[str] = None) -> "VectorDocument":
        """从嵌入结果创建"""
        return cls(
            id=doc_id or str(uuid.uuid4()),
            vector=result.embedding,
            text=result.text,
            metadata=result.metadata
        )


@dataclass
class SearchResult:
    """搜索结果"""
    document: VectorDocument
    score: float
    rank: int
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "document": self.document.to_dict(),
            "score": self.score,
            "rank": self.rank
        }


@dataclass
class SearchResults:
    """搜索结果集"""
    results: List[SearchResult]
    query_vector: np.ndarray
    total_results: int
    search_time: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def get_documents(self) -> List[VectorDocument]:
        """获取文档列表"""
        return [result.document for result in self.results]
    
    def get_texts(self) -> List[str]:
        """获取文本列表"""
        return [result.document.text for result in self.results]
    
    def get_scores(self) -> List[float]:
        """获取分数列表"""
        return [result.score for result in self.results]


class VectorStore(ABC):
    """向量存储抽象基类"""
    
    def __init__(self, config: VectorStoreConfig):
        self.config = config
        self.stats = {
            "total_documents": 0,
            "total_searches": 0,
            "total_insertions": 0,
            "total_deletions": 0,
            "average_search_time": 0.0,
            "average_insertion_time": 0.0
        }
    
    @abstractmethod
    async def initialize(self):
        """初始化存储"""
        pass
    
    @abstractmethod
    async def insert(self, documents: List[VectorDocument]) -> List[str]:
        """插入文档"""
        pass
    
    @abstractmethod
    async def search(self, query_vector: np.ndarray, k: int = 10, 
                    filters: Optional[Dict[str, Any]] = None) -> SearchResults:
        """搜索相似向量"""
        pass
    
    @abstractmethod
    async def delete(self, document_ids: List[str]) -> int:
        """删除文档"""
        pass
    
    @abstractmethod
    async def update(self, documents: List[VectorDocument]) -> int:
        """更新文档"""
        pass
    
    @abstractmethod
    async def get_document(self, document_id: str) -> Optional[VectorDocument]:
        """获取文档"""
        pass
    
    @abstractmethod
    async def count(self) -> int:
        """获取文档数量"""
        pass
    
    @abstractmethod
    async def clear(self):
        """清空存储"""
        pass
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        return self.stats.copy()


class FaissVectorStore(VectorStore):
    """FAISS向量存储"""
    
    def __init__(self, config: VectorStoreConfig):
        super().__init__(config)
        self.index = None
        self.documents: Dict[int, VectorDocument] = {}
        self.id_to_index: Dict[str, int] = {}
        self.index_to_id: Dict[int, str] = {}
        self.next_index = 0
    
    async def initialize(self):
        """初始化FAISS索引"""
        try:
            if self.config.index_type == IndexType.FLAT:
                if self.config.distance_metric == DistanceMetric.COSINE:
                    self.index = faiss.IndexFlatIP(self.config.dimension)
                else:
                    self.index = faiss.IndexFlatL2(self.config.dimension)
            
            elif self.config.index_type == IndexType.IVF_FLAT:
                quantizer = faiss.IndexFlatL2(self.config.dimension)
                self.index = faiss.IndexIVFFlat(quantizer, self.config.dimension, self.config.nlist)
            
            elif self.config.index_type == IndexType.IVF_PQ:
                quantizer = faiss.IndexFlatL2(self.config.dimension)
                self.index = faiss.IndexIVFPQ(quantizer, self.config.dimension, 
                                            self.config.nlist, self.config.m, 8)
            
            elif self.config.index_type == IndexType.HNSW:
                self.index = faiss.IndexHNSWFlat(self.config.dimension, self.config.max_connections)
                self.index.hnsw.efConstruction = self.config.ef_construction
                self.index.hnsw.efSearch = self.config.ef_search
            
            else:
                raise ValueError(f"不支持的索引类型: {self.config.index_type}")
            
            # GPU支持
            if self.config.enable_gpu and faiss.get_num_gpus() > 0:
                self.index = faiss.index_cpu_to_gpu(faiss.StandardGpuResources(), 0, self.index)
            
            logger.info(f"FAISS索引初始化完成: {self.config.index_type.value}")
            
        except Exception as e:
            logger.error(f"FAISS索引初始化失败: {str(e)}")
            raise
    
    async def insert(self, documents: List[VectorDocument]) -> List[str]:
        """插入文档到FAISS"""
        start_time = time.time()
        
        try:
            vectors = np.vstack([doc.vector for doc in documents])
            
            # 归一化（余弦相似度）
            if self.config.distance_metric == DistanceMetric.COSINE:
                faiss.normalize_L2(vectors)
            
            # 训练索引（如果需要）
            if not self.index.is_trained:
                self.index.train(vectors)
            
            # 添加向量
            start_idx = self.next_index
            self.index.add(vectors)
            
            # 更新映射
            inserted_ids = []
            for i, doc in enumerate(documents):
                idx = start_idx + i
                self.documents[idx] = doc
                self.id_to_index[doc.id] = idx
                self.index_to_id[idx] = doc.id
                inserted_ids.append(doc.id)
            
            self.next_index += len(documents)
            
            # 更新统计
            insertion_time = time.time() - start_time
            self.stats["total_insertions"] += len(documents)
            self.stats["total_documents"] = len(self.documents)
            self.stats["average_insertion_time"] = (
                (self.stats["average_insertion_time"] * (self.stats["total_insertions"] - len(documents)) + 
                 insertion_time) / self.stats["total_insertions"]
            )
            
            logger.info(f"插入 {len(documents)} 个文档到FAISS ({insertion_time:.3f}s)")
            return inserted_ids
            
        except Exception as e:
            logger.error(f"FAISS插入失败: {str(e)}")
            raise
    
    async def search(self, query_vector: np.ndarray, k: int = 10, 
                    filters: Optional[Dict[str, Any]] = None) -> SearchResults:
        """在FAISS中搜索"""
        start_time = time.time()
        
        try:
            # 归一化查询向量
            query = query_vector.reshape(1, -1).astype(np.float32)
            if self.config.distance_metric == DistanceMetric.COSINE:
                faiss.normalize_L2(query)
            
            # 搜索
            scores, indices = self.index.search(query, min(k, self.index.ntotal))
            
            # 构建结果
            results = []
            for rank, (score, idx) in enumerate(zip(scores[0], indices[0])):
                if idx == -1:  # FAISS返回-1表示无效结果
                    continue
                
                doc_id = self.index_to_id.get(idx)
                if doc_id and idx in self.documents:
                    doc = self.documents[idx]
                    
                    # 应用过滤器
                    if filters and not self._apply_filters(doc, filters):
                        continue
                    
                    results.append(SearchResult(
                        document=doc,
                        score=float(score),
                        rank=rank
                    ))
            
            search_time = time.time() - start_time
            
            # 更新统计
            self.stats["total_searches"] += 1
            self.stats["average_search_time"] = (
                (self.stats["average_search_time"] * (self.stats["total_searches"] - 1) + 
                 search_time) / self.stats["total_searches"]
            )
            
            logger.debug(f"FAISS搜索完成: {len(results)} 个结果 ({search_time:.3f}s)")
            
            return SearchResults(
                results=results,
                query_vector=query_vector,
                total_results=len(results),
                search_time=search_time
            )
            
        except Exception as e:
            logger.error(f"FAISS搜索失败: {str(e)}")
            raise
    
    def _apply_filters(self, doc: VectorDocument, filters: Dict[str, Any]) -> bool:
        """应用过滤器"""
        for key, value in filters.items():
            if key not in doc.metadata:
                return False
            
            doc_value = doc.metadata[key]
            
            if isinstance(value, dict):
                # 范围查询
                if "$gte" in value and doc_value < value["$gte"]:
                    return False
                if "$lte" in value and doc_value > value["$lte"]:
                    return False
                if "$gt" in value and doc_value <= value["$gt"]:
                    return False
                if "$lt" in value and doc_value >= value["$lt"]:
                    return False
                if "$in" in value and doc_value not in value["$in"]:
                    return False
                if "$nin" in value and doc_value in value["$nin"]:
                    return False
            else:
                # 精确匹配
                if doc_value != value:
                    return False
        
        return True
    
    async def delete(self, document_ids: List[str]) -> int:
        """删除文档"""
        deleted_count = 0
        
        for doc_id in document_ids:
            if doc_id in self.id_to_index:
                idx = self.id_to_index[doc_id]
                
                # 从映射中删除
                del self.id_to_index[doc_id]
                del self.index_to_id[idx]
                del self.documents[idx]
                
                deleted_count += 1
        
        self.stats["total_deletions"] += deleted_count
        self.stats["total_documents"] = len(self.documents)
        
        logger.info(f"从FAISS删除 {deleted_count} 个文档")
        return deleted_count
    
    async def update(self, documents: List[VectorDocument]) -> int:
        """更新文档"""
        updated_count = 0
        
        for doc in documents:
            if doc.id in self.id_to_index:
                idx = self.id_to_index[doc.id]
                doc.updated_at = datetime.now()
                self.documents[idx] = doc
                updated_count += 1
        
        logger.info(f"更新 {updated_count} 个FAISS文档")
        return updated_count
    
    async def get_document(self, document_id: str) -> Optional[VectorDocument]:
        """获取文档"""
        if document_id in self.id_to_index:
            idx = self.id_to_index[document_id]
            return self.documents.get(idx)
        return None
    
    async def count(self) -> int:
        """获取文档数量"""
        return len(self.documents)
    
    async def clear(self):
        """清空存储"""
        self.documents.clear()
        self.id_to_index.clear()
        self.index_to_id.clear()
        self.next_index = 0
        
        # 重新初始化索引
        await self.initialize()
        
        self.stats["total_documents"] = 0
        logger.info("FAISS存储已清空")


class ChromaVectorStore(VectorStore):
    """ChromaDB向量存储"""
    
    def __init__(self, config: VectorStoreConfig):
        super().__init__(config)
        self.client = None
        self.collection = None
    
    async def initialize(self):
        """初始化ChromaDB"""
        try:
            if self.config.persist_directory:
                self.client = chromadb.PersistentClient(
                    path=self.config.persist_directory,
                    settings=Settings(anonymized_telemetry=False)
                )
            else:
                self.client = chromadb.Client()
            
            # 创建或获取集合
            distance_map = {
                DistanceMetric.COSINE: "cosine",
                DistanceMetric.EUCLIDEAN: "l2",
                DistanceMetric.DOT_PRODUCT: "ip"
            }
            
            distance_function = distance_map.get(self.config.distance_metric, "cosine")
            
            try:
                self.collection = self.client.get_collection(
                    name=self.config.collection_name,
                    metadata={"hnsw:space": distance_function}
                )
            except:
                self.collection = self.client.create_collection(
                    name=self.config.collection_name,
                    metadata={"hnsw:space": distance_function}
                )
            
            logger.info(f"ChromaDB初始化完成: {self.config.collection_name}")
            
        except Exception as e:
            logger.error(f"ChromaDB初始化失败: {str(e)}")
            raise
    
    async def insert(self, documents: List[VectorDocument]) -> List[str]:
        """插入文档到ChromaDB"""
        start_time = time.time()
        
        try:
            ids = [doc.id for doc in documents]
            embeddings = [doc.vector.tolist() for doc in documents]
            metadatas = [doc.metadata for doc in documents]
            documents_text = [doc.text for doc in documents]
            
            self.collection.add(
                ids=ids,
                embeddings=embeddings,
                metadatas=metadatas,
                documents=documents_text
            )
            
            insertion_time = time.time() - start_time
            self.stats["total_insertions"] += len(documents)
            self.stats["total_documents"] = self.collection.count()
            
            logger.info(f"插入 {len(documents)} 个文档到ChromaDB ({insertion_time:.3f}s)")
            return ids
            
        except Exception as e:
            logger.error(f"ChromaDB插入失败: {str(e)}")
            raise
    
    async def search(self, query_vector: np.ndarray, k: int = 10, 
                    filters: Optional[Dict[str, Any]] = None) -> SearchResults:
        """在ChromaDB中搜索"""
        start_time = time.time()
        
        try:
            results = self.collection.query(
                query_embeddings=[query_vector.tolist()],
                n_results=k,
                where=filters
            )
            
            search_results = []
            
            if results["ids"] and results["ids"][0]:
                for rank, (doc_id, distance, metadata, text) in enumerate(zip(
                    results["ids"][0],
                    results["distances"][0],
                    results["metadatas"][0],
                    results["documents"][0]
                )):
                    # ChromaDB返回距离，需要转换为相似度分数
                    if self.config.distance_metric == DistanceMetric.COSINE:
                        score = 1.0 - distance
                    else:
                        score = 1.0 / (1.0 + distance)
                    
                    doc = VectorDocument(
                        id=doc_id,
                        vector=np.array([]),  # ChromaDB不返回向量
                        text=text,
                        metadata=metadata or {}
                    )
                    
                    search_results.append(SearchResult(
                        document=doc,
                        score=score,
                        rank=rank
                    ))
            
            search_time = time.time() - start_time
            self.stats["total_searches"] += 1
            
            logger.debug(f"ChromaDB搜索完成: {len(search_results)} 个结果 ({search_time:.3f}s)")
            
            return SearchResults(
                results=search_results,
                query_vector=query_vector,
                total_results=len(search_results),
                search_time=search_time
            )
            
        except Exception as e:
            logger.error(f"ChromaDB搜索失败: {str(e)}")
            raise
    
    async def delete(self, document_ids: List[str]) -> int:
        """删除文档"""
        try:
            self.collection.delete(ids=document_ids)
            
            self.stats["total_deletions"] += len(document_ids)
            self.stats["total_documents"] = self.collection.count()
            
            logger.info(f"从ChromaDB删除 {len(document_ids)} 个文档")
            return len(document_ids)
            
        except Exception as e:
            logger.error(f"ChromaDB删除失败: {str(e)}")
            raise
    
    async def update(self, documents: List[VectorDocument]) -> int:
        """更新文档"""
        try:
            ids = [doc.id for doc in documents]
            embeddings = [doc.vector.tolist() for doc in documents]
            metadatas = [doc.metadata for doc in documents]
            documents_text = [doc.text for doc in documents]
            
            self.collection.update(
                ids=ids,
                embeddings=embeddings,
                metadatas=metadatas,
                documents=documents_text
            )
            
            logger.info(f"更新 {len(documents)} 个ChromaDB文档")
            return len(documents)
            
        except Exception as e:
            logger.error(f"ChromaDB更新失败: {str(e)}")
            raise
    
    async def get_document(self, document_id: str) -> Optional[VectorDocument]:
        """获取文档"""
        try:
            results = self.collection.get(ids=[document_id])
            
            if results["ids"] and results["ids"][0]:
                return VectorDocument(
                    id=results["ids"][0],
                    vector=np.array([]),  # ChromaDB不返回向量
                    text=results["documents"][0],
                    metadata=results["metadatas"][0] or {}
                )
            
            return None
            
        except Exception as e:
            logger.error(f"ChromaDB获取文档失败: {str(e)}")
            return None
    
    async def count(self) -> int:
        """获取文档数量"""
        return self.collection.count()
    
    async def clear(self):
        """清空存储"""
        try:
            # 删除集合
            self.client.delete_collection(name=self.config.collection_name)
            
            # 重新创建集合
            distance_map = {
                DistanceMetric.COSINE: "cosine",
                DistanceMetric.EUCLIDEAN: "l2",
                DistanceMetric.DOT_PRODUCT: "ip"
            }
            
            distance_function = distance_map.get(self.config.distance_metric, "cosine")
            
            self.collection = self.client.create_collection(
                name=self.config.collection_name,
                metadata={"hnsw:space": distance_function}
            )
            
            self.stats["total_documents"] = 0
            logger.info("ChromaDB存储已清空")
            
        except Exception as e:
            logger.error(f"ChromaDB清空失败: {str(e)}")
            raise


class MemoryVectorStore(VectorStore):
    """内存向量存储（用于测试和小规模应用）"""
    
    def __init__(self, config: VectorStoreConfig):
        super().__init__(config)
        self.documents: Dict[str, VectorDocument] = {}
        self.vectors: List[np.ndarray] = []
        self.doc_ids: List[str] = []
    
    async def initialize(self):
        """初始化内存存储"""
        logger.info("内存向量存储初始化完成")
    
    async def insert(self, documents: List[VectorDocument]) -> List[str]:
        """插入文档到内存"""
        start_time = time.time()
        
        inserted_ids = []
        for doc in documents:
            self.documents[doc.id] = doc
            self.vectors.append(doc.vector)
            self.doc_ids.append(doc.id)
            inserted_ids.append(doc.id)
        
        insertion_time = time.time() - start_time
        self.stats["total_insertions"] += len(documents)
        self.stats["total_documents"] = len(self.documents)
        
        logger.info(f"插入 {len(documents)} 个文档到内存 ({insertion_time:.3f}s)")
        return inserted_ids
    
    async def search(self, query_vector: np.ndarray, k: int = 10, 
                    filters: Optional[Dict[str, Any]] = None) -> SearchResults:
        """在内存中搜索"""
        start_time = time.time()
        
        if not self.vectors:
            return SearchResults(
                results=[],
                query_vector=query_vector,
                total_results=0,
                search_time=0.0
            )
        
        # 计算相似度
        vectors_matrix = np.vstack(self.vectors)
        
        if self.config.distance_metric == DistanceMetric.COSINE:
            # 余弦相似度
            query_norm = np.linalg.norm(query_vector)
            vectors_norm = np.linalg.norm(vectors_matrix, axis=1)
            similarities = np.dot(vectors_matrix, query_vector) / (vectors_norm * query_norm)
        elif self.config.distance_metric == DistanceMetric.DOT_PRODUCT:
            # 点积
            similarities = np.dot(vectors_matrix, query_vector)
        else:
            # 欧几里得距离（转换为相似度）
            distances = np.linalg.norm(vectors_matrix - query_vector, axis=1)
            similarities = 1.0 / (1.0 + distances)
        
        # 排序并获取top-k
        top_indices = np.argsort(similarities)[::-1][:k]
        
        results = []
        for rank, idx in enumerate(top_indices):
            doc_id = self.doc_ids[idx]
            doc = self.documents[doc_id]
            
            # 应用过滤器
            if filters and not self._apply_filters(doc, filters):
                continue
            
            results.append(SearchResult(
                document=doc,
                score=float(similarities[idx]),
                rank=rank
            ))
        
        search_time = time.time() - start_time
        self.stats["total_searches"] += 1
        
        logger.debug(f"内存搜索完成: {len(results)} 个结果 ({search_time:.3f}s)")
        
        return SearchResults(
            results=results,
            query_vector=query_vector,
            total_results=len(results),
            search_time=search_time
        )
    
    def _apply_filters(self, doc: VectorDocument, filters: Dict[str, Any]) -> bool:
        """应用过滤器"""
        for key, value in filters.items():
            if key not in doc.metadata:
                return False
            if doc.metadata[key] != value:
                return False
        return True
    
    async def delete(self, document_ids: List[str]) -> int:
        """删除文档"""
        deleted_count = 0
        
        for doc_id in document_ids:
            if doc_id in self.documents:
                # 找到索引
                idx = self.doc_ids.index(doc_id)
                
                # 删除
                del self.documents[doc_id]
                self.vectors.pop(idx)
                self.doc_ids.pop(idx)
                
                deleted_count += 1
        
        self.stats["total_deletions"] += deleted_count
        self.stats["total_documents"] = len(self.documents)
        
        logger.info(f"从内存删除 {deleted_count} 个文档")
        return deleted_count
    
    async def update(self, documents: List[VectorDocument]) -> int:
        """更新文档"""
        updated_count = 0
        
        for doc in documents:
            if doc.id in self.documents:
                # 找到索引
                idx = self.doc_ids.index(doc.id)
                
                # 更新
                doc.updated_at = datetime.now()
                self.documents[doc.id] = doc
                self.vectors[idx] = doc.vector
                
                updated_count += 1
        
        logger.info(f"更新 {updated_count} 个内存文档")
        return updated_count
    
    async def get_document(self, document_id: str) -> Optional[VectorDocument]:
        """获取文档"""
        return self.documents.get(document_id)
    
    async def count(self) -> int:
        """获取文档数量"""
        return len(self.documents)
    
    async def clear(self):
        """清空存储"""
        self.documents.clear()
        self.vectors.clear()
        self.doc_ids.clear()
        
        self.stats["total_documents"] = 0
        logger.info("内存存储已清空")


def create_vector_store(config: VectorStoreConfig) -> VectorStore:
    """创建向量存储实例
    
    Args:
        config: 向量存储配置
        
    Returns:
        向量存储实例
    """
    if config.store_type == VectorStoreType.FAISS:
        return FaissVectorStore(config)
    elif config.store_type == VectorStoreType.CHROMA:
        return ChromaVectorStore(config)
    elif config.store_type == VectorStoreType.MEMORY:
        return MemoryVectorStore(config)
    else:
        raise ValueError(f"不支持的向量存储类型: {config.store_type}")


# 预定义配置
DEFAULT_CONFIGS = {
    "faiss_hnsw": VectorStoreConfig(
        store_type=VectorStoreType.FAISS,
        dimension=768,
        index_type=IndexType.HNSW,
        distance_metric=DistanceMetric.COSINE
    ),
    "faiss_flat": VectorStoreConfig(
        store_type=VectorStoreType.FAISS,
        dimension=768,
        index_type=IndexType.FLAT,
        distance_metric=DistanceMetric.COSINE
    ),
    "chroma_default": VectorStoreConfig(
        store_type=VectorStoreType.CHROMA,
        dimension=768,
        distance_metric=DistanceMetric.COSINE,
        persist_directory="./chroma_db"
    ),
    "memory_default": VectorStoreConfig(
        store_type=VectorStoreType.MEMORY,
        dimension=768,
        distance_metric=DistanceMetric.COSINE
    )
}


def create_default_vector_store(config_name: str = "faiss_hnsw", **kwargs) -> VectorStore:
    """创建默认向量存储
    
    Args:
        config_name: 预定义配置名称
        **kwargs: 额外配置参数
        
    Returns:
        向量存储实例
    """
    if config_name not in DEFAULT_CONFIGS:
        raise ValueError(f"未知配置: {config_name}. 可用配置: {list(DEFAULT_CONFIGS.keys())}")
    
    config = DEFAULT_CONFIGS[config_name]
    
    # 应用额外参数
    for key, value in kwargs.items():
        if hasattr(config, key):
            setattr(config, key, value)
    
    return create_vector_store(config)