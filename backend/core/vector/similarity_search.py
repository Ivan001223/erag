"""相似性搜索

提供高级的相似性搜索功能，包括多种搜索策略、结果重排序和搜索优化。
"""

import asyncio
import math
import time
from enum import Enum
from typing import Dict, List, Optional, Union, Any, Tuple, Callable
from dataclasses import dataclass, field
from datetime import datetime

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import jieba
import re

from backend.utils.logger import get_logger
from .embedder import Embedder, EmbeddingResult
from .vector_store import VectorStore, VectorDocument, SearchResults, SearchResult

logger = get_logger(__name__)


class SearchStrategy(Enum):
    """搜索策略"""
    VECTOR_ONLY = "vector_only"  # 仅向量搜索
    KEYWORD_ONLY = "keyword_only"  # 仅关键词搜索
    HYBRID = "hybrid"  # 混合搜索
    SEMANTIC = "semantic"  # 语义搜索
    FUZZY = "fuzzy"  # 模糊搜索
    MULTI_VECTOR = "multi_vector"  # 多向量搜索


class RerankingStrategy(Enum):
    """重排序策略"""
    NONE = "none"  # 不重排序
    SCORE_FUSION = "score_fusion"  # 分数融合
    RRF = "rrf"  # 倒数排名融合
    WEIGHTED = "weighted"  # 加权融合
    CROSS_ENCODER = "cross_encoder"  # 交叉编码器
    LLM_RERANK = "llm_rerank"  # LLM重排序


class QueryExpansionStrategy(Enum):
    """查询扩展策略"""
    NONE = "none"  # 不扩展
    SYNONYMS = "synonyms"  # 同义词扩展
    RELATED_TERMS = "related_terms"  # 相关词扩展
    PSEUDO_RELEVANCE = "pseudo_relevance"  # 伪相关反馈
    LLM_EXPANSION = "llm_expansion"  # LLM扩展


@dataclass
class SearchConfig:
    """搜索配置"""
    # TODO: 配置放在配置文件里面
    strategy: SearchStrategy = SearchStrategy.HYBRID
    reranking_strategy: RerankingStrategy = RerankingStrategy.SCORE_FUSION
    query_expansion_strategy: QueryExpansionStrategy = QueryExpansionStrategy.NONE
    
    # 基本搜索参数
    top_k: int = 10
    min_score: float = 0.0
    max_results: int = 100
    
    # 混合搜索权重
    vector_weight: float = 0.7
    keyword_weight: float = 0.3
    
    # 查询扩展参数
    expansion_terms: int = 5
    expansion_weight: float = 0.3
    
    # 重排序参数
    rerank_top_k: int = 50
    rerank_model: Optional[str] = None
    
    # 过滤参数
    filters: Optional[Dict[str, Any]] = None
    date_range: Optional[Tuple[datetime, datetime]] = None
    
    # 性能参数
    enable_cache: bool = True
    cache_ttl: int = 300  # 秒
    timeout: float = 30.0  # 秒
    
    # 多样性参数
    enable_diversity: bool = False
    diversity_threshold: float = 0.8
    max_similar_results: int = 3


@dataclass
class SearchQuery:
    """搜索查询"""
    text: str
    vector: Optional[np.ndarray] = None
    keywords: Optional[List[str]] = None
    filters: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """后处理"""
        if not self.keywords:
            self.keywords = self._extract_keywords()
    
    def _extract_keywords(self) -> List[str]:
        """提取关键词"""
        # 简单的关键词提取
        words = jieba.lcut(self.text)
        # 过滤停用词和标点
        keywords = [word for word in words if len(word) > 1 and word.isalnum()]
        return keywords[:10]  # 限制关键词数量


@dataclass
class SearchMetrics:
    """搜索指标"""
    total_time: float
    vector_search_time: float = 0.0
    keyword_search_time: float = 0.0
    reranking_time: float = 0.0
    query_expansion_time: float = 0.0
    
    vector_results_count: int = 0
    keyword_results_count: int = 0
    final_results_count: int = 0
    
    cache_hit: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "total_time": self.total_time,
            "vector_search_time": self.vector_search_time,
            "keyword_search_time": self.keyword_search_time,
            "reranking_time": self.reranking_time,
            "query_expansion_time": self.query_expansion_time,
            "vector_results_count": self.vector_results_count,
            "keyword_results_count": self.keyword_results_count,
            "final_results_count": self.final_results_count,
            "cache_hit": self.cache_hit
        }


@dataclass
class EnhancedSearchResult:
    """增强搜索结果"""
    document: VectorDocument
    vector_score: float
    keyword_score: float
    final_score: float
    rank: int
    explanation: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "document": self.document.to_dict(),
            "vector_score": self.vector_score,
            "keyword_score": self.keyword_score,
            "final_score": self.final_score,
            "rank": self.rank,
            "explanation": self.explanation
        }


@dataclass
class EnhancedSearchResults:
    """增强搜索结果集"""
    results: List[EnhancedSearchResult]
    query: SearchQuery
    config: SearchConfig
    metrics: SearchMetrics
    total_results: int
    
    def get_documents(self) -> List[VectorDocument]:
        """获取文档列表"""
        return [result.document for result in self.results]
    
    def get_texts(self) -> List[str]:
        """获取文本列表"""
        return [result.document.text for result in self.results]
    
    def get_scores(self) -> List[float]:
        """获取最终分数列表"""
        return [result.final_score for result in self.results]
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "results": [result.to_dict() for result in self.results],
            "query": {
                "text": self.query.text,
                "keywords": self.query.keywords,
                "metadata": self.query.metadata
            },
            "config": {
                "strategy": self.config.strategy.value,
                "top_k": self.config.top_k,
                "vector_weight": self.config.vector_weight,
                "keyword_weight": self.config.keyword_weight
            },
            "metrics": self.metrics.to_dict(),
            "total_results": self.total_results
        }


class SimilaritySearch:
    """相似性搜索器
    
    提供高级的相似性搜索功能，支持多种搜索策略和优化。
    """
    
    def __init__(self, embedder: Embedder, vector_store: VectorStore, config: SearchConfig = None):
        """初始化搜索器
        
        Args:
            embedder: 嵌入器
            vector_store: 向量存储
            config: 搜索配置
        """
        self.embedder = embedder
        self.vector_store = vector_store
        self.config = config or SearchConfig()
        
        # 缓存
        self.search_cache: Dict[str, EnhancedSearchResults] = {}
        
        # 统计信息
        self.stats = {
            "total_searches": 0,
            "cache_hits": 0,
            "average_search_time": 0.0,
            "total_search_time": 0.0
        }
        
        # TF-IDF向量化器（用于关键词搜索）
        self.tfidf_vectorizer = None
        self.document_texts: List[str] = []
        self.document_ids: List[str] = []
        
        logger.info(f"相似性搜索器初始化完成: {config.strategy.value if config else 'default'}")
    
    async def initialize(self):
        """初始化搜索器"""
        # 构建TF-IDF索引
        await self._build_tfidf_index()
        logger.info("相似性搜索器初始化完成")
    
    async def _build_tfidf_index(self):
        """构建TF-IDF索引"""
        try:
            # 获取所有文档
            count = await self.vector_store.count()
            if count == 0:
                logger.warning("向量存储为空，跳过TF-IDF索引构建")
                return
            
            # 这里简化处理，实际应该分批获取
            # TODO：从向量存储获取所有文档
            # 由于VectorStore接口限制，这里使用模拟数据
            # TODO：使用实际数据
            self.document_texts = []
            self.document_ids = []
            
            # 创建TF-IDF向量化器
            self.tfidf_vectorizer = TfidfVectorizer(
                max_features=10000,
                stop_words=None,  # 中文需要自定义停用词
                ngram_range=(1, 2),
                tokenizer=lambda x: jieba.lcut(x)
            )
            
            logger.info(f"TF-IDF索引构建完成: {len(self.document_texts)} 个文档")
            
        except Exception as e:
            logger.error(f"TF-IDF索引构建失败: {str(e)}")
    
    def _get_cache_key(self, query: SearchQuery, config: SearchConfig) -> str:
        """生成缓存键"""
        import hashlib
        content = f"{query.text}:{config.strategy.value}:{config.top_k}:{config.vector_weight}:{config.keyword_weight}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def _get_from_cache(self, query: SearchQuery, config: SearchConfig) -> Optional[EnhancedSearchResults]:
        """从缓存获取结果"""
        if not config.enable_cache:
            return None
        
        cache_key = self._get_cache_key(query, config)
        result = self.search_cache.get(cache_key)
        
        if result:
            # 检查TTL
            age = time.time() - result.metrics.total_time
            if age <= config.cache_ttl:
                self.stats["cache_hits"] += 1
                return result
            else:
                del self.search_cache[cache_key]
        
        return None
    
    def _save_to_cache(self, query: SearchQuery, config: SearchConfig, results: EnhancedSearchResults):
        """保存到缓存"""
        if not config.enable_cache:
            return
        
        cache_key = self._get_cache_key(query, config)
        self.search_cache[cache_key] = results
    
    async def search(self, query: Union[str, SearchQuery], config: Optional[SearchConfig] = None) -> EnhancedSearchResults:
        """执行搜索
        
        Args:
            query: 搜索查询
            config: 搜索配置
            
        Returns:
            增强搜索结果
        """
        start_time = time.time()
        
        # 处理查询
        if isinstance(query, str):
            query = SearchQuery(text=query)
        
        # 使用配置
        search_config = config or self.config
        
        # 检查缓存
        cached_result = self._get_from_cache(query, search_config)
        if cached_result:
            cached_result.metrics.cache_hit = True
            logger.debug(f"缓存命中: {query.text[:50]}...")
            return cached_result
        
        try:
            # 初始化指标
            metrics = SearchMetrics(total_time=0.0)
            
            # 查询扩展
            if search_config.query_expansion_strategy != QueryExpansionStrategy.NONE:
                expansion_start = time.time()
                query = await self._expand_query(query, search_config)
                metrics.query_expansion_time = time.time() - expansion_start
            
            # 生成查询向量
            if not query.vector:
                embedding_result = await self.embedder.embed_text(query.text)
                query.vector = embedding_result.embedding
            
            # 执行搜索
            if search_config.strategy == SearchStrategy.VECTOR_ONLY:
                results = await self._vector_search(query, search_config, metrics)
            elif search_config.strategy == SearchStrategy.KEYWORD_ONLY:
                results = await self._keyword_search(query, search_config, metrics)
            elif search_config.strategy == SearchStrategy.HYBRID:
                results = await self._hybrid_search(query, search_config, metrics)
            elif search_config.strategy == SearchStrategy.SEMANTIC:
                results = await self._semantic_search(query, search_config, metrics)
            elif search_config.strategy == SearchStrategy.FUZZY:
                results = await self._fuzzy_search(query, search_config, metrics)
            else:
                results = await self._hybrid_search(query, search_config, metrics)
            
            # 重排序
            if search_config.reranking_strategy != RerankingStrategy.NONE:
                rerank_start = time.time()
                results = await self._rerank_results(query, results, search_config)
                metrics.reranking_time = time.time() - rerank_start
            
            # 多样性过滤
            if search_config.enable_diversity:
                results = self._apply_diversity_filter(results, search_config)
            
            # 应用过滤器
            if search_config.filters or query.filters:
                results = self._apply_filters(results, search_config.filters or query.filters)
            
            # 限制结果数量
            results = results[:search_config.top_k]
            
            # 更新排名
            for i, result in enumerate(results):
                result.rank = i
            
            # 完成指标
            metrics.total_time = time.time() - start_time
            metrics.final_results_count = len(results)
            
            # 创建最终结果
            enhanced_results = EnhancedSearchResults(
                results=results,
                query=query,
                config=search_config,
                metrics=metrics,
                total_results=len(results)
            )
            
            # 保存到缓存
            self._save_to_cache(query, search_config, enhanced_results)
            
            # 更新统计
            self.stats["total_searches"] += 1
            self.stats["total_search_time"] += metrics.total_time
            self.stats["average_search_time"] = (
                self.stats["total_search_time"] / self.stats["total_searches"]
            )
            
            logger.info(f"搜索完成: {len(results)} 个结果 ({metrics.total_time:.3f}s)")
            return enhanced_results
            
        except Exception as e:
            logger.error(f"搜索失败: {str(e)}")
            raise
    
    async def _expand_query(self, query: SearchQuery, config: SearchConfig) -> SearchQuery:
        """扩展查询"""
        if config.query_expansion_strategy == QueryExpansionStrategy.SYNONYMS:
            # 简单的同义词扩展（实际应该使用词典或模型）
            # TODO：实现同义词扩展
            expanded_text = query.text + " " + " ".join(query.keywords[:config.expansion_terms])
            query.text = expanded_text
        
        return query
    
    async def _vector_search(self, query: SearchQuery, config: SearchConfig, metrics: SearchMetrics) -> List[EnhancedSearchResult]:
        """向量搜索"""
        start_time = time.time()
        
        # 执行向量搜索
        search_results = await self.vector_store.search(
            query_vector=query.vector,
            k=config.rerank_top_k,
            filters=config.filters
        )
        
        metrics.vector_search_time = time.time() - start_time
        metrics.vector_results_count = len(search_results.results)
        
        # 转换为增强结果
        enhanced_results = []
        for result in search_results.results:
            enhanced_results.append(EnhancedSearchResult(
                document=result.document,
                vector_score=result.score,
                keyword_score=0.0,
                final_score=result.score,
                rank=result.rank,
                explanation={"strategy": "vector_only"}
            ))
        
        return enhanced_results
    
    async def _keyword_search(self, query: SearchQuery, config: SearchConfig, metrics: SearchMetrics) -> List[EnhancedSearchResult]:
        """关键词搜索"""
        start_time = time.time()
        
        results = []
        
        if self.tfidf_vectorizer and self.document_texts:
            # 使用TF-IDF搜索
            query_vector = self.tfidf_vectorizer.transform([query.text])
            doc_vectors = self.tfidf_vectorizer.transform(self.document_texts)
            
            # 计算相似度
            similarities = cosine_similarity(query_vector, doc_vectors)[0]
            
            # 获取top-k结果
            top_indices = np.argsort(similarities)[::-1][:config.rerank_top_k]
            
            for rank, idx in enumerate(top_indices):
                if similarities[idx] > config.min_score:
                    # 创建虚拟文档（实际应该从存储获取）
                    # TODO：从存储获取文档向量
                    doc = VectorDocument(
                        id=self.document_ids[idx] if idx < len(self.document_ids) else str(idx),
                        vector=np.array([]),
                        text=self.document_texts[idx],
                        metadata={}
                    )
                    
                    results.append(EnhancedSearchResult(
                        document=doc,
                        vector_score=0.0,
                        keyword_score=float(similarities[idx]),
                        final_score=float(similarities[idx]),
                        rank=rank,
                        explanation={"strategy": "keyword_only"}
                    ))
        
        metrics.keyword_search_time = time.time() - start_time
        metrics.keyword_results_count = len(results)
        
        return results
    
    async def _hybrid_search(self, query: SearchQuery, config: SearchConfig, metrics: SearchMetrics) -> List[EnhancedSearchResult]:
        """混合搜索"""
        # 并行执行向量搜索和关键词搜索
        vector_task = self._vector_search(query, config, metrics)
        keyword_task = self._keyword_search(query, config, metrics)
        
        vector_results, keyword_results = await asyncio.gather(vector_task, keyword_task)
        
        # 合并结果
        merged_results = self._merge_search_results(
            vector_results, keyword_results, config
        )
        
        return merged_results
    
    async def _semantic_search(self, query: SearchQuery, config: SearchConfig, metrics: SearchMetrics) -> List[EnhancedSearchResult]:
        """语义搜索"""
        # 语义搜索主要基于向量搜索，但可以加入更多语义理解
        results = await self._vector_search(query, config, metrics)
        
        # 可以在这里添加语义增强逻辑
        # TODO: 实现基于嵌入模型的语义增强
        for result in results:
            result.explanation["strategy"] = "semantic"
        
        return results
    
    async def _fuzzy_search(self, query: SearchQuery, config: SearchConfig, metrics: SearchMetrics) -> List[EnhancedSearchResult]:
        """模糊搜索"""
        # 模糊搜索可以结合编辑距离、音似等
        results = await self._hybrid_search(query, config, metrics)
        
        # 可以在这里添加模糊匹配逻辑
        # TODO: 实现基于编辑距离的模糊匹配
        for result in results:
            result.explanation["strategy"] = "fuzzy"
        
        return results
    
    def _merge_search_results(self, vector_results: List[EnhancedSearchResult], 
                             keyword_results: List[EnhancedSearchResult], 
                             config: SearchConfig) -> List[EnhancedSearchResult]:
        """合并搜索结果"""
        # 创建文档ID到结果的映射
        vector_map = {result.document.id: result for result in vector_results}
        keyword_map = {result.document.id: result for result in keyword_results}
        
        # 获取所有唯一文档ID
        all_doc_ids = set(vector_map.keys()) | set(keyword_map.keys())
        
        merged_results = []
        
        for doc_id in all_doc_ids:
            vector_result = vector_map.get(doc_id)
            keyword_result = keyword_map.get(doc_id)
            
            if vector_result and keyword_result:
                # 两种搜索都有结果
                final_score = (
                    vector_result.vector_score * config.vector_weight +
                    keyword_result.keyword_score * config.keyword_weight
                )
                
                merged_results.append(EnhancedSearchResult(
                    document=vector_result.document,
                    vector_score=vector_result.vector_score,
                    keyword_score=keyword_result.keyword_score,
                    final_score=final_score,
                    rank=0,  # 稍后重新排序
                    explanation={
                        "strategy": "hybrid",
                        "vector_weight": config.vector_weight,
                        "keyword_weight": config.keyword_weight
                    }
                ))
            
            elif vector_result:
                # 只有向量搜索结果
                final_score = vector_result.vector_score * config.vector_weight
                
                merged_results.append(EnhancedSearchResult(
                    document=vector_result.document,
                    vector_score=vector_result.vector_score,
                    keyword_score=0.0,
                    final_score=final_score,
                    rank=0,
                    explanation={"strategy": "vector_only_in_hybrid"}
                ))
            
            elif keyword_result:
                # 只有关键词搜索结果
                final_score = keyword_result.keyword_score * config.keyword_weight
                
                merged_results.append(EnhancedSearchResult(
                    document=keyword_result.document,
                    vector_score=0.0,
                    keyword_score=keyword_result.keyword_score,
                    final_score=final_score,
                    rank=0,
                    explanation={"strategy": "keyword_only_in_hybrid"}
                ))
        
        # 按最终分数排序
        merged_results.sort(key=lambda x: x.final_score, reverse=True)
        
        return merged_results
    
    async def _rerank_results(self, query: SearchQuery, results: List[EnhancedSearchResult], 
                             config: SearchConfig) -> List[EnhancedSearchResult]:
        """重排序结果"""
        if config.reranking_strategy == RerankingStrategy.SCORE_FUSION:
            return self._score_fusion_rerank(results)
        elif config.reranking_strategy == RerankingStrategy.RRF:
            return self._rrf_rerank(results)
        elif config.reranking_strategy == RerankingStrategy.WEIGHTED:
            return self._weighted_rerank(results, config)
        else:
            return results
    
    def _score_fusion_rerank(self, results: List[EnhancedSearchResult]) -> List[EnhancedSearchResult]:
        """分数融合重排序"""
        # 归一化分数
        if not results:
            return results
        
        max_vector_score = max(r.vector_score for r in results)
        max_keyword_score = max(r.keyword_score for r in results)
        
        for result in results:
            norm_vector_score = result.vector_score / max_vector_score if max_vector_score > 0 else 0
            norm_keyword_score = result.keyword_score / max_keyword_score if max_keyword_score > 0 else 0
            
            # 重新计算最终分数
            result.final_score = (norm_vector_score + norm_keyword_score) / 2
            result.explanation["reranking"] = "score_fusion"
        
        # 重新排序
        results.sort(key=lambda x: x.final_score, reverse=True)
        return results
    
    def _rrf_rerank(self, results: List[EnhancedSearchResult]) -> List[EnhancedSearchResult]:
        """倒数排名融合重排序"""
        k = 60  # RRF参数
        
        # 按向量分数排序
        vector_ranked = sorted(results, key=lambda x: x.vector_score, reverse=True)
        # 按关键词分数排序
        keyword_ranked = sorted(results, key=lambda x: x.keyword_score, reverse=True)
        
        # 计算RRF分数
        rrf_scores = {}
        
        for rank, result in enumerate(vector_ranked):
            doc_id = result.document.id
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0) + 1 / (k + rank + 1)
        
        for rank, result in enumerate(keyword_ranked):
            doc_id = result.document.id
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0) + 1 / (k + rank + 1)
        
        # 更新最终分数
        for result in results:
            result.final_score = rrf_scores.get(result.document.id, 0)
            result.explanation["reranking"] = "rrf"
        
        # 重新排序
        results.sort(key=lambda x: x.final_score, reverse=True)
        return results
    
    def _weighted_rerank(self, results: List[EnhancedSearchResult], config: SearchConfig) -> List[EnhancedSearchResult]:
        """加权重排序"""
        for result in results:
            result.final_score = (
                result.vector_score * config.vector_weight +
                result.keyword_score * config.keyword_weight
            )
            result.explanation["reranking"] = "weighted"
        
        results.sort(key=lambda x: x.final_score, reverse=True)
        return results
    
    def _apply_diversity_filter(self, results: List[EnhancedSearchResult], 
                               config: SearchConfig) -> List[EnhancedSearchResult]:
        """应用多样性过滤"""
        if not results:
            return results
        
        filtered_results = [results[0]]  # 保留第一个结果
        
        for result in results[1:]:
            # 检查与已选结果的相似度
            is_diverse = True
            
            for selected in filtered_results:
                # 计算文本相似度（简化版）
                similarity = self._calculate_text_similarity(
                    result.document.text, selected.document.text
                )
                
                if similarity > config.diversity_threshold:
                    is_diverse = False
                    break
            
            if is_diverse or len([r for r in filtered_results 
                                if self._calculate_text_similarity(r.document.text, result.document.text) > config.diversity_threshold]) < config.max_similar_results:
                filtered_results.append(result)
        
        return filtered_results
    
    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """计算文本相似度"""
        # 简单的Jaccard相似度
        words1 = set(jieba.lcut(text1))
        words2 = set(jieba.lcut(text2))
        
        intersection = words1 & words2
        union = words1 | words2
        
        if not union:
            return 0.0
        
        return len(intersection) / len(union)
    
    def _apply_filters(self, results: List[EnhancedSearchResult], 
                      filters: Dict[str, Any]) -> List[EnhancedSearchResult]:
        """应用过滤器"""
        filtered_results = []
        
        for result in results:
            if self._match_filters(result.document, filters):
                filtered_results.append(result)
        
        return filtered_results
    
    def _match_filters(self, document: VectorDocument, filters: Dict[str, Any]) -> bool:
        """检查文档是否匹配过滤器"""
        for key, value in filters.items():
            if key not in document.metadata:
                return False
            
            doc_value = document.metadata[key]
            
            if isinstance(value, dict):
                # 范围查询
                if "$gte" in value and doc_value < value["$gte"]:
                    return False
                if "$lte" in value and doc_value > value["$lte"]:
                    return False
                if "$in" in value and doc_value not in value["$in"]:
                    return False
            else:
                # 精确匹配
                if doc_value != value:
                    return False
        
        return True
    
    async def batch_search(self, queries: List[Union[str, SearchQuery]], 
                          config: Optional[SearchConfig] = None) -> List[EnhancedSearchResults]:
        """批量搜索
        
        Args:
            queries: 查询列表
            config: 搜索配置
            
        Returns:
            搜索结果列表
        """
        tasks = [self.search(query, config) for query in queries]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理异常
        final_results = []
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"批量搜索中的查询失败: {str(result)}")
                # 创建空结果
                final_results.append(EnhancedSearchResults(
                    results=[],
                    query=SearchQuery(text=""),
                    config=config or self.config,
                    metrics=SearchMetrics(total_time=0.0),
                    total_results=0
                ))
            else:
                final_results.append(result)
        
        return final_results
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        cache_hit_rate = 0
        if self.stats["total_searches"] > 0:
            cache_hit_rate = self.stats["cache_hits"] / self.stats["total_searches"]
        
        return {
            "total_searches": self.stats["total_searches"],
            "cache_hits": self.stats["cache_hits"],
            "cache_hit_rate": cache_hit_rate,
            "average_search_time": self.stats["average_search_time"],
            "total_search_time": self.stats["total_search_time"],
            "cache_size": len(self.search_cache),
            "tfidf_documents": len(self.document_texts)
        }
    
    def clear_cache(self):
        """清空缓存"""
        self.search_cache.clear()
        logger.info("搜索缓存已清空")
    
    async def update_index(self):
        """更新索引"""
        await self._build_tfidf_index()
        logger.info("搜索索引已更新")


# 预定义配置
DEFAULT_SEARCH_CONFIGS = {
    "vector_only": SearchConfig(
        strategy=SearchStrategy.VECTOR_ONLY,
        top_k=10
    ),
    "keyword_only": SearchConfig(
        strategy=SearchStrategy.KEYWORD_ONLY,
        top_k=10
    ),
    "hybrid_balanced": SearchConfig(
        strategy=SearchStrategy.HYBRID,
        vector_weight=0.5,
        keyword_weight=0.5,
        reranking_strategy=RerankingStrategy.SCORE_FUSION,
        top_k=10
    ),
    "hybrid_vector_heavy": SearchConfig(
        strategy=SearchStrategy.HYBRID,
        vector_weight=0.8,
        keyword_weight=0.2,
        reranking_strategy=RerankingStrategy.RRF,
        top_k=10
    ),
    "semantic_enhanced": SearchConfig(
        strategy=SearchStrategy.SEMANTIC,
        query_expansion_strategy=QueryExpansionStrategy.SYNONYMS,
        reranking_strategy=RerankingStrategy.SCORE_FUSION,
        enable_diversity=True,
        top_k=10
    )
}


def create_similarity_search(embedder: Embedder, vector_store: VectorStore, 
                           config_name: str = "hybrid_balanced", **kwargs) -> SimilaritySearch:
    """创建相似性搜索器
    
    Args:
        embedder: 嵌入器
        vector_store: 向量存储
        config_name: 预定义配置名称
        **kwargs: 额外配置参数
        
    Returns:
        相似性搜索器实例
    """
    if config_name not in DEFAULT_SEARCH_CONFIGS:
        raise ValueError(f"未知配置: {config_name}. 可用配置: {list(DEFAULT_SEARCH_CONFIGS.keys())}")
    
    config = DEFAULT_SEARCH_CONFIGS[config_name]
    
    # 应用额外参数
    for key, value in kwargs.items():
        if hasattr(config, key):
            setattr(config, key, value)
    
    return SimilaritySearch(embedder, vector_store, config)