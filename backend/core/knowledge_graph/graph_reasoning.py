#!/usr/bin/env python3
"""
知识图谱推理器

该模块负责知识图谱的推理和分析：
- 逻辑推理
- 路径推理
- 规则推理
- 知识补全
- 一致性检查
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional, Tuple, Set, Union
from datetime import datetime
import json
from dataclasses import dataclass
from enum import Enum

from backend.connectors.neo4j_client import Neo4jClient
from backend.connectors.starrocks_client import StarRocksClient
from backend.core.knowledge_graph.graph_query import GraphQuery
from backend.utils.logger import get_logger

logger = get_logger(__name__)

class ReasoningType(Enum):
    """推理类型枚举"""
    TRANSITIVE = "transitive"  # 传递性推理
    SYMMETRIC = "symmetric"    # 对称性推理
    INVERSE = "inverse"        # 逆向推理
    COMPOSITION = "composition"  # 组合推理
    INHERITANCE = "inheritance"  # 继承推理
    CAUSAL = "causal"          # 因果推理

@dataclass
class ReasoningRule:
    """推理规则"""
    id: str
    name: str
    rule_type: ReasoningType
    premise_pattern: str  # 前提模式（Cypher模式）
    conclusion_pattern: str  # 结论模式（Cypher模式）
    confidence_formula: str  # 置信度计算公式
    description: str
    enabled: bool = True

@dataclass
class InferredFact:
    """推理得出的事实"""
    id: str
    source_facts: List[str]  # 源事实ID列表
    reasoning_rule: str  # 使用的推理规则ID
    fact_type: str  # 事实类型（entity/relation）
    content: Dict[str, Any]  # 事实内容
    confidence: float  # 置信度
    created_at: datetime

class GraphReasoning:
    """
    知识图谱推理器
    
    提供各种推理功能，包括逻辑推理、路径推理、规则推理等。
    """
    
    def __init__(self, neo4j_client: Neo4jClient, starrocks_client: StarRocksClient,
                 graph_query: GraphQuery):
        self.neo4j_client = neo4j_client
        self.starrocks_client = starrocks_client
        self.graph_query = graph_query
        
        # 推理规则
        self.reasoning_rules = self._initialize_reasoning_rules()
        
        # 推理缓存
        self.inference_cache = {}
    
    def _initialize_reasoning_rules(self) -> List[ReasoningRule]:
        """
        初始化推理规则
        
        返回:
            List[ReasoningRule]: 推理规则列表
        """
        rules = [
            # 传递性推理规则
            ReasoningRule(
                id="transitive_part_of",
                name="传递性部分关系",
                rule_type=ReasoningType.TRANSITIVE,
                premise_pattern="(a)-[:RELATES_TO {type: 'part_of'}]->(b)-[:RELATES_TO {type: 'part_of'}]->(c)",
                conclusion_pattern="(a)-[:RELATES_TO {type: 'part_of'}]->(c)",
                confidence_formula="min(r1.confidence, r2.confidence) * 0.8",
                description="如果A是B的一部分，B是C的一部分，则A是C的一部分"
            ),
            
            # 对称性推理规则
            ReasoningRule(
                id="symmetric_similar_to",
                name="对称相似关系",
                rule_type=ReasoningType.SYMMETRIC,
                premise_pattern="(a)-[:RELATES_TO {type: 'similar_to'}]->(b)",
                conclusion_pattern="(b)-[:RELATES_TO {type: 'similar_to'}]->(a)",
                confidence_formula="r.confidence * 0.9",
                description="如果A与B相似，则B与A相似"
            ),
            
            # 逆向推理规则
            ReasoningRule(
                id="inverse_parent_child",
                name="逆向父子关系",
                rule_type=ReasoningType.INVERSE,
                premise_pattern="(parent)-[:RELATES_TO {type: 'parent_of'}]->(child)",
                conclusion_pattern="(child)-[:RELATES_TO {type: 'child_of'}]->(parent)",
                confidence_formula="r.confidence",
                description="如果A是B的父级，则B是A的子级"
            ),
            
            # 组合推理规则
            ReasoningRule(
                id="composition_location",
                name="组合位置关系",
                rule_type=ReasoningType.COMPOSITION,
                premise_pattern="(a)-[:RELATES_TO {type: 'located_in'}]->(b)-[:RELATES_TO {type: 'located_in'}]->(c)",
                conclusion_pattern="(a)-[:RELATES_TO {type: 'located_in'}]->(c)",
                confidence_formula="min(r1.confidence, r2.confidence) * 0.7",
                description="如果A位于B，B位于C，则A位于C"
            ),
            
            # 继承推理规则
            ReasoningRule(
                id="inheritance_is_a",
                name="继承类型关系",
                rule_type=ReasoningType.INHERITANCE,
                premise_pattern="(a)-[:RELATES_TO {type: 'is_a'}]->(b), (b)-[:RELATES_TO {type: 'has_property'}]->(p)",
                conclusion_pattern="(a)-[:RELATES_TO {type: 'has_property'}]->(p)",
                confidence_formula="min(r1.confidence, r2.confidence) * 0.6",
                description="如果A是B的一种，B具有属性P，则A也具有属性P"
            ),
            
            # 因果推理规则
            ReasoningRule(
                id="causal_chain",
                name="因果链推理",
                rule_type=ReasoningType.CAUSAL,
                premise_pattern="(a)-[:RELATES_TO {type: 'causes'}]->(b)-[:RELATES_TO {type: 'causes'}]->(c)",
                conclusion_pattern="(a)-[:RELATES_TO {type: 'indirectly_causes'}]->(c)",
                confidence_formula="min(r1.confidence, r2.confidence) * 0.5",
                description="如果A导致B，B导致C，则A间接导致C"
            )
        ]
        
        return rules
    
    async def perform_reasoning(self, reasoning_types: List[ReasoningType] = None,
                              max_iterations: int = 3,
                              confidence_threshold: float = 0.3) -> Dict[str, Any]:
        """
        执行推理过程
        
        参数:
            reasoning_types: 要执行的推理类型列表
            max_iterations: 最大迭代次数
            confidence_threshold: 置信度阈值
        
        返回:
            Dict[str, Any]: 推理结果统计
        """
        logger.info(f"开始执行推理，最大迭代次数: {max_iterations}")
        
        start_time = datetime.now()
        total_inferences = 0
        iteration_results = []
        
        try:
            for iteration in range(max_iterations):
                logger.debug(f"执行第 {iteration + 1} 轮推理")
                
                iteration_inferences = 0
                
                # 获取要执行的推理规则
                rules_to_execute = self.reasoning_rules
                if reasoning_types:
                    rules_to_execute = [
                        rule for rule in self.reasoning_rules 
                        if rule.rule_type in reasoning_types and rule.enabled
                    ]
                
                # 执行每个推理规则
                for rule in rules_to_execute:
                    inferences = await self._apply_reasoning_rule(
                        rule, confidence_threshold
                    )
                    iteration_inferences += len(inferences)
                    total_inferences += len(inferences)
                    
                    logger.debug(f"规则 {rule.name} 产生了 {len(inferences)} 个推理")
                
                iteration_results.append({
                    "iteration": iteration + 1,
                    "inferences_count": iteration_inferences
                })
                
                # 如果本轮没有新的推理，提前结束
                if iteration_inferences == 0:
                    logger.info(f"第 {iteration + 1} 轮推理无新发现，提前结束")
                    break
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            result = {
                "total_inferences": total_inferences,
                "iterations_executed": len(iteration_results),
                "iteration_results": iteration_results,
                "execution_time": execution_time,
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info(f"推理完成: {result}")
            return result
        
        except Exception as e:
            logger.error(f"推理执行失败: {e}")
            raise
    
    async def _apply_reasoning_rule(self, rule: ReasoningRule, 
                                  confidence_threshold: float) -> List[InferredFact]:
        """
        应用推理规则
        
        参数:
            rule: 推理规则
            confidence_threshold: 置信度阈值
        
        返回:
            List[InferredFact]: 推理得出的事实列表
        """
        try:
            # 查找符合前提模式的事实
            premise_query = f"""
            MATCH {rule.premise_pattern}
            WHERE NOT EXISTS {{
                MATCH {rule.conclusion_pattern}
            }}
            RETURN *
            """
            
            premise_results = await self.neo4j_client.execute_query(premise_query)
            
            inferred_facts = []
            
            for premise_result in premise_results:
                # 计算推理置信度
                confidence = await self._calculate_inference_confidence(
                    rule, premise_result
                )
                
                if confidence >= confidence_threshold:
                    # 创建推理事实
                    inferred_fact = await self._create_inferred_fact(
                        rule, premise_result, confidence
                    )
                    
                    if inferred_fact:
                        inferred_facts.append(inferred_fact)
                        
                        # 将推理事实添加到图谱中
                        await self._add_inferred_fact_to_graph(inferred_fact)
            
            return inferred_facts
        
        except Exception as e:
            logger.error(f"应用推理规则 {rule.name} 失败: {e}")
            return []
    
    async def _calculate_inference_confidence(self, rule: ReasoningRule, 
                                            premise_data: Any) -> float:
        """
        计算推理置信度
        
        参数:
            rule: 推理规则
            premise_data: 前提数据
        
        返回:
            float: 置信度值
        """
        try:
            # 这里简化处理，实际应该根据rule.confidence_formula计算
            # 可以使用eval或更安全的表达式解析器
            
            if rule.rule_type == ReasoningType.TRANSITIVE:
                # 传递性推理：取最小置信度并打折
                return min(0.8, 0.6)  # 简化示例
            elif rule.rule_type == ReasoningType.SYMMETRIC:
                # 对称性推理：保持较高置信度
                return 0.9
            elif rule.rule_type == ReasoningType.INVERSE:
                # 逆向推理：保持原置信度
                return 0.8
            else:
                # 其他类型：默认中等置信度
                return 0.6
        
        except Exception as e:
            logger.error(f"计算推理置信度失败: {e}")
            return 0.3
    
    async def _create_inferred_fact(self, rule: ReasoningRule, 
                                  premise_data: Any, confidence: float) -> Optional[InferredFact]:
        """
        创建推理事实
        
        参数:
            rule: 推理规则
            premise_data: 前提数据
            confidence: 置信度
        
        返回:
            Optional[InferredFact]: 推理事实
        """
        try:
            fact_id = f"inferred_{rule.id}_{datetime.now().timestamp()}"
            
            # 根据规则类型创建不同的事实内容
            if "RELATES_TO" in rule.conclusion_pattern:
                # 关系推理
                fact_content = {
                    "type": "relation",
                    "source_entity_id": "entity_a",  # 简化示例
                    "target_entity_id": "entity_b",
                    "relation_type": "inferred_relation",
                    "reasoning_rule": rule.id
                }
                fact_type = "relation"
            else:
                # 实体推理
                fact_content = {
                    "type": "entity",
                    "entity_id": "entity_a",
                    "property": "inferred_property",
                    "reasoning_rule": rule.id
                }
                fact_type = "entity"
            
            return InferredFact(
                id=fact_id,
                source_facts=["fact1", "fact2"],  # 简化示例
                reasoning_rule=rule.id,
                fact_type=fact_type,
                content=fact_content,
                confidence=confidence,
                created_at=datetime.now()
            )
        
        except Exception as e:
            logger.error(f"创建推理事实失败: {e}")
            return None
    
    async def _add_inferred_fact_to_graph(self, inferred_fact: InferredFact):
        """
        将推理事实添加到图谱中
        
        参数:
            inferred_fact: 推理事实
        """
        try:
            if inferred_fact.fact_type == "relation":
                # 添加推理关系
                query = """
                MATCH (source {id: $source_id}), (target {id: $target_id})
                CREATE (source)-[r:INFERRED_RELATION {
                    id: $fact_id,
                    type: $relation_type,
                    confidence: $confidence,
                    reasoning_rule: $reasoning_rule,
                    created_at: datetime($created_at),
                    is_inferred: true
                }]->(target)
                """
                
                await self.neo4j_client.execute_query(query, {
                    "source_id": inferred_fact.content.get("source_entity_id"),
                    "target_id": inferred_fact.content.get("target_entity_id"),
                    "fact_id": inferred_fact.id,
                    "relation_type": inferred_fact.content.get("relation_type"),
                    "confidence": inferred_fact.confidence,
                    "reasoning_rule": inferred_fact.reasoning_rule,
                    "created_at": inferred_fact.created_at.isoformat()
                })
            
            elif inferred_fact.fact_type == "entity":
                # 添加推理实体属性
                query = """
                MATCH (entity {id: $entity_id})
                SET entity.inferred_properties = 
                    CASE 
                        WHEN entity.inferred_properties IS NULL 
                        THEN [$property]
                        ELSE entity.inferred_properties + [$property]
                    END
                """
                
                await self.neo4j_client.execute_query(query, {
                    "entity_id": inferred_fact.content.get("entity_id"),
                    "property": inferred_fact.content.get("property")
                })
            
            # 记录推理事实到StarRocks
            await self._record_inference_to_starrocks(inferred_fact)
        
        except Exception as e:
            logger.error(f"添加推理事实到图谱失败: {e}")
    
    async def _record_inference_to_starrocks(self, inferred_fact: InferredFact):
        """
        将推理记录保存到StarRocks
        
        参数:
            inferred_fact: 推理事实
        """
        try:
            from backend.models.knowledge import InferenceModel
            from backend.config.database import get_async_session
            
            async with get_async_session() as session:
                new_inference = InferenceModel(
                    id=inferred_fact.id,
                    fact_type=inferred_fact.fact_type,
                    content=json.dumps(inferred_fact.content),
                    confidence=inferred_fact.confidence,
                    reasoning_rule=inferred_fact.reasoning_rule,
                    source_facts=json.dumps(inferred_fact.source_facts),
                    created_at=inferred_fact.created_at
                )
                
                session.add(new_inference)
                await session.commit()
        
        except Exception as e:
            logger.error(f"记录推理到StarRocks失败: {e}")
    
    async def check_consistency(self) -> Dict[str, Any]:
        """
        检查知识图谱的一致性
        
        返回:
            Dict[str, Any]: 一致性检查结果
        """
        logger.info("开始一致性检查")
        
        start_time = datetime.now()
        inconsistencies = []
        
        try:
            # 检查对称关系的一致性
            symmetric_inconsistencies = await self._check_symmetric_consistency()
            inconsistencies.extend(symmetric_inconsistencies)
            
            # 检查传递关系的一致性
            transitive_inconsistencies = await self._check_transitive_consistency()
            inconsistencies.extend(transitive_inconsistencies)
            
            # 检查逆向关系的一致性
            inverse_inconsistencies = await self._check_inverse_consistency()
            inconsistencies.extend(inverse_inconsistencies)
            
            # 检查类型一致性
            type_inconsistencies = await self._check_type_consistency()
            inconsistencies.extend(type_inconsistencies)
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            result = {
                "total_inconsistencies": len(inconsistencies),
                "inconsistencies": inconsistencies,
                "execution_time": execution_time,
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info(f"一致性检查完成，发现 {len(inconsistencies)} 个不一致")
            return result
        
        except Exception as e:
            logger.error(f"一致性检查失败: {e}")
            raise
    
    async def _check_symmetric_consistency(self) -> List[Dict[str, Any]]:
        """
        检查对称关系的一致性
        
        返回:
            List[Dict[str, Any]]: 不一致列表
        """
        query = """
        MATCH (a)-[r1:RELATES_TO {type: 'similar_to'}]->(b)
        WHERE NOT EXISTS {
            MATCH (b)-[r2:RELATES_TO {type: 'similar_to'}]->(a)
        }
        RETURN a.id as entity_a, b.id as entity_b, r1.id as relation_id
        """
        
        result = await self.neo4j_client.execute_query(query)
        
        return [
            {
                "type": "symmetric_violation",
                "description": f"实体 {row[0]} 与 {row[1]} 的相似关系不对称",
                "entity_a": row[0],
                "entity_b": row[1],
                "relation_id": row[2]
            }
            for row in result
        ] if result else []
    
    async def _check_transitive_consistency(self) -> List[Dict[str, Any]]:
        """
        检查传递关系的一致性
        
        返回:
            List[Dict[str, Any]]: 不一致列表
        """
        query = """
        MATCH (a)-[r1:RELATES_TO {type: 'part_of'}]->(b)-[r2:RELATES_TO {type: 'part_of'}]->(c)
        WHERE NOT EXISTS {
            MATCH (a)-[r3:RELATES_TO {type: 'part_of'}]->(c)
        }
        RETURN a.id as entity_a, b.id as entity_b, c.id as entity_c
        """
        
        result = await self.neo4j_client.execute_query(query)
        
        return [
            {
                "type": "transitive_violation",
                "description": f"缺少传递关系: {row[0]} -> {row[2]} (通过 {row[1]})",
                "entity_a": row[0],
                "entity_b": row[1],
                "entity_c": row[2]
            }
            for row in result
        ] if result else []
    
    async def _check_inverse_consistency(self) -> List[Dict[str, Any]]:
        """
        检查逆向关系的一致性
        
        返回:
            List[Dict[str, Any]]: 不一致列表
        """
        query = """
        MATCH (parent)-[r1:RELATES_TO {type: 'parent_of'}]->(child)
        WHERE NOT EXISTS {
            MATCH (child)-[r2:RELATES_TO {type: 'child_of'}]->(parent)
        }
        RETURN parent.id as parent_id, child.id as child_id, r1.id as relation_id
        """
        
        result = await self.neo4j_client.execute_query(query)
        
        return [
            {
                "type": "inverse_violation",
                "description": f"缺少逆向关系: {row[1]} -> {row[0]}",
                "parent_id": row[0],
                "child_id": row[1],
                "relation_id": row[2]
            }
            for row in result
        ] if result else []
    
    async def _check_type_consistency(self) -> List[Dict[str, Any]]:
        """
        检查类型一致性
        
        返回:
            List[Dict[str, Any]]: 不一致列表
        """
        # 检查实体类型与关系类型的匹配性
        query = """
        MATCH (a)-[r:RELATES_TO]->(b)
        WHERE (r.type = 'parent_of' AND a.type = b.type) OR
              (r.type = 'part_of' AND a.type = 'Location' AND b.type = 'Person')
        RETURN a.id as entity_a, a.type as type_a, 
               b.id as entity_b, b.type as type_b, 
               r.type as relation_type, r.id as relation_id
        """
        
        result = await self.neo4j_client.execute_query(query)
        
        return [
            {
                "type": "type_mismatch",
                "description": f"类型不匹配: {row[1]} {row[4]} {row[3]}",
                "entity_a": row[0],
                "type_a": row[1],
                "entity_b": row[2],
                "type_b": row[3],
                "relation_type": row[4],
                "relation_id": row[5]
            }
            for row in result
        ] if result else []
    
    async def suggest_knowledge_completion(self, entity_id: str = None, 
                                         limit: int = 20) -> Dict[str, Any]:
        """
        建议知识补全
        
        参数:
            entity_id: 特定实体ID（可选）
            limit: 建议数量限制
        
        返回:
            Dict[str, Any]: 知识补全建议
        """
        logger.info(f"生成知识补全建议，实体ID: {entity_id}")
        
        start_time = datetime.now()
        suggestions = []
        
        try:
            # 基于模式的补全建议
            pattern_suggestions = await self._suggest_pattern_completion(entity_id, limit)
            suggestions.extend(pattern_suggestions)
            
            # 基于相似实体的补全建议
            similarity_suggestions = await self._suggest_similarity_completion(entity_id, limit)
            suggestions.extend(similarity_suggestions)
            
            # 基于频率的补全建议
            frequency_suggestions = await self._suggest_frequency_completion(entity_id, limit)
            suggestions.extend(frequency_suggestions)
            
            # 去重和排序
            unique_suggestions = self._deduplicate_suggestions(suggestions)
            sorted_suggestions = sorted(
                unique_suggestions, 
                key=lambda x: x.get('confidence', 0), 
                reverse=True
            )[:limit]
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            result = {
                "entity_id": entity_id,
                "suggestions_count": len(sorted_suggestions),
                "suggestions": sorted_suggestions,
                "execution_time": execution_time,
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info(f"生成了 {len(sorted_suggestions)} 个知识补全建议")
            return result
        
        except Exception as e:
            logger.error(f"知识补全建议生成失败: {e}")
            raise
    
    async def _suggest_pattern_completion(self, entity_id: str, 
                                        limit: int) -> List[Dict[str, Any]]:
        """
        基于模式的补全建议
        
        参数:
            entity_id: 实体ID
            limit: 建议数量限制
        
        返回:
            List[Dict[str, Any]]: 建议列表
        """
        # 简化示例：基于同类型实体的常见关系模式
        if entity_id:
            query = """
            MATCH (target:Entity {id: $entity_id})
            MATCH (similar:Entity {type: target.type})-[r:RELATES_TO]->(related:Entity)
            WHERE similar.id <> target.id
            AND NOT EXISTS {
                MATCH (target)-[:RELATES_TO {type: r.type}]->(related)
            }
            RETURN r.type as relation_type, related.type as target_type, 
                   count(*) as frequency
            ORDER BY frequency DESC
            LIMIT $limit
            """
            
            result = await self.neo4j_client.execute_query(
                query, {"entity_id": entity_id, "limit": limit}
            )
            
            return [
                {
                    "type": "pattern_completion",
                    "suggestion": f"添加 {row[0]} 关系到 {row[1]} 类型实体",
                    "relation_type": row[0],
                    "target_type": row[1],
                    "confidence": min(0.8, row[2] / 10.0),
                    "frequency": row[2]
                }
                for row in result
            ] if result else []
        
        return []
    
    async def _suggest_similarity_completion(self, entity_id: str, 
                                           limit: int) -> List[Dict[str, Any]]:
        """
        基于相似实体的补全建议
        
        参数:
            entity_id: 实体ID
            limit: 建议数量限制
        
        返回:
            List[Dict[str, Any]]: 建议列表
        """
        # 简化示例
        return []
    
    async def _suggest_frequency_completion(self, entity_id: str, 
                                          limit: int) -> List[Dict[str, Any]]:
        """
        基于频率的补全建议
        
        参数:
            entity_id: 实体ID
            limit: 建议数量限制
        
        返回:
            List[Dict[str, Any]]: 建议列表
        """
        # 简化示例
        return []
    
    def _deduplicate_suggestions(self, suggestions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        去重建议
        
        参数:
            suggestions: 建议列表
        
        返回:
            List[Dict[str, Any]]: 去重后的建议列表
        """
        seen = set()
        unique_suggestions = []
        
        for suggestion in suggestions:
            key = (suggestion.get('type'), suggestion.get('suggestion'))
            if key not in seen:
                seen.add(key)
                unique_suggestions.append(suggestion)
        
        return unique_suggestions
    
    async def get_reasoning_statistics(self) -> Dict[str, Any]:
        """
        获取推理统计信息
        
        返回:
            Dict[str, Any]: 推理统计
        """
        try:
            from backend.models.knowledge import InferenceModel
            from backend.config.database import get_async_session
            from sqlalchemy import select, func
            
            async with get_async_session() as session:
                # 获取推理事实统计
                inference_stmt = select(InferenceModel.fact_type, func.count(InferenceModel.id)).group_by(InferenceModel.fact_type)
                inference_result = await session.execute(inference_stmt)
                inference_stats = inference_result.fetchall()
                
                # 获取推理规则使用统计
                rule_stmt = select(InferenceModel.reasoning_rule, func.count(InferenceModel.id)).group_by(InferenceModel.reasoning_rule)
                rule_result = await session.execute(rule_stmt)
                rule_stats = rule_result.fetchall()
            
            return {
                "inference_type_distribution": [
                    {"type": row[0], "count": row[1]}
                    for row in inference_stats
                ] if inference_stats else [],
                "rule_usage_distribution": [
                    {"rule": row[0], "count": row[1]}
                    for row in rule_stats
                ] if rule_stats else [],
                "total_rules": len(self.reasoning_rules),
                "enabled_rules": len([r for r in self.reasoning_rules if r.enabled])
            }
        
        except Exception as e:
            logger.error(f"获取推理统计失败: {e}")
            return {}