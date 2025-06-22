from typing import List, Dict, Any, Optional, Tuple, Set, Union
from dataclasses import dataclass, field
from enum import Enum
import asyncio
import logging
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import json
import numpy as np
import networkx as nx
from concurrent.futures import ThreadPoolExecutor
import math
from itertools import combinations

from backend.models.knowledge import Entity, Relation, KnowledgeGraph
from backend.core.knowledge_graph.graph_manager import GraphManager

logger = logging.getLogger(__name__)

class AnalysisType(Enum):
    """分析类型"""
    CENTRALITY = "centrality"  # 中心性分析
    COMMUNITY = "community"  # 社区检测
    PATH = "path"  # 路径分析
    SIMILARITY = "similarity"  # 相似性分析
    INFLUENCE = "influence"  # 影响力分析
    CLUSTERING = "clustering"  # 聚类分析
    ANOMALY = "anomaly"  # 异常检测
    EVOLUTION = "evolution"  # 演化分析

class CentralityMetric(Enum):
    """中心性指标"""
    DEGREE = "degree"  # 度中心性
    BETWEENNESS = "betweenness"  # 介数中心性
    CLOSENESS = "closeness"  # 接近中心性
    EIGENVECTOR = "eigenvector"  # 特征向量中心性
    PAGERANK = "pagerank"  # PageRank
    KATZ = "katz"  # Katz中心性

class CommunityAlgorithm(Enum):
    """社区检测算法"""
    LOUVAIN = "louvain"  # Louvain算法
    LEIDEN = "leiden"  # Leiden算法
    LABEL_PROPAGATION = "label_propagation"  # 标签传播
    GIRVAN_NEWMAN = "girvan_newman"  # Girvan-Newman算法
    MODULARITY = "modularity"  # 模块度优化

@dataclass
class AnalysisConfig:
    """分析配置"""
    analysis_types: List[AnalysisType] = field(default_factory=list)
    centrality_metrics: List[CentralityMetric] = field(default_factory=list)
    community_algorithm: CommunityAlgorithm = CommunityAlgorithm.LOUVAIN
    max_path_length: int = 6
    similarity_threshold: float = 0.7
    top_k_results: int = 20
    enable_parallel: bool = True
    cache_results: bool = True
    
    def __post_init__(self):
        if not self.analysis_types:
            self.analysis_types = [AnalysisType.CENTRALITY, AnalysisType.COMMUNITY]
        if not self.centrality_metrics:
            self.centrality_metrics = [CentralityMetric.DEGREE, CentralityMetric.PAGERANK]

@dataclass
class CentralityResult:
    """中心性分析结果"""
    metric: CentralityMetric
    scores: Dict[str, float]  # entity_id -> score
    top_entities: List[Tuple[str, float]]  # (entity_id, score)
    statistics: Dict[str, float]
    
@dataclass
class CommunityResult:
    """社区检测结果"""
    algorithm: CommunityAlgorithm
    communities: Dict[str, List[str]]  # community_id -> [entity_ids]
    modularity: float
    num_communities: int
    community_sizes: List[int]
    entity_to_community: Dict[str, str]  # entity_id -> community_id
    
@dataclass
class PathAnalysisResult:
    """路径分析结果"""
    shortest_paths: Dict[Tuple[str, str], List[str]]  # (source, target) -> path
    path_lengths: Dict[Tuple[str, str], int]
    diameter: int
    average_path_length: float
    connectivity_matrix: Dict[str, Dict[str, bool]]
    
@dataclass
class SimilarityResult:
    """相似性分析结果"""
    similarity_matrix: Dict[str, Dict[str, float]]  # entity_id -> entity_id -> similarity
    similar_pairs: List[Tuple[str, str, float]]  # (entity1, entity2, similarity)
    clusters: Dict[str, List[str]]  # cluster_id -> [entity_ids]
    
@dataclass
class InfluenceResult:
    """影响力分析结果"""
    influence_scores: Dict[str, float]  # entity_id -> influence_score
    influence_paths: Dict[str, List[List[str]]]  # entity_id -> [influence_paths]
    cascade_potential: Dict[str, float]  # entity_id -> cascade_potential
    top_influencers: List[Tuple[str, float]]
    
@dataclass
class AnomalyResult:
    """异常检测结果"""
    anomalous_entities: List[Tuple[str, float]]  # (entity_id, anomaly_score)
    anomalous_relations: List[Tuple[str, float]]  # (relation_id, anomaly_score)
    anomaly_patterns: List[Dict[str, Any]]
    statistics: Dict[str, float]
    
@dataclass
class GraphAnalysisResult:
    """图分析结果"""
    analysis_id: str
    timestamp: datetime
    graph_id: str
    config: AnalysisConfig
    centrality_results: Dict[CentralityMetric, CentralityResult] = field(default_factory=dict)
    community_result: Optional[CommunityResult] = None
    path_result: Optional[PathAnalysisResult] = None
    similarity_result: Optional[SimilarityResult] = None
    influence_result: Optional[InfluenceResult] = None
    anomaly_result: Optional[AnomalyResult] = None
    processing_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)

# 为了向后兼容，提供AnalysisResult别名
AnalysisResult = GraphAnalysisResult

class GraphAnalytics:
    """图分析器"""
    
    def __init__(self, graph_manager: GraphManager):
        self.graph_manager = graph_manager
        self._executor = ThreadPoolExecutor(max_workers=4)
        self._analysis_cache = {}
        
    async def analyze_graph(
        self,
        graph_id: str,
        config: AnalysisConfig = None
    ) -> GraphAnalysisResult:
        """分析图"""
        start_time = datetime.now()
        config = config or AnalysisConfig()
        
        analysis_id = f"analysis_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        
        result = GraphAnalysisResult(
            analysis_id=analysis_id,
            timestamp=start_time,
            graph_id=graph_id,
            config=config
        )
        
        try:
            # 获取NetworkX图
            nx_graph = await self._get_networkx_graph(graph_id)
            if not nx_graph or nx_graph.number_of_nodes() == 0:
                result.errors.append("图为空或不存在")
                return result
            
            # 并行执行分析
            tasks = []
            
            # 中心性分析
            if AnalysisType.CENTRALITY in config.analysis_types:
                tasks.append(self._analyze_centrality(nx_graph, config.centrality_metrics))
            
            # 社区检测
            if AnalysisType.COMMUNITY in config.analysis_types:
                tasks.append(self._detect_communities(nx_graph, config.community_algorithm))
            
            # 路径分析
            if AnalysisType.PATH in config.analysis_types:
                tasks.append(self._analyze_paths(nx_graph, config.max_path_length))
            
            # 相似性分析
            if AnalysisType.SIMILARITY in config.analysis_types:
                tasks.append(self._analyze_similarity(nx_graph, config.similarity_threshold))
            
            # 影响力分析
            if AnalysisType.INFLUENCE in config.analysis_types:
                tasks.append(self._analyze_influence(nx_graph))
            
            # 异常检测
            if AnalysisType.ANOMALY in config.analysis_types:
                tasks.append(self._detect_anomalies(nx_graph))
            
            # 执行分析任务
            if config.enable_parallel:
                results = await asyncio.gather(*tasks, return_exceptions=True)
            else:
                results = []
                for task in tasks:
                    try:
                        task_result = await task
                        results.append(task_result)
                    except Exception as e:
                        results.append(e)
            
            # 处理结果
            task_index = 0
            
            if AnalysisType.CENTRALITY in config.analysis_types:
                centrality_result = results[task_index]
                if isinstance(centrality_result, dict):
                    result.centrality_results = centrality_result
                elif isinstance(centrality_result, Exception):
                    result.errors.append(f"中心性分析失败: {str(centrality_result)}")
                task_index += 1
            
            if AnalysisType.COMMUNITY in config.analysis_types:
                community_result = results[task_index]
                if isinstance(community_result, CommunityResult):
                    result.community_result = community_result
                elif isinstance(community_result, Exception):
                    result.errors.append(f"社区检测失败: {str(community_result)}")
                task_index += 1
            
            if AnalysisType.PATH in config.analysis_types:
                path_result = results[task_index]
                if isinstance(path_result, PathAnalysisResult):
                    result.path_result = path_result
                elif isinstance(path_result, Exception):
                    result.errors.append(f"路径分析失败: {str(path_result)}")
                task_index += 1
            
            if AnalysisType.SIMILARITY in config.analysis_types:
                similarity_result = results[task_index]
                if isinstance(similarity_result, SimilarityResult):
                    result.similarity_result = similarity_result
                elif isinstance(similarity_result, Exception):
                    result.errors.append(f"相似性分析失败: {str(similarity_result)}")
                task_index += 1
            
            if AnalysisType.INFLUENCE in config.analysis_types:
                influence_result = results[task_index]
                if isinstance(influence_result, InfluenceResult):
                    result.influence_result = influence_result
                elif isinstance(influence_result, Exception):
                    result.errors.append(f"影响力分析失败: {str(influence_result)}")
                task_index += 1
            
            if AnalysisType.ANOMALY in config.analysis_types:
                anomaly_result = results[task_index]
                if isinstance(anomaly_result, AnomalyResult):
                    result.anomaly_result = anomaly_result
                elif isinstance(anomaly_result, Exception):
                    result.errors.append(f"异常检测失败: {str(anomaly_result)}")
                task_index += 1
            
            # 计算处理时间
            result.processing_time = (datetime.now() - start_time).total_seconds()
            
            # 添加元数据
            result.metadata = {
                "num_nodes": nx_graph.number_of_nodes(),
                "num_edges": nx_graph.number_of_edges(),
                "density": nx.density(nx_graph),
                "is_connected": nx.is_weakly_connected(nx_graph)
            }
            
            # 缓存结果
            if config.cache_results:
                self._analysis_cache[analysis_id] = result
            
            logger.info(f"图分析完成: {analysis_id}, 耗时: {result.processing_time:.2f}秒")
            
        except Exception as e:
            result.errors.append(f"图分析失败: {str(e)}")
            logger.error(f"图分析失败: {str(e)}")
        
        return result
    
    async def _get_networkx_graph(self, graph_id: str) -> Optional[nx.MultiDiGraph]:
        """获取NetworkX图"""
        try:
            # 从图管理器获取NetworkX图
            return self.graph_manager.nx_graph
        except Exception as e:
            logger.error(f"获取NetworkX图失败: {str(e)}")
            return None
    
    async def _analyze_centrality(
        self,
        graph: nx.MultiDiGraph,
        metrics: List[CentralityMetric]
    ) -> Dict[CentralityMetric, CentralityResult]:
        """分析中心性"""
        results = {}
        
        # 转换为无向图用于某些中心性计算
        undirected_graph = graph.to_undirected()
        
        for metric in metrics:
            try:
                if metric == CentralityMetric.DEGREE:
                    scores = nx.degree_centrality(undirected_graph)
                elif metric == CentralityMetric.BETWEENNESS:
                    scores = nx.betweenness_centrality(undirected_graph)
                elif metric == CentralityMetric.CLOSENESS:
                    scores = nx.closeness_centrality(undirected_graph)
                elif metric == CentralityMetric.EIGENVECTOR:
                    try:
                        scores = nx.eigenvector_centrality(undirected_graph, max_iter=1000)
                    except nx.PowerIterationFailedConvergence:
                        scores = nx.eigenvector_centrality_numpy(undirected_graph)
                elif metric == CentralityMetric.PAGERANK:
                    scores = nx.pagerank(graph)
                elif metric == CentralityMetric.KATZ:
                    try:
                        scores = nx.katz_centrality(graph)
                    except nx.PowerIterationFailedConvergence:
                        scores = nx.katz_centrality_numpy(graph)
                else:
                    continue
                
                # 排序获取top实体
                top_entities = sorted(
                    scores.items(),
                    key=lambda x: x[1],
                    reverse=True
                )[:20]
                
                # 计算统计信息
                score_values = list(scores.values())
                statistics = {
                    "mean": np.mean(score_values),
                    "std": np.std(score_values),
                    "min": np.min(score_values),
                    "max": np.max(score_values),
                    "median": np.median(score_values)
                }
                
                results[metric] = CentralityResult(
                    metric=metric,
                    scores=scores,
                    top_entities=top_entities,
                    statistics=statistics
                )
                
            except Exception as e:
                logger.error(f"中心性分析失败 ({metric.value}): {str(e)}")
        
        return results
    
    async def _detect_communities(
        self,
        graph: nx.MultiDiGraph,
        algorithm: CommunityAlgorithm
    ) -> CommunityResult:
        """检测社区"""
        try:
            undirected_graph = graph.to_undirected()
            
            if algorithm == CommunityAlgorithm.LOUVAIN:
                partition = await self._louvain_communities(undirected_graph)
            elif algorithm == CommunityAlgorithm.LABEL_PROPAGATION:
                partition = await self._label_propagation_communities(undirected_graph)
            elif algorithm == CommunityAlgorithm.GIRVAN_NEWMAN:
                partition = await self._girvan_newman_communities(undirected_graph)
            else:
                # 默认使用连通组件
                partition = await self._connected_components_communities(undirected_graph)
            
            # 构建社区结果
            communities = defaultdict(list)
            entity_to_community = {}
            
            for entity_id, community_id in partition.items():
                community_key = f"community_{community_id}"
                communities[community_key].append(entity_id)
                entity_to_community[entity_id] = community_key
            
            # 计算模块度
            try:
                modularity = nx.community.modularity(
                    undirected_graph,
                    communities.values()
                )
            except:
                modularity = 0.0
            
            # 社区大小统计
            community_sizes = [len(members) for members in communities.values()]
            
            return CommunityResult(
                algorithm=algorithm,
                communities=dict(communities),
                modularity=modularity,
                num_communities=len(communities),
                community_sizes=community_sizes,
                entity_to_community=entity_to_community
            )
            
        except Exception as e:
            logger.error(f"社区检测失败: {str(e)}")
            raise
    
    async def _louvain_communities(self, graph: nx.Graph) -> Dict[str, int]:
        """Louvain社区检测"""
        try:
            import community as community_louvain
            partition = community_louvain.best_partition(graph)
            return partition
        except ImportError:
            logger.warning("python-louvain未安装，使用连通组件代替")
            return await self._connected_components_communities(graph)
    
    async def _label_propagation_communities(self, graph: nx.Graph) -> Dict[str, int]:
        """标签传播社区检测"""
        communities = nx.community.label_propagation_communities(graph)
        partition = {}
        for i, community in enumerate(communities):
            for node in community:
                partition[node] = i
        return partition
    
    async def _girvan_newman_communities(self, graph: nx.Graph) -> Dict[str, int]:
        """Girvan-Newman社区检测"""
        communities_generator = nx.community.girvan_newman(graph)
        # 取第一级分割
        communities = next(communities_generator)
        partition = {}
        for i, community in enumerate(communities):
            for node in community:
                partition[node] = i
        return partition
    
    async def _connected_components_communities(self, graph: nx.Graph) -> Dict[str, int]:
        """连通组件社区检测"""
        components = nx.connected_components(graph)
        partition = {}
        for i, component in enumerate(components):
            for node in component:
                partition[node] = i
        return partition
    
    async def _analyze_paths(
        self,
        graph: nx.MultiDiGraph,
        max_length: int
    ) -> PathAnalysisResult:
        """分析路径"""
        try:
            undirected_graph = graph.to_undirected()
            
            # 计算最短路径
            shortest_paths = {}
            path_lengths = {}
            
            nodes = list(undirected_graph.nodes())
            
            # 限制节点数量以避免计算过于复杂
            if len(nodes) > 100:
                nodes = nodes[:100]
            
            for source in nodes:
                for target in nodes:
                    if source != target:
                        try:
                            path = nx.shortest_path(undirected_graph, source, target)
                            if len(path) <= max_length + 1:  # +1因为路径包含起点和终点
                                shortest_paths[(source, target)] = path
                                path_lengths[(source, target)] = len(path) - 1
                        except nx.NetworkXNoPath:
                            continue
            
            # 计算图的直径
            diameter = 0
            if nx.is_connected(undirected_graph):
                try:
                    diameter = nx.diameter(undirected_graph)
                except:
                    diameter = 0
            
            # 计算平均路径长度
            if path_lengths:
                average_path_length = np.mean(list(path_lengths.values()))
            else:
                average_path_length = 0
            
            # 构建连通性矩阵
            connectivity_matrix = {}
            for node in nodes:
                connectivity_matrix[node] = {}
                for other_node in nodes:
                    connectivity_matrix[node][other_node] = (node, other_node) in shortest_paths
            
            return PathAnalysisResult(
                shortest_paths=shortest_paths,
                path_lengths=path_lengths,
                diameter=diameter,
                average_path_length=average_path_length,
                connectivity_matrix=connectivity_matrix
            )
            
        except Exception as e:
            logger.error(f"路径分析失败: {str(e)}")
            raise
    
    async def _analyze_similarity(
        self,
        graph: nx.MultiDiGraph,
        threshold: float
    ) -> SimilarityResult:
        """分析相似性"""
        try:
            nodes = list(graph.nodes())
            similarity_matrix = {}
            similar_pairs = []
            
            # 计算节点相似性
            for node1 in nodes:
                similarity_matrix[node1] = {}
                for node2 in nodes:
                    if node1 == node2:
                        similarity = 1.0
                    else:
                        # 基于共同邻居的Jaccard相似性
                        neighbors1 = set(graph.neighbors(node1))
                        neighbors2 = set(graph.neighbors(node2))
                        
                        if len(neighbors1) == 0 and len(neighbors2) == 0:
                            similarity = 1.0
                        elif len(neighbors1) == 0 or len(neighbors2) == 0:
                            similarity = 0.0
                        else:
                            intersection = len(neighbors1 & neighbors2)
                            union = len(neighbors1 | neighbors2)
                            similarity = intersection / union if union > 0 else 0.0
                    
                    similarity_matrix[node1][node2] = similarity
                    
                    if node1 < node2 and similarity >= threshold:
                        similar_pairs.append((node1, node2, similarity))
            
            # 基于相似性进行聚类
            clusters = self._cluster_by_similarity(similar_pairs, threshold)
            
            # 排序相似对
            similar_pairs.sort(key=lambda x: x[2], reverse=True)
            
            return SimilarityResult(
                similarity_matrix=similarity_matrix,
                similar_pairs=similar_pairs[:50],  # 限制返回数量
                clusters=clusters
            )
            
        except Exception as e:
            logger.error(f"相似性分析失败: {str(e)}")
            raise
    
    def _cluster_by_similarity(
        self,
        similar_pairs: List[Tuple[str, str, float]],
        threshold: float
    ) -> Dict[str, List[str]]:
        """基于相似性聚类"""
        # 构建相似性图
        similarity_graph = nx.Graph()
        for node1, node2, similarity in similar_pairs:
            if similarity >= threshold:
                similarity_graph.add_edge(node1, node2, weight=similarity)
        
        # 查找连通组件作为聚类
        clusters = {}
        for i, component in enumerate(nx.connected_components(similarity_graph)):
            clusters[f"cluster_{i}"] = list(component)
        
        return clusters
    
    async def _analyze_influence(
        self,
        graph: nx.MultiDiGraph
    ) -> InfluenceResult:
        """分析影响力"""
        try:
            # 使用PageRank作为基础影响力分数
            pagerank_scores = nx.pagerank(graph)
            
            # 计算级联潜力（基于出度和PageRank的组合）
            cascade_potential = {}
            for node in graph.nodes():
                out_degree = graph.out_degree(node)
                pr_score = pagerank_scores.get(node, 0)
                cascade_potential[node] = out_degree * pr_score
            
            # 计算影响路径
            influence_paths = {}
            nodes = list(graph.nodes())
            
            # 限制节点数量
            if len(nodes) > 50:
                # 选择影响力最高的50个节点
                top_nodes = sorted(
                    pagerank_scores.items(),
                    key=lambda x: x[1],
                    reverse=True
                )[:50]
                nodes = [node for node, _ in top_nodes]
            
            for node in nodes:
                paths = []
                # 查找从该节点出发的路径（最多3跳）
                try:
                    for target in graph.nodes():
                        if node != target:
                            try:
                                path = nx.shortest_path(graph, node, target)
                                if len(path) <= 4:  # 最多3跳
                                    paths.append(path)
                            except nx.NetworkXNoPath:
                                continue
                except:
                    continue
                
                influence_paths[node] = paths[:10]  # 限制路径数量
            
            # 综合影响力分数
            influence_scores = {}
            for node in graph.nodes():
                pr_score = pagerank_scores.get(node, 0)
                cascade_score = cascade_potential.get(node, 0)
                path_count = len(influence_paths.get(node, []))
                
                # 综合分数
                influence_scores[node] = pr_score * 0.5 + cascade_score * 0.3 + path_count * 0.2
            
            # 获取顶级影响者
            top_influencers = sorted(
                influence_scores.items(),
                key=lambda x: x[1],
                reverse=True
            )[:20]
            
            return InfluenceResult(
                influence_scores=influence_scores,
                influence_paths=influence_paths,
                cascade_potential=cascade_potential,
                top_influencers=top_influencers
            )
            
        except Exception as e:
            logger.error(f"影响力分析失败: {str(e)}")
            raise
    
    async def _detect_anomalies(
        self,
        graph: nx.MultiDiGraph
    ) -> AnomalyResult:
        """检测异常"""
        try:
            anomalous_entities = []
            anomalous_relations = []
            anomaly_patterns = []
            
            # 计算节点的异常分数
            degrees = dict(graph.degree())
            degree_values = list(degrees.values())
            
            if degree_values:
                degree_mean = np.mean(degree_values)
                degree_std = np.std(degree_values)
                
                # 基于度的异常检测
                for node, degree in degrees.items():
                    if degree_std > 0:
                        z_score = abs(degree - degree_mean) / degree_std
                        if z_score > 2:  # 2个标准差之外
                            anomalous_entities.append((node, z_score))
            
            # 检测异常关系模式
            relation_types = defaultdict(int)
            for u, v, data in graph.edges(data=True):
                rel_type = data.get('relation_type', 'unknown')
                relation_types[rel_type] += 1
            
            # 查找稀有关系类型
            total_relations = sum(relation_types.values())
            for rel_type, count in relation_types.items():
                frequency = count / total_relations if total_relations > 0 else 0
                if frequency < 0.01:  # 频率小于1%
                    anomaly_patterns.append({
                        "type": "rare_relation_type",
                        "relation_type": rel_type,
                        "frequency": frequency,
                        "count": count
                    })
            
            # 检测孤立节点
            isolated_nodes = list(nx.isolates(graph))
            for node in isolated_nodes:
                anomalous_entities.append((node, 1.0))  # 孤立节点异常分数为1
            
            # 检测异常高度连接的节点
            if degree_values:
                max_degree = max(degree_values)
                degree_threshold = degree_mean + 3 * degree_std
                
                for node, degree in degrees.items():
                    if degree > degree_threshold:
                        anomaly_patterns.append({
                            "type": "highly_connected_node",
                            "node": node,
                            "degree": degree,
                            "threshold": degree_threshold
                        })
            
            # 排序异常实体
            anomalous_entities.sort(key=lambda x: x[1], reverse=True)
            
            # 计算统计信息
            statistics = {
                "num_anomalous_entities": len(anomalous_entities),
                "num_anomalous_relations": len(anomalous_relations),
                "num_anomaly_patterns": len(anomaly_patterns),
                "anomaly_rate": len(anomalous_entities) / graph.number_of_nodes() if graph.number_of_nodes() > 0 else 0
            }
            
            return AnomalyResult(
                anomalous_entities=anomalous_entities[:20],  # 限制返回数量
                anomalous_relations=anomalous_relations[:20],
                anomaly_patterns=anomaly_patterns,
                statistics=statistics
            )
            
        except Exception as e:
            logger.error(f"异常检测失败: {str(e)}")
            raise
    
    async def get_analysis_result(self, analysis_id: str) -> Optional[GraphAnalysisResult]:
        """获取分析结果"""
        return self._analysis_cache.get(analysis_id)
    
    async def list_analysis_results(self, limit: int = 50) -> List[Dict[str, Any]]:
        """列出分析结果"""
        results = []
        for analysis_id, result in list(self._analysis_cache.items())[-limit:]:
            results.append({
                "analysis_id": analysis_id,
                "timestamp": result.timestamp.isoformat(),
                "graph_id": result.graph_id,
                "processing_time": result.processing_time,
                "analysis_types": [t.value for t in result.config.analysis_types],
                "has_errors": len(result.errors) > 0
            })
        return results
    
    async def compare_graphs(
        self,
        graph_id1: str,
        graph_id2: str,
        config: AnalysisConfig = None
    ) -> Dict[str, Any]:
        """比较两个图"""
        try:
            # 分析两个图
            result1 = await self.analyze_graph(graph_id1, config)
            result2 = await self.analyze_graph(graph_id2, config)
            
            comparison = {
                "graph1_id": graph_id1,
                "graph2_id": graph_id2,
                "timestamp": datetime.now().isoformat(),
                "basic_comparison": {
                    "nodes_diff": result2.metadata.get("num_nodes", 0) - result1.metadata.get("num_nodes", 0),
                    "edges_diff": result2.metadata.get("num_edges", 0) - result1.metadata.get("num_edges", 0),
                    "density_diff": result2.metadata.get("density", 0) - result1.metadata.get("density", 0)
                }
            }
            
            # 比较中心性结果
            if result1.centrality_results and result2.centrality_results:
                centrality_comparison = {}
                for metric in result1.centrality_results.keys():
                    if metric in result2.centrality_results:
                        centrality_comparison[metric.value] = {
                            "correlation": self._calculate_correlation(
                                result1.centrality_results[metric].scores,
                                result2.centrality_results[metric].scores
                            )
                        }
                comparison["centrality_comparison"] = centrality_comparison
            
            # 比较社区结构
            if result1.community_result and result2.community_result:
                comparison["community_comparison"] = {
                    "modularity_diff": result2.community_result.modularity - result1.community_result.modularity,
                    "num_communities_diff": result2.community_result.num_communities - result1.community_result.num_communities
                }
            
            return comparison
            
        except Exception as e:
            logger.error(f"图比较失败: {str(e)}")
            return {"error": str(e)}
    
    def _calculate_correlation(
        self,
        scores1: Dict[str, float],
        scores2: Dict[str, float]
    ) -> float:
        """计算两个分数字典的相关性"""
        try:
            common_keys = set(scores1.keys()) & set(scores2.keys())
            if len(common_keys) < 2:
                return 0.0
            
            values1 = [scores1[key] for key in common_keys]
            values2 = [scores2[key] for key in common_keys]
            
            correlation = np.corrcoef(values1, values2)[0, 1]
            return correlation if not np.isnan(correlation) else 0.0
            
        except Exception:
            return 0.0
    
    async def export_analysis_result(
        self,
        analysis_id: str,
        format: str = "json"
    ) -> Optional[str]:
        """导出分析结果"""
        try:
            result = await self.get_analysis_result(analysis_id)
            if not result:
                return None
            
            if format == "json":
                # 转换为可序列化的格式
                export_data = {
                    "analysis_id": result.analysis_id,
                    "timestamp": result.timestamp.isoformat(),
                    "graph_id": result.graph_id,
                    "processing_time": result.processing_time,
                    "metadata": result.metadata,
                    "errors": result.errors
                }
                
                # 添加中心性结果
                if result.centrality_results:
                    export_data["centrality_results"] = {}
                    for metric, centrality_result in result.centrality_results.items():
                        export_data["centrality_results"][metric.value] = {
                            "top_entities": centrality_result.top_entities,
                            "statistics": centrality_result.statistics
                        }
                
                # 添加社区结果
                if result.community_result:
                    export_data["community_result"] = {
                        "algorithm": result.community_result.algorithm.value,
                        "num_communities": result.community_result.num_communities,
                        "modularity": result.community_result.modularity,
                        "community_sizes": result.community_result.community_sizes
                    }
                
                return json.dumps(export_data, indent=2, ensure_ascii=False)
            
            return None
            
        except Exception as e:
            logger.error(f"导出分析结果失败: {str(e)}")
            return None
    
    async def cleanup(self):
        """清理资源"""
        try:
            if self._executor:
                self._executor.shutdown(wait=True)
            
            self._analysis_cache.clear()
            
            logger.info("图分析器资源清理完成")
            
        except Exception as e:
            logger.error(f"图分析器资源清理失败: {str(e)}")