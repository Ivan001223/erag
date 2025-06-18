#!/usr/bin/env python3
"""
知识图谱构建器

该模块负责构建和维护知识图谱：
- 图谱结构构建
- 节点和边的创建
- 图谱优化
- 增量更新
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional, Tuple, Set
from datetime import datetime
import uuid

from backend.connectors.neo4j_client import Neo4jClient
from backend.connectors.starrocks_client import StarRocksClient
from backend.core.knowledge_graph.entity_extractor import EntityExtractor
from backend.core.knowledge_graph.relation_extractor import RelationExtractor
from backend.utils.logger import get_logger

logger = get_logger(__name__)

class GraphNode:
    """
    图节点表示
    """
    
    def __init__(self, id: str, label: str, properties: Dict[str, Any]):
        self.id = id
        self.label = label
        self.properties = properties
        self.created_at = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "label": self.label,
            "properties": self.properties,
            "created_at": self.created_at.isoformat()
        }

class GraphEdge:
    """
    图边表示
    """
    
    def __init__(self, source_id: str, target_id: str, relation_type: str, 
                 properties: Dict[str, Any]):
        self.id = str(uuid.uuid4())
        self.source_id = source_id
        self.target_id = target_id
        self.relation_type = relation_type
        self.properties = properties
        self.created_at = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "relation_type": self.relation_type,
            "properties": self.properties,
            "created_at": self.created_at.isoformat()
        }

class GraphBuilder:
    """
    知识图谱构建器
    
    负责从提取的实体和关系构建完整的知识图谱。
    """
    
    def __init__(self, neo4j_client: Neo4jClient, starrocks_client: StarRocksClient,
                 entity_extractor: EntityExtractor, relation_extractor: RelationExtractor):
        self.neo4j_client = neo4j_client
        self.starrocks_client = starrocks_client
        self.entity_extractor = entity_extractor
        self.relation_extractor = relation_extractor
        
        # 图谱统计信息
        self.node_count = 0
        self.edge_count = 0
        self.last_build_time = None
    
    async def build_graph_from_document(self, document_id: str, content: str, 
                                      metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        从文档内容构建知识图谱
        
        参数:
            document_id: 文档ID
            content: 文档内容
            metadata: 文档元数据
        
        返回:
            Dict[str, Any]: 构建结果统计
        """
        logger.info(f"开始为文档 {document_id} 构建知识图谱")
        
        try:
            # 1. 提取实体
            entities = await self.entity_extractor.extract_entities(content, metadata)
            logger.debug(f"提取到 {len(entities)} 个实体")
            
            # 2. 提取关系
            relations = await self.relation_extractor.extract_relations(content, entities)
            logger.debug(f"提取到 {len(relations)} 个关系")
            
            # 3. 创建图节点
            nodes = await self._create_nodes(entities, document_id)
            
            # 4. 创建图边
            edges = await self._create_edges(relations, nodes, document_id)
            
            # 5. 持久化到图数据库
            await self._persist_graph(nodes, edges)
            
            # 6. 更新统计信息
            stats = {
                "document_id": document_id,
                "nodes_created": len(nodes),
                "edges_created": len(edges),
                "total_entities": len(entities),
                "total_relations": len(relations),
                "build_time": datetime.now().isoformat()
            }
            
            self.node_count += len(nodes)
            self.edge_count += len(edges)
            self.last_build_time = datetime.now()
            
            logger.info(f"文档 {document_id} 知识图谱构建完成: {stats}")
            return stats
        
        except Exception as e:
            logger.error(f"文档 {document_id} 知识图谱构建失败: {e}")
            raise
    
    async def _create_nodes(self, entities: List[Dict[str, Any]], 
                          document_id: str) -> List[GraphNode]:
        """
        从实体创建图节点
        
        参数:
            entities: 提取的实体列表
            document_id: 源文档ID
        
        返回:
            List[GraphNode]: 创建的节点列表
        """
        nodes = []
        
        for entity in entities:
            # 检查实体是否已存在
            existing_node = await self._find_existing_node(entity['name'], entity['type'])
            
            if existing_node:
                # 更新现有节点
                await self._update_node(existing_node['id'], entity, document_id)
                nodes.append(GraphNode(
                    id=existing_node['id'],
                    label=entity['type'],
                    properties=entity
                ))
            else:
                # 创建新节点
                node_id = str(uuid.uuid4())
                properties = {
                    **entity,
                    'source_documents': [document_id],
                    'created_at': datetime.now().isoformat(),
                    'updated_at': datetime.now().isoformat()
                }
                
                node = GraphNode(
                    id=node_id,
                    label=entity['type'],
                    properties=properties
                )
                nodes.append(node)
        
        return nodes
    
    async def _create_edges(self, relations: List[Dict[str, Any]], 
                          nodes: List[GraphNode], document_id: str) -> List[GraphEdge]:
        """
        从关系创建图边
        
        参数:
            relations: 提取的关系列表
            nodes: 已创建的节点列表
            document_id: 源文档ID
        
        返回:
            List[GraphEdge]: 创建的边列表
        """
        edges = []
        node_map = {node.properties['name']: node.id for node in nodes}
        
        for relation in relations:
            source_name = relation.get('source_entity')
            target_name = relation.get('target_entity')
            
            if source_name in node_map and target_name in node_map:
                source_id = node_map[source_name]
                target_id = node_map[target_name]
                
                # 检查关系是否已存在
                existing_edge = await self._find_existing_edge(
                    source_id, target_id, relation['relation_type']
                )
                
                if not existing_edge:
                    properties = {
                        **relation,
                        'source_documents': [document_id],
                        'created_at': datetime.now().isoformat()
                    }
                    
                    edge = GraphEdge(
                        source_id=source_id,
                        target_id=target_id,
                        relation_type=relation['relation_type'],
                        properties=properties
                    )
                    edges.append(edge)
                else:
                    # 更新现有关系
                    await self._update_edge(existing_edge['id'], relation, document_id)
        
        return edges
    
    async def _find_existing_node(self, name: str, entity_type: str) -> Optional[Dict[str, Any]]:
        """
        查找已存在的节点
        
        参数:
            name: 实体名称
            entity_type: 实体类型
        
        返回:
            Optional[Dict[str, Any]]: 存在的节点信息
        """
        query = """
        MATCH (n:Entity {name: $name, type: $type})
        RETURN n.id as id, n.name as name, n.type as type
        LIMIT 1
        """
        
        result = await self.neo4j_client.execute_query(
            query, {"name": name, "type": entity_type}
        )
        
        return result[0] if result else None
    
    async def _find_existing_edge(self, source_id: str, target_id: str, 
                                relation_type: str) -> Optional[Dict[str, Any]]:
        """
        查找已存在的边
        
        参数:
            source_id: 源节点ID
            target_id: 目标节点ID
            relation_type: 关系类型
        
        返回:
            Optional[Dict[str, Any]]: 存在的边信息
        """
        query = """
        MATCH (source {id: $source_id})-[r:RELATES_TO {type: $relation_type}]->(target {id: $target_id})
        RETURN r.id as id, r.type as type
        LIMIT 1
        """
        
        result = await self.neo4j_client.execute_query(
            query, {
                "source_id": source_id,
                "target_id": target_id,
                "relation_type": relation_type
            }
        )
        
        return result[0] if result else None
    
    async def _update_node(self, node_id: str, entity: Dict[str, Any], 
                         document_id: str):
        """
        更新现有节点
        
        参数:
            node_id: 节点ID
            entity: 实体信息
            document_id: 源文档ID
        """
        query = """
        MATCH (n {id: $node_id})
        SET n.confidence = CASE 
            WHEN n.confidence < $confidence THEN $confidence 
            ELSE n.confidence 
        END,
        n.source_documents = CASE 
            WHEN NOT $document_id IN n.source_documents 
            THEN n.source_documents + [$document_id]
            ELSE n.source_documents
        END,
        n.updated_at = $updated_at
        """
        
        await self.neo4j_client.execute_query(
            query, {
                "node_id": node_id,
                "confidence": entity.get('confidence', 0.0),
                "document_id": document_id,
                "updated_at": datetime.now().isoformat()
            }
        )
    
    async def _update_edge(self, edge_id: str, relation: Dict[str, Any], 
                         document_id: str):
        """
        更新现有边
        
        参数:
            edge_id: 边ID
            relation: 关系信息
            document_id: 源文档ID
        """
        query = """
        MATCH ()-[r {id: $edge_id}]->()
        SET r.confidence = CASE 
            WHEN r.confidence < $confidence THEN $confidence 
            ELSE r.confidence 
        END,
        r.source_documents = CASE 
            WHEN NOT $document_id IN r.source_documents 
            THEN r.source_documents + [$document_id]
            ELSE r.source_documents
        END,
        r.updated_at = $updated_at
        """
        
        await self.neo4j_client.execute_query(
            query, {
                "edge_id": edge_id,
                "confidence": relation.get('confidence', 0.0),
                "document_id": document_id,
                "updated_at": datetime.now().isoformat()
            }
        )
    
    async def _persist_graph(self, nodes: List[GraphNode], edges: List[GraphEdge]):
        """
        持久化图数据到数据库
        
        参数:
            nodes: 节点列表
            edges: 边列表
        """
        # 1. 创建节点
        for node in nodes:
            # Neo4j
            await self._create_neo4j_node(node)
            
            # StarRocks
            await self._create_starrocks_entity(node)
        
        # 2. 创建边
        for edge in edges:
            # Neo4j
            await self._create_neo4j_edge(edge)
            
            # StarRocks
            await self._create_starrocks_relation(edge)
    
    async def _create_neo4j_node(self, node: GraphNode):
        """
        在Neo4j中创建节点
        
        参数:
            node: 图节点
        """
        query = f"""
        CREATE (n:{node.label} {{
            id: $id,
            name: $name,
            type: $type,
            description: $description,
            confidence: $confidence,
            source_documents: $source_documents,
            created_at: datetime($created_at),
            updated_at: datetime($updated_at)
        }})
        """
        
        await self.neo4j_client.execute_query(query, {
            "id": node.id,
            "name": node.properties.get('name'),
            "type": node.properties.get('type'),
            "description": node.properties.get('description'),
            "confidence": node.properties.get('confidence', 0.0),
            "source_documents": node.properties.get('source_documents', []),
            "created_at": node.properties.get('created_at'),
            "updated_at": node.properties.get('updated_at')
        })
    
    async def _create_neo4j_edge(self, edge: GraphEdge):
        """
        在Neo4j中创建边
        
        参数:
            edge: 图边
        """
        query = """
        MATCH (source {id: $source_id}), (target {id: $target_id})
        CREATE (source)-[r:RELATES_TO {
            id: $id,
            type: $relation_type,
            confidence: $confidence,
            source_documents: $source_documents,
            created_at: datetime($created_at)
        }]->(target)
        """
        
        await self.neo4j_client.execute_query(query, {
            "id": edge.id,
            "source_id": edge.source_id,
            "target_id": edge.target_id,
            "relation_type": edge.relation_type,
            "confidence": edge.properties.get('confidence', 0.0),
            "source_documents": edge.properties.get('source_documents', []),
            "created_at": edge.properties.get('created_at')
        })
    
    async def _create_starrocks_entity(self, node: GraphNode):
        """
        在StarRocks中创建实体记录
        
        参数:
            node: 图节点
        """
        import json
        
        from backend.models.knowledge import EntityModel
        from backend.config.database import get_async_session
        
        source_docs = node.properties.get('source_documents', [])
        source_doc_id = source_docs[0] if source_docs else None
        
        async with get_async_session() as session:
            new_entity = EntityModel(
                id=node.id,
                name=node.properties.get('name'),
                type=node.properties.get('type'),
                description=node.properties.get('description'),
                confidence=node.properties.get('confidence', 0.0),
                source_document_id=source_doc_id,
                properties=json.dumps(node.properties),
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
            session.add(new_entity)
            await session.commit()
    
    async def _create_starrocks_relation(self, edge: GraphEdge):
        """
        在StarRocks中创建关系记录
        
        参数:
            edge: 图边
        """
        import json
        
        from backend.models.knowledge import RelationModel
        from backend.config.database import get_async_session
        
        source_docs = edge.properties.get('source_documents', [])
        source_doc_id = source_docs[0] if source_docs else None
        
        async with get_async_session() as session:
            new_relation = RelationModel(
                id=edge.id,
                source_entity_id=edge.source_id,
                target_entity_id=edge.target_id,
                relation_type=edge.relation_type,
                confidence=edge.properties.get('confidence', 0.0),
                source_document_id=source_doc_id,
                properties=json.dumps(edge.properties),
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
            session.add(new_relation)
            await session.commit()
    
    async def rebuild_graph(self, document_ids: List[str] = None) -> Dict[str, Any]:
        """
        重建知识图谱
        
        参数:
            document_ids: 要重建的文档ID列表，None表示重建全部
        
        返回:
            Dict[str, Any]: 重建结果统计
        """
        logger.info("开始重建知识图谱")
        
        try:
            # 1. 获取要处理的文档
            if document_ids:
                documents = await self._get_documents_by_ids(document_ids)
            else:
                documents = await self._get_all_documents()
            
            # 2. 清理现有图谱数据（如果是全量重建）
            if not document_ids:
                await self._clear_graph()
            
            # 3. 重新构建
            total_nodes = 0
            total_edges = 0
            
            for doc in documents:
                stats = await self.build_graph_from_document(
                    doc['id'], doc['content'], doc.get('metadata')
                )
                total_nodes += stats['nodes_created']
                total_edges += stats['edges_created']
            
            rebuild_stats = {
                "documents_processed": len(documents),
                "total_nodes_created": total_nodes,
                "total_edges_created": total_edges,
                "rebuild_time": datetime.now().isoformat()
            }
            
            logger.info(f"知识图谱重建完成: {rebuild_stats}")
            return rebuild_stats
        
        except Exception as e:
            logger.error(f"知识图谱重建失败: {e}")
            raise
    
    async def _get_documents_by_ids(self, document_ids: List[str]) -> List[Dict[str, Any]]:
        """
        根据ID获取文档
        
        参数:
            document_ids: 文档ID列表
        
        返回:
            List[Dict[str, Any]]: 文档列表
        """
        placeholders = ','.join(['?' for _ in document_ids])
        query = f"""
        SELECT id, title, content, metadata 
        FROM knowledge_base.documents 
        WHERE id IN ({placeholders}) AND status = 'processed'
        """
        
        result = await self.starrocks_client.execute(query, document_ids)
        
        return [
            {
                "id": row[0],
                "title": row[1],
                "content": row[2],
                "metadata": row[3]
            }
            for row in result
        ] if result else []
    
    async def _get_all_documents(self) -> List[Dict[str, Any]]:
        """
        获取所有已处理的文档
        
        返回:
            List[Dict[str, Any]]: 文档列表
        """
        query = """
        SELECT id, title, content, metadata 
        FROM knowledge_base.documents 
        WHERE status = 'processed'
        ORDER BY created_at
        """
        
        result = await self.starrocks_client.execute(query)
        
        return [
            {
                "id": row[0],
                "title": row[1],
                "content": row[2],
                "metadata": row[3]
            }
            for row in result
        ] if result else []
    
    async def _clear_graph(self):
        """
        清理图谱数据
        """
        logger.info("清理现有图谱数据")
        
        # 清理 Neo4j
        await self.neo4j_client.execute_query("MATCH (n) DETACH DELETE n")
        
        # 清理 StarRocks - 使用SQLAlchemy方法
        await self.starrocks_client.truncate_table("entities")
        await self.starrocks_client.truncate_table("relations")
        
        # 重置统计
        self.node_count = 0
        self.edge_count = 0
    
    async def get_graph_statistics(self) -> Dict[str, Any]:
        """
        获取图谱统计信息
        
        返回:
            Dict[str, Any]: 统计信息
        """
        # Neo4j 统计
        neo4j_stats = await self.neo4j_client.execute_query(
            "MATCH (n) RETURN count(n) as node_count"
        )
        
        neo4j_edge_stats = await self.neo4j_client.execute_query(
            "MATCH ()-[r]->() RETURN count(r) as edge_count"
        )
        
        # StarRocks 统计 - 使用SQLAlchemy方法
        starrocks_stats = await self.starrocks_client.get_database_stats()
        starrocks_entity_count = starrocks_stats.get("entities_count", 0)
        starrocks_relation_count = starrocks_stats.get("relations_count", 0)
        
        return {
            "neo4j": {
                "nodes": neo4j_stats[0][0] if neo4j_stats else 0,
                "edges": neo4j_edge_stats[0][0] if neo4j_edge_stats else 0
            },
            "starrocks": {
                "entities": starrocks_entity_count,
                "relations": starrocks_relation_count
            },
            "last_build_time": self.last_build_time.isoformat() if self.last_build_time else None
        }