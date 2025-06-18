"""向量存储和搜索模块

该模块提供向量嵌入、存储和相似性搜索功能，支持多种嵌入模型和向量数据库。
"""

from .embedder import Embedder, EmbeddingModel, EmbeddingConfig
from .vector_store import VectorStore, VectorStoreConfig, VectorStoreType
from .similarity_search import SimilaritySearch, SearchConfig, SearchResult

__all__ = [
    "Embedder",
    "EmbeddingModel", 
    "EmbeddingConfig",
    "VectorStore",
    "VectorStoreConfig",
    "VectorStoreType",
    "SimilaritySearch",
    "SearchConfig",
    "SearchResult"
]