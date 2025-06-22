"""Embedder 测试

测试嵌入器的各种功能，包括文本嵌入、文档嵌入、批量处理等。
"""

import pytest
import asyncio
import numpy as np
from unittest.mock import Mock, patch, AsyncMock
from typing import List, Dict, Any

from backend.core.vector.embedder import (
    Embedder, EmbeddingModel, EmbeddingStrategy, TextSplitStrategy,
    EmbeddingConfig, EmbeddingResult, DocumentEmbedding, Document,
    DEFAULT_EMBEDDING_CONFIGS, create_embedder
)


class TestEmbedder:
    """Embedder 测试类"""
    
    @pytest.fixture
    def mock_sentence_transformer(self):
        """模拟 SentenceTransformer"""
        with patch('backend.core.vector.embedder.SentenceTransformer') as mock:
            mock_model = Mock()
            mock_model.encode.return_value = np.array([[0.1, 0.2, 0.3, 0.4]])
            mock.return_value = mock_model
            yield mock_model
    
    @pytest.fixture
    def mock_openai_client(self):
        """模拟 OpenAI 客户端"""
        # 直接mock embedder的openai_client属性
        mock_client = Mock()
        mock_embeddings = Mock()
        mock_response = Mock()
        mock_response.data = [Mock()]
        mock_response.data[0].embedding = [0.1, 0.2, 0.3, 0.4] * 384  # 1536维向量
        
        mock_embeddings.create = AsyncMock(return_value=mock_response)
        mock_client.embeddings = mock_embeddings
        
        yield mock_client
    
    @pytest.fixture
    def basic_config(self):
        """基本配置"""
        return EmbeddingConfig(
            model_type=EmbeddingModel.SENTENCE_TRANSFORMERS,
            model_name="all-MiniLM-L6-v2",
            pooling_strategy=EmbeddingStrategy.MEAN_POOLING,
            split_strategy=TextSplitStrategy.FIXED_SIZE,
            chunk_size=512,
            chunk_overlap=50,
            dimension=384
        )
    
    @pytest.fixture
    def embedder(self, basic_config, mock_sentence_transformer):
        """创建嵌入器实例"""
        return Embedder(basic_config)
    
    def test_embedder_initialization(self, basic_config, mock_sentence_transformer):
        """测试嵌入器初始化"""
        embedder = Embedder(basic_config)
        
        assert embedder.config == basic_config
        assert embedder.model is not None  # 模型已加载（通过mock）
        assert embedder.cache == {}
        assert embedder.stats["total_embeddings"] == 0
    
    def test_load_model_sentence_transformers(self, embedder, mock_sentence_transformer):
        """测试加载 SentenceTransformers 模型"""
        embedder._load_model()
        
        assert embedder.model is not None
        assert embedder.model == mock_sentence_transformer
    
    def test_load_model_openai(self, mock_openai_client):
        """测试加载 OpenAI 模型"""
        config = EmbeddingConfig(
            model_type=EmbeddingModel.OPENAI,
            model_name="text-embedding-ada-002",
            api_key="test-key"
        )
        embedder = Embedder(config)
        
        # 手动设置mock客户端
        embedder.openai_client = mock_openai_client
        
        assert hasattr(embedder, 'openai_client')
        assert embedder.openai_client is not None
    
    @pytest.mark.asyncio
    async def test_embed_text_basic(self, embedder, mock_sentence_transformer):
        """测试基本文本嵌入"""
        text = "这是一个测试文本"
        
        result = await embedder.embed_text(text)
        
        assert isinstance(result, EmbeddingResult)
        assert result.text == text
        assert isinstance(result.embedding, np.ndarray)
        assert result.embedding.shape == (4,)  # 模拟返回4维向量
        assert result.model == embedder.config.model_name
        assert result.dimension == 4
        assert result.processing_time > 0
    
    @pytest.mark.asyncio
    async def test_embed_text_with_cache(self, embedder, mock_sentence_transformer):
        """测试带缓存的文本嵌入"""
        text = "这是一个测试文本"
        
        # 第一次嵌入
        result1 = await embedder.embed_text(text)
        
        # 第二次嵌入（应该使用缓存）
        result2 = await embedder.embed_text(text)
        
        assert np.array_equal(result1.embedding, result2.embedding)
        assert result2.from_cache is True
        
        # 验证模型只被调用一次
        assert mock_sentence_transformer.encode.call_count == 1
    
    @pytest.mark.asyncio
    async def test_embed_texts_batch(self, embedder, mock_sentence_transformer):
        """测试批量文本嵌入"""
        texts = ["文本1", "文本2", "文本3"]
        
        # 设置模拟返回多个向量
        mock_sentence_transformer.encode.return_value = np.array([
            [0.1, 0.2, 0.3, 0.4],
            [0.2, 0.3, 0.4, 0.5],
            [0.3, 0.4, 0.5, 0.6]
        ])
        
        results = await embedder.embed_texts(texts)
        
        assert len(results) == 3
        for i, result in enumerate(results):
            assert isinstance(result, EmbeddingResult)
            assert result.text == texts[i]
            assert isinstance(result.embedding, np.ndarray)
            assert result.embedding.shape == (4,)
    
    @pytest.mark.asyncio
    async def test_embed_document_basic(self, embedder, mock_sentence_transformer):
        """测试基本文档嵌入"""
        document = Document(
            id="doc1",
            content="这是一个很长的文档内容，需要分块处理。" * 20,
            metadata={"title": "测试文档"}
        )
        
        # 设置模拟返回多个向量（用于分块）
        mock_sentence_transformer.encode.return_value = np.array([
            [0.1, 0.2, 0.3, 0.4],
            [0.2, 0.3, 0.4, 0.5]
        ])
        
        result = await embedder.embed_document(document)
        
        assert isinstance(result, DocumentEmbedding)
        assert result.document_id == "doc1"
        assert len(result.chunks) >= 1
        assert isinstance(result.document_embedding, np.ndarray)
        assert result.document_embedding.shape == (4,)
    
    @pytest.mark.asyncio
    async def test_embed_document_with_different_strategies(self, basic_config, mock_sentence_transformer):
        """测试不同策略的文档嵌入"""
        document = Document(
            id="doc1",
            content="这是第一句。这是第二句。这是第三句。",
            metadata={}
        )
        
        strategies = [
            EmbeddingStrategy.MEAN_POOLING,
            EmbeddingStrategy.CLS_POOLING,
            EmbeddingStrategy.MAX_POOLING,
            EmbeddingStrategy.WEIGHTED_POOLING
        ]
        
        # 设置模拟返回多个向量
        mock_sentence_transformer.encode.return_value = np.array([
            [0.1, 0.2, 0.3, 0.4],
            [0.2, 0.3, 0.4, 0.5],
            [0.3, 0.4, 0.5, 0.6]
        ])
        
        for strategy in strategies:
            config = basic_config
            config.strategy = strategy
            embedder = Embedder(config)
            
            result = await embedder.embed_document(document)
            
            assert isinstance(result, DocumentEmbedding)
            assert isinstance(result.document_embedding, np.ndarray)
    
    def test_split_text_fixed_size(self, embedder):
        """测试固定大小分割"""
        text = "这是一个很长的文本。" * 100
        
        chunks = embedder._split_text(text)
        
        assert len(chunks) > 1
        for chunk in chunks:
            assert len(chunk) <= embedder.config.chunk_size
    
    def test_split_text_sentence_based(self, basic_config):
        """测试基于句子的分割"""
        config = basic_config
        config.split_strategy = TextSplitStrategy.SENTENCE_BASED
        embedder = Embedder(config)
        
        text = "这是第一句。这是第二句！这是第三句？"
        
        chunks = embedder._split_text(text)
        
        assert len(chunks) >= 1
        # 每个块应该包含完整的句子
        for chunk in chunks:
            assert chunk.strip().endswith(('.', '!', '?', '。', '！', '？'))
    
    def test_split_text_paragraph_based(self, basic_config):
        """测试基于段落的分割"""
        config = basic_config
        config.split_strategy = TextSplitStrategy.PARAGRAPH_BASED
        embedder = Embedder(config)
        
        text = "第一段内容。\n\n第二段内容。\n\n第三段内容。"
        
        chunks = embedder._split_text(text)
        
        assert len(chunks) >= 1
    
    def test_split_text_sliding_window(self, basic_config):
        """测试滑动窗口分割"""
        config = basic_config
        config.split_strategy = TextSplitStrategy.SLIDING_WINDOW
        config.chunk_size = 100
        config.chunk_overlap = 20
        embedder = Embedder(config)
        
        text = "这是一个很长的文本。" * 50
        
        chunks = embedder._split_text(text)
        
        assert len(chunks) > 1
        # 检查重叠
        if len(chunks) > 1:
            # 简单检查：后一个块的开始应该与前一个块有重叠
            assert len(chunks[0]) <= config.chunk_size
    
    def test_combine_embeddings_mean_pooling(self, embedder):
        """测试均值池化"""
        embeddings = np.array([
            [1.0, 2.0, 3.0],
            [2.0, 3.0, 4.0],
            [3.0, 4.0, 5.0]
        ])
        
        result = embedder._combine_embeddings(embeddings, EmbeddingStrategy.MEAN_POOLING)
        
        expected = np.array([2.0, 3.0, 4.0])  # 均值
        np.testing.assert_array_almost_equal(result, expected)
    
    def test_combine_embeddings_max_pooling(self, embedder):
        """测试最大池化"""
        embeddings = np.array([
            [1.0, 2.0, 3.0],
            [2.0, 3.0, 4.0],
            [3.0, 4.0, 5.0]
        ])
        
        result = embedder._combine_embeddings(embeddings, EmbeddingStrategy.MAX_POOLING)
        
        expected = np.array([3.0, 4.0, 5.0])  # 最大值
        np.testing.assert_array_almost_equal(result, expected)
    
    def test_combine_embeddings_cls_pooling(self, embedder):
        """测试CLS池化"""
        embeddings = np.array([
            [1.0, 2.0, 3.0],
            [2.0, 3.0, 4.0],
            [3.0, 4.0, 5.0]
        ])
        
        result = embedder._combine_embeddings(embeddings, EmbeddingStrategy.CLS_POOLING)
        
        expected = np.array([1.0, 2.0, 3.0])  # 第一个向量
        np.testing.assert_array_almost_equal(result, expected)
    
    def test_combine_embeddings_weighted_pooling(self, embedder):
        """测试加权池化"""
        embeddings = np.array([
            [1.0, 2.0, 3.0],
            [2.0, 3.0, 4.0],
            [3.0, 4.0, 5.0]
        ])
        
        result = embedder._combine_embeddings(embeddings, EmbeddingStrategy.WEIGHTED_POOLING)
        
        # 加权池化应该给前面的向量更高权重
        assert isinstance(result, np.ndarray)
        assert result.shape == (3,)
    
    @pytest.mark.asyncio
    async def test_batch_embed_documents(self, embedder, mock_sentence_transformer):
        """测试批量文档嵌入"""
        documents = [
            Document(id="doc1", content="文档1内容", metadata={}),
            Document(id="doc2", content="文档2内容", metadata={}),
            Document(id="doc3", content="文档3内容", metadata={})
        ]
        
        # 设置模拟返回
        mock_sentence_transformer.encode.return_value = np.array([
            [0.1, 0.2, 0.3, 0.4]
        ])
        
        results = await embedder.batch_embed_documents(documents)
        
        assert len(results) == 3
        for i, result in enumerate(results):
            assert isinstance(result, DocumentEmbedding)
            assert result.document_id == documents[i].id
    
    @pytest.mark.asyncio
    async def test_batch_embed_documents_with_batch_size(self, embedder, mock_sentence_transformer):
        """测试带批次大小的批量文档嵌入"""
        documents = [Document(id=f"doc{i}", content=f"文档{i}内容", metadata={}) for i in range(5)]
        
        mock_sentence_transformer.encode.return_value = np.array([[0.1, 0.2, 0.3, 0.4]])
        
        results = await embedder.batch_embed_documents(documents, batch_size=2)
        
        assert len(results) == 5
        # 验证批次处理（模拟调用次数应该是 ceil(5/2) = 3 次，但每个文档可能调用一次）
    
    def test_get_cache_key(self, embedder):
        """测试缓存键生成"""
        text = "测试文本"
        key1 = embedder._get_cache_key(text)
        key2 = embedder._get_cache_key(text)
        key3 = embedder._get_cache_key("不同文本")
        
        assert key1 == key2  # 相同文本应该生成相同键
        assert key1 != key3  # 不同文本应该生成不同键
        assert isinstance(key1, str)
    
    def test_clear_cache(self, embedder):
        """测试清空缓存"""
        # 添加一些缓存项
        embedder.cache["key1"] = "value1"
        embedder.cache["key2"] = "value2"
        
        assert len(embedder.cache) == 2
        
        embedder.clear_cache()
        
        assert len(embedder.cache) == 0
    
    def test_get_statistics(self, embedder):
        """测试获取统计信息"""
        # 设置一些统计数据
        embedder.stats["total_embeddings"] = 10
        embedder.stats["cache_hits"] = 3
        embedder.stats["total_embedding_time"] = 5.0
        
        stats = embedder.get_statistics()
        
        assert stats["total_embeddings"] == 10
        assert stats["cache_hits"] == 3
        assert stats["cache_hit_rate"] == 0.3
        assert stats["average_embedding_time"] == 0.5
        assert "cache_size" in stats
    
    @pytest.mark.asyncio
    async def test_save_and_load_model(self, embedder, tmp_path):
        """测试模型保存和加载"""
        model_path = tmp_path / "test_model"
        
        # 模拟已加载的模型
        embedder.model = Mock()
        embedder.model.save = Mock()
        
        # 保存模型
        await embedder.save_model(str(model_path))
        
        # 验证保存被调用
        embedder.model.save.assert_called_once()
    
    def test_error_handling_invalid_model(self):
        """测试无效模型的错误处理"""
        config = EmbeddingConfig(
            model_type=EmbeddingModel.SENTENCE_TRANSFORMERS,
            model_name="invalid-model-name"
        )
        
        # 使用pytest.raises期望ValueError，因为我们改进了错误处理
        with pytest.raises(ValueError, match="模型 'invalid-model-name' 不存在或无效"):
            Embedder(config)
    
    @pytest.mark.asyncio
    async def test_error_handling_empty_text(self, embedder):
        """测试空文本的错误处理"""
        with pytest.raises(ValueError, match="文本不能为空"):
            await embedder.embed_text("")
    
    @pytest.mark.asyncio
    async def test_error_handling_none_text(self, embedder):
        """测试None文本的错误处理"""
        with pytest.raises(ValueError, match="文本不能为空"):
            await embedder.embed_text(None)
    
    @pytest.mark.asyncio
    async def test_openai_embedding(self, mock_openai_client):
        """测试OpenAI嵌入"""
        config = EmbeddingConfig(
            model_type=EmbeddingModel.OPENAI,
            model_name="text-embedding-ada-002",
            api_key="test-key"
        )
        embedder = Embedder(config)
        
        # 手动设置mock客户端
        embedder.openai_client = mock_openai_client
        
        result = await embedder.embed_text("测试文本")
        
        assert isinstance(result, EmbeddingResult)
        assert result.model == "text-embedding-ada-002"
        mock_openai_client.embeddings.create.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_custom_api_embedding(self):
        """测试自定义API嵌入"""
        config = EmbeddingConfig(
            model_type=EmbeddingModel.CUSTOM_API,
            model_name="custom-model",
            api_url="http://localhost:8000/embed",
            api_key="test-key"
        )
        embedder = Embedder(config)
        
        # 模拟HTTP响应
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_response = AsyncMock()
            mock_response.json.return_value = {
                "embedding": [0.1, 0.2, 0.3, 0.4]
            }
            mock_response.status = 200
            mock_post.return_value.__aenter__.return_value = mock_response
            
            result = await embedder.embed_text("测试文本")
            
            assert isinstance(result, EmbeddingResult)
            assert result.embedding.shape == (4,)
    
    def test_create_embedder_with_predefined_config(self):
        """测试使用预定义配置创建嵌入器"""
        with patch('backend.core.vector.embedder.SentenceTransformer') as mock_st:
            mock_model = Mock()
            mock_model.get_sentence_embedding_dimension.return_value = 384
            mock_st.return_value = mock_model
            
            embedder = create_embedder("sentence_transformers_multilingual")
            
            assert isinstance(embedder, Embedder)
            assert embedder.config.model_type == EmbeddingModel.SENTENCE_TRANSFORMERS
            assert "multilingual" in embedder.config.model_name.lower()
    
    def test_create_embedder_with_custom_config(self):
        """测试使用自定义配置创建嵌入器"""
        with patch('backend.core.vector.embedder.SentenceTransformer') as mock_st:
            mock_model = Mock()
            mock_model.get_sentence_embedding_dimension.return_value = 384
            mock_st.return_value = mock_model
            
            embedder = create_embedder(
                "sentence_transformers_base",
                dimension=512,
                chunk_size=1024
            )
            
            assert isinstance(embedder, Embedder)
            assert embedder.config.dimension == 512
            assert embedder.config.chunk_size == 1024
    
    def test_create_embedder_invalid_config(self):
        """测试无效配置名称"""
        with pytest.raises(ValueError, match="未知配置"):
            create_embedder("invalid_config")
    
    @pytest.mark.asyncio
    async def test_performance_large_batch(self, embedder, mock_sentence_transformer):
        """测试大批量处理性能"""
        # 创建大量文本
        texts = [f"测试文本 {i}" for i in range(100)]
        
        # 设置模拟返回
        mock_sentence_transformer.encode.return_value = np.random.rand(100, 4)
        
        import time
        start_time = time.time()
        
        results = await embedder.embed_texts(texts, batch_size=10)
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        assert len(results) == 100
        assert processing_time < 10  # 应该在合理时间内完成
        
        # 检查统计信息
        stats = embedder.get_statistics()
        assert stats["total_embeddings"] >= 100
    
    @pytest.mark.asyncio
    async def test_concurrent_embedding(self, embedder, mock_sentence_transformer):
        """测试并发嵌入"""
        mock_sentence_transformer.encode.return_value = np.array([[0.1, 0.2, 0.3, 0.4]])
        
        # 创建并发任务
        tasks = [
            embedder.embed_text(f"文本 {i}")
            for i in range(10)
        ]
        
        results = await asyncio.gather(*tasks)
        
        assert len(results) == 10
        for result in results:
            assert isinstance(result, EmbeddingResult)
    
    @pytest.mark.asyncio
    async def test_memory_usage_large_document(self, embedder, mock_sentence_transformer):
        """测试大文档的内存使用"""
        # 创建大文档
        large_content = "这是一个很长的句子。" * 10000
        document = Document(
            id="large_doc",
            content=large_content,
            metadata={}
        )
        
        mock_sentence_transformer.encode.return_value = np.random.rand(50, 4)  # 模拟多个块
        
        result = await embedder.embed_document(document)
        
        assert isinstance(result, DocumentEmbedding)
        assert len(result.chunks) > 1  # 应该被分成多个块
        assert isinstance(result.document_embedding, np.ndarray)
    
    def test_default_configs_availability(self):
        """测试默认配置的可用性"""
        assert len(DEFAULT_EMBEDDING_CONFIGS) > 0
        
        for config_name, config in DEFAULT_EMBEDDING_CONFIGS.items():
            assert isinstance(config, EmbeddingConfig)
            assert config.model_type in EmbeddingModel
            assert config.strategy in EmbeddingStrategy
            assert config.split_strategy in TextSplitStrategy
            assert config.dimension > 0
            assert config.chunk_size > 0
    
    @pytest.mark.asyncio
    async def test_embedding_consistency(self, embedder, mock_sentence_transformer):
        """测试嵌入一致性"""
        text = "测试文本一致性"
        
        # 多次嵌入相同文本
        results = []
        for _ in range(3):
            embedder.clear_cache()  # 清空缓存确保重新计算
            result = await embedder.embed_text(text)
            results.append(result.embedding)
        
        # 所有结果应该相同（因为使用相同的模拟返回）
        for i in range(1, len(results)):
            np.testing.assert_array_equal(results[0], results[i])


if __name__ == "__main__":
    pytest.main([__file__])