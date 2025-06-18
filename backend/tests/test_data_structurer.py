"""数据结构化器测试

测试DataStructurer类的各种功能，包括数据结构化、实体提取、关系提取、文本分块等。
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, List, Any

from backend.core.etl.data_structurer import (
    DataStructurer, DataType, StructuredData, EntityInfo, RelationInfo,
    TextChunk, QualityMetrics
)


class TestDataStructurer:
    """数据结构化器测试类"""
    
    @pytest.fixture
    def structurer(self):
        """创建数据结构化器实例"""
        return DataStructurer()
    
    @pytest.fixture
    def sample_text_data(self):
        """示例文本数据"""
        return "这是一个关于人工智能的文档。人工智能（AI）是计算机科学的一个分支。"
    
    @pytest.fixture
    def sample_json_data(self):
        """示例JSON数据"""
        return {
            "name": "张三",
            "age": 30,
            "company": "科技公司",
            "skills": ["Python", "机器学习", "数据分析"]
        }
    
    @pytest.fixture
    def sample_csv_data(self):
        """示例CSV数据"""
        return "name,age,company\n张三,30,科技公司\n李四,25,互联网公司"
    
    @pytest.fixture
    def sample_html_data(self):
        """示例HTML数据"""
        return "<html><body><h1>标题</h1><p>这是一个段落。</p></body></html>"
    
    # ==================== 数据类型检测测试 ====================
    
    def test_detect_data_type_text(self, structurer, sample_text_data):
        """测试文本数据类型检测"""
        data_type = structurer._detect_data_type(sample_text_data)
        assert data_type == DataType.TEXT
    
    def test_detect_data_type_json(self, structurer, sample_json_data):
        """测试JSON数据类型检测"""
        data_type = structurer._detect_data_type(sample_json_data)
        assert data_type == DataType.JSON
    
    def test_detect_data_type_csv(self, structurer, sample_csv_data):
        """测试CSV数据类型检测"""
        data_type = structurer._detect_data_type(sample_csv_data)
        assert data_type == DataType.CSV
    
    def test_detect_data_type_html(self, structurer, sample_html_data):
        """测试HTML数据类型检测"""
        data_type = structurer._detect_data_type(sample_html_data)
        assert data_type == DataType.HTML
    
    def test_detect_data_type_auto(self, structurer):
        """测试自动数据类型检测"""
        # 测试各种数据类型
        test_cases = [
            ("plain text", DataType.TEXT),
            ('{"key": "value"}', DataType.JSON),
            ("col1,col2\nval1,val2", DataType.CSV),
            ("<html><body>content</body></html>", DataType.HTML)
        ]
        
        for data, expected_type in test_cases:
            detected_type = structurer._detect_data_type(data)
            assert detected_type == expected_type
    
    # ==================== 数据结构化测试 ====================
    
    @pytest.mark.asyncio
    async def test_structure_text_data(self, structurer, sample_text_data):
        """测试文本数据结构化"""
        result = await structurer.structure_data(
            data=sample_text_data,
            data_type="text",
            extract_entities=True,
            extract_relations=True
        )
        
        assert isinstance(result, StructuredData)
        assert result.original_data == sample_text_data
        assert result.data_type == DataType.TEXT
        assert result.structured_content is not None
        assert isinstance(result.entities, list)
        assert isinstance(result.relations, list)
        assert isinstance(result.quality_score, float)
        assert 0 <= result.quality_score <= 1
    
    @pytest.mark.asyncio
    async def test_structure_json_data(self, structurer, sample_json_data):
        """测试JSON数据结构化"""
        result = await structurer.structure_data(
            data=sample_json_data,
            data_type="json"
        )
        
        assert isinstance(result, StructuredData)
        assert result.data_type == DataType.JSON
        assert result.structured_content == sample_json_data
        assert result.quality_score > 0.8  # JSON数据质量通常较高
    
    @pytest.mark.asyncio
    async def test_structure_csv_data(self, structurer, sample_csv_data):
        """测试CSV数据结构化"""
        result = await structurer.structure_data(
            data=sample_csv_data,
            data_type="csv"
        )
        
        assert isinstance(result, StructuredData)
        assert result.data_type == DataType.CSV
        assert isinstance(result.structured_content, list)
        assert len(result.structured_content) == 2  # 两行数据
        assert "name" in result.structured_content[0]
        assert "age" in result.structured_content[0]
    
    @pytest.mark.asyncio
    async def test_structure_html_data(self, structurer, sample_html_data):
        """测试HTML数据结构化"""
        result = await structurer.structure_data(
            data=sample_html_data,
            data_type="html"
        )
        
        assert isinstance(result, StructuredData)
        assert result.data_type == DataType.HTML
        assert isinstance(result.structured_content, dict)
        assert "title" in result.structured_content
        assert "content" in result.structured_content
    
    @pytest.mark.asyncio
    async def test_structure_data_with_options(self, structurer, sample_text_data):
        """测试带选项的数据结构化"""
        options = {
            "language": "zh",
            "preserve_formatting": True,
            "extract_metadata": True
        }
        
        result = await structurer.structure_data(
            data=sample_text_data,
            data_type="text",
            options=options
        )
        
        assert isinstance(result, StructuredData)
        assert result.metadata.get("language") == "zh"
    
    # ==================== 实体提取测试 ====================
    
    @pytest.mark.asyncio
    async def test_extract_entities(self, structurer):
        """测试实体提取"""
        text = "张三在北京的清华大学学习计算机科学。"
        
        entities = await structurer._extract_entities(text)
        
        assert isinstance(entities, list)
        assert len(entities) > 0
        
        # 检查实体信息
        for entity in entities:
            assert isinstance(entity, EntityInfo)
            assert entity.text
            assert entity.entity_type
            assert 0 <= entity.confidence <= 1
            assert isinstance(entity.start_pos, int)
            assert isinstance(entity.end_pos, int)
    
    @pytest.mark.asyncio
    async def test_extract_entities_with_types(self, structurer):
        """测试特定类型实体提取"""
        text = "苹果公司的CEO蒂姆·库克在2023年发布了新产品。"
        entity_types = ["PERSON", "ORG", "DATE"]
        
        entities = await structurer._extract_entities(text, entity_types)
        
        assert isinstance(entities, list)
        
        # 检查是否只包含指定类型
        for entity in entities:
            assert entity.entity_type in entity_types
    
    @pytest.mark.asyncio
    async def test_extract_entities_empty_text(self, structurer):
        """测试空文本实体提取"""
        entities = await structurer._extract_entities("")
        assert entities == []
    
    # ==================== 关系提取测试 ====================
    
    @pytest.mark.asyncio
    async def test_extract_relations(self, structurer):
        """测试关系提取"""
        text = "张三是清华大学的学生，他学习计算机科学。"
        entities = [
            EntityInfo(
                text="张三",
                entity_type="PERSON",
                start_pos=0,
                end_pos=2,
                confidence=0.9
            ),
            EntityInfo(
                text="清华大学",
                entity_type="ORG",
                start_pos=3,
                end_pos=7,
                confidence=0.95
            )
        ]
        
        relations = await structurer._extract_relations(text, entities)
        
        assert isinstance(relations, list)
        
        # 检查关系信息
        for relation in relations:
            assert isinstance(relation, RelationInfo)
            assert relation.subject
            assert relation.predicate
            assert relation.object
            assert 0 <= relation.confidence <= 1
    
    @pytest.mark.asyncio
    async def test_extract_relations_no_entities(self, structurer):
        """测试无实体时的关系提取"""
        text = "这是一个简单的句子。"
        entities = []
        
        relations = await structurer._extract_relations(text, entities)
        assert relations == []
    
    # ==================== 文本分块测试 ====================
    
    def test_chunk_text_basic(self, structurer):
        """测试基本文本分块"""
        text = "这是第一段。" * 100 + "这是第二段。" * 100
        
        chunks = structurer._chunk_text(
            text=text,
            chunk_size=100,
            chunk_overlap=20
        )
        
        assert isinstance(chunks, list)
        assert len(chunks) > 1
        
        # 检查分块信息
        for chunk in chunks:
            assert isinstance(chunk, TextChunk)
            assert chunk.text
            assert len(chunk.text) <= 120  # chunk_size + overlap
            assert isinstance(chunk.start_pos, int)
            assert isinstance(chunk.end_pos, int)
            assert chunk.chunk_id
    
    def test_chunk_text_small_text(self, structurer):
        """测试小文本分块"""
        text = "短文本"
        
        chunks = structurer._chunk_text(
            text=text,
            chunk_size=100,
            chunk_overlap=20
        )
        
        assert len(chunks) == 1
        assert chunks[0].text == text
    
    def test_chunk_text_custom_strategy(self, structurer):
        """测试自定义分块策略"""
        text = "句子一。句子二。句子三。句子四。"
        
        chunks = structurer._chunk_text(
            text=text,
            chunk_size=10,
            chunk_overlap=2,
            strategy="sentence"
        )
        
        assert isinstance(chunks, list)
        assert len(chunks) > 0
    
    # ==================== 质量评估测试 ====================
    
    def test_calculate_quality_score_high_quality(self, structurer):
        """测试高质量数据评分"""
        data = {
            "title": "完整的标题",
            "content": "这是一个完整且结构良好的内容，包含了足够的信息。",
            "author": "作者姓名",
            "date": "2023-01-01"
        }
        
        score = structurer._calculate_quality_score(data, DataType.JSON)
        
        assert isinstance(score, float)
        assert 0.7 <= score <= 1.0  # 高质量数据
    
    def test_calculate_quality_score_low_quality(self, structurer):
        """测试低质量数据评分"""
        data = {
            "incomplete": "",
            "missing": None
        }
        
        score = structurer._calculate_quality_score(data, DataType.JSON)
        
        assert isinstance(score, float)
        assert 0.0 <= score <= 0.5  # 低质量数据
    
    def test_calculate_confidence_score(self, structurer):
        """测试置信度计算"""
        # 测试不同数据类型的置信度
        test_cases = [
            ({"key": "value"}, DataType.JSON, 0.8),  # 结构化数据置信度高
            ("plain text", DataType.TEXT, 0.6),      # 文本数据置信度中等
            ("", DataType.TEXT, 0.1)                 # 空数据置信度低
        ]
        
        for data, data_type, expected_min in test_cases:
            confidence = structurer._calculate_confidence_score(data, data_type)
            assert isinstance(confidence, float)
            assert 0 <= confidence <= 1
            assert confidence >= expected_min
    
    # ==================== 批量处理测试 ====================
    
    @pytest.mark.asyncio
    async def test_structure_batch(self, structurer):
        """测试批量数据结构化"""
        data_list = [
            "第一个文本数据",
            {"key": "第二个JSON数据"},
            "name,age\n张三,30"
        ]
        
        results = await structurer.structure_batch(
            data_list=data_list,
            data_type="auto",
            batch_size=2
        )
        
        assert isinstance(results, list)
        assert len(results) == 3
        
        # 检查每个结果
        for result in results:
            assert isinstance(result, StructuredData)
            assert result.structured_content is not None
    
    @pytest.mark.asyncio
    async def test_structure_batch_with_errors(self, structurer):
        """测试批量处理中的错误处理"""
        data_list = [
            "正常数据",
            None,  # 无效数据
            "另一个正常数据"
        ]
        
        results = await structurer.structure_batch(
            data_list=data_list,
            data_type="auto",
            skip_errors=True
        )
        
        # 应该跳过错误数据，只返回有效结果
        assert isinstance(results, list)
        assert len(results) == 2
    
    @pytest.mark.asyncio
    async def test_structure_batch_parallel(self, structurer):
        """测试并行批量处理"""
        data_list = [f"文本数据 {i}" for i in range(5)]
        
        results = await structurer.structure_batch(
            data_list=data_list,
            data_type="text",
            parallel=True,
            max_workers=2
        )
        
        assert isinstance(results, list)
        assert len(results) == 5
    
    # ==================== 错误处理测试 ====================
    
    @pytest.mark.asyncio
    async def test_structure_invalid_data_type(self, structurer):
        """测试无效数据类型处理"""
        with pytest.raises(ValueError, match="不支持的数据类型"):
            await structurer.structure_data(
                data="test",
                data_type="invalid_type"
            )
    
    @pytest.mark.asyncio
    async def test_structure_none_data(self, structurer):
        """测试None数据处理"""
        with pytest.raises(ValueError, match="数据不能为空"):
            await structurer.structure_data(data=None)
    
    @pytest.mark.asyncio
    async def test_structure_empty_string(self, structurer):
        """测试空字符串处理"""
        result = await structurer.structure_data(
            data="",
            data_type="text"
        )
        
        assert isinstance(result, StructuredData)
        assert result.structured_content == ""
        assert result.quality_score < 0.3  # 空数据质量低
    
    # ==================== 配置和选项测试 ====================
    
    def test_structurer_initialization(self):
        """测试结构化器初始化"""
        # 默认配置
        structurer1 = DataStructurer()
        assert structurer1.config is not None
        
        # 自定义配置
        custom_config = {
            "max_entities": 50,
            "max_relations": 30,
            "chunk_size": 500
        }
        structurer2 = DataStructurer(config=custom_config)
        assert structurer2.config["max_entities"] == 50
    
    def test_update_config(self, structurer):
        """测试配置更新"""
        new_config = {
            "max_entities": 100,
            "enable_caching": True
        }
        
        structurer.update_config(new_config)
        
        assert structurer.config["max_entities"] == 100
        assert structurer.config["enable_caching"] is True
    
    def test_get_supported_types(self, structurer):
        """测试获取支持的数据类型"""
        supported_types = structurer.get_supported_types()
        
        assert isinstance(supported_types, list)
        assert "text" in supported_types
        assert "json" in supported_types
        assert "csv" in supported_types
        assert "html" in supported_types
    
    # ==================== 性能测试 ====================
    
    @pytest.mark.asyncio
    async def test_performance_large_text(self, structurer):
        """测试大文本处理性能"""
        import time
        
        # 创建大文本（约10KB）
        large_text = "这是一个很长的文本。" * 1000
        
        start_time = time.time()
        result = await structurer.structure_data(
            data=large_text,
            data_type="text",
            chunk_text=True,
            chunk_size=1000
        )
        end_time = time.time()
        
        # 检查处理时间（应该在合理范围内）
        processing_time = end_time - start_time
        assert processing_time < 30  # 30秒内完成
        
        # 检查结果
        assert isinstance(result, StructuredData)
        assert len(result.chunks) > 1
    
    @pytest.mark.asyncio
    async def test_memory_usage_batch_processing(self, structurer):
        """测试批量处理内存使用"""
        import psutil
        import os
        
        # 获取初始内存使用
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        # 批量处理大量数据
        data_list = [f"文本数据 {i}" * 100 for i in range(100)]
        
        results = await structurer.structure_batch(
            data_list=data_list,
            data_type="text",
            batch_size=10
        )
        
        # 检查内存增长
        final_memory = process.memory_info().rss
        memory_growth = final_memory - initial_memory
        
        # 内存增长应该在合理范围内（小于100MB）
        assert memory_growth < 100 * 1024 * 1024
        
        # 检查结果
        assert len(results) == 100
    
    # ==================== 集成测试 ====================
    
    @pytest.mark.asyncio
    async def test_end_to_end_workflow(self, structurer):
        """测试端到端工作流"""
        # 模拟完整的数据处理流程
        raw_data = """
        公司名称：科技创新有限公司
        成立时间：2020年1月1日
        创始人：张三、李四
        主要业务：人工智能、机器学习、数据分析
        员工数量：150人
        总部地址：北京市海淀区中关村大街1号
        """
        
        # 1. 数据结构化
        result = await structurer.structure_data(
            data=raw_data,
            data_type="text",
            extract_entities=True,
            extract_relations=True,
            chunk_text=True,
            chunk_size=200
        )
        
        # 2. 验证结果
        assert isinstance(result, StructuredData)
        assert result.data_type == DataType.TEXT
        assert len(result.entities) > 0
        assert len(result.relations) > 0
        assert len(result.chunks) > 0
        assert result.quality_score > 0.5
        
        # 3. 检查提取的实体
        entity_texts = [entity.text for entity in result.entities]
        assert any("科技创新有限公司" in text for text in entity_texts)
        assert any("张三" in text for text in entity_texts)
        assert any("北京" in text for text in entity_texts)
        
        # 4. 检查提取的关系
        assert len(result.relations) > 0
        
        # 5. 检查文本分块
        total_chunk_length = sum(len(chunk.text) for chunk in result.chunks)
        assert total_chunk_length >= len(raw_data.strip())
    
    @pytest.mark.asyncio
    async def test_multilingual_support(self, structurer):
        """测试多语言支持"""
        # 测试中英文混合文本
        mixed_text = """
        Apple Inc. 是一家美国的科技公司，由Steve Jobs创立。
        The company is headquartered in Cupertino, California.
        苹果公司的主要产品包括iPhone、iPad和Mac电脑。
        """
        
        result = await structurer.structure_data(
            data=mixed_text,
            data_type="text",
            extract_entities=True,
            options={"language": "mixed"}
        )
        
        assert isinstance(result, StructuredData)
        assert len(result.entities) > 0
        
        # 检查是否提取了中英文实体
        entity_texts = [entity.text for entity in result.entities]
        has_english = any("Apple" in text or "Steve Jobs" in text for text in entity_texts)
        has_chinese = any("苹果公司" in text or "科技公司" in text for text in entity_texts)
        
        assert has_english or has_chinese  # 至少提取了一种语言的实体


if __name__ == "__main__":
    # 运行测试
    pytest.main(["-v", __file__])