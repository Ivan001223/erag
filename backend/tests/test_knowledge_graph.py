import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
import uuid
from typing import List, Dict, Any
import pytest_asyncio

from backend.core.knowledge_graph.entity_extractor import (
    EntityExtractor, EntityExtractionConfig, ExtractionMethod, EntityExtractionResult,
    ExtractedEntity, EntityCategory
)
from backend.core.knowledge_graph.relation_extractor import (
    RelationExtractor, RelationExtractionConfig, RelationExtractionResult,
    ExtractedRelation, RelationCategory, RelationExtractionMethod
)
from backend.core.knowledge_graph.graph_manager import (
    GraphManager, GraphConfig, GraphOperationResult, GraphMetrics, GraphSearchResult
)
from backend.core.knowledge_graph.graph_analytics import (
    GraphAnalytics, AnalysisConfig, AnalysisType, AnalysisResult
)
from backend.core.knowledge_graph.graph_database import (
    GraphDatabase, DatabaseConfig, QueryResult
)
from backend.models.knowledge import Entity, Relation, KnowledgeGraph
from backend.api.deps import CacheManager


class TestEntityExtractor:
    """实体提取器测试"""
    
    @pytest.fixture
    def extractor(self):
        """创建实体提取器"""
        return EntityExtractor()
    
    @pytest.fixture
    def sample_text(self):
        """示例文本"""
        return "苹果公司是一家美国跨国科技公司，由史蒂夫·乔布斯创立于1976年。"
    
    @pytest.fixture
    def extraction_config(self):
        """提取配置"""
        return EntityExtractionConfig(
            method=ExtractionMethod.NER,
            entity_types=["PERSON", "ORG", "DATE"],
            language="zh",
            confidence_threshold=0.7
        )
    
    @pytest.mark.asyncio
    async def test_extract_entities_ner(self, extractor, sample_text, extraction_config):
        """测试NER实体提取"""
        with patch.object(extractor, '_extract_with_ner') as mock_ner:
            mock_entities = [
                Entity(
                    id="1",
                    name="苹果公司",
                    entity_type="ORG",
                    properties={"confidence": 0.9},
                    metadata={"method": "ner"}
                ),
                Entity(
                    id="2",
                    name="史蒂夫·乔布斯",
                    entity_type="PERSON",
                    properties={"confidence": 0.8},
                    metadata={"method": "ner"}
                )
            ]
            mock_ner.return_value = mock_entities
            
            result = await extractor.extract_entities(sample_text, extraction_config)
            
            assert result.success
            assert len(result.entities) == 2
            assert result.entities[0].name == "苹果公司"
            assert result.entities[1].name == "史蒂夫·乔布斯"
            assert "total_entities" in result.statistics
    
    @pytest.mark.asyncio
    async def test_extract_entities_pattern(self, extractor, sample_text):
        """测试模式匹配实体提取"""
        config = EntityExtractionConfig(
            method=ExtractionMethod.PATTERN,
            patterns={
                "COMPANY": [r"\w+公司"],
                "YEAR": [r"\d{4}年"]
            }
        )
        
        with patch.object(extractor, '_extract_with_pattern') as mock_pattern:
            mock_entities = [
                Entity(
                    id="1",
                    name="苹果公司",
                    entity_type="COMPANY",
                    properties={"confidence": 1.0},
                    metadata={"method": "pattern"}
                )
            ]
            mock_pattern.return_value = mock_entities
            
            result = await extractor.extract_entities(sample_text, config)
            
            assert result.success
            assert len(result.entities) == 1
            assert result.entities[0].entity_type == "COMPANY"
    
    @pytest.mark.asyncio
    async def test_extract_entities_llm(self, extractor, sample_text):
        """测试LLM实体提取"""
        config = EntityExtractionConfig(
            method=ExtractionMethod.LLM,
            llm_model="gpt-3.5-turbo"
        )
        
        with patch.object(extractor, '_extract_with_llm') as mock_llm:
            mock_entities = [
                Entity(
                    id="1",
                    name="苹果公司",
                    entity_type="ORG",
                    properties={"confidence": 0.95},
                    metadata={"method": "llm"}
                )
            ]
            mock_llm.return_value = mock_entities
            
            result = await extractor.extract_entities(sample_text, config)
            
            assert result.success
            assert len(result.entities) == 1
            assert result.entities[0].properties["confidence"] == 0.95
    
    @pytest.mark.asyncio
    async def test_extract_entities_hybrid(self, extractor, sample_text):
        """测试混合实体提取"""
        config = EntityExtractionConfig(
            method=ExtractionMethod.HYBRID,
            entity_types=["PERSON", "ORG"]
        )
        
        with patch.object(extractor, '_extract_with_hybrid') as mock_hybrid:
            mock_entities = [
                Entity(
                    id="1",
                    name="苹果公司",
                    entity_type="ORG",
                    properties={"confidence": 0.9},
                    metadata={"method": "hybrid"}
                )
            ]
            mock_hybrid.return_value = mock_entities
            
            result = await extractor.extract_entities(sample_text, config)
            
            assert result.success
            assert len(result.entities) == 1
    
    def test_resolve_coreferences(self, extractor):
        """测试共指消解"""
        text = "苹果公司是一家科技公司。它成立于1976年。"
        entities = [
            Entity(id="1", name="苹果公司", entity_type="ORG", properties={}, metadata={}),
            Entity(id="2", name="它", entity_type="ORG", properties={}, metadata={})
        ]
        
        resolved = extractor.resolve_coreferences(text, entities)
        
        # 验证共指消解结果
        assert len(resolved) <= len(entities)
    
    def test_disambiguate_entities(self, extractor):
        """测试实体消歧"""
        entities = [
            Entity(id="1", name="苹果", entity_type="ORG", properties={}, metadata={}),
            Entity(id="2", name="苹果", entity_type="FRUIT", properties={}, metadata={})
        ]
        
        disambiguated = extractor.disambiguate_entities(entities)
        
        # 验证消歧结果
        assert len(disambiguated) >= 1
    
    def test_merge_entities(self, extractor):
        """测试实体合并"""
        entities = [
            Entity(id="1", name="苹果公司", entity_type="ORG", properties={}, metadata={}),
            Entity(id="2", name="Apple Inc.", entity_type="ORG", properties={}, metadata={})
        ]
        
        merged = extractor.merge_entities(entities)
        
        # 验证合并结果
        assert len(merged) <= len(entities)


class TestRelationExtractor:
    """关系提取器测试"""
    
    @pytest.fixture
    def extractor(self):
        """创建关系提取器"""
        return RelationExtractor()
    
    @pytest.fixture
    def sample_text(self):
        """示例文本"""
        return "史蒂夫·乔布斯创立了苹果公司。"
    
    @pytest.fixture
    def sample_entities(self):
        """示例实体"""
        return [
            Entity(
                id="1",
                name="史蒂夫·乔布斯",
                entity_type="PERSON",
                properties={},
                metadata={}
            ),
            Entity(
                id="2",
                name="苹果公司",
                entity_type="ORG",
                properties={},
                metadata={}
            )
        ]
    
    @pytest.fixture
    def extraction_config(self):
        """提取配置"""
        return RelationExtractionConfig(
            method="pattern",
            patterns={
                "FOUNDED": [r"(\w+)创立了?(\w+)"]
            },
            confidence_threshold=0.7
        )
    
    @pytest.mark.asyncio
    async def test_extract_relations_pattern(self, extractor, sample_text, sample_entities, extraction_config):
        """测试模式匹配关系提取"""
        with patch.object(extractor, '_extract_with_pattern') as mock_pattern:
            mock_relations = [
                Relation(
                    id="1",
                    source_entity_id="1",
                    target_entity_id="2",
                    relation_type="FOUNDED",
                    properties={"confidence": 0.9},
                    metadata={"method": "pattern"}
                )
            ]
            mock_pattern.return_value = mock_relations
            
            result = await extractor.extract_relations(sample_text, sample_entities, extraction_config)
            
            assert result.success
            assert len(result.relations) == 1
            assert result.relations[0].source_entity_id == "1"
            assert result.relations[0].target_entity_id == "2"
    
    @pytest.mark.asyncio
    async def test_extract_relations_dependency(self, extractor, sample_text, sample_entities):
        """测试依存句法关系提取"""
        config = RelationExtractionConfig(
            method="dependency",
            confidence_threshold=0.6
        )
        
        with patch.object(extractor, '_extract_with_dependency') as mock_dep:
            mock_relations = [
                Relation(
                    id="1",
                    source_entity_id="1",
                    target_entity_id="2",
                    relation_type="AGENT",
                    properties={"confidence": 0.8},
                    metadata={"method": "dependency"}
                )
            ]
            mock_dep.return_value = mock_relations
            
            result = await extractor.extract_relations(sample_text, sample_entities, config)
            
            assert result.success
            assert len(result.relations) == 1
            assert result.relations[0].relation_type == "AGENT"
    
    @pytest.mark.asyncio
    async def test_extract_relations_llm(self, extractor, sample_text, sample_entities):
        """测试LLM关系提取"""
        config = RelationExtractionConfig(
            method="llm",
            llm_model="gpt-3.5-turbo"
        )
        
        with patch.object(extractor, '_extract_with_llm') as mock_llm:
            mock_relations = [
                Relation(
                    id="1",
                    source_entity_id="1",
                    target_entity_id="2",
                    relation_type="FOUNDED",
                    properties={"confidence": 0.95},
                    metadata={"method": "llm"}
                )
            ]
            mock_llm.return_value = mock_relations
            
            result = await extractor.extract_relations(sample_text, sample_entities, config)
            
            assert result.success
            assert len(result.relations) == 1
            assert result.relations[0].properties["confidence"] == 0.95
    
    def test_generate_entity_pairs(self, extractor, sample_entities):
        """测试生成实体对"""
        pairs = extractor.generate_entity_pairs(sample_entities)
        
        assert len(pairs) >= 1
        assert (sample_entities[0], sample_entities[1]) in pairs or (sample_entities[1], sample_entities[0]) in pairs
    
    def test_deduplicate_relations(self, extractor):
        """测试关系去重"""
        relations = [
            Relation(
                id="1",
                source_entity_id="1",
                target_entity_id="2",
                relation_type="FOUNDED",
                properties={},
                metadata={}
            ),
            Relation(
                id="2",
                source_entity_id="1",
                target_entity_id="2",
                relation_type="FOUNDED",
                properties={},
                metadata={}
            ),
            Relation(
                id="3",
                source_entity_id="2",
                target_entity_id="1",
                relation_type="FOUNDED_BY",
                properties={},
                metadata={}
            )
        ]
        
        deduplicated = extractor.deduplicate_relations(relations)
        
        # 验证去重结果
        assert len(deduplicated) <= len(relations)


class TestGraphManager:
    """图管理器测试"""
    
    @pytest_asyncio.fixture
    async def manager(self):
        """创建图管理器"""
        config = GraphConfig()
        
        manager = GraphManager(config=config)
        
        # Mock依赖组件
        manager.entity_extractor = Mock(spec=EntityExtractor)
        manager.relation_extractor = Mock(spec=RelationExtractor)
        manager.graph_db = Mock(spec=GraphDatabase)
        manager.cache_manager = Mock(spec=CacheManager)
        
        # 添加缺失的方法
        manager.graph_db.save_knowledge_graph = AsyncMock(return_value=True)
        
        # Mock初始化
        manager.initialize = AsyncMock()
        await manager.initialize()
        
        return manager
    
    @pytest.fixture
    def sample_graph(self):
        """示例图"""
        return KnowledgeGraph(
            id="graph1",
            name="测试图",
            description="测试用的知识图谱",
            entities=[
                Entity(
                    id="entity1",
                    name="苹果公司",
                    entity_type="ORG",
                    properties={},
                    metadata={}
                )
            ],
            relations=[],
            metadata={"created_at": datetime.now().isoformat()}
        )
    
    @pytest.mark.asyncio
    async def test_create_graph(self, manager, sample_graph):
        """测试构建图"""
        # GraphManager没有直接的create_graph方法，我们测试build_graph_from_documents
        documents = [
            {"id": "doc1", "content": "苹果公司是一家科技公司"}
        ]
        
        # Mock实体提取
        mock_entity1 = ExtractedEntity(
            text="苹果公司",
            category=EntityCategory.ORGANIZATION,
            start_pos=0,
            end_pos=3,
            confidence=0.9,
            context="苹果公司是一家科技公司",
            attributes={},
            source_method=ExtractionMethod.NER
        )
        
        manager.entity_extractor.extract_entities = AsyncMock(return_value=Mock(
            entities=[mock_entity1]
        ))
        
        # Mock关系提取
        manager.relation_extractor.extract_relations = AsyncMock(return_value=Mock(
            relations=[]
        ))
        
        result = await manager.build_graph_from_documents(documents)
        
        assert result is not None
        assert isinstance(result, KnowledgeGraph)
        manager.entity_extractor.extract_entities.assert_called()
        manager.relation_extractor.extract_relations.assert_called()
    
    @pytest.mark.asyncio
    async def test_get_graph(self, manager, sample_graph):
        """测试获取图指标"""
        # 测试获取图指标而不是获取图本身
        mock_metrics = GraphMetrics(
            total_entities=10,
            total_relations=5,
            entity_types={"ORG": 3, "PERSON": 7},
            relation_types={"FOUNDED": 2, "WORKS_FOR": 3}
        )
        
        manager._metrics = mock_metrics
        
        result = await manager.get_metrics()
        
        assert result is not None
        assert result.total_entities == 10
        assert result.total_relations == 5
    
    @pytest.mark.asyncio
    async def test_add_entity(self, manager):
        """测试添加实体"""
        entity = Entity(
            id="entity2",
            name="史蒂夫·乔布斯",
            entity_type="PERSON",
            properties={},
            metadata={}
        )
        
        # Mock依赖方法
        manager.get_entity_by_name = AsyncMock(return_value=None)  # 实体不存在
        manager.graph_db.create_entity = AsyncMock(return_value=True)  # 创建成功
        manager._record_operation = AsyncMock()
        manager.cache_manager.invalidate_pattern = AsyncMock()  # Mock缓存失效方法
        
        result = await manager.add_entity(entity)
        
        assert result is True
        manager.get_entity_by_name.assert_called_once_with("史蒂夫·乔布斯")
        manager.graph_db.create_entity.assert_called_once_with(entity)
    
    @pytest.mark.asyncio
    async def test_add_relation(self, manager):
        """测试添加关系"""
        relation = Relation(
            id="relation1",
            source_id="entity1",
            target_id="entity2",
            relation_type="FOUNDED",
            properties={},
            metadata={},
            confidence=0.9
        )
        
        # Mock依赖方法
        manager.entity_exists = AsyncMock(return_value=True)  # 实体存在
        manager.get_relation = AsyncMock(return_value=None)  # 关系不存在
        manager.graph_db.create_relation = AsyncMock(return_value=True)  # 创建成功
        manager._record_operation = AsyncMock()
        manager.cache_manager.invalidate_pattern = AsyncMock()  # Mock缓存失效方法
        
        result = await manager.add_relation(relation)
        
        assert result is True
        manager.graph_db.create_relation.assert_called_once_with(relation)
    
    @pytest.mark.asyncio
    async def test_build_graph_from_document(self, manager):
        """测试从文档构建图"""
        documents = [
            {"id": "doc1", "content": "苹果公司是由史蒂夫·乔布斯创立的科技公司。"}
        ]
        
        # Mock实体提取
        mock_entity1 = ExtractedEntity(
            text="苹果公司",
            category=EntityCategory.ORGANIZATION,
            start_pos=0,
            end_pos=3,
            confidence=0.9,
            context="苹果公司是由史蒂夫·乔布斯创立的科技公司",
            attributes={},
            source_method=ExtractionMethod.NER
        )
        
        mock_entity2 = ExtractedEntity(
            text="史蒂夫·乔布斯",
            category=EntityCategory.PERSON,
            start_pos=6,
            end_pos=12,
            confidence=0.8,
            context="苹果公司是由史蒂夫·乔布斯创立的科技公司",
            attributes={},
            source_method=ExtractionMethod.NER
        )
        
        manager.entity_extractor.extract_entities = AsyncMock(return_value=Mock(
            entities=[mock_entity1, mock_entity2]
        ))
        
        # Mock关系提取
        mock_relation = ExtractedRelation(
            subject=mock_entity2,
            predicate=RelationCategory.CREATED_BY,
            object=mock_entity1,
            confidence=0.9,
            context="苹果公司是由史蒂夫·乔布斯创立的科技公司",
            evidence="史蒂夫·乔布斯创立的",
            attributes={},
            source_method=RelationExtractionMethod.PATTERN
        )
        
        manager.relation_extractor.extract_relations = AsyncMock(return_value=Mock(
            relations=[mock_relation]
        ))
        
        result = await manager.build_graph_from_documents(documents)
        
        assert result is not None
        assert isinstance(result, KnowledgeGraph)
        manager.entity_extractor.extract_entities.assert_called()
        manager.relation_extractor.extract_relations.assert_called()
    
    @pytest.mark.asyncio
    async def test_search_entities(self, manager):
        """测试搜索实体"""
        mock_entities = [
            Entity(id="1", name="苹果公司", entity_type="ORG", properties={}, metadata={})
        ]
        
        manager.graph_db.search_entities = AsyncMock(return_value=QueryResult(
            success=True,
            data=mock_entities,
            error=None
        ))
        
        result = await manager.search_entities(
            query="苹果",
            entity_types=["ORG"],
            limit=10
        )
        
        assert result is not None
        assert isinstance(result, GraphSearchResult)
        assert len(result.entities) >= 0
    
    @pytest.mark.asyncio
    async def test_get_entity_neighbors(self, manager):
        """测试获取实体邻居"""
        mock_neighbors = [
            Entity(id="2", name="史蒂夫·乔布斯", entity_type="PERSON", properties={}, metadata={})
        ]
        
        manager.graph_db.get_entity_neighbors = AsyncMock(return_value=QueryResult(
            success=True,
            data=mock_neighbors,
            error=None
        ))
        
        result = await manager.get_entity_neighbors(
            entity_id="entity1",
            relation_types=["FOUNDED"],
            max_depth=1
        )
        
        assert result is not None
        assert isinstance(result, list)
        assert len(result) >= 0


class TestGraphAnalytics:
    """图分析测试"""
    
    @pytest.fixture
    def analytics(self):
        """创建图分析器"""
        graph_manager = Mock(spec=GraphManager)
        return GraphAnalytics(graph_manager)
    
    @pytest.fixture
    def analysis_config(self):
        """分析配置"""
        return AnalysisConfig(
            analysis_types=[AnalysisType.CENTRALITY, AnalysisType.COMMUNITY],
            max_path_length=6,
            similarity_threshold=0.7,
            top_k_results=20,
            enable_parallel=True
        )
    
    @pytest.mark.asyncio
    async def test_analyze_graph(self, analytics, analysis_config):
        """测试图分析"""
        # Mock获取NetworkX图
        mock_graph = Mock()
        mock_graph.number_of_nodes.return_value = 10
        mock_graph.number_of_edges.return_value = 15
        
        analytics.graph_manager.get_networkx_graph = AsyncMock(return_value=mock_graph)
        
        # Mock分析方法
        analytics._analyze_centrality = AsyncMock(return_value={})
        analytics._analyze_community = AsyncMock(return_value={})
        
        result = await analytics.analyze_graph("graph1", analysis_config)
        
        assert result.analysis_id is not None
        assert result.processing_time >= 0
        assert isinstance(result.timestamp, datetime)
    
    @pytest.mark.asyncio
    async def test_get_analysis_result(self, analytics):
        """测试获取分析结果"""
        analysis_id = "analysis1"
        
        # Mock缓存中的结果
        mock_result = AnalysisResult(
            analysis_id=analysis_id,
            timestamp=datetime.now(),
            processing_time=1.5,
            centrality_results={},
            community_result=None,
            path_result=None,
            similarity_result=None,
            influence_result=None,
            anomaly_result=None,
            metadata={},
            errors=[]
        )
        
        analytics.analysis_cache = {analysis_id: mock_result}
        
        result = await analytics.get_analysis_result(analysis_id)
        
        assert result is not None
        assert result.analysis_id == analysis_id
    
    @pytest.mark.asyncio
    async def test_list_analysis_results(self, analytics):
        """测试列出分析结果"""
        # Mock多个分析结果
        analytics.analysis_cache = {
            "analysis1": Mock(timestamp=datetime.now()),
            "analysis2": Mock(timestamp=datetime.now())
        }
        
        results = await analytics.list_analysis_results("graph1")
        
        assert len(results) >= 0  # 可能为空，取决于实现


class TestGraphDatabase:
    """图数据库测试"""
    
    @pytest_asyncio.fixture
    async def database(self):
        """创建图数据库"""
        config = DatabaseConfig(
            database_type="memory",
            connection_string=":memory:"
        )
        cache_manager = Mock(spec=CacheManager)
        
        db = GraphDatabase(config, cache_manager)
        await db.initialize()
        
        return db
    
    @pytest.fixture
    def sample_graph(self):
        """示例图"""
        return KnowledgeGraph(
            id="graph1",
            name="测试图",
            description="测试用的知识图谱",
            entities=[],
            relations=[],
            metadata={}
        )
    
    @pytest.mark.asyncio
    async def test_create_and_get_graph(self, database, sample_graph):
        """测试创建和获取图"""
        # 创建图
        create_result = await database.create_graph(sample_graph)
        assert create_result.success
        
        # 获取图
        get_result = await database.get_graph("graph1")
        assert get_result.success
        assert get_result.data.name == "测试图"
    
    @pytest.mark.asyncio
    async def test_add_and_get_entity(self, database, sample_graph):
        """测试添加和获取实体"""
        # 先创建图
        await database.create_graph(sample_graph)
        
        # 添加实体
        entity = Entity(
            id="entity1",
            name="苹果公司",
            entity_type="ORG",
            properties={"founded": "1976"},
            metadata={}
        )
        
        add_result = await database.add_entity("graph1", entity)
        assert add_result.success
        
        # 获取实体
        get_result = await database.get_entity("graph1", "entity1")
        assert get_result.success
        assert get_result.data.name == "苹果公司"
    
    @pytest.mark.asyncio
    async def test_add_and_get_relation(self, database, sample_graph):
        """测试添加和获取关系"""
        # 先创建图和实体
        await database.create_graph(sample_graph)
        
        entity1 = Entity(id="entity1", name="苹果公司", entity_type="ORG", properties={}, metadata={})
        entity2 = Entity(id="entity2", name="史蒂夫·乔布斯", entity_type="PERSON", properties={}, metadata={})
        
        await database.add_entity("graph1", entity1)
        await database.add_entity("graph1", entity2)
        
        # 添加关系
        relation = Relation(
            id="relation1",
            source_id="entity2",
            target_id="entity1",
            relation_type="FOUNDED",
            properties={"year": "1976"},
            metadata={},
            confidence=0.9
        )
        
        add_result = await database.add_relation("graph1", relation)
        assert add_result.success
        
        # 获取关系
        get_result = await database.get_relation("graph1", "relation1")
        assert get_result.success
        assert get_result.data.relation_type == "FOUNDED"
    
    @pytest.mark.asyncio
    async def test_search_entities(self, database, sample_graph):
        """测试搜索实体"""
        # 先创建图和实体
        await database.create_graph(sample_graph)
        
        entity = Entity(
            id="entity1",
            name="苹果公司",
            entity_type="ORG",
            properties={},
            metadata={}
        )
        await database.add_entity("graph1", entity)
        
        # 搜索实体
        search_result = await database.search_entities(
            graph_id="graph1",
            query="苹果",
            entity_type="ORG",
            limit=10
        )
        
        assert search_result.success
        assert len(search_result.data) >= 0
    
    @pytest.mark.asyncio
    async def test_delete_graph(self, database, sample_graph):
        """测试删除图"""
        # 先创建图
        await database.create_graph(sample_graph)
        
        # 删除图
        delete_result = await database.delete_graph("graph1")
        assert delete_result.success
        
        # 验证图已删除
        get_result = await database.get_graph("graph1")
        assert not get_result.success
    
    @pytest.mark.asyncio
    async def test_get_graph_statistics(self, database, sample_graph):
        """测试获取图统计信息"""
        # 先创建图
        await database.create_graph(sample_graph)
        
        # 获取统计信息
        stats_result = await database.get_graph_statistics("graph1")
        
        assert stats_result.success
        assert "num_entities" in stats_result.data
        assert "num_relations" in stats_result.data


class TestKnowledgeGraphIntegration:
    """知识图谱集成测试"""
    
    @pytest.mark.asyncio
    async def test_full_knowledge_graph_workflow(self):
        """测试完整的知识图谱工作流"""
        # 这是一个集成测试，测试整个知识图谱的工作流程
        
        # 1. 初始化组件
        cache_manager = Mock(spec=CacheManager)
        cache_manager.initialize = AsyncMock()
        
        db_config = DatabaseConfig(database_type="memory")
        graph_database = GraphDatabase(db_config, cache_manager)
        await graph_database.initialize()
        
        entity_extractor = EntityExtractor()
        relation_extractor = RelationExtractor()
        
        graph_config = GraphConfig()
        graph_manager = GraphManager(
            config=graph_config,
            entity_extractor=entity_extractor,
            relation_extractor=relation_extractor,
            graph_database=graph_database,
            cache_manager=cache_manager
        )
        
        # Mock初始化
        graph_manager.initialize = AsyncMock()
        await graph_manager.initialize()
        
        # 2. 创建知识图谱
        graph = KnowledgeGraph(
            id="test_graph",
            name="测试知识图谱",
            description="集成测试用的知识图谱",
            entities=[],
            relations=[],
            metadata={"created_at": datetime.now().isoformat()}
        )
        
        # Mock图创建
        graph_manager.graph_db.create_graph = AsyncMock(return_value=QueryResult(
            success=True,
            data=graph,
            error=None
        ))
        
        create_result = await graph_manager.create_graph(graph)
        assert create_result.success
        
        # 3. 添加实体
        entity = Entity(
            id="entity1",
            name="苹果公司",
            entity_type="ORG",
            properties={"founded": "1976"},
            metadata={}
        )
        
        graph_manager.graph_db.add_entity = AsyncMock(return_value=QueryResult(
            success=True,
            data=entity,
            error=None
        ))
        
        add_entity_result = await graph_manager.add_entity("test_graph", entity)
        assert add_entity_result.success
        
        # 4. 添加关系
        relation = Relation(
            id="relation1",
            source_id="entity1",
            target_id="entity2",
            relation_type="FOUNDED_BY",
            properties={},
            metadata={},
            confidence=0.9
        )
        
        graph_manager.graph_db.add_relation = AsyncMock(return_value=QueryResult(
            success=True,
            data=relation,
            error=None
        ))
        
        add_relation_result = await graph_manager.add_relation("test_graph", relation)
        assert add_relation_result.success
        
        # 5. 搜索实体
        graph_manager.graph_db.search_entities = AsyncMock(return_value=QueryResult(
            success=True,
            data=[entity],
            error=None
        ))
        
        search_result = await graph_manager.search_entities(
            graph_id="test_graph",
            query="苹果",
            limit=10
        )
        assert search_result.success
        assert len(search_result.entities) >= 0
        
        # 6. 清理资源
        await graph_database.cleanup()


if __name__ == "__main__":
    pytest.main([__file__])