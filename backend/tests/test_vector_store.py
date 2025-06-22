"""VectorStore 测试

测试向量存储的各种功能，包括插入、搜索、删除、更新等操作。
"""

import pytest
import asyncio
import numpy as np
import tempfile
import shutil
from unittest.mock import Mock, patch, MagicMock
from typing import List, Dict, Any

from backend.core.vector.vector_store import (
    VectorStore, FaissVectorStore, ChromaVectorStore, MemoryVectorStore,
    VectorStoreType, IndexType, DistanceMetric,
    VectorStoreConfig, VectorDocument, SearchResult, SearchResults,
    create_vector_store, create_default_vector_store
)


class TestVectorDocument:
    """VectorDocument 测试类"""
    
    def test_vector_document_creation(self):
        """测试向量文档创建"""
        vector = np.array([0.1, 0.2, 0.3, 0.4])
        doc = VectorDocument(
            id="doc1",
            vector=vector,
            text="测试文档",
            metadata={"category": "test"}
        )
        
        assert doc.id == "doc1"
        assert np.array_equal(doc.vector, vector)
        assert doc.text == "测试文档"
        assert doc.metadata["category"] == "test"
    
    def test_vector_document_to_dict(self):
        """测试向量文档转换为字典"""
        vector = np.array([0.1, 0.2, 0.3, 0.4])
        doc = VectorDocument(
            id="doc1",
            vector=vector,
            text="测试文档",
            metadata={"category": "test"}
        )
        
        doc_dict = doc.to_dict()
        
        assert doc_dict["id"] == "doc1"
        assert np.array_equal(doc_dict["vector"], vector)
        assert doc_dict["text"] == "测试文档"
        assert doc_dict["metadata"]["category"] == "test"
    
    def test_vector_document_from_dict(self):
        """测试从字典创建向量文档"""
        from datetime import datetime
        doc_dict = {
            "id": "doc1",
            "vector": [0.1, 0.2, 0.3, 0.4],
            "text": "测试文档",
            "metadata": {"category": "test"},
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        doc = VectorDocument.from_dict(doc_dict)
        
        assert doc.id == "doc1"
        assert np.array_equal(doc.vector, np.array([0.1, 0.2, 0.3, 0.4]))
        assert doc.text == "测试文档"
        assert doc.metadata["category"] == "test"


class TestSearchResult:
    """SearchResult 测试类"""
    
    def test_search_result_creation(self):
        """测试搜索结果创建"""
        vector = np.array([0.1, 0.2, 0.3, 0.4])
        doc = VectorDocument(
            id="doc1",
            vector=vector,
            text="测试文档",
            metadata={}
        )
        
        result = SearchResult(
            document=doc,
            score=0.95,
            rank=0
        )
        
        assert result.document == doc
        assert result.score == 0.95
        assert result.rank == 0
    
    def test_search_result_to_dict(self):
        """测试搜索结果转换为字典"""
        vector = np.array([0.1, 0.2, 0.3, 0.4])
        doc = VectorDocument(
            id="doc1",
            vector=vector,
            text="测试文档",
            metadata={}
        )
        
        result = SearchResult(
            document=doc,
            score=0.95,
            rank=0
        )
        
        result_dict = result.to_dict()
        
        assert result_dict["score"] == 0.95
        assert result_dict["rank"] == 0
        assert "document" in result_dict


class TestMemoryVectorStore:
    """MemoryVectorStore 测试类"""
    
    @pytest.fixture
    def config(self):
        """基本配置"""
        return VectorStoreConfig(
            store_type=VectorStoreType.MEMORY,
            dimension=4,
            distance_metric=DistanceMetric.COSINE
        )
    
    @pytest.fixture
    def vector_store(self, config):
        """创建内存向量存储实例"""
        return MemoryVectorStore(config)
    
    @pytest.fixture
    def sample_documents(self):
        """示例文档"""
        return [
            VectorDocument(
                id="doc1",
                vector=np.array([1.0, 0.0, 0.0, 0.0]),
                text="第一个文档",
                metadata={"category": "A"}
            ),
            VectorDocument(
                id="doc2",
                vector=np.array([0.0, 1.0, 0.0, 0.0]),
                text="第二个文档",
                metadata={"category": "B"}
            ),
            VectorDocument(
                id="doc3",
                vector=np.array([0.0, 0.0, 1.0, 0.0]),
                text="第三个文档",
                metadata={"category": "A"}
            )
        ]
    
    @pytest.mark.asyncio
    async def test_initialize(self, vector_store):
        """测试初始化"""
        await vector_store.initialize()
        
        assert vector_store.documents == {}
        assert vector_store.vectors.size == 0
        assert vector_store.document_ids == []
    
    @pytest.mark.asyncio
    async def test_insert_single_document(self, vector_store, sample_documents):
        """测试插入单个文档"""
        await vector_store.initialize()
        
        doc = sample_documents[0]
        await vector_store.insert(doc)
        
        assert len(vector_store.documents) == 1
        assert "doc1" in vector_store.documents
        assert vector_store.vectors.shape == (1, 4)
        assert vector_store.document_ids == ["doc1"]
    
    @pytest.mark.asyncio
    async def test_insert_multiple_documents(self, vector_store, sample_documents):
        """测试插入多个文档"""
        await vector_store.initialize()
        
        await vector_store.insert_batch(sample_documents)
        
        assert len(vector_store.documents) == 3
        assert vector_store.vectors.shape == (3, 4)
        assert len(vector_store.document_ids) == 3
    
    @pytest.mark.asyncio
    async def test_search_basic(self, vector_store, sample_documents):
        """测试基本搜索"""
        await vector_store.initialize()
        await vector_store.insert_batch(sample_documents)
        
        # 搜索与第一个文档相似的向量
        query_vector = np.array([0.9, 0.1, 0.0, 0.0])
        results = await vector_store.search(query_vector, k=2)
        
        assert len(results.results) == 2
        assert results.results[0].document.id == "doc1"  # 最相似的应该是doc1
        assert results.results[0].score > results.results[1].score
    
    @pytest.mark.asyncio
    async def test_search_with_filters(self, vector_store, sample_documents):
        """测试带过滤器的搜索"""
        await vector_store.initialize()
        await vector_store.insert_batch(sample_documents)
        
        query_vector = np.array([0.5, 0.5, 0.5, 0.5])
        filters = {"category": "A"}
        
        results = await vector_store.search(query_vector, k=5, filters=filters)
        
        # 应该只返回category为A的文档
        assert len(results.results) == 2
        for result in results.results:
            assert result.document.metadata["category"] == "A"
    
    @pytest.mark.asyncio
    async def test_get_document(self, vector_store, sample_documents):
        """测试获取文档"""
        await vector_store.initialize()
        await vector_store.insert_batch(sample_documents)
        
        doc = await vector_store.get("doc1")
        
        assert doc is not None
        assert doc.id == "doc1"
        assert doc.text == "第一个文档"
    
    @pytest.mark.asyncio
    async def test_get_nonexistent_document(self, vector_store):
        """测试获取不存在的文档"""
        await vector_store.initialize()
        
        doc = await vector_store.get("nonexistent")
        
        assert doc is None
    
    @pytest.mark.asyncio
    async def test_delete_document(self, vector_store, sample_documents):
        """测试删除文档"""
        await vector_store.initialize()
        await vector_store.insert_batch(sample_documents)
        
        # 删除前检查
        assert len(vector_store.documents) == 3
        
        # 删除文档
        success = await vector_store.delete("doc2")
        
        assert success is True
        assert len(vector_store.documents) == 2
        assert "doc2" not in vector_store.documents
        assert vector_store.vectors.shape == (2, 4)
        assert "doc2" not in vector_store.document_ids
    
    @pytest.mark.asyncio
    async def test_delete_nonexistent_document(self, vector_store):
        """测试删除不存在的文档"""
        await vector_store.initialize()
        
        success = await vector_store.delete("nonexistent")
        
        assert success is False
    
    @pytest.mark.asyncio
    async def test_update_document(self, vector_store, sample_documents):
        """测试更新文档"""
        await vector_store.initialize()
        await vector_store.insert_batch(sample_documents)
        
        # 更新文档
        updated_doc = VectorDocument(
            id="doc1",
            vector=np.array([0.5, 0.5, 0.5, 0.5]),
            text="更新后的第一个文档",
            metadata={"category": "C"}
        )
        
        success = await vector_store.update("doc1", updated_doc)
        
        assert success is True
        
        # 验证更新
        doc = await vector_store.get("doc1")
        assert doc.text == "更新后的第一个文档"
        assert doc.metadata["category"] == "C"
        np.testing.assert_array_equal(doc.vector, np.array([0.5, 0.5, 0.5, 0.5]))
    
    @pytest.mark.asyncio
    async def test_count(self, vector_store, sample_documents):
        """测试计数"""
        await vector_store.initialize()
        
        # 初始计数
        count = await vector_store.count()
        assert count == 0
        
        # 插入文档后计数
        await vector_store.insert_batch(sample_documents)
        count = await vector_store.count()
        assert count == 3
    
    @pytest.mark.asyncio
    async def test_clear(self, vector_store, sample_documents):
        """测试清空"""
        await vector_store.initialize()
        await vector_store.insert_batch(sample_documents)
        
        # 清空前检查
        assert await vector_store.count() == 3
        
        # 清空
        await vector_store.clear()
        
        # 清空后检查
        assert await vector_store.count() == 0
        assert len(vector_store.documents) == 0
        assert vector_store.vectors.size == 0
        assert len(vector_store.document_ids) == 0
    
    @pytest.mark.asyncio
    async def test_get_statistics(self, vector_store, sample_documents):
        """测试获取统计信息"""
        await vector_store.initialize()
        await vector_store.insert_batch(sample_documents)
        
        stats = vector_store.get_statistics()  # 移除await，因为这是同步方法
        
        assert stats["total_documents"] == 3
        assert stats["dimension"] == 4
        assert stats["index_type"] == "memory"
        assert "memory_usage_mb" in stats
    
    def test_calculate_distance_cosine(self, vector_store):
        """测试余弦距离计算"""
        vec1 = np.array([1.0, 0.0, 0.0, 0.0])
        vec2 = np.array([0.0, 1.0, 0.0, 0.0])
        
        distance = vector_store._calculate_distance(vec1, vec2, DistanceMetric.COSINE)
        
        # 余弦距离应该是1.0（完全不相似）
        assert abs(distance - 1.0) < 1e-6
    
    def test_calculate_distance_euclidean(self, vector_store):
        """测试欧几里得距离计算"""
        vec1 = np.array([1.0, 0.0, 0.0, 0.0])
        vec2 = np.array([0.0, 1.0, 0.0, 0.0])
        
        distance = vector_store._calculate_distance(vec1, vec2, DistanceMetric.EUCLIDEAN)
        
        # 欧几里得距离应该是sqrt(2)
        expected = np.sqrt(2.0)
        assert abs(distance - expected) < 1e-6
    
    def test_calculate_distance_manhattan(self, vector_store):
        """测试曼哈顿距离计算"""
        vec1 = np.array([1.0, 0.0, 0.0, 0.0])
        vec2 = np.array([0.0, 1.0, 0.0, 0.0])
        
        distance = vector_store._calculate_distance(vec1, vec2, DistanceMetric.MANHATTAN)
        
        # 曼哈顿距离应该是2.0
        assert abs(distance - 2.0) < 1e-6
    
    def test_match_filters(self, vector_store):
        """测试过滤器匹配"""
        doc = VectorDocument(
            id="doc1",
            vector=np.array([1.0, 0.0, 0.0, 0.0]),
            text="测试文档",
            metadata={
                "category": "A",
                "score": 85,
                "tags": ["test", "document"]
            }
        )
        
        # 精确匹配
        assert vector_store._match_filters(doc, {"category": "A"}) is True
        assert vector_store._match_filters(doc, {"category": "B"}) is False
        
        # 范围查询
        assert vector_store._match_filters(doc, {"score": {"$gte": 80}}) is True
        assert vector_store._match_filters(doc, {"score": {"$lte": 90}}) is True
        assert vector_store._match_filters(doc, {"score": {"$gte": 90}}) is False
        
        # 包含查询
        assert vector_store._match_filters(doc, {"category": {"$in": ["A", "B"]}}) is True
        assert vector_store._match_filters(doc, {"category": {"$in": ["C", "D"]}}) is False


class TestFaissVectorStore:
    """FaissVectorStore 测试类"""
    
    @pytest.fixture
    def config(self):
        """基本配置"""
        return VectorStoreConfig(
            store_type=VectorStoreType.FAISS,
            dimension=4,
            index_type=IndexType.FLAT,
            distance_metric=DistanceMetric.COSINE
        )
    
    @pytest.fixture
    def vector_store(self, config):
        """创建Faiss向量存储实例"""
        with patch('faiss.IndexFlatIP') as mock_index:
            mock_index_instance = Mock()
            mock_index_instance.ntotal = 0
            mock_index_instance.d = 4
            mock_index.return_value = mock_index_instance
            
            store = FaissVectorStore(config)
            store.index = mock_index_instance
            return store
    
    @pytest.mark.asyncio
    async def test_initialize_faiss(self, vector_store):
        """测试Faiss初始化"""
        await vector_store.initialize()
        
        assert vector_store.index is not None
        assert vector_store.documents == {}
        assert vector_store.document_ids == []
    
    @pytest.mark.asyncio
    async def test_insert_faiss(self, vector_store):
        """测试Faiss插入"""
        await vector_store.initialize()
        
        doc = VectorDocument(
            id="doc1",
            vector=np.array([1.0, 0.0, 0.0, 0.0]),
            text="测试文档",
            metadata={}
        )
        
        # 模拟Faiss索引行为
        vector_store.index.add = Mock()
        vector_store.index.ntotal = 1
        
        await vector_store.insert(doc)
        
        assert "doc1" in vector_store.documents
        assert "doc1" in vector_store.document_ids
        vector_store.index.add.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_search_faiss(self, vector_store):
        """测试Faiss搜索"""
        await vector_store.initialize()
        
        # 模拟搜索结果
        vector_store.index.search = Mock(return_value=(
            np.array([[0.9, 0.8]]),  # 分数
            np.array([[0, 1]])       # 索引
        ))
        
        # 添加一些文档到内存中
        vector_store.documents = {
            "doc1": VectorDocument(id="doc1", vector=np.array([1.0, 0.0, 0.0, 0.0]), text="文档1", metadata={}),
            "doc2": VectorDocument(id="doc2", vector=np.array([0.0, 1.0, 0.0, 0.0]), text="文档2", metadata={})
        }
        vector_store.document_ids = ["doc1", "doc2"]
        
        query_vector = np.array([0.9, 0.1, 0.0, 0.0])
        results = await vector_store.search(query_vector, k=2)
        
        assert len(results.results) == 2
        vector_store.index.search.assert_called_once()


class TestChromaVectorStore:
    """ChromaVectorStore 测试类"""
    
    @pytest.fixture
    def config(self):
        """基本配置"""
        return VectorStoreConfig(
            store_type=VectorStoreType.CHROMA,
            dimension=4,
            collection_name="test_collection"
        )
    
    @pytest.fixture
    def vector_store(self, config):
        """创建Chroma向量存储实例"""
        with patch('chromadb.Client') as mock_client:
            mock_collection = Mock()
            mock_client_instance = Mock()
            mock_client_instance.get_or_create_collection.return_value = mock_collection
            mock_client.return_value = mock_client_instance
            
            store = ChromaVectorStore(config)
            store.client = mock_client_instance
            store.collection = mock_collection
            return store
    
    @pytest.mark.asyncio
    async def test_initialize_chroma(self, vector_store):
        """测试Chroma初始化"""
        await vector_store.initialize()
        
        assert vector_store.client is not None
        assert vector_store.collection is not None
    
    @pytest.mark.asyncio
    async def test_insert_chroma(self, vector_store):
        """测试Chroma插入"""
        await vector_store.initialize()
        
        doc = VectorDocument(
            id="doc1",
            vector=np.array([1.0, 0.0, 0.0, 0.0]),
            text="测试文档",
            metadata={"category": "test"}
        )
        
        vector_store.collection.add = Mock()
        
        await vector_store.insert(doc)
        
        vector_store.collection.add.assert_called_once()
        call_args = vector_store.collection.add.call_args[1]
        assert call_args["ids"] == ["doc1"]
        assert call_args["documents"] == ["测试文档"]
        assert call_args["metadatas"] == [{"category": "test"}]
    
    @pytest.mark.asyncio
    async def test_search_chroma(self, vector_store):
        """测试Chroma搜索"""
        await vector_store.initialize()
        
        # 模拟搜索结果
        mock_results = {
            "ids": [["doc1", "doc2"]],
            "documents": [["文档1", "文档2"]],
            "metadatas": [[{"category": "A"}, {"category": "B"}]],
            "distances": [[0.1, 0.2]],
            "embeddings": [[[1.0, 0.0, 0.0, 0.0], [0.0, 1.0, 0.0, 0.0]]]
        }
        
        vector_store.collection.query = Mock(return_value=mock_results)
        
        query_vector = np.array([0.9, 0.1, 0.0, 0.0])
        results = await vector_store.search(query_vector, k=2)
        
        assert len(results.results) == 2
        assert results.results[0].document.id == "doc1"
        assert results.results[1].document.id == "doc2"
        vector_store.collection.query.assert_called_once()


class TestVectorStoreFactory:
    """向量存储工厂测试类"""
    
    def test_create_memory_vector_store(self):
        """测试创建内存向量存储"""
        config = VectorStoreConfig(
            store_type=VectorStoreType.MEMORY,
            dimension=128
        )
        
        store = create_vector_store(config)
        
        assert isinstance(store, MemoryVectorStore)
        assert store.config.dimension == 128
    
    def test_create_faiss_vector_store(self):
        """测试创建Faiss向量存储"""
        with patch('faiss.IndexFlatIP'):
            config = VectorStoreConfig(
                store_type=VectorStoreType.FAISS,
                dimension=128,
                index_type=IndexType.FLAT
            )
            
            store = create_vector_store(config)
            
            assert isinstance(store, FaissVectorStore)
            assert store.config.dimension == 128
    
    def test_create_chroma_vector_store(self):
        """测试创建Chroma向量存储"""
        with patch('chromadb.Client'):
            config = VectorStoreConfig(
                store_type=VectorStoreType.CHROMA,
                dimension=128,
                collection_name="test"
            )
            
            store = create_vector_store(config)
            
            assert isinstance(store, ChromaVectorStore)
            assert store.config.dimension == 128
    
    def test_create_unknown_vector_store(self):
        """测试创建未知类型向量存储"""
        config = VectorStoreConfig(
            store_type="unknown",  # 无效类型
            dimension=128
        )
        
        with pytest.raises(ValueError, match="不支持的向量存储类型"):
            create_vector_store(config)
    
    def test_create_default_vector_store(self):
        """测试创建默认向量存储"""
        store = create_default_vector_store(dimension=256)
        
        assert isinstance(store, MemoryVectorStore)
        assert store.config.dimension == 256
        assert store.config.store_type == VectorStoreType.MEMORY


class TestVectorStorePerformance:
    """向量存储性能测试类"""
    
    @pytest.fixture
    def large_dataset(self):
        """大数据集"""
        documents = []
        for i in range(1000):
            vector = np.random.rand(128).astype(np.float32)
            doc = VectorDocument(
                id=f"doc_{i}",
                vector=vector,
                text=f"文档 {i} 的内容",
                metadata={"index": i, "category": f"cat_{i % 10}"}
            )
            documents.append(doc)
        return documents
    
    @pytest.mark.asyncio
    async def test_batch_insert_performance(self, large_dataset):
        """测试批量插入性能"""
        config = VectorStoreConfig(
            store_type=VectorStoreType.MEMORY,
            dimension=128
        )
        store = MemoryVectorStore(config)
        await store.initialize()
        
        import time
        start_time = time.time()
        
        await store.insert_batch(large_dataset)
        
        end_time = time.time()
        insert_time = end_time - start_time
        
        assert await store.count() == 1000
        assert insert_time < 5.0  # 应该在5秒内完成
        
        print(f"批量插入1000个文档耗时: {insert_time:.3f}秒")
    
    @pytest.mark.asyncio
    async def test_search_performance(self, large_dataset):
        """测试搜索性能"""
        config = VectorStoreConfig(
            store_type=VectorStoreType.MEMORY,
            dimension=128
        )
        store = MemoryVectorStore(config)
        await store.initialize()
        await store.insert_batch(large_dataset)
        
        query_vector = np.random.rand(128).astype(np.float32)
        
        import time
        start_time = time.time()
        
        # 执行多次搜索
        for _ in range(100):
            results = await store.search(query_vector, k=10)
            assert len(results.results) == 10
        
        end_time = time.time()
        search_time = end_time - start_time
        
        assert search_time < 10.0  # 100次搜索应该在10秒内完成
        
        print(f"100次搜索耗时: {search_time:.3f}秒")
    
    @pytest.mark.asyncio
    async def test_concurrent_operations(self, large_dataset):
        """测试并发操作"""
        config = VectorStoreConfig(
            store_type=VectorStoreType.MEMORY,
            dimension=128
        )
        store = MemoryVectorStore(config)
        await store.initialize()
        
        # 先插入一些数据
        await store.insert_batch(large_dataset[:500])
        
        # 并发执行插入和搜索
        async def insert_task():
            await store.insert_batch(large_dataset[500:])
        
        async def search_task():
            query_vector = np.random.rand(128).astype(np.float32)
            for _ in range(50):
                await store.search(query_vector, k=5)
        
        # 并发执行
        await asyncio.gather(insert_task(), search_task())
        
        # 验证最终状态
        assert await store.count() == 1000


class TestVectorStoreErrorHandling:
    """向量存储错误处理测试类"""
    
    @pytest.mark.asyncio
    async def test_insert_duplicate_id(self):
        """测试插入重复ID"""
        config = VectorStoreConfig(
            store_type=VectorStoreType.MEMORY,
            dimension=4
        )
        store = MemoryVectorStore(config)
        await store.initialize()
        
        doc1 = VectorDocument(
            id="doc1",
            vector=np.array([1.0, 0.0, 0.0, 0.0]),
            text="第一个文档",
            metadata={}
        )
        
        doc2 = VectorDocument(
            id="doc1",  # 相同ID
            vector=np.array([0.0, 1.0, 0.0, 0.0]),
            text="第二个文档",
            metadata={}
        )
        
        # 第一次插入应该成功
        await store.insert(doc1)
        assert await store.count() == 1
        
        # 第二次插入相同ID应该失败或覆盖（取决于实现）
        await store.insert(doc2)
        assert await store.count() == 1  # 数量不变
    
    @pytest.mark.asyncio
    async def test_search_empty_store(self):
        """测试在空存储中搜索"""
        config = VectorStoreConfig(
            store_type=VectorStoreType.MEMORY,
            dimension=4
        )
        store = MemoryVectorStore(config)
        await store.initialize()
        
        query_vector = np.array([1.0, 0.0, 0.0, 0.0])
        results = await store.search(query_vector, k=5)
        
        assert len(results.results) == 0
        assert results.total_results == 0
    
    @pytest.mark.asyncio
    async def test_invalid_vector_dimension(self):
        """测试无效向量维度"""
        config = VectorStoreConfig(
            store_type=VectorStoreType.MEMORY,
            dimension=4
        )
        store = MemoryVectorStore(config)
        await store.initialize()
        
        # 尝试插入错误维度的向量
        doc = VectorDocument(
            id="doc1",
            vector=np.array([1.0, 0.0]),  # 只有2维，期望4维
            text="测试文档",
            metadata={}
        )
        
        with pytest.raises(ValueError, match="向量维度不匹配"):
            await store.insert(doc)
    
    @pytest.mark.asyncio
    async def test_search_invalid_vector_dimension(self):
        """测试搜索时使用无效向量维度"""
        config = VectorStoreConfig(
            store_type=VectorStoreType.MEMORY,
            dimension=4
        )
        store = MemoryVectorStore(config)
        await store.initialize()
        
        # 尝试使用错误维度的查询向量
        query_vector = np.array([1.0, 0.0])  # 只有2维，期望4维
        
        with pytest.raises(ValueError, match="查询向量维度不匹配"):
            await store.search(query_vector, k=5)


if __name__ == "__main__":
    pytest.main([__file__])