"""数据结构化器测试

测试DataStructurer类的各种功能，包括数据结构化、实体提取、关系提取、文本分块等。
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, List, Any

from backend.core.etl.data_structurer import (
    DataStructurer, DataType, StructuredData, StructureType, StructureConfig
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
    
    # ==================== 基础功能测试 ====================
    
    def test_structurer_initialization(self):
        """测试数据结构化器初始化"""
        structurer = DataStructurer()
        assert structurer is not None
        assert isinstance(structurer.config, StructureConfig)
        assert structurer.processors is not None
    
    def test_structurer_with_config(self):
        """测试带配置的数据结构化器"""
        config = StructureConfig(chunk_size=500, extract_entities=False)
        structurer = DataStructurer(config)
        assert structurer.config.chunk_size == 500
        assert structurer.config.extract_entities == False
    
    def test_get_supported_types(self, structurer):
        """测试获取支持的数据类型"""
        supported_types = structurer.get_supported_types()
        assert isinstance(supported_types, list)
        assert DataType.TEXT in supported_types
        assert DataType.JSON in supported_types
        assert DataType.CSV in supported_types
    
    def test_update_config(self, structurer):
        """测试更新配置"""
        new_config = StructureConfig(chunk_size=800, language="en")
        structurer.update_config(new_config)
        assert structurer.config.chunk_size == 800
        assert structurer.config.language == "en"
    
    # ==================== 数据结构化测试 ====================
    
    @pytest.mark.asyncio
    async def test_structure_text_data(self, structurer, sample_text_data):
        """测试文本数据结构化"""
        with patch.object(structurer, '_extract_entities', return_value=[]):
            with patch.object(structurer, '_extract_relations', return_value=[]):
                with patch.object(structurer, '_create_chunks', return_value=[]):
                    result = await structurer.structure_data(
                        data=sample_text_data,
                        data_type=DataType.TEXT,
                        source_id="test-001"
                    )
        
        assert isinstance(result, StructuredData)
        assert result.source_id == "test-001"
        assert result.source_type == DataType.TEXT
        assert result.content is not None
        assert isinstance(result.entities, list)
        assert isinstance(result.relations, list)
        assert isinstance(result.quality_score, float)
        assert 0 <= result.quality_score <= 1
    
    @pytest.mark.asyncio
    async def test_structure_json_data(self, structurer, sample_json_data):
        """测试JSON数据结构化"""
        with patch.object(structurer, '_extract_entities', return_value=[]):
            with patch.object(structurer, '_extract_relations', return_value=[]):
                result = await structurer.structure_data(
                    data=sample_json_data,
                    data_type=DataType.JSON,
                    source_id="test-002"
                )
        
        assert isinstance(result, StructuredData)
        assert result.source_type == DataType.JSON
        assert result.content["data"] == sample_json_data
        assert result.quality_score > 0  # JSON数据质量通常较高
    
    @pytest.mark.asyncio
    async def test_structure_csv_data(self, structurer, sample_csv_data):
        """测试CSV数据结构化"""
        with patch.object(structurer, '_extract_entities', return_value=[]):
            with patch.object(structurer, '_extract_relations', return_value=[]):
                result = await structurer.structure_data(
                    data=sample_csv_data,
                    data_type=DataType.CSV,
                    source_id="test-003"
                )
        
        assert isinstance(result, StructuredData)
        assert result.source_type == DataType.CSV
        assert "data" in result.content
        assert isinstance(result.content["data"], list)
    
    @pytest.mark.asyncio
    async def test_structure_data_with_metadata(self, structurer, sample_text_data):
        """测试带元数据的数据结构化"""
        metadata = {"source": "test", "version": "1.0"}
        
        with patch.object(structurer, '_extract_entities', return_value=[]):
            with patch.object(structurer, '_extract_relations', return_value=[]):
                with patch.object(structurer, '_create_chunks', return_value=[]):
                    result = await structurer.structure_data(
                        data=sample_text_data,
                        data_type=DataType.TEXT,
                        source_id="test-004",
                        metadata=metadata
                    )
        
        assert isinstance(result, StructuredData)
        assert result.metadata == metadata
    
    # ==================== 错误处理测试 ====================
    
    @pytest.mark.asyncio
    async def test_structure_unsupported_data_type(self, structurer):
        """测试不支持的数据类型"""
        # 临时修改processors来模拟不支持的类型
        original_processors = structurer.processors.copy()
        structurer.processors = {}
        
        with pytest.raises(ValueError, match="不支持的数据类型"):
            await structurer.structure_data(
                data="test",
                data_type=DataType.TEXT,
                source_id="test-005"
            )
        
        # 恢复原始processors
        structurer.processors = original_processors
    
    @pytest.mark.asyncio
    async def test_structure_invalid_json(self, structurer):
        """测试无效JSON数据"""
        invalid_json = "{'invalid': json}"
        
        with pytest.raises(ValueError, match="无效的JSON格式"):
            await structurer.structure_data(
                data=invalid_json,
                data_type=DataType.JSON,
                source_id="test-006"
            )
    
    # ==================== 内部方法测试 ====================
    
    @pytest.mark.asyncio
    async def test_process_text(self, structurer):
        """测试文本处理"""
        text = "第一行\n第二行\n\n第二段"
        result = await structurer._process_text(text)
        
        assert isinstance(result, dict)
        assert result["text"] == text
        assert result["length"] == len(text)
        assert result["lines"] > 0
        assert result["words"] > 0
        assert result["paragraphs"] >= 1
    
    @pytest.mark.asyncio
    async def test_process_json_string(self, structurer):
        """测试JSON字符串处理"""
        json_str = '{"key": "value", "number": 42}'
        result = await structurer._process_json(json_str)
        
        assert isinstance(result, dict)
        assert result["data"]["key"] == "value"
        assert result["data"]["number"] == 42
        assert "keys" in result
        assert "size" in result
        assert "depth" in result
    
    @pytest.mark.asyncio
    async def test_process_json_dict(self, structurer):
        """测试JSON字典处理"""
        json_dict = {"key": "value", "number": 42}
        result = await structurer._process_json(json_dict)
        
        assert isinstance(result, dict)
        assert result["data"] == json_dict
        assert "key" in result["keys"]
        assert "number" in result["keys"]
        
    def test_calculate_json_depth(self, structurer):
        """测试JSON深度计算"""
        simple_dict = {"key": "value"}
        nested_dict = {"level1": {"level2": {"level3": "value"}}}
        
        depth1 = structurer._calculate_json_depth(simple_dict)
        depth2 = structurer._calculate_json_depth(nested_dict)
        
        assert depth1 == 1
        assert depth2 == 3


if __name__ == "__main__":
    # 运行测试
    pytest.main(["-v", __file__])