"""知识图谱服务"""

import asyncio
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple, Set
from uuid import uuid4

from ..config import get_settings
from ..config.constants import (
    EntityType, RelationType, ConfidenceLevel, QueryType,
    KNOWLEDGE_GRAPH_MAX_DEPTH, KNOWLEDGE_GRAPH_MAX_NODES
)
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from ..connectors import Neo4jClient, RedisClient
from ..models import (
    Entity, Relation, KnowledgeGraph, SearchQuery, SearchResult,
    KnowledgeGraphQuery, Document, DocumentChunk,
    APIResponse, PaginatedResponse, ErrorResponse
)
from ..repositories import (
    EntityRepository, RelationRepository, DocumentRepository,
    KnowledgeRepository, VectorRepository
)
from ..utils import get_logger
from .llm_service import LLMService
from .vector_service import VectorService


class KnowledgeService:
    """知识图谱服务"""
    
    def __init__(
        self,
        neo4j_client: Neo4jClient,
        redis_client: RedisClient,
        db_session: Session,
        llm_service: LLMService,
        vector_service: VectorService
    ):
        self.neo4j = neo4j_client
        self.redis = redis_client
        self.db = db_session
        self.llm_service = llm_service
        self.vector_service = vector_service
        self.settings = get_settings()
        self.logger = get_logger(__name__)
        
        # 初始化仓库
        self.entity_repo = EntityRepository(db_session)
        self.relation_repo = RelationRepository(db_session)
        self.document_repo = DocumentRepository(db_session)
        self.knowledge_repo = KnowledgeRepository(db_session)
        self.vector_repo = VectorRepository(db_session)
    
    async def extract_entities_from_text(
        self,
        text: str,
        document_id: Optional[str] = None,
        chunk_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> APIResponse[List[Entity]]:
        """从文本中提取实体"""
        try:
            # 使用LLM提取实体
            extraction_prompt = self._build_entity_extraction_prompt(text)
            llm_response = await self.llm_service.generate_response(
                prompt=extraction_prompt,
                max_tokens=2000,
                temperature=0.1
            )
            
            if not llm_response.is_success():
                return ErrorResponse(
                    message="Failed to extract entities using LLM",
                    error_code="LLM_EXTRACTION_FAILED"
                )
            
            # 解析LLM响应
            entities_data = self._parse_entity_extraction_response(llm_response.data)
            
            # 创建实体对象
            entities = []
            for entity_data in entities_data:
                entity = Entity(
                    id=str(uuid4()),
                    name=entity_data["name"],
                    entity_type=EntityType(entity_data.get("type", EntityType.CONCEPT.value)),
                    description=entity_data.get("description"),
                    properties=entity_data.get("properties", {}),
                    confidence=ConfidenceLevel(entity_data.get("confidence", ConfidenceLevel.MEDIUM.value)),
                    source_document_id=document_id,
                    source_chunk_id=chunk_id,
                    extracted_by=user_id,
                    metadata={
                        "extraction_method": "llm",
                        "source_text": text[:500],  # 保存前500字符作为上下文
                        "extraction_timestamp": datetime.now().isoformat()
                    }
                )
                entities.append(entity)
            
            # 保存实体
            for entity in entities:
                await self._save_entity(entity)
            
            self.logger.info(f"Extracted {len(entities)} entities from text")
            return APIResponse(
                status="success",
                message=f"Successfully extracted {len(entities)} entities",
                data=entities
            )
            
        except Exception as e:
            self.logger.error(f"Error extracting entities: {str(e)}")
            return ErrorResponse(
                message=f"Failed to extract entities: {str(e)}",
                error_code="ENTITY_EXTRACTION_FAILED"
            )
    
    async def extract_relations_from_text(
        self,
        text: str,
        entities: List[Entity],
        document_id: Optional[str] = None,
        chunk_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> APIResponse[List[Relation]]:
        """从文本中提取关系"""
        try:
            if len(entities) < 2:
                return APIResponse(
                    status="success",
                    message="Not enough entities to extract relations",
                    data=[]
                )
            
            # 使用LLM提取关系
            extraction_prompt = self._build_relation_extraction_prompt(text, entities)
            llm_response = await self.llm_service.generate_response(
                prompt=extraction_prompt,
                max_tokens=2000,
                temperature=0.1
            )
            
            if not llm_response.is_success():
                return ErrorResponse(
                    message="Failed to extract relations using LLM",
                    error_code="LLM_EXTRACTION_FAILED"
                )
            
            # 解析LLM响应
            relations_data = self._parse_relation_extraction_response(llm_response.data)
            
            # 创建关系对象
            relations = []
            entity_name_to_id = {entity.name: entity.id for entity in entities}
            
            for relation_data in relations_data:
                source_name = relation_data.get("source")
                target_name = relation_data.get("target")
                
                if source_name in entity_name_to_id and target_name in entity_name_to_id:
                    relation = Relation(
                        id=str(uuid4()),
                        source_entity_id=entity_name_to_id[source_name],
                        target_entity_id=entity_name_to_id[target_name],
                        relation_type=RelationType(relation_data.get("type", RelationType.RELATED_TO.value)),
                        description=relation_data.get("description"),
                        properties=relation_data.get("properties", {}),
                        confidence=ConfidenceLevel(relation_data.get("confidence", ConfidenceLevel.MEDIUM.value)),
                        source_document_id=document_id,
                        source_chunk_id=chunk_id,
                        extracted_by=user_id,
                        metadata={
                            "extraction_method": "llm",
                            "source_text": text[:500],
                            "extraction_timestamp": datetime.now().isoformat()
                        }
                    )
                    relations.append(relation)
            
            # 保存关系
            for relation in relations:
                await self._save_relation(relation)
            
            self.logger.info(f"Extracted {len(relations)} relations from text")
            return APIResponse(
                status="success",
                message=f"Successfully extracted {len(relations)} relations",
                data=relations
            )
            
        except Exception as e:
            self.logger.error(f"Error extracting relations: {str(e)}")
            return ErrorResponse(
                message=f"Failed to extract relations: {str(e)}",
                error_code="RELATION_EXTRACTION_FAILED"
            )
    
    async def get_entity(self, entity_id: str) -> APIResponse[Entity]:
        """获取实体"""
        try:
            entity = await self._get_entity_by_id(entity_id)
            if not entity:
                return ErrorResponse(
                    message="Entity not found",
                    error_code="NOT_FOUND"
                )
            
            return APIResponse(
                status="success",
                message="Entity retrieved successfully",
                data=entity
            )
            
        except Exception as e:
            self.logger.error(f"Error getting entity {entity_id}: {str(e)}")
            return ErrorResponse(
                message=f"Failed to get entity: {str(e)}",
                error_code="GET_FAILED"
            )
    
    async def search_entities(
        self,
        query: str,
        entity_type: Optional[EntityType] = None,
        limit: int = 20,
        similarity_threshold: float = 0.7
    ) -> APIResponse[List[Entity]]:
        """搜索实体"""
        try:
            # 向量搜索
            vector_results = await self.vector_service.search_entities(
                query=query,
                limit=limit * 2,  # 获取更多结果用于过滤
                threshold=similarity_threshold
            )
            
            if not vector_results.is_success():
                # 如果向量搜索失败，使用文本搜索
                return await self._text_search_entities(query, entity_type, limit)
            
            # 过滤结果
            entities = []
            for result in vector_results.data[:limit]:
                entity = await self._get_entity_by_id(result["entity_id"])
                if entity and (not entity_type or entity.entity_type == entity_type):
                    entities.append(entity)
            
            return APIResponse(
                status="success",
                message=f"Found {len(entities)} entities",
                data=entities
            )
            
        except Exception as e:
            self.logger.error(f"Error searching entities: {str(e)}")
            return ErrorResponse(
                message=f"Failed to search entities: {str(e)}",
                error_code="SEARCH_FAILED"
            )
    
    async def get_entity_relations(
        self,
        entity_id: str,
        relation_type: Optional[RelationType] = None,
        direction: str = "both",  # "incoming", "outgoing", "both"
        limit: int = 50
    ) -> APIResponse[List[Relation]]:
        """获取实体的关系"""
        try:
            relations = await self._get_entity_relations(
                entity_id, relation_type, direction, limit
            )
            
            return APIResponse(
                status="success",
                message=f"Found {len(relations)} relations",
                data=relations
            )
            
        except Exception as e:
            self.logger.error(f"Error getting entity relations: {str(e)}")
            return ErrorResponse(
                message=f"Failed to get entity relations: {str(e)}",
                error_code="GET_RELATIONS_FAILED"
            )
    
    async def get_knowledge_subgraph(
        self,
        entity_ids: List[str],
        max_depth: int = 2,
        max_nodes: int = 100,
        relation_types: Optional[List[RelationType]] = None
    ) -> APIResponse[KnowledgeGraph]:
        """获取知识子图"""
        try:
            # 限制参数
            max_depth = min(max_depth, KNOWLEDGE_GRAPH_MAX_DEPTH)
            max_nodes = min(max_nodes, KNOWLEDGE_GRAPH_MAX_NODES)
            
            # 构建子图
            entities = {}
            relations = []
            visited_entities = set()
            current_level_entities = set(entity_ids)
            
            for depth in range(max_depth + 1):
                if not current_level_entities or len(entities) >= max_nodes:
                    break
                
                next_level_entities = set()
                
                for entity_id in current_level_entities:
                    if entity_id in visited_entities:
                        continue
                    
                    # 获取实体
                    entity = await self._get_entity_by_id(entity_id)
                    if entity:
                        entities[entity_id] = entity
                        visited_entities.add(entity_id)
                    
                    # 获取关系
                    entity_relations = await self._get_entity_relations(
                        entity_id, None, "both", 50
                    )
                    
                    for relation in entity_relations:
                        if relation_types and relation.relation_type not in relation_types:
                            continue
                        
                        relations.append(relation)
                        
                        # 添加相关实体到下一层
                        if relation.source_entity_id != entity_id:
                            next_level_entities.add(relation.source_entity_id)
                        if relation.target_entity_id != entity_id:
                            next_level_entities.add(relation.target_entity_id)
                
                current_level_entities = next_level_entities - visited_entities
            
            # 创建知识图谱对象
            knowledge_graph = KnowledgeGraph(
                id=str(uuid4()),
                name=f"Subgraph_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                description=f"Knowledge subgraph with {len(entities)} entities and {len(relations)} relations",
                entities=list(entities.values()),
                relations=relations,
                metadata={
                    "max_depth": max_depth,
                    "max_nodes": max_nodes,
                    "actual_depth": depth,
                    "seed_entities": entity_ids,
                    "generation_timestamp": datetime.now().isoformat()
                }
            )
            
            return APIResponse(
                status="success",
                message="Knowledge subgraph generated successfully",
                data=knowledge_graph
            )
            
        except Exception as e:
            self.logger.error(f"Error generating knowledge subgraph: {str(e)}")
            return ErrorResponse(
                message=f"Failed to generate knowledge subgraph: {str(e)}",
                error_code="SUBGRAPH_GENERATION_FAILED"
            )
    
    async def query_knowledge_graph(
        self,
        query: KnowledgeGraphQuery
    ) -> APIResponse[SearchResult]:
        """查询知识图谱"""
        try:
            if query.query_type == QueryType.ENTITY_SEARCH:
                return await self._handle_entity_search_query(query)
            elif query.query_type == QueryType.RELATION_SEARCH:
                return await self._handle_relation_search_query(query)
            elif query.query_type == QueryType.PATH_SEARCH:
                return await self._handle_path_search_query(query)
            elif query.query_type == QueryType.SUBGRAPH_SEARCH:
                return await self._handle_subgraph_search_query(query)
            else:
                return ErrorResponse(
                    message="Unsupported query type",
                    error_code="UNSUPPORTED_QUERY_TYPE"
                )
                
        except Exception as e:
            self.logger.error(f"Error querying knowledge graph: {str(e)}")
            return ErrorResponse(
                message=f"Failed to query knowledge graph: {str(e)}",
                error_code="QUERY_FAILED"
            )
    
    async def merge_entities(
        self,
        primary_entity_id: str,
        secondary_entity_id: str,
        user_id: str
    ) -> APIResponse[Entity]:
        """合并实体"""
        try:
            # 获取两个实体
            primary_entity = await self._get_entity_by_id(primary_entity_id)
            secondary_entity = await self._get_entity_by_id(secondary_entity_id)
            
            if not primary_entity or not secondary_entity:
                return ErrorResponse(
                    message="One or both entities not found",
                    error_code="NOT_FOUND"
                )
            
            # 合并实体属性
            merged_properties = {**secondary_entity.properties, **primary_entity.properties}
            merged_aliases = list(set((primary_entity.aliases or []) + (secondary_entity.aliases or [])))
            
            # 更新主实体
            primary_entity.properties = merged_properties
            primary_entity.aliases = merged_aliases
            primary_entity.confidence = max(primary_entity.confidence, secondary_entity.confidence)
            primary_entity.updated_by = user_id
            primary_entity.mark_updated()
            
            # 获取次要实体的所有关系
            secondary_relations = await self._get_entity_relations(secondary_entity_id)
            
            # 将次要实体的关系转移到主实体
            for relation in secondary_relations:
                if relation.source_entity_id == secondary_entity_id:
                    relation.source_entity_id = primary_entity_id
                elif relation.target_entity_id == secondary_entity_id:
                    relation.target_entity_id = primary_entity_id
                
                relation.updated_by = user_id
                relation.mark_updated()
                await self._update_relation(relation)
            
            # 软删除次要实体
            await self._soft_delete_entity(secondary_entity_id)
            
            # 更新主实体
            await self._update_entity(primary_entity)
            
            self.logger.info(f"Merged entity {secondary_entity_id} into {primary_entity_id}")
            return APIResponse(
                status="success",
                message="Entities merged successfully",
                data=primary_entity
            )
            
        except Exception as e:
            self.logger.error(f"Error merging entities: {str(e)}")
            return ErrorResponse(
                message=f"Failed to merge entities: {str(e)}",
                error_code="MERGE_FAILED"
            )
    
    async def get_entity_statistics(self) -> APIResponse[Dict[str, Any]]:
        """获取实体统计信息"""
        try:
            # 从缓存获取
            cached_stats = await self.redis.get("entity_statistics")
            if cached_stats:
                return APIResponse(
                    status="success",
                    message="Entity statistics retrieved from cache",
                    data=eval(cached_stats)
                )
            
            # 计算统计信息
            stats = await self._calculate_entity_statistics()
            
            # 缓存结果（5分钟）
            await self.redis.set("entity_statistics", str(stats), expire=300)
            
            return APIResponse(
                status="success",
                message="Entity statistics calculated successfully",
                data=stats
            )
            
        except Exception as e:
            self.logger.error(f"Error getting entity statistics: {str(e)}")
            return ErrorResponse(
                message=f"Failed to get entity statistics: {str(e)}",
                error_code="STATS_FAILED"
            )
    
    # 私有方法
    
    def _build_entity_extraction_prompt(self, text: str) -> str:
        """构建实体提取提示"""
        return f"""
请从以下文本中提取实体，并以JSON格式返回。每个实体应包含以下字段：
- name: 实体名称
- type: 实体类型（PERSON, ORGANIZATION, LOCATION, CONCEPT, EVENT, PRODUCT, OTHER之一）
- description: 实体描述（可选）
- properties: 实体属性（可选，键值对格式）
- confidence: 置信度（HIGH, MEDIUM, LOW之一）

文本内容：
{text}

请返回JSON格式的实体列表：
```json
[
  {{
    "name": "实体名称",
    "type": "PERSON",
    "description": "实体描述",
    "properties": {{}},
    "confidence": "HIGH"
  }}
]
```
"""
    
    def _build_relation_extraction_prompt(self, text: str, entities: List[Entity]) -> str:
        """构建关系提取提示"""
        entity_names = [entity.name for entity in entities]
        
        return f"""
请从以下文本中提取实体之间的关系，并以JSON格式返回。

已识别的实体：{', '.join(entity_names)}

文本内容：
{text}

每个关系应包含以下字段：
- source: 源实体名称
- target: 目标实体名称
- type: 关系类型（RELATED_TO, IS_A, PART_OF, LOCATED_IN, WORKS_FOR, CREATED_BY, CONTAINS, SIMILAR_TO, OPPOSITE_TO, CAUSED_BY, LEADS_TO, DEPENDS_ON, COLLABORATES_WITH, COMPETES_WITH, OWNS, MANAGES, TEACHES, LEARNS_FROM, INFLUENCES, SUPPORTS, OPPOSES, PRECEDES, FOLLOWS, INCLUDES, EXCLUDES, IMPLEMENTS, USES, PRODUCES, CONSUMES, REPLACES, EXTENDS, INHERITS_FROM, ASSOCIATED_WITH, MENTIONED_WITH, CO_OCCURS_WITH, OTHER之一）
- description: 关系描述（可选）
- properties: 关系属性（可选）
- confidence: 置信度（HIGH, MEDIUM, LOW之一）

请返回JSON格式的关系列表：
```json
[
  {{
    "source": "源实体名称",
    "target": "目标实体名称",
    "type": "RELATED_TO",
    "description": "关系描述",
    "properties": {{}},
    "confidence": "HIGH"
  }}
]
```
"""
    
    def _parse_entity_extraction_response(self, response: str) -> List[Dict[str, Any]]:
        """解析实体提取响应"""
        try:
            # 简化实现，实际应该更robust地解析JSON
            import json
            import re
            
            # 提取JSON部分
            json_match = re.search(r'```json\s*([\s\S]*?)\s*```', response)
            if json_match:
                json_str = json_match.group(1)
                return json.loads(json_str)
            
            # 如果没有找到代码块，尝试直接解析
            return json.loads(response)
            
        except Exception as e:
            self.logger.warning(f"Failed to parse entity extraction response: {str(e)}")
            return []
    
    def _parse_relation_extraction_response(self, response: str) -> List[Dict[str, Any]]:
        """解析关系提取响应"""
        try:
            import json
            import re
            
            # 提取JSON部分
            json_match = re.search(r'```json\s*([\s\S]*?)\s*```', response)
            if json_match:
                json_str = json_match.group(1)
                return json.loads(json_str)
            
            # 如果没有找到代码块，尝试直接解析
            return json.loads(response)
            
        except Exception as e:
            self.logger.warning(f"Failed to parse relation extraction response: {str(e)}")
            return []
    
    async def _save_entity(self, entity: Entity) -> None:
        """保存实体"""
        # 保存到StarRocks
        await self.starrocks.insert_entity(entity.dict())
        
        # 保存到Neo4j
        await self.neo4j.create_entity(
            "Entity",
            entity.id,
            entity.dict()
        )
        
        # 缓存到Redis
        await self.redis.set(
            f"entity:{entity.id}",
            entity.json(),
            expire=3600
        )
    
    async def _save_relation(self, relation: Relation) -> None:
        """保存关系"""
        # 保存到StarRocks
        await self.starrocks.insert_relation(relation.dict())
        
        # 保存到Neo4j
        await self.neo4j.create_relationship(
            "Entity", relation.source_entity_id,
            "Entity", relation.target_entity_id,
            relation.relation_type.value,
            relation.dict()
        )
    
    async def _get_entity_by_id(self, entity_id: str) -> Optional[Entity]:
        """根据ID获取实体"""
        # 先从Redis缓存获取
        cached_entity = await self.redis.get(f"entity:{entity_id}")
        if cached_entity:
            return Entity.parse_raw(cached_entity)
        
        # 使用仓库查询
        entity_model = await self.entity_repo.get_by_id(entity_id)
        
        if entity_model:
            # 转换为Entity对象
            entity = Entity(
                id=entity_model.id,
                name=entity_model.name,
                entity_type=EntityType(entity_model.entity_type),
                description=entity_model.description,
                properties=entity_model.properties or {},
                confidence=ConfidenceLevel(entity_model.confidence),
                source_document_id=entity_model.source_document_id,
                source_chunk_id=entity_model.source_chunk_id,
                extracted_by=entity_model.extracted_by,
                metadata=entity_model.metadata or {}
            )
            
            # 缓存到Redis
            await self.redis.set(
                f"entity:{entity_id}",
                entity.json(),
                expire=3600
            )
            return entity
        
        return None
    
    async def _text_search_entities(
        self,
        query: str,
        entity_type: Optional[EntityType] = None,
        limit: int = 20
    ) -> APIResponse[List[Entity]]:
        """文本搜索实体"""
        # 使用仓库搜索
        entity_models = await self.entity_repo.search(
            query=query,
            entity_type=entity_type.value if entity_type else None,
            limit=limit
        )
        
        # 转换为Entity对象
        entities = []
        for entity_model in entity_models:
            entity = Entity(
                id=entity_model.id,
                name=entity_model.name,
                entity_type=EntityType(entity_model.entity_type),
                description=entity_model.description,
                properties=entity_model.properties or {},
                confidence=ConfidenceLevel(entity_model.confidence),
                source_document_id=entity_model.source_document_id,
                source_chunk_id=entity_model.source_chunk_id,
                extracted_by=entity_model.extracted_by,
                metadata=entity_model.metadata or {}
            )
            entities.append(entity)
        
        return APIResponse(
            status="success",
            message=f"Found {len(entities)} entities",
            data=entities
        )
    
    async def _get_entity_relations(
        self,
        entity_id: str,
        relation_type: Optional[RelationType] = None,
        direction: str = "both",
        limit: int = 50
    ) -> List[Relation]:
        """获取实体关系"""
        # 使用仓库查询关系
        if direction == "incoming":
            relation_models = await self.relation_repo.get_by_target_entity(
                target_entity_id=entity_id,
                relation_type=relation_type.value if relation_type else None,
                limit=limit
            )
        elif direction == "outgoing":
            relation_models = await self.relation_repo.get_by_source_entity(
                source_entity_id=entity_id,
                relation_type=relation_type.value if relation_type else None,
                limit=limit
            )
        else:  # both
            relation_models = await self.relation_repo.get_by_entity(
                entity_id=entity_id,
                relation_type=relation_type.value if relation_type else None,
                limit=limit
            )
        
        # 转换为Relation对象
        relations = []
        for relation_model in relation_models:
            relation = Relation(
                id=relation_model.id,
                source_entity_id=relation_model.source_entity_id,
                target_entity_id=relation_model.target_entity_id,
                relation_type=RelationType(relation_model.relation_type),
                description=relation_model.description,
                properties=relation_model.properties or {},
                confidence=ConfidenceLevel(relation_model.confidence),
                source_document_id=relation_model.source_document_id,
                source_chunk_id=relation_model.source_chunk_id,
                extracted_by=relation_model.extracted_by,
                metadata=relation_model.metadata or {}
            )
            relations.append(relation)
        
        return relations
    
    async def _update_entity(self, entity: Entity) -> None:
        """更新实体"""
        # 更新StarRocks
        await self.starrocks.update_entity(entity.id, entity.dict())
        
        # 更新Neo4j
        await self.neo4j.update_entity("Entity", entity.id, entity.dict())
        
        # 删除Redis缓存
        await self.redis.delete(f"entity:{entity.id}")
    
    async def _update_relation(self, relation: Relation) -> None:
        """更新关系"""
        # 更新StarRocks
        await self.starrocks.update_relation(relation.id, relation.dict())
        
        # 更新Neo4j关系比较复杂，这里简化处理
        # 实际应该先删除旧关系，再创建新关系
    
    async def _soft_delete_entity(self, entity_id: str) -> None:
        """软删除实体"""
        # 使用仓库软删除实体
        await self.entity_repo.soft_delete(entity_id)
        
        # 软删除Neo4j中的实体节点
        await self.neo4j.update_entity("Entity", entity_id, {"deleted_at": datetime.now().isoformat()})
        
        # 删除Redis缓存
        await self.redis.delete(f"entity:{entity_id}")
    
    async def _calculate_entity_statistics(self) -> Dict[str, Any]:
        """计算实体统计信息"""
        # 使用仓库获取统计信息
        entity_stats = await self.entity_repo.get_statistics()
        relation_stats = await self.relation_repo.get_statistics()
        
        stats = {
            "total_entities": entity_stats.get("total_count", 0),
            "entities_by_type": entity_stats.get("type_distribution", {}),
            "entities_by_confidence": entity_stats.get("confidence_distribution", {}),
            "total_relations": relation_stats.get("total_count", 0),
            "relations_by_type": relation_stats.get("type_distribution", {})
        }
        
        return stats
    
    async def _handle_entity_search_query(self, query: KnowledgeGraphQuery) -> APIResponse[SearchResult]:
        """处理实体搜索查询"""
        entities_response = await self.search_entities(
            query=query.query,
            entity_type=query.filters.get("entity_type"),
            limit=query.limit or 20
        )
        
        if not entities_response.is_success():
            return entities_response
        
        search_result = SearchResult(
            query=query.query,
            query_type=query.query_type,
            entities=entities_response.data,
            relations=[],
            total_results=len(entities_response.data),
            execution_time=0.0,  # 应该计算实际执行时间
            metadata={"search_type": "entity_search"}
        )
        
        return APIResponse(
            status="success",
            message="Entity search completed",
            data=search_result
        )
    
    async def _handle_relation_search_query(self, query: KnowledgeGraphQuery) -> APIResponse[SearchResult]:
        """处理关系搜索查询"""
        # 实现关系搜索逻辑
        # 这里简化实现
        return APIResponse(
            status="success",
            message="Relation search not implemented yet",
            data=SearchResult(
                query=query.query,
                query_type=query.query_type,
                entities=[],
                relations=[],
                total_results=0,
                execution_time=0.0,
                metadata={"search_type": "relation_search"}
            )
        )
    
    async def _handle_path_search_query(self, query: KnowledgeGraphQuery) -> APIResponse[SearchResult]:
        """处理路径搜索查询"""
        # 实现路径搜索逻辑
        # 这里简化实现
        return APIResponse(
            status="success",
            message="Path search not implemented yet",
            data=SearchResult(
                query=query.query,
                query_type=query.query_type,
                entities=[],
                relations=[],
                total_results=0,
                execution_time=0.0,
                metadata={"search_type": "path_search"}
            )
        )
    
    async def _handle_subgraph_search_query(self, query: KnowledgeGraphQuery) -> APIResponse[SearchResult]:
        """处理子图搜索查询"""
        # 实现子图搜索逻辑
        # 这里简化实现
        return APIResponse(
            status="success",
            message="Subgraph search not implemented yet",
            data=SearchResult(
                query=query.query,
                query_type=query.query_type,
                entities=[],
                relations=[],
                total_results=0,
                execution_time=0.0,
                metadata={"search_type": "subgraph_search"}
            )
        )