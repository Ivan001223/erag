from typing import List, Dict, Any, Optional, Set, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
import asyncio
import logging
from datetime import datetime, timedelta
from collections import defaultdict, deque
import json
import networkx as nx
import numpy as np
from concurrent.futures import ThreadPoolExecutor
import threading

from backend.models.knowledge import Entity, Relation, KnowledgeGraph
from backend.core.knowledge_graph.entity_extractor import EntityExtractor, ExtractedEntity, ExtractionResult
from backend.core.knowledge_graph.relation_extractor import RelationExtractor, ExtractedRelation, RelationExtractionResult
from backend.core.knowledge_graph.graph_database import GraphDatabase
from backend.api.deps import CacheManager

logger = logging.getLogger(__name__)

class GraphOperationType(Enum):
    """图操作类型"""
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    MERGE = "merge"
    QUERY = "query"
    ANALYZE = "analyze"

class GraphConsistencyLevel(Enum):
    """图一致性级别"""
    EVENTUAL = "eventual"  # 最终一致性
    STRONG = "strong"  # 强一致性
    WEAK = "weak"  # 弱一致性

@dataclass
class GraphConfig:
    """图配置"""
    max_entities: int = 100000
    max_relations: int = 500000
    enable_caching: bool = True
    cache_ttl: int = 3600  # 缓存TTL（秒）
    consistency_level: GraphConsistencyLevel = GraphConsistencyLevel.EVENTUAL
    enable_versioning: bool = True
    auto_merge_threshold: float = 0.9
    enable_inference: bool = True
    max_inference_depth: int = 3
    batch_size: int = 1000
    enable_metrics: bool = True
    
@dataclass
class GraphMetrics:
    """图指标"""
    total_entities: int = 0
    total_relations: int = 0
    entity_types: Dict[str, int] = field(default_factory=dict)
    relation_types: Dict[str, int] = field(default_factory=dict)
    avg_degree: float = 0.0
    clustering_coefficient: float = 0.0
    connected_components: int = 0
    diameter: int = 0
    density: float = 0.0
    last_updated: datetime = field(default_factory=datetime.now)
    
@dataclass
class GraphOperation:
    """图操作"""
    operation_id: str
    operation_type: GraphOperationType
    timestamp: datetime
    user_id: str
    data: Dict[str, Any]
    status: str = "pending"
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    
@dataclass
class GraphSearchResult:
    """图搜索结果"""
    entities: List[Entity]
    relations: List[Relation]
    subgraph: Optional[Dict[str, Any]] = None
    total_count: int = 0
    search_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

class GraphManager:
    """知识图谱管理器"""
    
    def __init__(self, config: GraphConfig = None):
        self.config = config or GraphConfig()
        self.entity_extractor = EntityExtractor()
        self.relation_extractor = RelationExtractor()
        self.graph_db = None
        self.cache_manager = None
        self.nx_graph = nx.MultiDiGraph()  # NetworkX图用于分析
        self._operation_queue = deque()
        self._operation_lock = threading.Lock()
        self._metrics = GraphMetrics()
        self._executor = ThreadPoolExecutor(max_workers=4)
        self._initialize_components()
    
    def _initialize_components(self):
        """初始化组件"""
        try:
            # 初始化图数据库
            self.graph_db = GraphDatabase()
            
            # 初始化缓存管理器
            if self.config.enable_caching:
                self.cache_manager = CacheManager()
            
            logger.info("图管理器组件初始化成功")
        except Exception as e:
            logger.error(f"图管理器组件初始化失败: {str(e)}")
    
    async def build_graph_from_documents(
        self,
        documents: List[Dict[str, Any]],
        user_id: str = None
    ) -> KnowledgeGraph:
        """从文档构建知识图谱"""
        start_time = datetime.now()
        
        try:
            # 提取实体和关系
            all_entities = []
            all_relations = []
            
            for doc in documents:
                doc_id = doc.get("id", "unknown")
                content = doc.get("content", "")
                
                # 提取实体
                entity_result = await self.entity_extractor.extract_entities(
                    text=content,
                    document_id=doc_id
                )
                
                # 提取关系
                relation_result = await self.relation_extractor.extract_relations(
                    entities=entity_result.entities,
                    text=content,
                    document_id=doc_id
                )
                
                all_entities.extend(entity_result.entities)
                all_relations.extend(relation_result.relations)
            
            # 去重和合并实体
            merged_entities = await self._merge_entities(all_entities)
            
            # 过滤和验证关系
            validated_relations = await self._validate_relations(all_relations, merged_entities)
            
            # 创建知识图谱
            knowledge_graph = await self._create_knowledge_graph(
                entities=merged_entities,
                relations=validated_relations,
                metadata={
                    "source_documents": len(documents),
                    "created_by": user_id,
                    "created_at": start_time.isoformat()
                }
            )
            
            # 更新NetworkX图
            await self._update_nx_graph(knowledge_graph)
            
            # 计算图指标
            if self.config.enable_metrics:
                await self._update_metrics()
            
            processing_time = (datetime.now() - start_time).total_seconds()
            logger.info(f"知识图谱构建完成，耗时: {processing_time:.2f}秒")
            
            return knowledge_graph
        
        except Exception as e:
            logger.error(f"知识图谱构建失败: {str(e)}")
            raise
    
    async def add_entity(self, entity: Entity, user_id: str = None) -> bool:
        """添加实体"""
        try:
            # 检查实体是否已存在
            existing_entity = await self.get_entity_by_name(entity.name)
            if existing_entity:
                # 合并实体信息
                merged_entity = await self._merge_entity_info(existing_entity, entity)
                return await self.update_entity(merged_entity, user_id)
            
            # 添加新实体
            success = await self.graph_db.create_entity(entity)
            
            if success:
                # 更新NetworkX图
                self.nx_graph.add_node(
                    entity.id,
                    name=entity.name,
                    entity_type=entity.entity_type,
                    properties=entity.properties
                )
                
                # 清除相关缓存
                if self.cache_manager:
                    await self.cache_manager.invalidate_pattern(f"entity:*")
                
                # 记录操作
                await self._record_operation(
                    operation_type=GraphOperationType.CREATE,
                    user_id=user_id,
                    data={"entity_id": entity.id, "entity_name": entity.name}
                )
                
                logger.info(f"实体添加成功: {entity.name}")
            
            return success
        
        except Exception as e:
            logger.error(f"添加实体失败: {str(e)}")
            return False
    
    async def add_relation(self, relation: Relation, user_id: str = None) -> bool:
        """添加关系"""
        try:
            # 验证关系的实体是否存在
            subject_exists = await self.entity_exists(relation.subject_id)
            object_exists = await self.entity_exists(relation.object_id)
            
            if not subject_exists or not object_exists:
                logger.warning(f"关系的实体不存在: {relation.subject_id} -> {relation.object_id}")
                return False
            
            # 检查关系是否已存在
            existing_relation = await self.get_relation(
                relation.subject_id,
                relation.relation_type,
                relation.object_id
            )
            
            if existing_relation:
                # 更新关系置信度和属性
                merged_relation = await self._merge_relation_info(existing_relation, relation)
                return await self.update_relation(merged_relation, user_id)
            
            # 添加新关系
            success = await self.graph_db.create_relation(relation)
            
            if success:
                # 更新NetworkX图
                self.nx_graph.add_edge(
                    relation.subject_id,
                    relation.object_id,
                    relation_type=relation.relation_type,
                    confidence=relation.confidence,
                    properties=relation.properties
                )
                
                # 清除相关缓存
                if self.cache_manager:
                    await self.cache_manager.invalidate_pattern(f"relation:*")
                
                # 记录操作
                await self._record_operation(
                    operation_type=GraphOperationType.CREATE,
                    user_id=user_id,
                    data={
                        "relation_id": relation.id,
                        "subject_id": relation.subject_id,
                        "object_id": relation.object_id,
                        "relation_type": relation.relation_type
                    }
                )
                
                logger.info(f"关系添加成功: {relation.subject_id} -> {relation.object_id}")
            
            return success
        
        except Exception as e:
            logger.error(f"添加关系失败: {str(e)}")
            return False
    
    async def get_entity_by_name(self, name: str) -> Optional[Entity]:
        """根据名称获取实体"""
        try:
            # 检查缓存
            if self.cache_manager:
                cache_key = f"entity:name:{name}"
                cached_entity = await self.cache_manager.get(cache_key)
                if cached_entity:
                    return Entity(**cached_entity)
            
            # 从数据库查询
            entity = await self.graph_db.get_entity_by_name(name)
            
            # 缓存结果
            if entity and self.cache_manager:
                await self.cache_manager.set(
                    cache_key,
                    entity.dict(),
                    ttl=self.config.cache_ttl
                )
            
            return entity
        
        except Exception as e:
            logger.error(f"获取实体失败: {str(e)}")
            return None
    
    async def get_entity_neighbors(
        self,
        entity_id: str,
        max_depth: int = 1,
        relation_types: List[str] = None
    ) -> List[Entity]:
        """获取实体邻居"""
        try:
            # 检查缓存
            cache_key = f"neighbors:{entity_id}:{max_depth}:{relation_types}"
            if self.cache_manager:
                cached_neighbors = await self.cache_manager.get(cache_key)
                if cached_neighbors:
                    return [Entity(**e) for e in cached_neighbors]
            
            # 从数据库查询
            neighbors = await self.graph_db.get_entity_neighbors(
                entity_id=entity_id,
                max_depth=max_depth,
                relation_types=relation_types
            )
            
            # 缓存结果
            if neighbors and self.cache_manager:
                await self.cache_manager.set(
                    cache_key,
                    [e.dict() for e in neighbors],
                    ttl=self.config.cache_ttl
                )
            
            return neighbors
        
        except Exception as e:
            logger.error(f"获取实体邻居失败: {str(e)}")
            return []
    
    async def search_entities(
        self,
        query: str,
        entity_types: List[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> GraphSearchResult:
        """搜索实体"""
        start_time = datetime.now()
        
        try:
            # 执行搜索
            entities = await self.graph_db.search_entities(
                query=query,
                entity_types=entity_types,
                limit=limit,
                offset=offset
            )
            
            # 获取相关关系
            relations = []
            if entities:
                entity_ids = [e.id for e in entities]
                relations = await self.graph_db.get_relations_between_entities(entity_ids)
            
            search_time = (datetime.now() - start_time).total_seconds()
            
            return GraphSearchResult(
                entities=entities,
                relations=relations,
                total_count=len(entities),
                search_time=search_time,
                metadata={
                    "query": query,
                    "entity_types": entity_types,
                    "limit": limit,
                    "offset": offset
                }
            )
        
        except Exception as e:
            logger.error(f"搜索实体失败: {str(e)}")
            return GraphSearchResult(entities=[], relations=[])
    
    async def find_shortest_path(
        self,
        source_entity_id: str,
        target_entity_id: str,
        max_depth: int = 6
    ) -> List[Tuple[Entity, Relation]]:
        """查找最短路径"""
        try:
            # 使用NetworkX查找最短路径
            if self.nx_graph.has_node(source_entity_id) and self.nx_graph.has_node(target_entity_id):
                try:
                    path = nx.shortest_path(
                        self.nx_graph,
                        source_entity_id,
                        target_entity_id
                    )
                    
                    # 构建路径结果
                    path_result = []
                    for i in range(len(path) - 1):
                        source_id = path[i]
                        target_id = path[i + 1]
                        
                        # 获取实体
                        source_entity = await self.graph_db.get_entity_by_id(source_id)
                        target_entity = await self.graph_db.get_entity_by_id(target_id)
                        
                        # 获取关系
                        relation = await self.graph_db.get_relation_between(
                            source_id, target_id
                        )
                        
                        if source_entity and relation:
                            path_result.append((source_entity, relation))
                    
                    # 添加最后一个实体
                    if path:
                        last_entity = await self.graph_db.get_entity_by_id(path[-1])
                        if last_entity:
                            path_result.append((last_entity, None))
                    
                    return path_result
                
                except nx.NetworkXNoPath:
                    logger.info(f"未找到路径: {source_entity_id} -> {target_entity_id}")
                    return []
            
            # 如果NetworkX图中没有节点，从数据库查询
            return await self.graph_db.find_shortest_path(
                source_entity_id,
                target_entity_id,
                max_depth
            )
        
        except Exception as e:
            logger.error(f"查找最短路径失败: {str(e)}")
            return []
    
    async def get_subgraph(
        self,
        entity_ids: List[str],
        max_depth: int = 2
    ) -> Dict[str, Any]:
        """获取子图"""
        try:
            # 获取实体
            entities = []
            for entity_id in entity_ids:
                entity = await self.graph_db.get_entity_by_id(entity_id)
                if entity:
                    entities.append(entity)
            
            # 扩展实体集合
            expanded_entity_ids = set(entity_ids)
            for entity_id in entity_ids:
                neighbors = await self.get_entity_neighbors(
                    entity_id=entity_id,
                    max_depth=max_depth
                )
                expanded_entity_ids.update([n.id for n in neighbors])
            
            # 获取所有相关实体
            all_entities = []
            for entity_id in expanded_entity_ids:
                entity = await self.graph_db.get_entity_by_id(entity_id)
                if entity:
                    all_entities.append(entity)
            
            # 获取实体间的关系
            relations = await self.graph_db.get_relations_between_entities(
                list(expanded_entity_ids)
            )
            
            # 构建子图
            subgraph = {
                "entities": [e.dict() for e in all_entities],
                "relations": [r.dict() for r in relations],
                "metadata": {
                    "center_entities": entity_ids,
                    "max_depth": max_depth,
                    "total_entities": len(all_entities),
                    "total_relations": len(relations)
                }
            }
            
            return subgraph
        
        except Exception as e:
            logger.error(f"获取子图失败: {str(e)}")
            return {"entities": [], "relations": [], "metadata": {}}
    
    async def analyze_graph_structure(self) -> Dict[str, Any]:
        """分析图结构"""
        try:
            if not self.nx_graph.nodes():
                await self._load_graph_to_nx()
            
            analysis = {}
            
            # 基本统计
            analysis["basic_stats"] = {
                "num_nodes": self.nx_graph.number_of_nodes(),
                "num_edges": self.nx_graph.number_of_edges(),
                "density": nx.density(self.nx_graph),
                "is_connected": nx.is_weakly_connected(self.nx_graph)
            }
            
            # 度分布
            degrees = [d for n, d in self.nx_graph.degree()]
            analysis["degree_stats"] = {
                "avg_degree": np.mean(degrees) if degrees else 0,
                "max_degree": max(degrees) if degrees else 0,
                "min_degree": min(degrees) if degrees else 0,
                "degree_distribution": np.histogram(degrees, bins=10)[0].tolist() if degrees else []
            }
            
            # 连通性分析
            if nx.is_weakly_connected(self.nx_graph):
                analysis["connectivity"] = {
                    "diameter": nx.diameter(self.nx_graph.to_undirected()),
                    "average_shortest_path_length": nx.average_shortest_path_length(
                        self.nx_graph.to_undirected()
                    )
                }
            else:
                components = list(nx.weakly_connected_components(self.nx_graph))
                analysis["connectivity"] = {
                    "num_components": len(components),
                    "largest_component_size": max(len(c) for c in components) if components else 0
                }
            
            # 中心性分析
            if self.nx_graph.number_of_nodes() > 0:
                undirected_graph = self.nx_graph.to_undirected()
                
                # 度中心性
                degree_centrality = nx.degree_centrality(undirected_graph)
                top_degree_nodes = sorted(
                    degree_centrality.items(),
                    key=lambda x: x[1],
                    reverse=True
                )[:10]
                
                # 介数中心性
                betweenness_centrality = nx.betweenness_centrality(undirected_graph)
                top_betweenness_nodes = sorted(
                    betweenness_centrality.items(),
                    key=lambda x: x[1],
                    reverse=True
                )[:10]
                
                analysis["centrality"] = {
                    "top_degree_nodes": top_degree_nodes,
                    "top_betweenness_nodes": top_betweenness_nodes
                }
            
            # 聚类分析
            if self.nx_graph.number_of_nodes() > 2:
                try:
                    clustering_coefficient = nx.average_clustering(
                        self.nx_graph.to_undirected()
                    )
                    analysis["clustering"] = {
                        "average_clustering_coefficient": clustering_coefficient
                    }
                except:
                    analysis["clustering"] = {"average_clustering_coefficient": 0}
            
            return analysis
        
        except Exception as e:
            logger.error(f"图结构分析失败: {str(e)}")
            return {}
    
    async def detect_communities(self, algorithm: str = "louvain") -> Dict[str, List[str]]:
        """检测社区"""
        try:
            if not self.nx_graph.nodes():
                await self._load_graph_to_nx()
            
            undirected_graph = self.nx_graph.to_undirected()
            
            if algorithm == "louvain":
                try:
                    import community as community_louvain
                    partition = community_louvain.best_partition(undirected_graph)
                except ImportError:
                    logger.warning("python-louvain未安装，使用默认社区检测")
                    # 使用简单的连通组件作为社区
                    components = nx.connected_components(undirected_graph)
                    partition = {}
                    for i, component in enumerate(components):
                        for node in component:
                            partition[node] = i
            
            # 按社区分组
            communities = defaultdict(list)
            for node, community_id in partition.items():
                communities[f"community_{community_id}"].append(node)
            
            return dict(communities)
        
        except Exception as e:
            logger.error(f"社区检测失败: {str(e)}")
            return {}
    
    async def update_entity(self, entity: Entity, user_id: str = None) -> bool:
        """更新实体"""
        try:
            success = await self.graph_db.update_entity(entity)
            
            if success:
                # 更新NetworkX图
                if self.nx_graph.has_node(entity.id):
                    self.nx_graph.nodes[entity.id].update({
                        "name": entity.name,
                        "entity_type": entity.entity_type,
                        "properties": entity.properties
                    })
                
                # 清除相关缓存
                if self.cache_manager:
                    await self.cache_manager.invalidate_pattern(f"entity:*")
                
                # 记录操作
                await self._record_operation(
                    operation_type=GraphOperationType.UPDATE,
                    user_id=user_id,
                    data={"entity_id": entity.id, "entity_name": entity.name}
                )
            
            return success
        
        except Exception as e:
            logger.error(f"更新实体失败: {str(e)}")
            return False
    
    async def delete_entity(self, entity_id: str, user_id: str = None) -> bool:
        """删除实体"""
        try:
            # 删除相关关系
            relations = await self.graph_db.get_entity_relations(entity_id)
            for relation in relations:
                await self.graph_db.delete_relation(relation.id)
            
            # 删除实体
            success = await self.graph_db.delete_entity(entity_id)
            
            if success:
                # 从NetworkX图中删除
                if self.nx_graph.has_node(entity_id):
                    self.nx_graph.remove_node(entity_id)
                
                # 清除相关缓存
                if self.cache_manager:
                    await self.cache_manager.invalidate_pattern(f"entity:*")
                    await self.cache_manager.invalidate_pattern(f"relation:*")
                
                # 记录操作
                await self._record_operation(
                    operation_type=GraphOperationType.DELETE,
                    user_id=user_id,
                    data={"entity_id": entity_id}
                )
            
            return success
        
        except Exception as e:
            logger.error(f"删除实体失败: {str(e)}")
            return False
    
    async def entity_exists(self, entity_id: str) -> bool:
        """检查实体是否存在"""
        try:
            entity = await self.graph_db.get_entity_by_id(entity_id)
            return entity is not None
        except Exception as e:
            logger.error(f"检查实体存在性失败: {str(e)}")
            return False
    
    async def get_relation(
        self,
        subject_id: str,
        relation_type: str,
        object_id: str
    ) -> Optional[Relation]:
        """获取关系"""
        try:
            return await self.graph_db.get_relation(
                subject_id=subject_id,
                relation_type=relation_type,
                object_id=object_id
            )
        except Exception as e:
            logger.error(f"获取关系失败: {str(e)}")
            return None
    
    async def update_relation(self, relation: Relation, user_id: str = None) -> bool:
        """更新关系"""
        try:
            success = await self.graph_db.update_relation(relation)
            
            if success:
                # 更新NetworkX图
                if self.nx_graph.has_edge(relation.subject_id, relation.object_id):
                    edge_data = self.nx_graph.get_edge_data(
                        relation.subject_id,
                        relation.object_id
                    )
                    if edge_data:
                        edge_data[0].update({
                            "relation_type": relation.relation_type,
                            "confidence": relation.confidence,
                            "properties": relation.properties
                        })
                
                # 清除相关缓存
                if self.cache_manager:
                    await self.cache_manager.invalidate_pattern(f"relation:*")
                
                # 记录操作
                await self._record_operation(
                    operation_type=GraphOperationType.UPDATE,
                    user_id=user_id,
                    data={"relation_id": relation.id}
                )
            
            return success
        
        except Exception as e:
            logger.error(f"更新关系失败: {str(e)}")
            return False
    
    async def get_metrics(self) -> GraphMetrics:
        """获取图指标"""
        if self.config.enable_metrics:
            await self._update_metrics()
        return self._metrics
    
    async def _merge_entities(self, entities: List[ExtractedEntity]) -> List[Entity]:
        """合并实体"""
        # 按名称分组
        entity_groups = defaultdict(list)
        for entity in entities:
            canonical_name = entity.canonical_form.lower()
            entity_groups[canonical_name].append(entity)
        
        merged_entities = []
        for group in entity_groups.values():
            if len(group) == 1:
                # 单个实体，直接转换
                extracted_entity = group[0]
                entity = Entity(
                    id=f"entity_{len(merged_entities)}",
                    name=extracted_entity.text,
                    entity_type=extracted_entity.category.value,
                    properties={
                        "confidence": extracted_entity.confidence,
                        "canonical_form": extracted_entity.canonical_form,
                        "aliases": extracted_entity.aliases,
                        "context": extracted_entity.context
                    },
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                )
                merged_entities.append(entity)
            else:
                # 多个实体，需要合并
                best_entity = max(group, key=lambda x: x.confidence)
                all_aliases = set()
                all_contexts = []
                total_confidence = 0
                
                for e in group:
                    all_aliases.update(e.aliases)
                    all_contexts.append(e.context)
                    total_confidence += e.confidence
                
                merged_entity = Entity(
                    id=f"entity_{len(merged_entities)}",
                    name=best_entity.text,
                    entity_type=best_entity.category.value,
                    properties={
                        "confidence": total_confidence / len(group),
                        "canonical_form": best_entity.canonical_form,
                        "aliases": list(all_aliases),
                        "contexts": all_contexts,
                        "merge_count": len(group)
                    },
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                )
                merged_entities.append(merged_entity)
        
        return merged_entities
    
    async def _validate_relations(self, relations: List[ExtractedRelation], entities: List[Entity]) -> List[Relation]:
        """验证关系"""
        # 创建实体名称到ID的映射
        entity_name_to_id = {}
        for entity in entities:
            entity_name_to_id[entity.name] = entity.id
            # 添加别名映射
            aliases = entity.properties.get("aliases", [])
            for alias in aliases:
                entity_name_to_id[alias] = entity.id
        
        validated_relations = []
        for extracted_relation in relations:
            subject_name = extracted_relation.subject.text
            object_name = extracted_relation.object.text
            
            subject_id = entity_name_to_id.get(subject_name)
            object_id = entity_name_to_id.get(object_name)
            
            if subject_id and object_id and subject_id != object_id:
                relation = Relation(
                    id=f"relation_{len(validated_relations)}",
                    subject_id=subject_id,
                    object_id=object_id,
                    relation_type=extracted_relation.predicate.value,
                    confidence=extracted_relation.confidence,
                    properties={
                        "evidence": extracted_relation.evidence,
                        "context": extracted_relation.context,
                        "source_method": extracted_relation.source_method.value,
                        "attributes": extracted_relation.attributes
                    },
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                )
                validated_relations.append(relation)
        
        return validated_relations
    
    async def _create_knowledge_graph(
        self,
        entities: List[Entity],
        relations: List[Relation],
        metadata: Dict[str, Any]
    ) -> KnowledgeGraph:
        """创建知识图谱"""
        knowledge_graph = KnowledgeGraph(
            id=f"kg_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            name=f"Knowledge Graph {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            description="Auto-generated knowledge graph",
            entities=entities,
            relations=relations,
            metadata=metadata,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        # 保存到数据库
        await self.graph_db.save_knowledge_graph(knowledge_graph)
        
        return knowledge_graph
    
    async def _update_nx_graph(self, knowledge_graph: KnowledgeGraph):
        """更新NetworkX图"""
        # 清空现有图
        self.nx_graph.clear()
        
        # 添加节点
        for entity in knowledge_graph.entities:
            self.nx_graph.add_node(
                entity.id,
                name=entity.name,
                entity_type=entity.entity_type,
                properties=entity.properties
            )
        
        # 添加边
        for relation in knowledge_graph.relations:
            self.nx_graph.add_edge(
                relation.subject_id,
                relation.object_id,
                relation_type=relation.relation_type,
                confidence=relation.confidence,
                properties=relation.properties
            )
    
    async def _load_graph_to_nx(self):
        """从数据库加载图到NetworkX"""
        try:
            # 加载所有实体
            entities = await self.graph_db.get_all_entities()
            for entity in entities:
                self.nx_graph.add_node(
                    entity.id,
                    name=entity.name,
                    entity_type=entity.entity_type,
                    properties=entity.properties
                )
            
            # 加载所有关系
            relations = await self.graph_db.get_all_relations()
            for relation in relations:
                self.nx_graph.add_edge(
                    relation.subject_id,
                    relation.object_id,
                    relation_type=relation.relation_type,
                    confidence=relation.confidence,
                    properties=relation.properties
                )
        
        except Exception as e:
            logger.error(f"加载图到NetworkX失败: {str(e)}")
    
    async def _update_metrics(self):
        """更新图指标"""
        try:
            # 基本统计
            self._metrics.total_entities = await self.graph_db.count_entities()
            self._metrics.total_relations = await self.graph_db.count_relations()
            
            # 实体类型分布
            self._metrics.entity_types = await self.graph_db.get_entity_type_distribution()
            
            # 关系类型分布
            self._metrics.relation_types = await self.graph_db.get_relation_type_distribution()
            
            # NetworkX图指标
            if self.nx_graph.number_of_nodes() > 0:
                degrees = [d for n, d in self.nx_graph.degree()]
                self._metrics.avg_degree = np.mean(degrees) if degrees else 0
                self._metrics.density = nx.density(self.nx_graph)
                
                if nx.is_weakly_connected(self.nx_graph):
                    self._metrics.connected_components = 1
                    try:
                        self._metrics.diameter = nx.diameter(self.nx_graph.to_undirected())
                    except:
                        self._metrics.diameter = 0
                else:
                    components = list(nx.weakly_connected_components(self.nx_graph))
                    self._metrics.connected_components = len(components)
                
                try:
                    self._metrics.clustering_coefficient = nx.average_clustering(
                        self.nx_graph.to_undirected()
                    )
                except:
                    self._metrics.clustering_coefficient = 0
            
            self._metrics.last_updated = datetime.now()
        
        except Exception as e:
            logger.error(f"更新图指标失败: {str(e)}")
    
    async def _merge_entity_info(self, existing: Entity, new: Entity) -> Entity:
        """合并实体信息"""
        # 合并属性
        merged_properties = existing.properties.copy()
        merged_properties.update(new.properties)
        
        # 更新置信度（取平均值）
        existing_confidence = existing.properties.get("confidence", 0.5)
        new_confidence = new.properties.get("confidence", 0.5)
        merged_properties["confidence"] = (existing_confidence + new_confidence) / 2
        
        # 合并别名
        existing_aliases = set(existing.properties.get("aliases", []))
        new_aliases = set(new.properties.get("aliases", []))
        merged_properties["aliases"] = list(existing_aliases | new_aliases)
        
        existing.properties = merged_properties
        existing.updated_at = datetime.now()
        
        return existing
    
    async def _merge_relation_info(self, existing: Relation, new: Relation) -> Relation:
        """合并关系信息"""
        # 更新置信度（取最大值）
        existing.confidence = max(existing.confidence, new.confidence)
        
        # 合并属性
        merged_properties = existing.properties.copy()
        merged_properties.update(new.properties)
        existing.properties = merged_properties
        
        existing.updated_at = datetime.now()
        
        return existing
    
    async def _record_operation(
        self,
        operation_type: GraphOperationType,
        user_id: str = None,
        data: Dict[str, Any] = None
    ):
        """记录操作"""
        operation = GraphOperation(
            operation_id=f"op_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}",
            operation_type=operation_type,
            timestamp=datetime.now(),
            user_id=user_id or "system",
            data=data or {},
            status="completed"
        )
        
        with self._operation_lock:
            self._operation_queue.append(operation)
            
            # 保持队列大小
            if len(self._operation_queue) > 1000:
                self._operation_queue.popleft()
    
    def get_operation_history(self, limit: int = 100) -> List[GraphOperation]:
        """获取操作历史"""
        with self._operation_lock:
            return list(self._operation_queue)[-limit:]
    
    async def cleanup(self):
        """清理资源"""
        try:
            if self._executor:
                self._executor.shutdown(wait=True)
            
            if self.graph_db:
                await self.graph_db.close()
            
            if self.cache_manager:
                await self.cache_manager.close()
            
            logger.info("图管理器资源清理完成")
        
        except Exception as e:
            logger.error(f"图管理器资源清理失败: {str(e)}")