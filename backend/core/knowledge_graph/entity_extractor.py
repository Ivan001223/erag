from typing import List, Dict, Any, Optional, Tuple, Set
from dataclasses import dataclass
from enum import Enum
import re
import spacy
import logging
from collections import defaultdict, Counter
import asyncio
from datetime import datetime

from backend.models.knowledge import Document
from backend.models.knowledge import Entity
from backend.config.constants import EntityType
from backend.core.llm.llm_orchestrator import LLMOrchestrator

logger = logging.getLogger(__name__)

class ExtractionMethod(Enum):
    """实体提取方法"""
    NER = "ner"  # 命名实体识别
    PATTERN = "pattern"  # 模式匹配
    LLM = "llm"  # 大语言模型
    HYBRID = "hybrid"  # 混合方法

class EntityCategory(Enum):
    """实体类别"""
    PERSON = "person"
    ORGANIZATION = "organization"
    LOCATION = "location"
    EVENT = "event"
    CONCEPT = "concept"
    PRODUCT = "product"
    DATE = "date"
    MONEY = "money"
    QUANTITY = "quantity"
    MISC = "misc"

@dataclass
class ExtractionConfig:
    """实体提取配置"""
    methods: List[ExtractionMethod] = None
    min_confidence: float = 0.7
    max_entities_per_document: int = 100
    enable_coreference: bool = True
    enable_disambiguation: bool = True
    custom_patterns: Dict[str, List[str]] = None
    llm_model: str = "gpt-3.5-turbo"
    batch_size: int = 10
    
    def __post_init__(self):
        if self.methods is None:
            self.methods = [ExtractionMethod.HYBRID]
        if self.custom_patterns is None:
            self.custom_patterns = {}

@dataclass
class ExtractedEntity:
    """提取的实体"""
    text: str
    category: EntityCategory
    start_pos: int
    end_pos: int
    confidence: float
    context: str
    attributes: Dict[str, Any]
    source_method: ExtractionMethod
    canonical_form: Optional[str] = None
    aliases: List[str] = None
    
    def __post_init__(self):
        if self.aliases is None:
            self.aliases = []
        if self.canonical_form is None:
            self.canonical_form = self.text

@dataclass
class ExtractionResult:
    """实体提取结果"""
    entities: List[ExtractedEntity]
    document_id: str
    processing_time: float
    method_stats: Dict[ExtractionMethod, int]
    confidence_distribution: Dict[str, int]
    errors: List[str]
    metadata: Dict[str, Any]

class EntityExtractor:
    """实体提取器"""
    
    def __init__(self, config: ExtractionConfig = None):
        self.config = config or ExtractionConfig()
        self.nlp = None
        self.llm_orchestrator = None
        self._entity_cache = {}
        self._pattern_cache = {}
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
        if ExtractionMethod.LLM in self.config.methods or ExtractionMethod.HYBRID in self.config.methods:
            self.llm_orchestrator = LLMOrchestrator()
        
        # 编译自定义模式
        self._compile_patterns()
    
    def _compile_patterns(self):
        """编译自定义模式"""
        for category, patterns in self.config.custom_patterns.items():
            compiled_patterns = []
            for pattern in patterns:
                try:
                    compiled_patterns.append(re.compile(pattern, re.IGNORECASE))
                except re.error as e:
                    logger.warning(f"模式编译失败: {pattern}, 错误: {e}")
            self._pattern_cache[category] = compiled_patterns
    
    async def extract_entities(
        self, 
        text: str, 
        document_id: str = None,
        context: Dict[str, Any] = None
    ) -> ExtractionResult:
        """提取实体"""
        start_time = datetime.now()
        entities = []
        method_stats = defaultdict(int)
        errors = []
        
        try:
            # 根据配置的方法提取实体
            for method in self.config.methods:
                try:
                    if method == ExtractionMethod.NER:
                        ner_entities = await self._extract_with_ner(text)
                        entities.extend(ner_entities)
                        method_stats[method] += len(ner_entities)
                    
                    elif method == ExtractionMethod.PATTERN:
                        pattern_entities = await self._extract_with_patterns(text)
                        entities.extend(pattern_entities)
                        method_stats[method] += len(pattern_entities)
                    
                    elif method == ExtractionMethod.LLM:
                        llm_entities = await self._extract_with_llm(text, context)
                        entities.extend(llm_entities)
                        method_stats[method] += len(llm_entities)
                    
                    elif method == ExtractionMethod.HYBRID:
                        hybrid_entities = await self._extract_with_hybrid(text, context)
                        entities.extend(hybrid_entities)
                        method_stats[method] += len(hybrid_entities)
                
                except Exception as e:
                    error_msg = f"方法 {method.value} 提取失败: {str(e)}"
                    errors.append(error_msg)
                    logger.error(error_msg)
            
            # 去重和合并
            entities = await self._deduplicate_entities(entities)
            
            # 共指消解
            if self.config.enable_coreference:
                entities = await self._resolve_coreferences(entities, text)
            
            # 实体消歧
            if self.config.enable_disambiguation:
                entities = await self._disambiguate_entities(entities, context)
            
            # 过滤低置信度实体
            entities = [e for e in entities if e.confidence >= self.config.min_confidence]
            
            # 限制实体数量
            if len(entities) > self.config.max_entities_per_document:
                entities = sorted(entities, key=lambda x: x.confidence, reverse=True)
                entities = entities[:self.config.max_entities_per_document]
            
            # 计算置信度分布
            confidence_distribution = self._calculate_confidence_distribution(entities)
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            return ExtractionResult(
                entities=entities,
                document_id=document_id or "unknown",
                processing_time=processing_time,
                method_stats=dict(method_stats),
                confidence_distribution=confidence_distribution,
                errors=errors,
                metadata={
                    "total_entities": len(entities),
                    "text_length": len(text),
                    "methods_used": [m.value for m in self.config.methods]
                }
            )
        
        except Exception as e:
            logger.error(f"实体提取失败: {str(e)}")
            processing_time = (datetime.now() - start_time).total_seconds()
            return ExtractionResult(
                entities=[],
                document_id=document_id or "unknown",
                processing_time=processing_time,
                method_stats={},
                confidence_distribution={},
                errors=[str(e)],
                metadata={}
            )
    
    async def _extract_with_ner(self, text: str) -> List[ExtractedEntity]:
        """使用命名实体识别提取实体"""
        entities = []
        
        if not self.nlp:
            return entities
        
        try:
            doc = self.nlp(text)
            
            for ent in doc.ents:
                category = self._map_spacy_label_to_category(ent.label_)
                if category:
                    entity = ExtractedEntity(
                        text=ent.text,
                        category=category,
                        start_pos=ent.start_char,
                        end_pos=ent.end_char,
                        confidence=0.8,  # spaCy默认置信度
                        context=self._extract_context(text, ent.start_char, ent.end_char),
                        attributes={
                            "label": ent.label_,
                            "lemma": ent.lemma_ if hasattr(ent, 'lemma_') else ent.text
                        },
                        source_method=ExtractionMethod.NER
                    )
                    entities.append(entity)
        
        except Exception as e:
            logger.error(f"NER提取失败: {str(e)}")
        
        return entities
    
    async def _extract_with_patterns(self, text: str) -> List[ExtractedEntity]:
        """使用模式匹配提取实体"""
        entities = []
        
        # 内置模式
        built_in_patterns = {
            EntityCategory.DATE: [
                r'\b\d{4}-\d{2}-\d{2}\b',  # YYYY-MM-DD
                r'\b\d{1,2}/\d{1,2}/\d{4}\b',  # MM/DD/YYYY
                r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2},?\s+\d{4}\b'
            ],
            EntityCategory.MONEY: [
                r'\$[\d,]+(?:\.\d{2})?\b',  # $1,000.00
                r'\b\d+(?:,\d{3})*(?:\.\d{2})?\s*(?:dollars?|USD|yuan|RMB)\b'
            ],
            EntityCategory.QUANTITY: [
                r'\b\d+(?:\.\d+)?\s*(?:kg|km|m|cm|mm|g|lb|oz|ft|in)\b',
                r'\b\d+(?:,\d{3})*\s*(?:percent|%|pieces?|units?)\b'
            ]
        }
        
        # 合并内置模式和自定义模式
        all_patterns = {**built_in_patterns}
        for category_name, patterns in self._pattern_cache.items():
            try:
                category = EntityCategory(category_name.lower())
                if category in all_patterns:
                    all_patterns[category].extend(patterns)
                else:
                    all_patterns[category] = patterns
            except ValueError:
                logger.warning(f"未知的实体类别: {category_name}")
        
        # 应用模式
        for category, patterns in all_patterns.items():
            for pattern in patterns:
                if isinstance(pattern, str):
                    pattern = re.compile(pattern, re.IGNORECASE)
                
                for match in pattern.finditer(text):
                    entity = ExtractedEntity(
                        text=match.group(),
                        category=category,
                        start_pos=match.start(),
                        end_pos=match.end(),
                        confidence=0.9,  # 模式匹配高置信度
                        context=self._extract_context(text, match.start(), match.end()),
                        attributes={"pattern": pattern.pattern},
                        source_method=ExtractionMethod.PATTERN
                    )
                    entities.append(entity)
        
        return entities
    
    async def _extract_with_llm(self, text: str, context: Dict[str, Any] = None) -> List[ExtractedEntity]:
        """使用大语言模型提取实体"""
        entities = []
        
        if not self.llm_orchestrator:
            return entities
        
        try:
            prompt = self._build_llm_extraction_prompt(text, context)
            
            response = await self.llm_orchestrator.generate_response(
                prompt=prompt,
                model=self.config.llm_model,
                temperature=0.1,
                max_tokens=2000
            )
            
            # 解析LLM响应
            entities = self._parse_llm_response(response, text)
        
        except Exception as e:
            logger.error(f"LLM实体提取失败: {str(e)}")
        
        return entities
    
    async def _extract_with_hybrid(self, text: str, context: Dict[str, Any] = None) -> List[ExtractedEntity]:
        """使用混合方法提取实体"""
        # 并行执行多种方法
        tasks = []
        
        if self.nlp:
            tasks.append(self._extract_with_ner(text))
        
        tasks.append(self._extract_with_patterns(text))
        
        if self.llm_orchestrator:
            tasks.append(self._extract_with_llm(text, context))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 合并结果
        all_entities = []
        for result in results:
            if isinstance(result, list):
                all_entities.extend(result)
            elif isinstance(result, Exception):
                logger.error(f"混合提取中的错误: {str(result)}")
        
        return all_entities
    
    async def _deduplicate_entities(self, entities: List[ExtractedEntity]) -> List[ExtractedEntity]:
        """去重实体"""
        if not entities:
            return entities
        
        # 按位置和文本分组
        groups = defaultdict(list)
        for entity in entities:
            key = (entity.text.lower(), entity.start_pos, entity.end_pos)
            groups[key].append(entity)
        
        deduplicated = []
        for group in groups.values():
            if len(group) == 1:
                deduplicated.append(group[0])
            else:
                # 选择置信度最高的实体
                best_entity = max(group, key=lambda x: x.confidence)
                
                # 合并属性
                merged_attributes = {}
                for entity in group:
                    merged_attributes.update(entity.attributes)
                
                # 合并别名
                all_aliases = set()
                for entity in group:
                    all_aliases.update(entity.aliases)
                    all_aliases.add(entity.text)
                
                best_entity.attributes = merged_attributes
                best_entity.aliases = list(all_aliases - {best_entity.canonical_form})
                
                deduplicated.append(best_entity)
        
        return deduplicated
    
    async def _resolve_coreferences(self, entities: List[ExtractedEntity], text: str) -> List[ExtractedEntity]:
        """共指消解"""
        # 简单的共指消解实现
        # 在实际应用中，可以使用更复杂的共指消解模型
        
        person_entities = [e for e in entities if e.category == EntityCategory.PERSON]
        
        # 查找代词和可能的指代关系
        pronouns = ["he", "she", "it", "they", "him", "her", "them"]
        
        for entity in entities:
            if entity.text.lower() in pronouns:
                # 查找最近的同类型实体
                nearest_entity = self._find_nearest_entity(entity, person_entities, text)
                if nearest_entity:
                    entity.canonical_form = nearest_entity.canonical_form
                    entity.category = nearest_entity.category
                    entity.confidence *= 0.8  # 降低置信度
        
        return entities
    
    async def _disambiguate_entities(self, entities: List[ExtractedEntity], context: Dict[str, Any] = None) -> List[ExtractedEntity]:
        """实体消歧"""
        # 简单的实体消歧实现
        # 基于上下文和知识库进行消歧
        
        for entity in entities:
            # 检查是否有歧义
            if self._has_ambiguity(entity):
                # 使用上下文进行消歧
                disambiguated = await self._disambiguate_with_context(entity, context)
                if disambiguated:
                    entity.canonical_form = disambiguated
                    entity.confidence *= 0.9  # 稍微降低置信度
        
        return entities
    
    def _map_spacy_label_to_category(self, label: str) -> Optional[EntityCategory]:
        """映射spaCy标签到实体类别"""
        mapping = {
            "PERSON": EntityCategory.PERSON,
            "ORG": EntityCategory.ORGANIZATION,
            "GPE": EntityCategory.LOCATION,
            "LOC": EntityCategory.LOCATION,
            "EVENT": EntityCategory.EVENT,
            "DATE": EntityCategory.DATE,
            "MONEY": EntityCategory.MONEY,
            "QUANTITY": EntityCategory.QUANTITY,
            "PRODUCT": EntityCategory.PRODUCT
        }
        return mapping.get(label)
    
    def _extract_context(self, text: str, start: int, end: int, window: int = 50) -> str:
        """提取实体上下文"""
        context_start = max(0, start - window)
        context_end = min(len(text), end + window)
        return text[context_start:context_end]
    
    def _build_llm_extraction_prompt(self, text: str, context: Dict[str, Any] = None) -> str:
        """构建LLM实体提取提示"""
        prompt = f"""请从以下文本中提取实体，并按照指定格式返回：

文本：
{text}

请提取以下类型的实体：
- 人物 (PERSON)
- 组织 (ORGANIZATION) 
- 地点 (LOCATION)
- 事件 (EVENT)
- 概念 (CONCEPT)
- 产品 (PRODUCT)
- 日期 (DATE)
- 金额 (MONEY)
- 数量 (QUANTITY)

返回格式（JSON）：
[
  {{
    "text": "实体文本",
    "category": "实体类别",
    "start_pos": 开始位置,
    "end_pos": 结束位置,
    "confidence": 置信度(0-1),
    "attributes": {{"key": "value"}}
  }}
]

只返回JSON，不要其他解释。"""
        
        if context:
            prompt += f"\n\n上下文信息：{context}"
        
        return prompt
    
    def _parse_llm_response(self, response: str, text: str) -> List[ExtractedEntity]:
        """解析LLM响应"""
        entities = []
        
        try:
            import json
            data = json.loads(response)
            
            for item in data:
                try:
                    category = EntityCategory(item["category"].lower())
                    entity = ExtractedEntity(
                        text=item["text"],
                        category=category,
                        start_pos=item.get("start_pos", 0),
                        end_pos=item.get("end_pos", len(item["text"])),
                        confidence=item.get("confidence", 0.8),
                        context=self._extract_context(text, item.get("start_pos", 0), item.get("end_pos", len(item["text"]))),
                        attributes=item.get("attributes", {}),
                        source_method=ExtractionMethod.LLM
                    )
                    entities.append(entity)
                except (KeyError, ValueError) as e:
                    logger.warning(f"解析LLM实体失败: {item}, 错误: {e}")
        
        except json.JSONDecodeError as e:
            logger.error(f"LLM响应JSON解析失败: {e}")
        
        return entities
    
    def _find_nearest_entity(self, target: ExtractedEntity, candidates: List[ExtractedEntity], text: str) -> Optional[ExtractedEntity]:
        """查找最近的实体"""
        if not candidates:
            return None
        
        # 查找在目标实体之前且距离最近的实体
        before_entities = [e for e in candidates if e.end_pos < target.start_pos]
        if before_entities:
            return min(before_entities, key=lambda x: target.start_pos - x.end_pos)
        
        return None
    
    def _has_ambiguity(self, entity: ExtractedEntity) -> bool:
        """检查实体是否有歧义"""
        # 简单的歧义检测
        ambiguous_terms = {
            "apple": ["公司", "水果"],
            "washington": ["城市", "人名", "州名"],
            "jordan": ["国家", "人名", "品牌"]
        }
        
        return entity.text.lower() in ambiguous_terms
    
    async def _disambiguate_with_context(self, entity: ExtractedEntity, context: Dict[str, Any] = None) -> Optional[str]:
        """基于上下文消歧"""
        # 简单的上下文消歧
        if not context:
            return None
        
        # 这里可以实现更复杂的消歧逻辑
        # 例如使用知识库、词向量相似度等
        
        return None
    
    def _calculate_confidence_distribution(self, entities: List[ExtractedEntity]) -> Dict[str, int]:
        """计算置信度分布"""
        distribution = {
            "high": 0,    # >= 0.8
            "medium": 0,  # 0.6 - 0.8
            "low": 0      # < 0.6
        }
        
        for entity in entities:
            if entity.confidence >= 0.8:
                distribution["high"] += 1
            elif entity.confidence >= 0.6:
                distribution["medium"] += 1
            else:
                distribution["low"] += 1
        
        return distribution
    
    async def extract_entities_from_documents(
        self, 
        documents: List[Document],
        batch_size: int = None
    ) -> Dict[str, ExtractionResult]:
        """从多个文档中提取实体"""
        batch_size = batch_size or self.config.batch_size
        results = {}
        
        # 分批处理
        for i in range(0, len(documents), batch_size):
            batch = documents[i:i + batch_size]
            
            tasks = []
            for doc in batch:
                task = self.extract_entities(
                    text=doc.content,
                    document_id=doc.id,
                    context={
                        "title": doc.title,
                        "metadata": doc.metadata
                    }
                )
                tasks.append(task)
            
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for doc, result in zip(batch, batch_results):
                if isinstance(result, ExtractionResult):
                    results[doc.id] = result
                else:
                    logger.error(f"文档 {doc.id} 实体提取失败: {result}")
                    results[doc.id] = ExtractionResult(
                        entities=[],
                        document_id=doc.id,
                        processing_time=0,
                        method_stats={},
                        confidence_distribution={},
                        errors=[str(result)],
                        metadata={}
                    )
        
        return results
    
    def get_extraction_statistics(self, results: List[ExtractionResult]) -> Dict[str, Any]:
        """获取提取统计信息"""
        if not results:
            return {}
        
        total_entities = sum(len(r.entities) for r in results)
        total_time = sum(r.processing_time for r in results)
        
        # 方法统计
        method_counts = defaultdict(int)
        for result in results:
            for method, count in result.method_stats.items():
                method_counts[method] += count
        
        # 类别统计
        category_counts = defaultdict(int)
        for result in results:
            for entity in result.entities:
                category_counts[entity.category.value] += 1
        
        # 置信度统计
        confidence_stats = {
            "high": sum(r.confidence_distribution.get("high", 0) for r in results),
            "medium": sum(r.confidence_distribution.get("medium", 0) for r in results),
            "low": sum(r.confidence_distribution.get("low", 0) for r in results)
        }
        
        return {
            "total_documents": len(results),
            "total_entities": total_entities,
            "average_entities_per_document": total_entities / len(results) if results else 0,
            "total_processing_time": total_time,
            "average_processing_time": total_time / len(results) if results else 0,
            "method_distribution": dict(method_counts),
            "category_distribution": dict(category_counts),
            "confidence_distribution": confidence_stats,
            "error_rate": sum(1 for r in results if r.errors) / len(results) if results else 0
        }