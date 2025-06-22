"""知识图谱服务

优化后的知识图谱服务，提供完整的实体和关系管理功能。
"""

import asyncio
import json
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple, Set
from uuid import uuid4

from ..core.base_service import (
    BaseService, ServiceError, ValidationError, NotFoundError, 
    ConflictError, ExternalServiceError
)
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
from .llm_service import LLMService
from .vector_service import VectorService


class KnowledgeService(BaseService):
    """知识图谱服务
    
    提供完整的知识图谱管理功能，包括实体和关系的创建、查询、更新和删除。
    """
    
    def __init__(
        self,
        neo4j_client: Neo4jClient,
        redis_client: RedisClient,
        db_session: Session,
        llm_service: Optional[LLMService] = None,
        vector_service: Optional[VectorService] = None
    ):
        super().__init__("KnowledgeService")
        
        self.neo4j = neo4j_client
        self.redis = redis_client
        self.db = db_session
        self.llm_service = llm_service
        self.vector_service = vector_service
        
        # 初始化仓库
        self.entity_repo = EntityRepository(db_session)
        self.relation_repo = RelationRepository(db_session)
        self.document_repo = DocumentRepository(db_session)
        self.knowledge_repo = KnowledgeRepository(db_session)
        self.vector_repo = VectorRepository(db_session)
    
    async def initialize(self) -> None:
        """初始化服务"""
        await self._verify_dependencies()
        self.logger.info("知识服务初始化完成")
    
    async def cleanup(self) -> None:
        """清理服务资源"""
        self.clear_cache()
        self.logger.info("知识服务清理完成")
    
    async def _verify_dependencies(self) -> None:
        """验证依赖服务"""
        try:
            # 检查Neo4j连接
            await self.neo4j.verify_connectivity()
            
            # 检查Redis连接
            await self.redis.ping()
            
            self.logger.info("所有依赖服务验证通过")
        except Exception as e:
            raise ServiceError(f"依赖服务验证失败: {str(e)}", "DEPENDENCY_ERROR")
    
    async def extract_entities_from_text(
        self,
        text: str,
        document_id: Optional[str] = None,
        chunk_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> List[Entity]:
        """从文本中提取实体
        
        Args:
            text: 要处理的文本
            document_id: 源文档ID
            chunk_id: 源文档块ID
            user_id: 用户ID
            
        Returns:
            提取的实体列表
            
        Raises:
            ValidationError: 输入验证错误
            ExternalServiceError: LLM服务错误
        """
        if not text or not text.strip():
            raise ValidationError("文本内容不能为空", "text", text)
        
        if len(text) > 10000:  # 限制文本长度
            raise ValidationError("文本长度不能超过10000字符", "text", len(text))
        
        if not self.llm_service:
            raise ServiceError("LLM服务未初始化", "LLM_SERVICE_NOT_AVAILABLE")
        
        try:
            # 使用LLM提取实体
            extraction_prompt = self._build_entity_extraction_prompt(text)
            llm_response = await self.llm_service.generate_response(
                prompt=extraction_prompt,
                max_tokens=2000,
                temperature=0.1
            )
            
            if not llm_response.is_success():
                raise ExternalServiceError("LLM", "实体提取失败")
            
            # 解析LLM响应
            entities_data = self._parse_entity_extraction_response(llm_response.data)
            
            # 创建实体对象
            entities = []
            for entity_data in entities_data:
                # 验证实体数据
                self._validate_entity_data(entity_data)
                
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
            
            # 批量保存实体
            await self._batch_save_entities(entities)
            
            self.logger.info(f"成功提取 {len(entities)} 个实体", extra={
                "entity_count": len(entities),
                "document_id": document_id,
                "user_id": user_id
            })
            
            return entities
            
        except ServiceError:
            raise
        except Exception as e:
            self.logger.error(f"实体提取过程中发生错误: {str(e)}")
            raise ServiceError(f"实体提取失败: {str(e)}", "ENTITY_EXTRACTION_FAILED")
    
    async def extract_relations_from_text(
        self,
        text: str,
        entities: List[Entity],
        document_id: Optional[str] = None,
        chunk_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> List[Relation]:
        """从文本中提取关系
        
        Args:
            text: 要处理的文本
            entities: 已提取的实体列表
            document_id: 源文档ID
            chunk_id: 源文档块ID
            user_id: 用户ID
            
        Returns:
            提取的关系列表
        """
        if not text or not text.strip():
            raise ValidationError("文本内容不能为空", "text", text)
        
        if len(entities) < 2:
            self.logger.info("实体数量不足，无法提取关系")
            return []
        
        if not self.llm_service:
            raise ServiceError("LLM服务未初始化", "LLM_SERVICE_NOT_AVAILABLE")
        
        try:
            # 使用LLM提取关系
            extraction_prompt = self._build_relation_extraction_prompt(text, entities)
            llm_response = await self.llm_service.generate_response(
                prompt=extraction_prompt,
                max_tokens=2000,
                temperature=0.1
            )
            
            if not llm_response.is_success():
                raise ExternalServiceError("LLM", "关系提取失败")
            
            # 解析LLM响应
            relations_data = self._parse_relation_extraction_response(llm_response.data)
            
            # 创建关系对象
            relations = []
            entity_name_to_id = {entity.name: entity.id for entity in entities}
            
            for relation_data in relations_data:
                # 验证关系数据
                self._validate_relation_data(relation_data, entity_name_to_id)
                
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
            
            # 批量保存关系
            await self._batch_save_relations(relations)
            
            self.logger.info(f"成功提取 {len(relations)} 个关系", extra={
                "relation_count": len(relations),
                "document_id": document_id,
                "user_id": user_id
            })
            
            return relations
            
        except ServiceError:
            raise
        except Exception as e:
            self.logger.error(f"关系提取过程中发生错误: {str(e)}")
            raise ServiceError(f"关系提取失败: {str(e)}", "RELATION_EXTRACTION_FAILED")
    
    async def search_entities(
        self,
        query: str,
        entity_type: Optional[EntityType] = None,
        limit: int = 20,
        similarity_threshold: float = 0.7
    ) -> List[Entity]:
        """搜索实体
        
        Args:
            query: 搜索查询
            entity_type: 实体类型过滤
            limit: 返回结果数量限制
            similarity_threshold: 相似度阈值
            
        Returns:
            匹配的实体列表
        """
        if not query or not query.strip():
            raise ValidationError("搜索查询不能为空", "query", query)
        
        if limit <= 0 or limit > 100:
            raise ValidationError("结果数量限制必须在1-100之间", "limit", limit)
        
        try:
            # 首先尝试精确匹配
            exact_matches = await self._exact_search_entities(query, entity_type, limit)
            
            if len(exact_matches) >= limit:
                return exact_matches[:limit]
            
            # 如果精确匹配结果不足，使用向量搜索
            if self.vector_service:
                vector_matches = await self._vector_search_entities(
                    query, entity_type, limit - len(exact_matches), similarity_threshold
                )
                
                # 合并结果并去重
                all_matches = exact_matches + vector_matches
                seen_ids = set()
                unique_matches = []
                
                for entity in all_matches:
                    if entity.id not in seen_ids:
                        unique_matches.append(entity)
                        seen_ids.add(entity.id)
                
                return unique_matches[:limit]
            else:
                return exact_matches
                
        except ServiceError:
            raise
        except Exception as e:
            self.logger.error(f"实体搜索过程中发生错误: {str(e)}")
            raise ServiceError(f"实体搜索失败: {str(e)}", "ENTITY_SEARCH_FAILED")
    
    async def get_entity_relations(
        self,
        entity_id: str,
        relation_type: Optional[RelationType] = None,
        direction: str = "both",  # "incoming", "outgoing", "both"
        limit: int = 50
    ) -> List[Relation]:
        """获取实体的关系
        
        Args:
            entity_id: 实体ID
            relation_type: 关系类型过滤
            direction: 关系方向
            limit: 返回结果数量限制
            
        Returns:
            相关的关系列表
        """
        if not entity_id:
            raise ValidationError("实体ID不能为空", "entity_id", entity_id)
        
        if direction not in ["incoming", "outgoing", "both"]:
            raise ValidationError("关系方向必须是 incoming、outgoing 或 both", "direction", direction)
        
        if limit <= 0 or limit > 200:
            raise ValidationError("结果数量限制必须在1-200之间", "limit", limit)
        
        # 检查实体是否存在
        entity = await self._get_entity_by_id(entity_id)
        if not entity:
            raise NotFoundError("Entity", entity_id)
        
        try:
            relations = await self._query_entity_relations(
                entity_id, relation_type, direction, limit
            )
            
            self.logger.debug(f"获取实体关系成功", extra={
                "entity_id": entity_id,
                "relation_count": len(relations),
                "direction": direction
            })
            
            return relations
            
        except ServiceError:
            raise
        except Exception as e:
            self.logger.error(f"获取实体关系过程中发生错误: {str(e)}")
            raise ServiceError(f"获取实体关系失败: {str(e)}", "GET_ENTITY_RELATIONS_FAILED")
    
    # 私有辅助方法
    def _validate_entity_data(self, entity_data: Dict[str, Any]) -> None:
        """验证实体数据"""
        if not entity_data.get("name"):
            raise ValidationError("实体名称不能为空", "name")
        
        if len(entity_data["name"]) > 200:
            raise ValidationError("实体名称长度不能超过200字符", "name")
        
        entity_type = entity_data.get("type")
        if entity_type and entity_type not in [e.value for e in EntityType]:
            raise ValidationError(f"无效的实体类型: {entity_type}", "type")
    
    def _validate_relation_data(self, relation_data: Dict[str, Any], entity_mapping: Dict[str, str]) -> None:
        """验证关系数据"""
        source = relation_data.get("source")
        target = relation_data.get("target")
        
        if not source or not target:
            raise ValidationError("关系的源实体和目标实体不能为空")
        
        if source not in entity_mapping:
            raise ValidationError(f"源实体未找到: {source}", "source")
        
        if target not in entity_mapping:
            raise ValidationError(f"目标实体未找到: {target}", "target")
        
        if source == target:
            raise ValidationError("关系的源实体和目标实体不能相同")
    
    def _build_entity_extraction_prompt(self, text: str) -> str:
        """构建实体提取提示词"""
        return f"""
请从以下文本中提取所有重要的实体，包括人名、地名、组织名、概念等。

文本：
{text}

请以JSON格式返回结果，格式如下：
[
    {{
        "name": "实体名称",
        "type": "实体类型（PERSON/ORGANIZATION/LOCATION/CONCEPT等）",
        "description": "简短描述",
        "confidence": "置信度（HIGH/MEDIUM/LOW）",
        "properties": {{}}
    }}
]

注意：
1. 只提取真正重要和有意义的实体
2. 避免提取过于常见或无意义的词汇
3. 确保实体名称准确且完整
4. 为每个实体选择最合适的类型
"""
    
    def _build_relation_extraction_prompt(self, text: str, entities: List[Entity]) -> str:
        """构建关系提取提示词"""
        entity_names = [entity.name for entity in entities]
        
        return f"""
请从以下文本中提取实体之间的关系。

文本：
{text}

已识别的实体：
{', '.join(entity_names)}

请以JSON格式返回结果，格式如下：
[
    {{
        "source": "源实体名称",
        "target": "目标实体名称",
        "type": "关系类型",
        "description": "关系描述",
        "confidence": "置信度（HIGH/MEDIUM/LOW）",
        "properties": {{}}
    }}
]

注意：
1. 只在已识别的实体之间建立关系
2. 确保关系在文本中有明确的依据
3. 选择合适的关系类型
4. 避免创建过于冗余或不准确的关系
"""
    
    def _parse_entity_extraction_response(self, response: str) -> List[Dict[str, Any]]:
        """解析实体提取响应"""
        try:
            # 尝试直接解析JSON
            return json.loads(response)
        except json.JSONDecodeError:
            try:
                # 如果失败，尝试提取JSON部分
                start = response.find('[')
                end = response.rfind(']') + 1
                if start >= 0 and end > start:
                    json_part = response[start:end]
                    return json.loads(json_part)
            except:
                pass
            
            self.logger.error(f"无法解析实体提取响应: {response}")
            return []
    
    def _parse_relation_extraction_response(self, response: str) -> List[Dict[str, Any]]:
        """解析关系提取响应"""
        try:
            # 尝试直接解析JSON
            return json.loads(response)
        except json.JSONDecodeError:
            try:
                # 如果失败，尝试提取JSON部分
                start = response.find('[')
                end = response.rfind(']') + 1
                if start >= 0 and end > start:
                    json_part = response[start:end]
                    return json.loads(json_part)
            except:
                pass
            
            self.logger.error(f"无法解析关系提取响应: {response}")
            return []
    
    async def _batch_save_entities(self, entities: List[Entity]) -> None:
        """批量保存实体"""
        try:
            # 保存到关系数据库
            for entity in entities:
                await self.entity_repo.create(**entity.dict())
            
            # 保存到Neo4j
            if self.neo4j:
                await self._save_entities_to_neo4j(entities)
                
        except Exception as e:
            self.logger.error(f"批量保存实体失败: {str(e)}")
            raise ServiceError(f"保存实体失败: {str(e)}", "SAVE_ENTITIES_FAILED")
    
    async def _batch_save_relations(self, relations: List[Relation]) -> None:
        """批量保存关系"""
        try:
            # 保存到关系数据库
            for relation in relations:
                await self.relation_repo.create(**relation.dict())
            
            # 保存到Neo4j
            if self.neo4j:
                await self._save_relations_to_neo4j(relations)
                
        except Exception as e:
            self.logger.error(f"批量保存关系失败: {str(e)}")
            raise ServiceError(f"保存关系失败: {str(e)}", "SAVE_RELATIONS_FAILED")
    
    async def _save_entities_to_neo4j(self, entities: List[Entity]) -> None:
        """将实体保存到Neo4j"""
        try:
            for entity in entities:
                cypher = """
                MERGE (e:Entity {id: $id})
                SET e.name = $name,
                    e.type = $type,
                    e.description = $description,
                    e.confidence = $confidence,
                    e.created_at = datetime(),
                    e.properties = $properties
                """
                await self.neo4j.run(cypher, {
                    "id": entity.id,
                    "name": entity.name,
                    "type": entity.entity_type.value,
                    "description": entity.description,
                    "confidence": entity.confidence.value,
                    "properties": entity.properties
                })
        except Exception as e:
            self.logger.error(f"保存实体到Neo4j失败: {str(e)}")
            raise
    
    async def _save_relations_to_neo4j(self, relations: List[Relation]) -> None:
        """将关系保存到Neo4j"""
        try:
            for relation in relations:
                cypher = """
                MATCH (source:Entity {id: $source_id})
                MATCH (target:Entity {id: $target_id})
                MERGE (source)-[r:RELATION {id: $id}]->(target)
                SET r.type = $type,
                    r.description = $description,
                    r.confidence = $confidence,
                    r.created_at = datetime(),
                    r.properties = $properties
                """
                await self.neo4j.run(cypher, {
                    "id": relation.id,
                    "source_id": relation.source_entity_id,
                    "target_id": relation.target_entity_id,
                    "type": relation.relation_type.value,
                    "description": relation.description,
                    "confidence": relation.confidence.value,
                    "properties": relation.properties
                })
        except Exception as e:
            self.logger.error(f"保存关系到Neo4j失败: {str(e)}")
            raise
    
    async def _exact_search_entities(
        self, 
        query: str, 
        entity_type: Optional[EntityType], 
        limit: int
    ) -> List[Entity]:
        """精确搜索实体"""
        filters = {}
        if entity_type:
            filters["entity_type"] = entity_type.value
        
        # 使用仓库进行搜索
        return await self.entity_repo.search(
            search_fields=["name", "description"],
            search_term=query,
            limit=limit,
            **filters
        )
    
    async def _vector_search_entities(
        self,
        query: str,
        entity_type: Optional[EntityType],
        limit: int,
        threshold: float
    ) -> List[Entity]:
        """向量搜索实体"""
        if not self.vector_service:
            return []
        
        try:
            # 使用向量服务进行相似性搜索
            similar_entities = await self.vector_service.search_similar_entities(
                query, limit, threshold
            )
            
            # 如果需要，按实体类型过滤
            if entity_type:
                similar_entities = [
                    entity for entity in similar_entities
                    if entity.entity_type == entity_type
                ]
            
            return similar_entities
            
        except Exception as e:
            self.logger.warning(f"向量搜索失败，跳过: {str(e)}")
            return []
    
    async def _get_entity_by_id(self, entity_id: str) -> Optional[Entity]:
        """根据ID获取实体"""
        return await self.entity_repo.get_by_id(entity_id)
    
    async def _query_entity_relations(
        self,
        entity_id: str,
        relation_type: Optional[RelationType],
        direction: str,
        limit: int
    ) -> List[Relation]:
        """查询实体关系"""
        filters = {}
        
        if relation_type:
            filters["relation_type"] = relation_type.value
        
        if direction == "incoming":
            filters["target_entity_id"] = entity_id
        elif direction == "outgoing":
            filters["source_entity_id"] = entity_id
        else:  # both
            # 需要分别查询并合并结果
            incoming_relations = await self.relation_repo.get_all(
                limit=limit//2,
                target_entity_id=entity_id,
                **({k: v for k, v in filters.items() if k != "target_entity_id"})
            )
            
            outgoing_relations = await self.relation_repo.get_all(
                limit=limit//2,
                source_entity_id=entity_id,
                **({k: v for k, v in filters.items() if k != "source_entity_id"})
            )
            
            all_relations = incoming_relations + outgoing_relations
            return all_relations[:limit]
        
        return await self.relation_repo.get_all(limit=limit, **filters)
    
    # 新增的文档处理方法
    async def process_document_async(self, document_id: str) -> None:
        """异步处理文档"""
        try:
            # 获取文档
            document = await self.document_repo.get_by_id(document_id)
            if not document:
                raise NotFoundError("Document", document_id)
            
            # 更新文档状态为处理中
            await self.document_repo.update(document_id, status="processing")
            
            # 这里可以添加OCR、向量化等处理逻辑
            # TODO: 实现完整的文档处理流程
            
            # 模拟处理时间
            await asyncio.sleep(1)
            
            # 更新文档状态为已完成
            await self.document_repo.update(document_id, status="completed")
            
            self.logger.info(f"文档处理完成: {document_id}")
            
        except Exception as e:
            # 更新文档状态为失败
            try:
                await self.document_repo.update(document_id, status="failed")
            except:
                pass
            
            self.logger.error(f"文档处理失败: {document_id} - {str(e)}")
            raise ServiceError(f"文档处理失败: {str(e)}", "DOCUMENT_PROCESSING_FAILED")