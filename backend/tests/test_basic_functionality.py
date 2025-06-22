import pytest
import asyncio
from unittest.mock import Mock, patch
from backend.core.vector.embedder import Embedder, EmbeddingConfig, EmbeddingModel, EmbeddingStrategy, TextSplitStrategy


class TestBasicFunctionality:
    """基本功能测试"""
    
    def test_basic_imports(self):
        """测试基本导入"""
        assert Embedder is not None
        assert EmbeddingConfig is not None
        assert EmbeddingModel is not None
        assert EmbeddingStrategy is not None
        assert TextSplitStrategy is not None
    
    def test_embedding_config_creation(self):
        """测试嵌入配置创建"""
        config = EmbeddingConfig(
            model_name="test-model",
            model_type=EmbeddingModel.SENTENCE_TRANSFORMERS,
            dimension=768
        )
        
        assert config.model_name == "test-model"
        assert config.model_type == EmbeddingModel.SENTENCE_TRANSFORMERS
        assert config.dimension == 768
    
    @patch('backend.core.vector.embedder.Embedder._load_model')
    def test_embedder_initialization(self, mock_load_model):
        """测试嵌入器初始化"""
        mock_load_model.return_value = None  # 避免实际加载模型
        
        config = EmbeddingConfig(
            model_name="test-model",
            model_type=EmbeddingModel.SENTENCE_TRANSFORMERS,
            dimension=768
        )
        
        embedder = Embedder(config)
        assert embedder.config == config
        assert embedder.model is None  # 延迟加载
    
    @patch('backend.core.vector.embedder.Embedder._load_model')
    def test_text_preprocessing(self, mock_load_model):
        """测试文本预处理"""
        mock_load_model.return_value = None  # 避免实际加载模型
        
        config = EmbeddingConfig(
            model_name="test-model",
            model_type=EmbeddingModel.SENTENCE_TRANSFORMERS,
            dimension=768,
            lowercase=True,
            remove_special_chars=True
        )
        
        embedder = Embedder(config)
        
        # 测试小写转换
        result = embedder._preprocess_text("Hello World")
        assert result == "hello world"
    
    @patch('backend.core.vector.embedder.Embedder._load_model')
    def test_text_splitting_fixed_size(self, mock_load_model):
        """测试固定大小文本分割"""
        mock_load_model.return_value = None  # 避免实际加载模型
        
        config = EmbeddingConfig(
            model_name="test-model",
            model_type=EmbeddingModel.SENTENCE_TRANSFORMERS,
            dimension=768,
            split_strategy=TextSplitStrategy.FIXED_SIZE,
            chunk_size=100,
            chunk_overlap=20
        )
        
        embedder = Embedder(config)
        text = "这是一个很长的文本。" * 20  # 创建长文本
        
        chunks = embedder._split_text(text)
        
        assert len(chunks) > 1
        for chunk in chunks:
            assert len(chunk) <= config.chunk_size or len(chunk) <= config.min_text_length
    
    @patch('backend.core.vector.embedder.Embedder._load_model')
    def test_cache_key_generation(self, mock_load_model):
        """测试缓存键生成"""
        mock_load_model.return_value = None  # 避免实际加载模型
        
        config = EmbeddingConfig(
            model_name="test-model",
            model_type=EmbeddingModel.SENTENCE_TRANSFORMERS,
            dimension=768
        )
        
        embedder = Embedder(config)
        
        text1 = "测试文本"
        text2 = "测试文本"
        text3 = "不同文本"
        
        key1 = embedder._get_cache_key(text1)
        key2 = embedder._get_cache_key(text2)
        key3 = embedder._get_cache_key(text3)
        
        assert key1 == key2  # 相同文本应该生成相同键
        assert key1 != key3  # 不同文本应该生成不同键
        assert isinstance(key1, str)
    
    @patch('backend.core.vector.embedder.Embedder._load_model')
    def test_statistics_initialization(self, mock_load_model):
        """测试统计信息初始化"""
        mock_load_model.return_value = None  # 避免实际加载模型
        
        config = EmbeddingConfig(
            model_name="test-model",
            model_type=EmbeddingModel.SENTENCE_TRANSFORMERS,
            dimension=768
        )
        
        embedder = Embedder(config)
        stats = embedder.get_statistics()
        
        assert stats["total_embeddings"] == 0
        assert stats["cache_size"] == 0
        assert stats["cache_hit_rate"] == 0
        assert stats["model_name"] == "test-model"
    
    def test_enums_values(self):
        """测试枚举值"""
        # 测试 EmbeddingModel 枚举
        assert EmbeddingModel.SENTENCE_TRANSFORMERS.value == "sentence_transformers"
        assert EmbeddingModel.OPENAI.value == "openai"
        
        # 测试 EmbeddingStrategy 枚举
        assert EmbeddingStrategy.MEAN_POOLING.value == "mean_pooling"
        assert EmbeddingStrategy.CLS_POOLING.value == "cls_pooling"
        
        # 测试 TextSplitStrategy 枚举
        assert TextSplitStrategy.FIXED_SIZE.value == "fixed_size"
        assert TextSplitStrategy.SENTENCE_BASED.value == "sentence_based" 