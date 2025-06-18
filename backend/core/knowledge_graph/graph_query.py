#!/usr/bin/env python3
"""
知识图谱查询器

该模块负责知识图谱的查询和检索：
- 实体查询
- 关系查询
- 路径查询
- 图谱遍历
- 复杂查询构建
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional, Tuple, Set, Union
from datetime import datetime
import json

from backend.connectors.neo4j_client import Neo4jClient
from backend.connectors.starrocks_client import StarRocksClient
from backend.utils.logger import get_logger

logger = get_logger(__name__)

class QueryResult:
    """
    查询结果封装
    """
    
    def __init__(self, data: List[Dict[str, Any]], query_type: str, 
                 execution_time: float, total_count: int = None):
        self.data = data
        self.query_type = query_type
        self.execution_time = execution_time
        self.total_count = total_count or len(data)
        self.timestamp = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "data": self.data,
            "query_type": self.query_type,
            "execution_time": self.execution_time,
            "total_count": self.total_count,
            "timestamp": self.timestamp.isoformat()
        }

class GraphQuery:
    """
    知识图谱查询器
    
    提供各种图谱查询功能，包括实体查询、关系查询、路径查询等。
    """
    
    def __init__(self, neo4j_client: Neo4jClient, starrocks_client: StarRocksClient):
        self.neo4j_client = neo4j_client
        self.starrocks_client = starrocks_client
    
    async def find_entities(self, name: str = None, entity_type: str = None, 
                          properties: Dict[str, Any] = None, 
                          limit: int = 100, offset: int = 0) -> QueryResult:
        """
        查找实体
        
        参数:
            name: 实体名称（支持模糊匹配）
            entity_type: 实体类型
            properties: 其他属性过滤条件
            limit: 返回数量限制
            offset: 偏移量
        
        返回:
            QueryResult: 查询结果
        """
        start_time = datetime.now()
        
        # 构建查询条件
        where_conditions = []
        params = {"limit": limit, "offset": offset}
        
        if name:
            where_conditions.append("n.name CONTAINS $name")
            params["name"] = name
        
        if entity_type:
            where_conditions.append("n.type = $entity_type")
            params["entity_type"] = entity_type
        
        if properties:
            for key, value in properties.items():
                param_key = f"prop_{key}"
                where_conditions.append(f"n.{key} = ${param_key}")
                params[param_key] = value
        
        where_clause = "WHERE " + " AND ".join(where_conditions) if where_conditions else ""
        
        query = f"""
        MATCH (n:Entity)
        {where_clause}
        RETURN n.id as id, n.name as name, n.type as type, 
               n.description as description, n.confidence as confidence,
               n.source_documents as source_documents,
               n.created_at as created_at, n.updated_at as updated_at
        ORDER BY n.confidence DESC, n.name
        SKIP $offset LIMIT $limit
        """
        
        try:
            result = await self.neo4j_client.execute_query(query, params)
            
            entities = [
                {
                    "id": row[0],
                    "name": row[1],
                    "type": row[2],
                    "description": row[3],
                    "confidence": row[4],
                    "source_documents": row[5],
                    "created_at": row[6],
                    "updated_at": row[7]
                }
                for row in result
            ] if result else []
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            return QueryResult(
                data=entities,
                query_type="find_entities",
                execution_time=execution_time
            )
        
        except Exception as e:
            logger.error(f"实体查询失败: {e}")
            raise
    
    async def find_relations(self, source_entity_id: str = None, 
                           target_entity_id: str = None,
                           relation_type: str = None,
                           limit: int = 100, offset: int = 0) -> QueryResult:
        """
        查找关系
        
        参数:
            source_entity_id: 源实体ID
            target_entity_id: 目标实体ID
            relation_type: 关系类型
            limit: 返回数量限制
            offset: 偏移量
        
        返回:
            QueryResult: 查询结果
        """
        start_time = datetime.now()
        
        # 构建查询条件
        where_conditions = []
        params = {"limit": limit, "offset": offset}
        
        if source_entity_id:
            where_conditions.append("source.id = $source_id")
            params["source_id"] = source_entity_id
        
        if target_entity_id:
            where_conditions.append("target.id = $target_id")
            params["target_id"] = target_entity_id
        
        if relation_type:
            where_conditions.append("r.type = $relation_type")
            params["relation_type"] = relation_type
        
        where_clause = "WHERE " + " AND ".join(where_conditions) if where_conditions else ""
        
        query = f"""
        MATCH (source:Entity)-[r:RELATES_TO]->(target:Entity)
        {where_clause}
        RETURN r.id as id, source.id as source_id, source.name as source_name,
               target.id as target_id, target.name as target_name,
               r.type as relation_type, r.confidence as confidence,
               r.source_documents as source_documents, r.created_at as created_at
        ORDER BY r.confidence DESC
        SKIP $offset LIMIT $limit
        """
        
        try:
            result = await self.neo4j_client.execute_query(query, params)
            
            relations = [
                {
                    "id": row[0],
                    "source_entity": {
                        "id": row[1],
                        "name": row[2]
                    },
                    "target_entity": {
                        "id": row[3],
                        "name": row[4]
                    },
                    "relation_type": row[5],
                    "confidence": row[6],
                    "source_documents": row[7],
                    "created_at": row[8]
                }
                for row in result
            ] if result else []
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            return QueryResult(
                data=relations,
                query_type="find_relations",
                execution_time=execution_time
            )
        
        except Exception as e:
            logger.error(f"关系查询失败: {e}")
            raise
    
    async def find_entity_neighbors(self, entity_id: str, 
                                  relation_types: List[str] = None,
                                  direction: str = "both",
                                  max_depth: int = 1,
                                  limit: int = 100) -> QueryResult:
        """
        查找实体的邻居节点
        
        参数:
            entity_id: 实体ID
            relation_types: 关系类型过滤
            direction: 方向（"in", "out", "both"）
            max_depth: 最大深度
            limit: 返回数量限制
        
        返回:
            QueryResult: 查询结果
        """
        start_time = datetime.now()
        
        # 构建关系类型过滤
        relation_filter = ""
        if relation_types:
            relation_filter = f":{':'.join(relation_types)}"
        
        # 构建方向
        if direction == "in":
            pattern = f"(neighbor)-[r{relation_filter}]->(entity)"
        elif direction == "out":
            pattern = f"(entity)-[r{relation_filter}]->(neighbor)"
        else:  # both
            pattern = f"(entity)-[r{relation_filter}]-(neighbor)"
        
        query = f"""
        MATCH (entity:Entity {{id: $entity_id}})
        MATCH {pattern}
        WHERE neighbor.id <> entity.id
        RETURN DISTINCT neighbor.id as id, neighbor.name as name, 
               neighbor.type as type, neighbor.confidence as confidence,
               r.type as relation_type, r.confidence as relation_confidence,
               CASE 
                   WHEN startNode(r).id = entity.id THEN 'outgoing'
                   ELSE 'incoming'
               END as direction
        ORDER BY neighbor.confidence DESC, r.confidence DESC
        LIMIT $limit
        """
        
        try:
            result = await self.neo4j_client.execute_query(
                query, {"entity_id": entity_id, "limit": limit}
            )
            
            neighbors = [
                {
                    "entity": {
                        "id": row[0],
                        "name": row[1],
                        "type": row[2],
                        "confidence": row[3]
                    },
                    "relation": {
                        "type": row[4],
                        "confidence": row[5],
                        "direction": row[6]
                    }
                }
                for row in result
            ] if result else []
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            return QueryResult(
                data=neighbors,
                query_type="find_neighbors",
                execution_time=execution_time
            )
        
        except Exception as e:
            logger.error(f"邻居查询失败: {e}")
            raise
    
    async def find_shortest_path(self, source_entity_id: str, 
                               target_entity_id: str,
                               max_depth: int = 5,
                               relation_types: List[str] = None) -> QueryResult:
        """
        查找两个实体之间的最短路径
        
        参数:
            source_entity_id: 源实体ID
            target_entity_id: 目标实体ID
            max_depth: 最大搜索深度
            relation_types: 关系类型过滤
        
        返回:
            QueryResult: 查询结果
        """
        start_time = datetime.now()
        
        # 构建关系类型过滤
        relation_filter = ""
        if relation_types:
            relation_filter = f":{':'.join(relation_types)}"
        
        query = f"""
        MATCH (source:Entity {{id: $source_id}}), (target:Entity {{id: $target_id}})
        MATCH path = shortestPath((source)-[*1..{max_depth}]-(target))
        RETURN 
            [node in nodes(path) | {{id: node.id, name: node.name, type: node.type}}] as nodes,
            [rel in relationships(path) | {{type: rel.type, confidence: rel.confidence}}] as relationships,
            length(path) as path_length
        ORDER BY path_length
        LIMIT 10
        """
        
        try:
            result = await self.neo4j_client.execute_query(
                query, {
                    "source_id": source_entity_id,
                    "target_id": target_entity_id
                }
            )
            
            paths = [
                {
                    "nodes": row[0],
                    "relationships": row[1],
                    "length": row[2]
                }
                for row in result
            ] if result else []
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            return QueryResult(
                data=paths,
                query_type="shortest_path",
                execution_time=execution_time
            )
        
        except Exception as e:
            logger.error(f"路径查询失败: {e}")
            raise
    
    async def find_subgraph(self, entity_ids: List[str], 
                          max_depth: int = 2,
                          include_relations: bool = True) -> QueryResult:
        """
        查找子图
        
        参数:
            entity_ids: 实体ID列表
            max_depth: 最大深度
            include_relations: 是否包含关系信息
        
        返回:
            QueryResult: 查询结果
        """
        start_time = datetime.now()
        
        query = f"""
        MATCH (seed:Entity)
        WHERE seed.id IN $entity_ids
        MATCH (seed)-[*0..{max_depth}]-(connected:Entity)
        WITH DISTINCT connected as node
        MATCH (node)
        OPTIONAL MATCH (node)-[r:RELATES_TO]-(other:Entity)
        WHERE other.id IN [n.id | n IN collect(node)]
        RETURN 
            collect(DISTINCT {{id: node.id, name: node.name, type: node.type, 
                             confidence: node.confidence}}) as nodes,
            collect(DISTINCT {{id: r.id, source_id: startNode(r).id, 
                             target_id: endNode(r).id, type: r.type, 
                             confidence: r.confidence}}) as relationships
        """
        
        try:
            result = await self.neo4j_client.execute_query(
                query, {"entity_ids": entity_ids}
            )
            
            if result:
                subgraph = {
                    "nodes": result[0][0] or [],
                    "relationships": result[0][1] or [] if include_relations else []
                }
            else:
                subgraph = {"nodes": [], "relationships": []}
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            return QueryResult(
                data=[subgraph],
                query_type="subgraph",
                execution_time=execution_time
            )
        
        except Exception as e:
            logger.error(f"子图查询失败: {e}")
            raise
    
    async def search_entities_by_text(self, search_text: str, 
                                    entity_types: List[str] = None,
                                    limit: int = 50) -> QueryResult:
        """
        基于文本搜索实体
        
        参数:
            search_text: 搜索文本
            entity_types: 实体类型过滤
            limit: 返回数量限制
        
        返回:
            QueryResult: 查询结果
        """
        start_time = datetime.now()
        
        # 构建类型过滤
        type_filter = ""
        params = {"search_text": search_text, "limit": limit}
        
        if entity_types:
            type_filter = "AND n.type IN $entity_types"
            params["entity_types"] = entity_types
        
        query = f"""
        MATCH (n:Entity)
        WHERE (n.name CONTAINS $search_text OR n.description CONTAINS $search_text)
        {type_filter}
        RETURN n.id as id, n.name as name, n.type as type, 
               n.description as description, n.confidence as confidence,
               CASE 
                   WHEN n.name CONTAINS $search_text THEN 2
                   WHEN n.description CONTAINS $search_text THEN 1
                   ELSE 0
               END as relevance_score
        ORDER BY relevance_score DESC, n.confidence DESC
        LIMIT $limit
        """
        
        try:
            result = await self.neo4j_client.execute_query(query, params)
            
            entities = [
                {
                    "id": row[0],
                    "name": row[1],
                    "type": row[2],
                    "description": row[3],
                    "confidence": row[4],
                    "relevance_score": row[5]
                }
                for row in result
            ] if result else []
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            return QueryResult(
                data=entities,
                query_type="text_search",
                execution_time=execution_time
            )
        
        except Exception as e:
            logger.error(f"文本搜索失败: {e}")
            raise
    
    async def get_entity_statistics(self, entity_id: str) -> QueryResult:
        """
        获取实体统计信息
        
        参数:
            entity_id: 实体ID
        
        返回:
            QueryResult: 查询结果
        """
        start_time = datetime.now()
        
        query = """
        MATCH (entity:Entity {id: $entity_id})
        OPTIONAL MATCH (entity)-[out_rel:RELATES_TO]->()
        OPTIONAL MATCH ()-[in_rel:RELATES_TO]->(entity)
        RETURN 
            entity.id as id,
            entity.name as name,
            entity.type as type,
            entity.confidence as confidence,
            count(DISTINCT out_rel) as outgoing_relations,
            count(DISTINCT in_rel) as incoming_relations,
            count(DISTINCT out_rel) + count(DISTINCT in_rel) as total_relations
        """
        
        try:
            result = await self.neo4j_client.execute_query(
                query, {"entity_id": entity_id}
            )
            
            if result:
                stats = {
                    "entity": {
                        "id": result[0][0],
                        "name": result[0][1],
                        "type": result[0][2],
                        "confidence": result[0][3]
                    },
                    "statistics": {
                        "outgoing_relations": result[0][4],
                        "incoming_relations": result[0][5],
                        "total_relations": result[0][6]
                    }
                }
            else:
                stats = {"entity": None, "statistics": None}
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            return QueryResult(
                data=[stats],
                query_type="entity_statistics",
                execution_time=execution_time
            )
        
        except Exception as e:
            logger.error(f"实体统计查询失败: {e}")
            raise
    
    async def get_graph_overview(self) -> QueryResult:
        """
        获取图谱概览信息
        
        返回:
            QueryResult: 查询结果
        """
        start_time = datetime.now()
        
        # 获取基本统计
        stats_query = """
        MATCH (n:Entity)
        OPTIONAL MATCH ()-[r:RELATES_TO]->()
        RETURN 
            count(DISTINCT n) as total_entities,
            count(DISTINCT r) as total_relations,
            count(DISTINCT n.type) as entity_types_count
        """
        
        # 获取实体类型分布
        types_query = """
        MATCH (n:Entity)
        RETURN n.type as entity_type, count(n) as count
        ORDER BY count DESC
        LIMIT 20
        """
        
        # 获取关系类型分布
        relations_query = """
        MATCH ()-[r:RELATES_TO]->()
        RETURN r.type as relation_type, count(r) as count
        ORDER BY count DESC
        LIMIT 20
        """
        
        try:
            # 执行查询
            stats_result = await self.neo4j_client.execute_query(stats_query)
            types_result = await self.neo4j_client.execute_query(types_query)
            relations_result = await self.neo4j_client.execute_query(relations_query)
            
            # 构建结果
            overview = {
                "basic_statistics": {
                    "total_entities": stats_result[0][0] if stats_result else 0,
                    "total_relations": stats_result[0][1] if stats_result else 0,
                    "entity_types_count": stats_result[0][2] if stats_result else 0
                },
                "entity_type_distribution": [
                    {"type": row[0], "count": row[1]}
                    for row in types_result
                ] if types_result else [],
                "relation_type_distribution": [
                    {"type": row[0], "count": row[1]}
                    for row in relations_result
                ] if relations_result else []
            }
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            return QueryResult(
                data=[overview],
                query_type="graph_overview",
                execution_time=execution_time
            )
        
        except Exception as e:
            logger.error(f"图谱概览查询失败: {e}")
            raise
    
    async def execute_custom_query(self, cypher_query: str, 
                                 parameters: Dict[str, Any] = None) -> QueryResult:
        """
        执行自定义Cypher查询
        
        参数:
            cypher_query: Cypher查询语句
            parameters: 查询参数
        
        返回:
            QueryResult: 查询结果
        """
        start_time = datetime.now()
        
        try:
            result = await self.neo4j_client.execute_query(
                cypher_query, parameters or {}
            )
            
            # 转换结果为字典列表
            data = []
            if result:
                # 假设查询返回的是记录列表
                for row in result:
                    if isinstance(row, (list, tuple)):
                        # 如果是列表/元组，转换为字典
                        data.append({f"column_{i}": value for i, value in enumerate(row)})
                    else:
                        # 如果已经是字典，直接使用
                        data.append(row)
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            return QueryResult(
                data=data,
                query_type="custom_query",
                execution_time=execution_time
            )
        
        except Exception as e:
            logger.error(f"自定义查询执行失败: {e}")
            raise
    
    async def find_similar_entities(self, entity_id: str, 
                                  similarity_threshold: float = 0.7,
                                  limit: int = 20) -> QueryResult:
        """
        查找相似实体
        
        参数:
            entity_id: 参考实体ID
            similarity_threshold: 相似度阈值
            limit: 返回数量限制
        
        返回:
            QueryResult: 查询结果
        """
        start_time = datetime.now()
        
        # 基于共同邻居和属性相似度计算相似实体
        query = """
        MATCH (target:Entity {id: $entity_id})
        MATCH (target)-[:RELATES_TO]-(common)-[:RELATES_TO]-(similar:Entity)
        WHERE similar.id <> target.id AND similar.type = target.type
        WITH similar, count(common) as common_neighbors, target
        MATCH (similar)-[:RELATES_TO]-(all_similar_neighbors)
        MATCH (target)-[:RELATES_TO]-(all_target_neighbors)
        WITH similar, common_neighbors, 
             count(DISTINCT all_similar_neighbors) as similar_total,
             count(DISTINCT all_target_neighbors) as target_total,
             target
        WITH similar, common_neighbors, similar_total, target_total,
             CASE 
                 WHEN similar_total + target_total - common_neighbors > 0 
                 THEN toFloat(common_neighbors) / (similar_total + target_total - common_neighbors)
                 ELSE 0.0
             END as jaccard_similarity
        WHERE jaccard_similarity >= $threshold
        RETURN similar.id as id, similar.name as name, similar.type as type,
               similar.confidence as confidence, jaccard_similarity as similarity_score,
               common_neighbors
        ORDER BY similarity_score DESC, common_neighbors DESC
        LIMIT $limit
        """
        
        try:
            result = await self.neo4j_client.execute_query(
                query, {
                    "entity_id": entity_id,
                    "threshold": similarity_threshold,
                    "limit": limit
                }
            )
            
            similar_entities = [
                {
                    "entity": {
                        "id": row[0],
                        "name": row[1],
                        "type": row[2],
                        "confidence": row[3]
                    },
                    "similarity_score": row[4],
                    "common_neighbors": row[5]
                }
                for row in result
            ] if result else []
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            return QueryResult(
                data=similar_entities,
                query_type="similar_entities",
                execution_time=execution_time
            )
        
        except Exception as e:
            logger.error(f"相似实体查询失败: {e}")
            raise