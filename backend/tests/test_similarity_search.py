"""SimilaritySearch 测试

测试相似性搜索的各种功能，包括不同搜索策略、查询扩展、结果重排序等。
"""

import pytest
import asyncio
import numpy as np
from unittest.mock import Mock, patch, AsyncMock
from typing import List, Dict, Any

from backend.core.vector.similarity_search import (
    SimilaritySearch, SearchStrategy, QueryExpansionStrategy, RerankingStrategy,
    SearchConfig, SearchQuery, SearchMetrics, EnhancedSearchResult,
    create_similarity_search
)
from backend.core.vector.vector_store import (
    VectorStore, VectorDocument, SearchResult, SearchResults,
    VectorStoreConfig, VectorStoreType, DistanceMetric
)
from backend.core.vector.embedder import Embedder, EmbedderConfig, EmbedderType


class TestSearchConfig:
    """SearchConfig 测试类"""
    
    def test_search_config_creation(self):
        """测试搜索配置创建"""
        config = SearchConfig(
            strategy=SearchStrategy.VECTOR,
            k=10,
            score_threshold=0.7,
            query_expansion=QueryExpansionStrategy.SYNONYMS,
            reranking=RerankingStrategy.SCORE_FUSION
        )
        
        assert config.strategy == SearchStrategy.VECTOR
        assert config.k == 10
        assert config.score_threshold == 0.7
        assert config.query_expansion == QueryExpansionStrategy.SYNONYMS
        assert config.reranking == RerankingStrategy.SCORE_FUSION
    
    def test_search_config_defaults(self):
        """测试搜索配置默认值"""
        config = SearchConfig()
        
        assert config.strategy == SearchStrategy.VECTOR
        assert config.k == 10
        assert config.score_threshold == 0.0
        assert config.query_expansion == QueryExpansionStrategy.NONE
        assert config.reranking == RerankingStrategy.NONE
        assert config.diversity_threshold == 0.8
        assert config.max_query_terms == 20
        assert config.enable_caching is True


class TestSearchQuery:
    """SearchQuery 测试类"""
    
    def test_search_query_creation(self):
        """测试搜索查询创建"""
        query = SearchQuery(
            text="机器学习算法",
            vector=np.array([0.1, 0.2, 0.3, 0.4]),
            filters={"category": "AI"},
            boost_fields={"title": 2.0}
        )
        
        assert query.text == "机器学习算法"
        assert np.array_equal(query.vector, np.array([0.1, 0.2, 0.3, 0.4]))
        assert query.filters["category"] == "AI"
        assert query.boost_fields["title"] == 2.0
    
    def test_search_query_to_dict(self):
        """测试搜索查询转换为字典"""
        query = SearchQuery(
            text="测试查询",
            vector=np.array([0.1, 0.2]),
            filters={"type": "document"}
        )
        
        query_dict = query.to_dict()
        
        assert query_dict["text"] == "测试查询"
        assert np.array_equal(query_dict["vector"], np.array([0.1, 0.2]))
        assert query_dict["filters"]["type"] == "document"


class TestEnhancedSearchResult:
    """EnhancedSearchResult 测试类"""
    
    def test_enhanced_search_result_creation(self):
        """测试增强搜索结果创建"""
        doc = VectorDocument(
            id="doc1",
            vector=np.array([0.1, 0.2, 0.3, 0.4]),
            text="测试文档",
            metadata={"category": "test"}
        )
        
        result = EnhancedSearchResult(
            document=doc,
            score=0.95,
            rank=0,
            explanation="高相似度匹配",
            highlights=["测试", "文档"],
            rerank_score=0.92
        )
        
        assert result.document == doc
        assert result.score == 0.95
        assert result.rank == 0
        assert result.explanation == "高相似度匹配"
        assert result.highlights == ["测试", "文档"]
        assert result.rerank_score == 0.92
    
    def test_enhanced_search_result_to_dict(self):
        """测试增强搜索结果转换为字典"""
        doc = VectorDocument(
            id="doc1",
            vector=np.array([0.1, 0.2]),
            text="测试",
            metadata={}
        )
        
        result = EnhancedSearchResult(
            document=doc,
            score=0.8,
            rank=1
        )
        
        result_dict = result.to_dict()
        
        assert result_dict["score"] == 0.8
        assert result_dict["rank"] == 1
        assert "document" in result_dict


class TestSimilaritySearch:
    """SimilaritySearch 测试类"""
    
    @pytest.fixture
    def mock_vector_store(self):
        """模拟向量存储"""
        store = Mock(spec=VectorStore)
        
        # 模拟搜索结果
        doc1 = VectorDocument(
            id="doc1",
            vector=np.array([1.0, 0.0, 0.0, 0.0]),
            text="机器学习是人工智能的一个分支",
            metadata={"category": "AI", "title": "机器学习介绍"}
        )
        doc2 = VectorDocument(
            id="doc2",
            vector=np.array([0.0, 1.0, 0.0, 0.0]),
            text="深度学习是机器学习的子领域",
            metadata={"category": "AI", "title": "深度学习概述"}
        )
        doc3 = VectorDocument(
            id="doc3",
            vector=np.array([0.0, 0.0, 1.0, 0.0]),
            text="自然语言处理技术应用广泛",
            metadata={"category": "NLP", "title": "NLP应用"}
        )
        
        search_results = SearchResults(
            results=[
                SearchResult(document=doc1, score=0.95, rank=0),
                SearchResult(document=doc2, score=0.88, rank=1),
                SearchResult(document=doc3, score=0.75, rank=2)
            ],
            total_results=3,
            query_time=0.05
        )
        
        store.search = AsyncMock(return_value=search_results)
        store.get_statistics = AsyncMock(return_value={"total_documents": 1000})
        
        return store
    
    @pytest.fixture
    def mock_embedder(self):
        """模拟嵌入器"""
        embedder = Mock(spec=Embedder)
        embedder.embed_text = AsyncMock(return_value=np.array([0.5, 0.5, 0.5, 0.5]))
        embedder.embed_batch = AsyncMock(return_value=[
            np.array([0.5, 0.5, 0.5, 0.5]),
            np.array([0.4, 0.6, 0.4, 0.6])
        ])
        return embedder
    
    @pytest.fixture
    def similarity_search(self, mock_vector_store, mock_embedder):
        """创建相似性搜索实例"""
        config = SearchConfig(
            strategy=SearchStrategy.VECTOR,
            k=10,
            score_threshold=0.7
        )
        return SimilaritySearch(mock_vector_store, mock_embedder, config)
    
    @pytest.mark.asyncio
    async def test_vector_search(self, similarity_search, mock_vector_store):
        """测试向量搜索"""
        query = SearchQuery(
            text="机器学习算法",
            filters={"category": "AI"}
        )
        
        results = await similarity_search.search(query)
        
        assert len(results) == 3
        assert all(isinstance(r, EnhancedSearchResult) for r in results)
        assert results[0].score >= results[1].score >= results[2].score
        
        # 验证向量存储被调用
        mock_vector_store.search.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_keyword_search(self, similarity_search):
        """测试关键词搜索"""
        # 更新配置为关键词搜索
        similarity_search.config.strategy = SearchStrategy.KEYWORD
        
        query = SearchQuery(text="机器学习")
        
        with patch.object(similarity_search, '_keyword_search') as mock_keyword:
            mock_keyword.return_value = []
            
            results = await similarity_search.search(query)
            
            mock_keyword.assert_called_once_with(query)
    
    @pytest.mark.asyncio
    async def test_hybrid_search(self, similarity_search):
        """测试混合搜索"""
        # 更新配置为混合搜索
        similarity_search.config.strategy = SearchStrategy.HYBRID
        
        query = SearchQuery(text="机器学习")
        
        with patch.object(similarity_search, '_hybrid_search') as mock_hybrid:
            mock_hybrid.return_value = []
            
            results = await similarity_search.search(query)
            
            mock_hybrid.assert_called_once_with(query)
    
    @pytest.mark.asyncio
    async def test_semantic_search(self, similarity_search):
        """测试语义搜索"""
        # 更新配置为语义搜索
        similarity_search.config.strategy = SearchStrategy.SEMANTIC
        
        query = SearchQuery(text="机器学习")
        
        with patch.object(similarity_search, '_semantic_search') as mock_semantic:
            mock_semantic.return_value = []
            
            results = await similarity_search.search(query)
            
            mock_semantic.assert_called_once_with(query)
    
    @pytest.mark.asyncio
    async def test_fuzzy_search(self, similarity_search):
        """测试模糊搜索"""
        # 更新配置为模糊搜索
        similarity_search.config.strategy = SearchStrategy.FUZZY
        
        query = SearchQuery(text="机器学习")
        
        with patch.object(similarity_search, '_fuzzy_search') as mock_fuzzy:
            mock_fuzzy.return_value = []
            
            results = await similarity_search.search(query)
            
            mock_fuzzy.assert_called_once_with(query)
    
    @pytest.mark.asyncio
    async def test_batch_search(self, similarity_search, mock_embedder):
        """测试批量搜索"""
        queries = [
            SearchQuery(text="机器学习"),
            SearchQuery(text="深度学习")
        ]
        
        results = await similarity_search.batch_search(queries)
        
        assert len(results) == 2
        assert all(isinstance(r, list) for r in results)
        
        # 验证嵌入器被调用
        mock_embedder.embed_batch.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_query_expansion_synonyms(self, similarity_search):
        """测试同义词查询扩展"""
        similarity_search.config.query_expansion = QueryExpansionStrategy.SYNONYMS
        
        query = SearchQuery(text="机器学习")
        
        with patch.object(similarity_search, '_expand_with_synonyms') as mock_expand:
            mock_expand.return_value = ["机器学习", "ML", "人工智能"]
            
            expanded = await similarity_search._expand_query(query)
            
            mock_expand.assert_called_once_with("机器学习")
            assert "ML" in expanded
    
    @pytest.mark.asyncio
    async def test_query_expansion_related_terms(self, similarity_search):
        """测试相关词查询扩展"""
        similarity_search.config.query_expansion = QueryExpansionStrategy.RELATED_TERMS
        
        query = SearchQuery(text="机器学习")
        
        with patch.object(similarity_search, '_expand_with_related_terms') as mock_expand:
            mock_expand.return_value = ["机器学习", "算法", "模型"]
            
            expanded = await similarity_search._expand_query(query)
            
            mock_expand.assert_called_once_with("机器学习")
            assert "算法" in expanded
    
    @pytest.mark.asyncio
    async def test_query_expansion_embeddings(self, similarity_search, mock_embedder):
        """测试嵌入查询扩展"""
        similarity_search.config.query_expansion = QueryExpansionStrategy.EMBEDDINGS
        
        query = SearchQuery(text="机器学习")
        
        with patch.object(similarity_search, '_expand_with_embeddings') as mock_expand:
            mock_expand.return_value = ["机器学习", "深度学习", "神经网络"]
            
            expanded = await similarity_search._expand_query(query)
            
            mock_expand.assert_called_once_with("机器学习")
            assert "深度学习" in expanded
    
    @pytest.mark.asyncio
    async def test_reranking_score_fusion(self, similarity_search):
        """测试分数融合重排序"""
        similarity_search.config.reranking = RerankingStrategy.SCORE_FUSION
        
        # 创建测试结果
        results = [
            EnhancedSearchResult(
                document=VectorDocument(id="doc1", vector=np.array([1, 0]), text="文档1", metadata={}),
                score=0.9, rank=0
            ),
            EnhancedSearchResult(
                document=VectorDocument(id="doc2", vector=np.array([0, 1]), text="文档2", metadata={}),
                score=0.8, rank=1
            )
        ]
        
        reranked = await similarity_search._rerank_results(results, SearchQuery(text="测试"))
        
        assert len(reranked) == 2
        assert all(hasattr(r, 'rerank_score') for r in reranked)
    
    @pytest.mark.asyncio
    async def test_reranking_rrf(self, similarity_search):
        """测试RRF重排序"""
        similarity_search.config.reranking = RerankingStrategy.RRF
        
        results = [
            EnhancedSearchResult(
                document=VectorDocument(id="doc1", vector=np.array([1, 0]), text="文档1", metadata={}),
                score=0.9, rank=0
            ),
            EnhancedSearchResult(
                document=VectorDocument(id="doc2", vector=np.array([0, 1]), text="文档2", metadata={}),
                score=0.8, rank=1
            )
        ]
        
        reranked = await similarity_search._rerank_results(results, SearchQuery(text="测试"))
        
        assert len(reranked) == 2
        # RRF应该重新计算排名
        assert reranked[0].rank == 0
        assert reranked[1].rank == 1
    
    @pytest.mark.asyncio
    async def test_reranking_weighted(self, similarity_search):
        """测试加权重排序"""
        similarity_search.config.reranking = RerankingStrategy.WEIGHTED
        similarity_search.config.reranking_weights = {
            "vector_score": 0.7,
            "keyword_score": 0.3
        }
        
        results = [
            EnhancedSearchResult(
                document=VectorDocument(id="doc1", vector=np.array([1, 0]), text="文档1", metadata={}),
                score=0.9, rank=0
            )
        ]
        
        reranked = await similarity_search._rerank_results(results, SearchQuery(text="测试"))
        
        assert len(reranked) == 1
        assert hasattr(reranked[0], 'rerank_score')
    
    @pytest.mark.asyncio
    async def test_diversity_filtering(self, similarity_search):
        """测试多样性过滤"""
        similarity_search.config.enable_diversity = True
        similarity_search.config.diversity_threshold = 0.8
        
        # 创建相似的文档
        results = [
            EnhancedSearchResult(
                document=VectorDocument(id="doc1", vector=np.array([1.0, 0.0]), text="机器学习算法", metadata={}),
                score=0.95, rank=0
            ),
            EnhancedSearchResult(
                document=VectorDocument(id="doc2", vector=np.array([0.9, 0.1]), text="机器学习方法", metadata={}),
                score=0.90, rank=1
            ),
            EnhancedSearchResult(
                document=VectorDocument(id="doc3", vector=np.array([0.0, 1.0]), text="自然语言处理", metadata={}),
                score=0.85, rank=2
            )
        ]
        
        filtered = await similarity_search._apply_diversity_filter(results)
        
        # 应该过滤掉相似的文档
        assert len(filtered) < len(results)
    
    @pytest.mark.asyncio
    async def test_score_threshold_filtering(self, similarity_search):
        """测试分数阈值过滤"""
        similarity_search.config.score_threshold = 0.8
        
        query = SearchQuery(text="机器学习")
        results = await similarity_search.search(query)
        
        # 所有结果的分数都应该高于阈值
        assert all(r.score >= 0.8 for r in results)
    
    @pytest.mark.asyncio
    async def test_get_statistics(self, similarity_search):
        """测试获取统计信息"""
        # 执行一些搜索以生成统计信息
        query = SearchQuery(text="测试")
        await similarity_search.search(query)
        await similarity_search.search(query)
        
        stats = await similarity_search.get_statistics()
        
        assert "total_searches" in stats
        assert "average_query_time" in stats
        assert "cache_hit_rate" in stats
        assert stats["total_searches"] == 2
    
    @pytest.mark.asyncio
    async def test_clear_cache(self, similarity_search):
        """测试清空缓存"""
        # 执行搜索以填充缓存
        query = SearchQuery(text="测试")
        await similarity_search.search(query)
        
        # 清空缓存
        await similarity_search.clear_cache()
        
        # 验证缓存被清空
        assert len(similarity_search.cache) == 0
    
    @pytest.mark.asyncio
    async def test_update_index(self, similarity_search, mock_vector_store):
        """测试更新索引"""
        await similarity_search.update_index()
        
        # 验证向量存储的统计信息被更新
        mock_vector_store.get_statistics.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_caching_enabled(self, similarity_search):
        """测试启用缓存"""
        similarity_search.config.enable_caching = True
        
        query = SearchQuery(text="机器学习")
        
        # 第一次搜索
        results1 = await similarity_search.search(query)
        
        # 第二次搜索（应该使用缓存）
        results2 = await similarity_search.search(query)
        
        # 结果应该相同
        assert len(results1) == len(results2)
        assert results1[0].document.id == results2[0].document.id
    
    @pytest.mark.asyncio
    async def test_caching_disabled(self, similarity_search, mock_vector_store):
        """测试禁用缓存"""
        similarity_search.config.enable_caching = False
        
        query = SearchQuery(text="机器学习")
        
        # 执行两次搜索
        await similarity_search.search(query)
        await similarity_search.search(query)
        
        # 向量存储应该被调用两次
        assert mock_vector_store.search.call_count == 2
    
    def test_calculate_similarity(self, similarity_search):
        """测试计算相似度"""
        vec1 = np.array([1.0, 0.0, 0.0, 0.0])
        vec2 = np.array([0.0, 1.0, 0.0, 0.0])
        
        # 余弦相似度
        similarity = similarity_search._calculate_similarity(vec1, vec2, "cosine")
        assert abs(similarity - 0.0) < 1e-6  # 垂直向量的余弦相似度为0
        
        # 点积相似度
        similarity = similarity_search._calculate_similarity(vec1, vec2, "dot")
        assert abs(similarity - 0.0) < 1e-6
        
        # 欧几里得相似度
        similarity = similarity_search._calculate_similarity(vec1, vec2, "euclidean")
        assert similarity > 0  # 距离越小，相似度越高
    
    def test_extract_keywords(self, similarity_search):
        """测试提取关键词"""
        text = "机器学习是人工智能的一个重要分支，包括监督学习和无监督学习"
        
        keywords = similarity_search._extract_keywords(text)
        
        assert isinstance(keywords, list)
        assert len(keywords) > 0
        assert "机器学习" in keywords or "人工智能" in keywords
    
    def test_calculate_keyword_score(self, similarity_search):
        """测试计算关键词分数"""
        query_keywords = ["机器学习", "算法"]
        document_text = "机器学习算法在人工智能中应用广泛"
        
        score = similarity_search._calculate_keyword_score(query_keywords, document_text)
        
        assert 0 <= score <= 1
        assert score > 0  # 应该有匹配的关键词
    
    def test_highlight_text(self, similarity_search):
        """测试文本高亮"""
        text = "机器学习是人工智能的重要分支"
        keywords = ["机器学习", "人工智能"]
        
        highlights = similarity_search._highlight_text(text, keywords)
        
        assert isinstance(highlights, list)
        assert len(highlights) > 0
        assert any("机器学习" in h for h in highlights)


class TestSimilaritySearchFactory:
    """相似性搜索工厂测试类"""
    
    @pytest.mark.asyncio
    async def test_create_similarity_search(self):
        """测试创建相似性搜索实例"""
        with patch('backend.core.vector.vector_store.create_default_vector_store') as mock_store:
            with patch('backend.core.vector.embedder.create_embedder') as mock_embedder:
                mock_store.return_value = Mock(spec=VectorStore)
                mock_embedder.return_value = Mock(spec=Embedder)
                
                search = await create_similarity_search(
                    dimension=128,
                    strategy=SearchStrategy.HYBRID
                )
                
                assert isinstance(search, SimilaritySearch)
                assert search.config.strategy == SearchStrategy.HYBRID
                
                mock_store.assert_called_once_with(dimension=128)
                mock_embedder.assert_called_once()


class TestSimilaritySearchPerformance:
    """相似性搜索性能测试类"""
    
    @pytest.fixture
    def large_vector_store(self):
        """大型向量存储模拟"""
        store = Mock(spec=VectorStore)
        
        # 模拟大量搜索结果
        documents = []
        for i in range(1000):
            doc = VectorDocument(
                id=f"doc_{i}",
                vector=np.random.rand(128).astype(np.float32),
                text=f"文档 {i} 的内容，包含各种关键词",
                metadata={"index": i, "category": f"cat_{i % 10}"}
            )
            documents.append(doc)
        
        search_results = SearchResults(
            results=[
                SearchResult(document=doc, score=np.random.rand(), rank=i)
                for i, doc in enumerate(documents[:100])  # 返回前100个结果
            ],
            total_results=1000,
            query_time=0.1
        )
        
        store.search = AsyncMock(return_value=search_results)
        store.get_statistics = AsyncMock(return_value={"total_documents": 10000})
        
        return store
    
    @pytest.mark.asyncio
    async def test_large_scale_search_performance(self, large_vector_store, mock_embedder):
        """测试大规模搜索性能"""
        config = SearchConfig(
            strategy=SearchStrategy.VECTOR,
            k=100,
            enable_caching=True
        )
        
        search = SimilaritySearch(large_vector_store, mock_embedder, config)
        
        import time
        start_time = time.time()
        
        # 执行多次搜索
        for i in range(50):
            query = SearchQuery(text=f"查询 {i}")
            results = await search.search(query)
            assert len(results) <= 100
        
        end_time = time.time()
        search_time = end_time - start_time
        
        assert search_time < 10.0  # 50次搜索应该在10秒内完成
        
        print(f"50次大规模搜索耗时: {search_time:.3f}秒")
    
    @pytest.mark.asyncio
    async def test_concurrent_search_performance(self, large_vector_store, mock_embedder):
        """测试并发搜索性能"""
        config = SearchConfig(
            strategy=SearchStrategy.VECTOR,
            k=50,
            enable_caching=True
        )
        
        search = SimilaritySearch(large_vector_store, mock_embedder, config)
        
        async def search_task(query_id):
            query = SearchQuery(text=f"并发查询 {query_id}")
            return await search.search(query)
        
        import time
        start_time = time.time()
        
        # 并发执行搜索
        tasks = [search_task(i) for i in range(20)]
        results = await asyncio.gather(*tasks)
        
        end_time = time.time()
        search_time = end_time - start_time
        
        assert len(results) == 20
        assert all(len(r) <= 50 for r in results)
        assert search_time < 5.0  # 20个并发搜索应该在5秒内完成
        
        print(f"20个并发搜索耗时: {search_time:.3f}秒")


class TestSimilaritySearchErrorHandling:
    """相似性搜索错误处理测试类"""
    
    @pytest.mark.asyncio
    async def test_empty_query(self, similarity_search):
        """测试空查询"""
        query = SearchQuery(text="")
        
        results = await similarity_search.search(query)
        
        # 空查询应该返回空结果
        assert len(results) == 0
    
    @pytest.mark.asyncio
    async def test_none_query(self, similarity_search):
        """测试None查询"""
        query = SearchQuery(text=None)
        
        with pytest.raises(ValueError, match="查询文本不能为空"):
            await similarity_search.search(query)
    
    @pytest.mark.asyncio
    async def test_vector_store_error(self, mock_embedder):
        """测试向量存储错误"""
        # 创建会抛出异常的向量存储
        error_store = Mock(spec=VectorStore)
        error_store.search = AsyncMock(side_effect=Exception("向量存储错误"))
        
        config = SearchConfig()
        search = SimilaritySearch(error_store, mock_embedder, config)
        
        query = SearchQuery(text="测试查询")
        
        with pytest.raises(Exception, match="向量存储错误"):
            await search.search(query)
    
    @pytest.mark.asyncio
    async def test_embedder_error(self, mock_vector_store):
        """测试嵌入器错误"""
        # 创建会抛出异常的嵌入器
        error_embedder = Mock(spec=Embedder)
        error_embedder.embed_text = AsyncMock(side_effect=Exception("嵌入错误"))
        
        config = SearchConfig()
        search = SimilaritySearch(mock_vector_store, error_embedder, config)
        
        query = SearchQuery(text="测试查询")
        
        with pytest.raises(Exception, match="嵌入错误"):
            await search.search(query)
    
    @pytest.mark.asyncio
    async def test_invalid_search_strategy(self, similarity_search):
        """测试无效搜索策略"""
        similarity_search.config.strategy = "invalid_strategy"
        
        query = SearchQuery(text="测试查询")
        
        with pytest.raises(ValueError, match="不支持的搜索策略"):
            await similarity_search.search(query)
    
    @pytest.mark.asyncio
    async def test_invalid_k_value(self, similarity_search):
        """测试无效k值"""
        query = SearchQuery(text="测试查询")
        
        # k值为0
        with pytest.raises(ValueError, match="k值必须大于0"):
            await similarity_search.search(query, k=0)
        
        # k值为负数
        with pytest.raises(ValueError, match="k值必须大于0"):
            await similarity_search.search(query, k=-1)


if __name__ == "__main__":
    pytest.main([__file__])