from typing import List, Dict, Any, Optional, Tuple, Set
from dataclasses import dataclass
from enum import Enum
import re
import spacy
import logging
from collections import defaultdict, Counter
import asyncio
from datetime import datetime
import numpy as np
from itertools import combinations

from backend.models.knowledge import Relation
from backend.config.constants import RelationType
from backend.core.knowledge_graph.entity_extractor import ExtractedEntity, EntityCategory
from backend.core.llm.llm_orchestrator import LLMOrchestrator

logger = logging.getLogger(__name__)

class RelationExtractionMethod(Enum):
    """关系提取方法"""
    PATTERN = "pattern"  # 模式匹配
    DEPENDENCY = "dependency"  # 依存句法分析
    LLM = "llm"  # 大语言模型
    HYBRID = "hybrid"  # 混合方法
    STATISTICAL = "statistical"  # 统计方法

class RelationCategory(Enum):
    """关系类别"""
    # 基本关系
    IS_A = "is_a"  # 是一个
    PART_OF = "part_of"  # 部分
    LOCATED_IN = "located_in"  # 位于
    WORKS_FOR = "works_for"  # 工作于
    OWNS = "owns"  # 拥有
    CREATED_BY = "created_by"  # 创建者
    
    # 时间关系
    BEFORE = "before"  # 之前
    AFTER = "after"  # 之后
    DURING = "during"  # 期间
    
    # 因果关系
    CAUSES = "causes"  # 导致
    CAUSED_BY = "caused_by"  # 由...导致
    ENABLES = "enables"  # 使能够
    
    # 社会关系
    FRIEND_OF = "friend_of"  # 朋友
    FAMILY_OF = "family_of"  # 家庭成员
    COLLEAGUE_OF = "colleague_of"  # 同事
    
    # 商业关系
    COMPETES_WITH = "competes_with"  # 竞争
    PARTNERS_WITH = "partners_with"  # 合作
    ACQUIRED_BY = "acquired_by"  # 被收购
    
    # 其他
    SIMILAR_TO = "similar_to"  # 相似
    OPPOSITE_TO = "opposite_to"  # 相反
    RELATED_TO = "related_to"  # 相关

@dataclass
class RelationExtractionConfig:
    """关系提取配置"""
    methods: List[RelationExtractionMethod] = None
    min_confidence: float = 0.6
    max_relations_per_document: int = 200
    max_entity_distance: int = 100  # 实体间最大距离（字符数）
    enable_bidirectional: bool = True
    enable_transitive: bool = False
    custom_patterns: Dict[str, List[str]] = None
    llm_model: str = "gpt-3.5-turbo"
    batch_size: int = 10
    
    def __post_init__(self):
        if self.methods is None:
            self.methods = [RelationExtractionMethod.HYBRID]
        if self.custom_patterns is None:
            self.custom_patterns = {}

@dataclass
class ExtractedRelation:
    """提取的关系"""
    subject: ExtractedEntity
    predicate: RelationCategory
    object: ExtractedEntity
    confidence: float
    context: str
    evidence: str  # 支持该关系的文本证据
    attributes: Dict[str, Any]
    source_method: RelationExtractionMethod
    bidirectional: bool = False
    temporal_info: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.temporal_info is None:
            self.temporal_info = {}

@dataclass
class RelationExtractionResult:
    """关系提取结果"""
    relations: List[ExtractedRelation]
    document_id: str
    processing_time: float
    method_stats: Dict[RelationExtractionMethod, int]
    relation_distribution: Dict[str, int]
    errors: List[str]
    metadata: Dict[str, Any]

class RelationExtractor:
    """关系提取器"""
    
    def __init__(self, config: RelationExtractionConfig = None):
        self.config = config or RelationExtractionConfig()
        self.nlp = None
        self.llm_orchestrator = None
        self._pattern_cache = {}
        self._relation_templates = {}
        self._initialize_components()
    
    def _initialize_components(self):
        """初始化组件"""
        try:
            # 加载spaCy模型
            self.nlp = spacy.load("en_core_web_sm")
            logger.info("spaCy模型加载成功")
        except OSError:
            logger.warning("spaCy模型未找到，将使用基础功能")
            self.nlp = None
        
        # 初始化LLM编排器
        if RelationExtractionMethod.LLM in self.config.methods or RelationExtractionMethod.HYBRID in self.config.methods:
            self.llm_orchestrator = LLMOrchestrator()
        
        # 初始化关系模板
        self._initialize_relation_templates()
        
        # 编译自定义模式
        self._compile_patterns()
    
    def _initialize_relation_templates(self):
        """初始化关系模板"""
        self._relation_templates = {
            RelationCategory.IS_A: [
                r"{subject} is (?:a|an) {object}",
                r"{subject} (?:are|is) {object}",
                r"{object} such as {subject}",
                r"{subject}, (?:a|an) {object}"
            ],
            RelationCategory.PART_OF: [
                r"{subject} (?:is|are) part of {object}",
                r"{subject} belongs to {object}",
                r"{object} contains {subject}",
                r"{subject} in {object}"
            ],
            RelationCategory.LOCATED_IN: [
                r"{subject} (?:is|are) located in {object}",
                r"{subject} (?:is|are) in {object}",
                r"{subject} (?:is|are) based in {object}",
                r"{subject} of {object}"
            ],
            RelationCategory.WORKS_FOR: [
                r"{subject} works for {object}",
                r"{subject} (?:is|are) employed by {object}",
                r"{subject} of {object}",
                r"{object} employee {subject}"
            ],
            RelationCategory.OWNS: [
                r"{subject} owns {object}",
                r"{subject} possesses {object}",
                r"{object} belongs to {subject}",
                r"{subject}'s {object}"
            ],
            RelationCategory.CREATED_BY: [
                r"{object} (?:was|were) created by {subject}",
                r"{object} (?:was|were) founded by {subject}",
                r"{subject} created {object}",
                r"{subject} founded {object}"
            ],
            RelationCategory.CAUSES: [
                r"{subject} causes {object}",
                r"{subject} leads to {object}",
                r"{subject} results in {object}",
                r"due to {subject}, {object}"
            ],
            RelationCategory.COMPETES_WITH: [
                r"{subject} competes with {object}",
                r"{subject} (?:is|are) (?:a )?competitor of {object}",
                r"{subject} and {object} (?:are )?competitors",
                r"{subject} vs {object}"
            ]
        }
    
    def _compile_patterns(self):
        """编译自定义模式"""
        for relation_name, patterns in self.config.custom_patterns.items():
            try:
                relation_category = RelationCategory(relation_name.lower())
                compiled_patterns = []
                for pattern in patterns:
                    try:
                        compiled_patterns.append(re.compile(pattern, re.IGNORECASE))
                    except re.error as e:
                        logger.warning(f"关系模式编译失败: {pattern}, 错误: {e}")
                self._pattern_cache[relation_category] = compiled_patterns
            except ValueError:
                logger.warning(f"未知的关系类别: {relation_name}")
    
    async def extract_relations(
        self,
        entities: List[ExtractedEntity],
        text: str,
        document_id: str = None,
        context: Dict[str, Any] = None
    ) -> RelationExtractionResult:
        """提取关系"""
        start_time = datetime.now()
        relations = []
        method_stats = defaultdict(int)
        errors = []
        
        try:
            # 生成实体对
            entity_pairs = self._generate_entity_pairs(entities, text)
            
            # 根据配置的方法提取关系
            for method in self.config.methods:
                try:
                    if method == RelationExtractionMethod.PATTERN:
                        pattern_relations = await self._extract_with_patterns(entity_pairs, text)
                        relations.extend(pattern_relations)
                        method_stats[method] += len(pattern_relations)
                    
                    elif method == RelationExtractionMethod.DEPENDENCY:
                        dep_relations = await self._extract_with_dependency(entity_pairs, text)
                        relations.extend(dep_relations)
                        method_stats[method] += len(dep_relations)
                    
                    elif method == RelationExtractionMethod.LLM:
                        llm_relations = await self._extract_with_llm(entity_pairs, text, context)
                        relations.extend(llm_relations)
                        method_stats[method] += len(llm_relations)
                    
                    elif method == RelationExtractionMethod.STATISTICAL:
                        stat_relations = await self._extract_with_statistical(entity_pairs, text)
                        relations.extend(stat_relations)
                        method_stats[method] += len(stat_relations)
                    
                    elif method == RelationExtractionMethod.HYBRID:
                        hybrid_relations = await self._extract_with_hybrid(entity_pairs, text, context)
                        relations.extend(hybrid_relations)
                        method_stats[method] += len(hybrid_relations)
                
                except Exception as e:
                    error_msg = f"方法 {method.value} 关系提取失败: {str(e)}"
                    errors.append(error_msg)
                    logger.error(error_msg)
            
            # 去重和合并
            relations = await self._deduplicate_relations(relations)
            
            # 添加双向关系
            if self.config.enable_bidirectional:
                relations = await self._add_bidirectional_relations(relations)
            
            # 传递关系推理
            if self.config.enable_transitive:
                relations = await self._infer_transitive_relations(relations)
            
            # 过滤低置信度关系
            relations = [r for r in relations if r.confidence >= self.config.min_confidence]
            
            # 限制关系数量
            if len(relations) > self.config.max_relations_per_document:
                relations = sorted(relations, key=lambda x: x.confidence, reverse=True)
                relations = relations[:self.config.max_relations_per_document]
            
            # 计算关系分布
            relation_distribution = self._calculate_relation_distribution(relations)
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            return RelationExtractionResult(
                relations=relations,
                document_id=document_id or "unknown",
                processing_time=processing_time,
                method_stats=dict(method_stats),
                relation_distribution=relation_distribution,
                errors=errors,
                metadata={
                    "total_relations": len(relations),
                    "total_entities": len(entities),
                    "entity_pairs_considered": len(entity_pairs),
                    "methods_used": [m.value for m in self.config.methods]
                }
            )
        
        except Exception as e:
            logger.error(f"关系提取失败: {str(e)}")
            processing_time = (datetime.now() - start_time).total_seconds()
            return RelationExtractionResult(
                relations=[],
                document_id=document_id or "unknown",
                processing_time=processing_time,
                method_stats={},
                relation_distribution={},
                errors=[str(e)],
                metadata={}
            )
    
    def _generate_entity_pairs(self, entities: List[ExtractedEntity], text: str) -> List[Tuple[ExtractedEntity, ExtractedEntity]]:
        """生成实体对"""
        pairs = []
        
        for i, entity1 in enumerate(entities):
            for j, entity2 in enumerate(entities):
                if i != j:
                    # 检查实体间距离
                    distance = abs(entity1.start_pos - entity2.start_pos)
                    if distance <= self.config.max_entity_distance:
                        pairs.append((entity1, entity2))
        
        return pairs
    
    async def _extract_with_patterns(self, entity_pairs: List[Tuple[ExtractedEntity, ExtractedEntity]], text: str) -> List[ExtractedRelation]:
        """使用模式匹配提取关系"""
        relations = []
        
        for subject, obj in entity_pairs:
            # 获取实体间的文本
            start_pos = min(subject.start_pos, obj.start_pos)
            end_pos = max(subject.end_pos, obj.end_pos)
            context_text = text[start_pos:end_pos]
            
            # 应用关系模板
            for relation_category, templates in self._relation_templates.items():
                for template in templates:
                    # 替换模板中的占位符
                    pattern = template.format(
                        subject=re.escape(subject.text),
                        object=re.escape(obj.text)
                    )
                    
                    if re.search(pattern, context_text, re.IGNORECASE):
                        relation = ExtractedRelation(
                            subject=subject,
                            predicate=relation_category,
                            object=obj,
                            confidence=0.8,
                            context=context_text,
                            evidence=context_text,
                            attributes={"pattern": template},
                            source_method=RelationExtractionMethod.PATTERN
                        )
                        relations.append(relation)
                        break
        
        return relations
    
    async def _extract_with_dependency(self, entity_pairs: List[Tuple[ExtractedEntity, ExtractedEntity]], text: str) -> List[ExtractedRelation]:
        """使用依存句法分析提取关系"""
        relations = []
        
        if not self.nlp:
            return relations
        
        try:
            doc = self.nlp(text)
            
            for subject, obj in entity_pairs:
                # 查找实体在依存树中的位置
                subject_tokens = self._find_entity_tokens(doc, subject)
                obj_tokens = self._find_entity_tokens(doc, obj)
                
                if subject_tokens and obj_tokens:
                    # 分析依存关系
                    relation_info = self._analyze_dependency_path(subject_tokens, obj_tokens, doc)
                    
                    if relation_info:
                        relation_category = self._map_dependency_to_relation(relation_info)
                        if relation_category:
                            relation = ExtractedRelation(
                                subject=subject,
                                predicate=relation_category,
                                object=obj,
                                confidence=0.7,
                                context=self._extract_sentence_context(doc, subject, obj),
                                evidence=relation_info["evidence"],
                                attributes={
                                    "dependency_path": relation_info["path"],
                                    "root_verb": relation_info.get("root_verb")
                                },
                                source_method=RelationExtractionMethod.DEPENDENCY
                            )
                            relations.append(relation)
        
        except Exception as e:
            logger.error(f"依存句法分析失败: {str(e)}")
        
        return relations
    
    async def _extract_with_llm(self, entity_pairs: List[Tuple[ExtractedEntity, ExtractedEntity]], text: str, context: Dict[str, Any] = None) -> List[ExtractedRelation]:
        """使用大语言模型提取关系"""
        relations = []
        
        if not self.llm_orchestrator:
            return relations
        
        try:
            # 分批处理实体对
            batch_size = 10
            for i in range(0, len(entity_pairs), batch_size):
                batch_pairs = entity_pairs[i:i + batch_size]
                
                prompt = self._build_llm_relation_prompt(batch_pairs, text, context)
                
                response = await self.llm_orchestrator.generate_response(
                    prompt=prompt,
                    model=self.config.llm_model,
                    temperature=0.1,
                    max_tokens=2000
                )
                
                # 解析LLM响应
                batch_relations = self._parse_llm_relation_response(response, batch_pairs)
                relations.extend(batch_relations)
        
        except Exception as e:
            logger.error(f"LLM关系提取失败: {str(e)}")
        
        return relations
    
    async def _extract_with_statistical(self, entity_pairs: List[Tuple[ExtractedEntity, ExtractedEntity]], text: str) -> List[ExtractedRelation]:
        """使用统计方法提取关系"""
        relations = []
        
        # 基于共现频率的统计方法
        for subject, obj in entity_pairs:
            # 计算实体间的统计特征
            distance = abs(subject.start_pos - obj.start_pos)
            
            # 基于距离的置信度
            distance_confidence = max(0, 1 - distance / self.config.max_entity_distance)
            
            # 基于实体类型的关系推断
            type_based_relation = self._infer_relation_from_types(subject.category, obj.category)
            
            if type_based_relation and distance_confidence > 0.5:
                relation = ExtractedRelation(
                    subject=subject,
                    predicate=type_based_relation,
                    object=obj,
                    confidence=distance_confidence * 0.6,  # 统计方法置信度较低
                    context=text[min(subject.start_pos, obj.start_pos):max(subject.end_pos, obj.end_pos)],
                    evidence=f"Statistical inference based on entity types and distance",
                    attributes={
                        "distance": distance,
                        "type_inference": True
                    },
                    source_method=RelationExtractionMethod.STATISTICAL
                )
                relations.append(relation)
        
        return relations
    
    async def _extract_with_hybrid(self, entity_pairs: List[Tuple[ExtractedEntity, ExtractedEntity]], text: str, context: Dict[str, Any] = None) -> List[ExtractedRelation]:
        """使用混合方法提取关系"""
        # 并行执行多种方法
        tasks = [
            self._extract_with_patterns(entity_pairs, text),
            self._extract_with_statistical(entity_pairs, text)
        ]
        
        if self.nlp:
            tasks.append(self._extract_with_dependency(entity_pairs, text))
        
        if self.llm_orchestrator:
            tasks.append(self._extract_with_llm(entity_pairs, text, context))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 合并结果
        all_relations = []
        for result in results:
            if isinstance(result, list):
                all_relations.extend(result)
            elif isinstance(result, Exception):
                logger.error(f"混合关系提取中的错误: {str(result)}")
        
        return all_relations
    
    async def _deduplicate_relations(self, relations: List[ExtractedRelation]) -> List[ExtractedRelation]:
        """去重关系"""
        if not relations:
            return relations
        
        # 按主体、谓词、客体分组
        groups = defaultdict(list)
        for relation in relations:
            key = (
                relation.subject.canonical_form,
                relation.predicate.value,
                relation.object.canonical_form
            )
            groups[key].append(relation)
        
        deduplicated = []
        for group in groups.values():
            if len(group) == 1:
                deduplicated.append(group[0])
            else:
                # 选择置信度最高的关系
                best_relation = max(group, key=lambda x: x.confidence)
                
                # 合并证据
                all_evidence = [r.evidence for r in group]
                best_relation.evidence = " | ".join(set(all_evidence))
                
                # 合并属性
                merged_attributes = {}
                for relation in group:
                    merged_attributes.update(relation.attributes)
                best_relation.attributes = merged_attributes
                
                deduplicated.append(best_relation)
        
        return deduplicated
    
    async def _add_bidirectional_relations(self, relations: List[ExtractedRelation]) -> List[ExtractedRelation]:
        """添加双向关系"""
        bidirectional_relations = []
        
        # 定义可双向的关系
        bidirectional_mappings = {
            RelationCategory.SIMILAR_TO: RelationCategory.SIMILAR_TO,
            RelationCategory.COMPETES_WITH: RelationCategory.COMPETES_WITH,
            RelationCategory.PARTNERS_WITH: RelationCategory.PARTNERS_WITH,
            RelationCategory.FRIEND_OF: RelationCategory.FRIEND_OF,
            RelationCategory.COLLEAGUE_OF: RelationCategory.COLLEAGUE_OF
        }
        
        for relation in relations:
            if relation.predicate in bidirectional_mappings:
                # 创建反向关系
                reverse_relation = ExtractedRelation(
                    subject=relation.object,
                    predicate=bidirectional_mappings[relation.predicate],
                    object=relation.subject,
                    confidence=relation.confidence * 0.9,  # 稍微降低置信度
                    context=relation.context,
                    evidence=relation.evidence,
                    attributes=relation.attributes.copy(),
                    source_method=relation.source_method,
                    bidirectional=True
                )
                bidirectional_relations.append(reverse_relation)
        
        return relations + bidirectional_relations
    
    async def _infer_transitive_relations(self, relations: List[ExtractedRelation]) -> List[ExtractedRelation]:
        """推理传递关系"""
        transitive_relations = []
        
        # 定义传递关系
        transitive_rules = {
            RelationCategory.IS_A: RelationCategory.IS_A,
            RelationCategory.PART_OF: RelationCategory.PART_OF,
            RelationCategory.LOCATED_IN: RelationCategory.LOCATED_IN
        }
        
        # 按关系类型分组
        relation_groups = defaultdict(list)
        for relation in relations:
            if relation.predicate in transitive_rules:
                relation_groups[relation.predicate].append(relation)
        
        # 应用传递规则
        for predicate, group_relations in relation_groups.items():
            for r1 in group_relations:
                for r2 in group_relations:
                    if (r1.object.canonical_form == r2.subject.canonical_form and 
                        r1.subject.canonical_form != r2.object.canonical_form):
                        
                        # 创建传递关系
                        transitive_relation = ExtractedRelation(
                            subject=r1.subject,
                            predicate=transitive_rules[predicate],
                            object=r2.object,
                            confidence=min(r1.confidence, r2.confidence) * 0.7,
                            context=f"{r1.context} | {r2.context}",
                            evidence=f"Transitive inference from: {r1.evidence} and {r2.evidence}",
                            attributes={
                                "transitive": True,
                                "source_relations": [r1, r2]
                            },
                            source_method=RelationExtractionMethod.STATISTICAL
                        )
                        transitive_relations.append(transitive_relation)
        
        return relations + transitive_relations
    
    def _find_entity_tokens(self, doc, entity: ExtractedEntity) -> List:
        """在spaCy文档中查找实体对应的token"""
        tokens = []
        for token in doc:
            if (token.idx >= entity.start_pos and 
                token.idx + len(token.text) <= entity.end_pos):
                tokens.append(token)
        return tokens
    
    def _analyze_dependency_path(self, subject_tokens: List, obj_tokens: List, doc) -> Optional[Dict[str, Any]]:
        """分析依存路径"""
        if not subject_tokens or not obj_tokens:
            return None
        
        # 简化实现：查找最短依存路径
        subject_token = subject_tokens[0]
        obj_token = obj_tokens[0]
        
        # 查找共同祖先
        path = self._find_dependency_path(subject_token, obj_token)
        
        if path:
            return {
                "path": [token.dep_ for token in path],
                "evidence": " ".join([token.text for token in path]),
                "root_verb": self._find_root_verb(path)
            }
        
        return None
    
    def _find_dependency_path(self, token1, token2) -> Optional[List]:
        """查找两个token之间的依存路径"""
        # 简化实现：直接检查是否有直接依存关系
        if token1.head == token2 or token2.head == token1:
            return [token1, token2]
        
        # 检查是否有共同的head
        if token1.head == token2.head:
            return [token1, token1.head, token2]
        
        return None
    
    def _find_root_verb(self, path: List) -> Optional[str]:
        """查找路径中的根动词"""
        for token in path:
            if token.pos_ == "VERB" and token.dep_ == "ROOT":
                return token.lemma_
        return None
    
    def _map_dependency_to_relation(self, relation_info: Dict[str, Any]) -> Optional[RelationCategory]:
        """将依存关系映射到关系类别"""
        path = relation_info.get("path", [])
        root_verb = relation_info.get("root_verb")
        
        # 简单的映射规则
        if "nsubj" in path and "dobj" in path:
            if root_verb in ["own", "have", "possess"]:
                return RelationCategory.OWNS
            elif root_verb in ["work", "employ"]:
                return RelationCategory.WORKS_FOR
            elif root_verb in ["create", "found", "establish"]:
                return RelationCategory.CREATED_BY
            elif root_verb in ["cause", "lead", "result"]:
                return RelationCategory.CAUSES
        
        return RelationCategory.RELATED_TO
    
    def _extract_sentence_context(self, doc, subject: ExtractedEntity, obj: ExtractedEntity) -> str:
        """提取句子上下文"""
        # 查找包含两个实体的句子
        for sent in doc.sents:
            if (sent.start_char <= subject.start_pos <= sent.end_char and
                sent.start_char <= obj.start_pos <= sent.end_char):
                return sent.text
        
        # 如果没有找到包含两个实体的句子，返回实体间的文本
        start_pos = min(subject.start_pos, obj.start_pos)
        end_pos = max(subject.end_pos, obj.end_pos)
        return doc.text[start_pos:end_pos]
    
    def _infer_relation_from_types(self, subject_type: EntityCategory, obj_type: EntityCategory) -> Optional[RelationCategory]:
        """基于实体类型推断关系"""
        type_mappings = {
            (EntityCategory.PERSON, EntityCategory.ORGANIZATION): RelationCategory.WORKS_FOR,
            (EntityCategory.PERSON, EntityCategory.LOCATION): RelationCategory.LOCATED_IN,
            (EntityCategory.ORGANIZATION, EntityCategory.LOCATION): RelationCategory.LOCATED_IN,
            (EntityCategory.PRODUCT, EntityCategory.ORGANIZATION): RelationCategory.CREATED_BY,
            (EntityCategory.EVENT, EntityCategory.LOCATION): RelationCategory.LOCATED_IN,
            (EntityCategory.PERSON, EntityCategory.PERSON): RelationCategory.RELATED_TO
        }
        
        return type_mappings.get((subject_type, obj_type))
    
    def _build_llm_relation_prompt(self, entity_pairs: List[Tuple[ExtractedEntity, ExtractedEntity]], text: str, context: Dict[str, Any] = None) -> str:
        """构建LLM关系提取提示"""
        pairs_text = "\n".join([
            f"- {pair[0].text} ({pair[0].category.value}) <-> {pair[1].text} ({pair[1].category.value})"
            for pair in entity_pairs
        ])
        
        prompt = f"""请分析以下文本中实体对之间的关系：

文本：
{text}

实体对：
{pairs_text}

请识别以下类型的关系：
- is_a (是一个)
- part_of (部分)
- located_in (位于)
- works_for (工作于)
- owns (拥有)
- created_by (创建者)
- causes (导致)
- similar_to (相似)
- competes_with (竞争)
- partners_with (合作)
- related_to (相关)

返回格式（JSON）：
[
  {{
    "subject": "主体实体文本",
    "predicate": "关系类型",
    "object": "客体实体文本",
    "confidence": 置信度(0-1),
    "evidence": "支持该关系的文本证据"
  }}
]

只返回JSON，不要其他解释。"""
        
        if context:
            prompt += f"\n\n上下文信息：{context}"
        
        return prompt
    
    def _parse_llm_relation_response(self, response: str, entity_pairs: List[Tuple[ExtractedEntity, ExtractedEntity]]) -> List[ExtractedRelation]:
        """解析LLM关系响应"""
        relations = []
        
        try:
            import json
            data = json.loads(response)
            
            # 创建实体查找字典
            entity_dict = {}
            for subject, obj in entity_pairs:
                entity_dict[subject.text] = subject
                entity_dict[obj.text] = obj
            
            for item in data:
                try:
                    subject_text = item["subject"]
                    obj_text = item["object"]
                    
                    if subject_text in entity_dict and obj_text in entity_dict:
                        predicate = RelationCategory(item["predicate"])
                        
                        relation = ExtractedRelation(
                            subject=entity_dict[subject_text],
                            predicate=predicate,
                            object=entity_dict[obj_text],
                            confidence=item.get("confidence", 0.8),
                            context="",  # 将在后续填充
                            evidence=item.get("evidence", ""),
                            attributes={"llm_generated": True},
                            source_method=RelationExtractionMethod.LLM
                        )
                        relations.append(relation)
                
                except (KeyError, ValueError) as e:
                    logger.warning(f"解析LLM关系失败: {item}, 错误: {e}")
        
        except json.JSONDecodeError as e:
            logger.error(f"LLM关系响应JSON解析失败: {e}")
        
        return relations
    
    def _calculate_relation_distribution(self, relations: List[ExtractedRelation]) -> Dict[str, int]:
        """计算关系分布"""
        distribution = defaultdict(int)
        
        for relation in relations:
            distribution[relation.predicate.value] += 1
        
        return dict(distribution)
    
    def get_relation_statistics(self, results: List[RelationExtractionResult]) -> Dict[str, Any]:
        """获取关系提取统计信息"""
        if not results:
            return {}
        
        total_relations = sum(len(r.relations) for r in results)
        total_time = sum(r.processing_time for r in results)
        
        # 方法统计
        method_counts = defaultdict(int)
        for result in results:
            for method, count in result.method_stats.items():
                method_counts[method] += count
        
        # 关系类型统计
        relation_counts = defaultdict(int)
        for result in results:
            for relation_type, count in result.relation_distribution.items():
                relation_counts[relation_type] += count
        
        # 置信度统计
        confidence_stats = {"high": 0, "medium": 0, "low": 0}
        for result in results:
            for relation in result.relations:
                if relation.confidence >= 0.8:
                    confidence_stats["high"] += 1
                elif relation.confidence >= 0.6:
                    confidence_stats["medium"] += 1
                else:
                    confidence_stats["low"] += 1
        
        return {
            "total_documents": len(results),
            "total_relations": total_relations,
            "average_relations_per_document": total_relations / len(results) if results else 0,
            "total_processing_time": total_time,
            "average_processing_time": total_time / len(results) if results else 0,
            "method_distribution": dict(method_counts),
            "relation_type_distribution": dict(relation_counts),
            "confidence_distribution": confidence_stats,
            "error_rate": sum(1 for r in results if r.errors) / len(results) if results else 0
        }