"""数据转换器

负责数据格式转换、内容处理和数据增强，支持多种转换规则和自定义转换逻辑。
"""

import re
import json
import uuid
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union, Callable, Tuple
from enum import Enum
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
from pydantic import BaseModel, Field

from backend.utils.logger import get_logger
from .data_structurer import StructuredData, DataType, StructureType

logger = get_logger(__name__)


class TransformationType(str, Enum):
    """转换类型枚举"""
    CLEAN = "clean"  # 数据清洗
    NORMALIZE = "normalize"  # 数据标准化
    ENRICH = "enrich"  # 数据增强
    AGGREGATE = "aggregate"  # 数据聚合
    FILTER = "filter"  # 数据过滤
    MAP = "map"  # 数据映射
    SPLIT = "split"  # 数据分割
    MERGE = "merge"  # 数据合并
    EXTRACT = "extract"  # 数据提取
    CUSTOM = "custom"  # 自定义转换


class TransformationStatus(str, Enum):
    """转换状态枚举"""
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"
    SKIPPED = "skipped"


@dataclass
class TransformationRule:
    """转换规则"""
    id: str
    name: str
    transformation_type: TransformationType
    source_field: str  # 源字段路径
    target_field: str  # 目标字段路径
    parameters: Dict[str, Any]
    condition: Optional[str] = None  # 执行条件
    priority: int = 5  # 优先级，数字越大优先级越高
    enabled: bool = True
    custom_function: Optional[Callable] = None
    description: Optional[str] = None


class TransformationResult(BaseModel):
    """转换结果"""
    rule_id: str
    rule_name: str
    status: TransformationStatus
    message: str
    source_field: str
    target_field: str
    original_value: Any = None
    transformed_value: Any = None
    execution_time_ms: Optional[int] = None
    timestamp: datetime = Field(default_factory=datetime.now)


class TransformationReport(BaseModel):
    """转换报告"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    data_id: str
    total_rules: int
    successful_rules: int
    failed_rules: int
    partial_rules: int
    skipped_rules: int
    results: List[TransformationResult]
    summary: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)
    duration_ms: Optional[int] = None


class DataTransformer:
    """数据转换器
    
    提供灵活的数据转换功能，支持多种转换规则和自定义转换逻辑。
    """

    def __init__(self):
        """初始化数据转换器"""
        self.rules: Dict[str, TransformationRule] = {}
        self.rule_chains: Dict[str, List[str]] = {}  # 转换链
        self._initialize_default_rules()
        
    def _initialize_default_rules(self) -> None:
        """初始化默认转换规则"""
        # 文本清洗规则
        self.add_rule(TransformationRule(
            id="clean_whitespace",
            name="清理空白字符",
            transformation_type=TransformationType.CLEAN,
            source_field="content.text",
            target_field="content.text",
            parameters={"strip": True, "normalize_spaces": True},
            description="移除多余的空白字符和换行符"
        ))
        
        self.add_rule(TransformationRule(
            id="remove_html_tags",
            name="移除HTML标签",
            transformation_type=TransformationType.CLEAN,
            source_field="content.text",
            target_field="content.text",
            parameters={"keep_text": True},
            description="移除HTML标签，保留文本内容"
        ))
        
        # 文本标准化规则
        self.add_rule(TransformationRule(
            id="normalize_encoding",
            name="编码标准化",
            transformation_type=TransformationType.NORMALIZE,
            source_field="content.text",
            target_field="content.text",
            parameters={"target_encoding": "utf-8"},
            description="统一文本编码格式"
        ))
        
        self.add_rule(TransformationRule(
            id="normalize_line_endings",
            name="换行符标准化",
            transformation_type=TransformationType.NORMALIZE,
            source_field="content.text",
            target_field="content.text",
            parameters={"line_ending": "\n"},
            description="统一换行符格式"
        ))
        
        # 数据增强规则
        self.add_rule(TransformationRule(
            id="add_word_count",
            name="添加词数统计",
            transformation_type=TransformationType.ENRICH,
            source_field="content.text",
            target_field="metadata.word_count",
            parameters={},
            description="计算并添加文本词数"
        ))
        
        self.add_rule(TransformationRule(
            id="add_character_count",
            name="添加字符数统计",
            transformation_type=TransformationType.ENRICH,
            source_field="content.text",
            target_field="metadata.character_count",
            parameters={},
            description="计算并添加字符数"
        ))
        
        self.add_rule(TransformationRule(
            id="add_content_hash",
            name="添加内容哈希",
            transformation_type=TransformationType.ENRICH,
            source_field="content",
            target_field="metadata.content_hash",
            parameters={"algorithm": "md5"},
            description="生成内容哈希值用于去重"
        ))
        
        # 实体标准化规则
        self.add_rule(TransformationRule(
            id="normalize_entities",
            name="实体标准化",
            transformation_type=TransformationType.NORMALIZE,
            source_field="entities",
            target_field="entities",
            parameters={"lowercase_types": True, "trim_values": True},
            description="标准化实体格式"
        ))
        
        # 创建默认转换链
        self.rule_chains["text_processing"] = [
            "clean_whitespace", "remove_html_tags", 
            "normalize_encoding", "normalize_line_endings"
        ]
        
        self.rule_chains["enrichment"] = [
            "add_word_count", "add_character_count", "add_content_hash"
        ]
        
        self.rule_chains["entity_processing"] = [
            "normalize_entities"
        ]
        
        self.rule_chains["complete"] = [
            "clean_whitespace", "remove_html_tags", "normalize_encoding",
            "normalize_line_endings", "add_word_count", "add_character_count",
            "add_content_hash", "normalize_entities"
        ]

    def add_rule(self, rule: TransformationRule) -> None:
        """添加转换规则
        
        Args:
            rule: 转换规则
        """
        self.rules[rule.id] = rule
        logger.debug(f"添加转换规则: {rule.name}")

    def remove_rule(self, rule_id: str) -> None:
        """移除转换规则
        
        Args:
            rule_id: 规则ID
        """
        if rule_id in self.rules:
            del self.rules[rule_id]
            logger.debug(f"移除转换规则: {rule_id}")

    def create_rule_chain(self, name: str, rule_ids: List[str]) -> None:
        """创建转换链
        
        Args:
            name: 转换链名称
            rule_ids: 规则ID列表（按执行顺序）
        """
        self.rule_chains[name] = rule_ids
        logger.debug(f"创建转换链: {name}, 包含 {len(rule_ids)} 个规则")

    async def transform(
        self,
        data: StructuredData,
        rule_chain: Optional[str] = None,
        rule_ids: Optional[List[str]] = None
    ) -> Tuple[StructuredData, TransformationReport]:
        """转换数据
        
        Args:
            data: 结构化数据
            rule_chain: 转换链名称
            rule_ids: 特定规则ID列表
            
        Returns:
            转换后的数据和转换报告
        """
        start_time = datetime.now()
        
        try:
            logger.info(f"开始转换数据: {data.id}")
            
            # 创建数据副本
            transformed_data = data.copy(deep=True)
            
            # 确定要使用的规则
            if rule_ids:
                rules_to_apply = rule_ids
            elif rule_chain and rule_chain in self.rule_chains:
                rules_to_apply = self.rule_chains[rule_chain]
            else:
                rules_to_apply = self.rule_chains.get("text_processing", [])
            
            # 按优先级排序规则
            sorted_rules = sorted(
                [(rule_id, self.rules[rule_id]) for rule_id in rules_to_apply if rule_id in self.rules],
                key=lambda x: x[1].priority,
                reverse=True
            )
            
            # 执行转换
            results = []
            for rule_id, rule in sorted_rules:
                if rule.enabled:
                    result = await self._apply_rule(transformed_data, rule)
                    results.append(result)
            
            # 更新时间戳
            transformed_data.updated_at = datetime.now()
            
            # 统计结果
            successful = sum(1 for r in results if r.status == TransformationStatus.SUCCESS)
            failed = sum(1 for r in results if r.status == TransformationStatus.FAILED)
            partial = sum(1 for r in results if r.status == TransformationStatus.PARTIAL)
            skipped = sum(1 for r in results if r.status == TransformationStatus.SKIPPED)
            
            # 创建报告
            duration = int((datetime.now() - start_time).total_seconds() * 1000)
            
            report = TransformationReport(
                data_id=data.id,
                total_rules=len(results),
                successful_rules=successful,
                failed_rules=failed,
                partial_rules=partial,
                skipped_rules=skipped,
                results=results,
                duration_ms=duration,
                summary=self._generate_summary(results)
            )
            
            logger.info(
                f"数据转换完成: {data.id}, 成功: {successful}, "
                f"失败: {failed}, 部分: {partial}, 跳过: {skipped}"
            )
            
            return transformed_data, report
            
        except Exception as e:
            logger.error(f"数据转换失败: {data.id}, 错误: {str(e)}")
            raise

    async def _apply_rule(
        self,
        data: StructuredData,
        rule: TransformationRule
    ) -> TransformationResult:
        """应用转换规则
        
        Args:
            data: 结构化数据
            rule: 转换规则
            
        Returns:
            转换结果
        """
        start_time = datetime.now()
        
        try:
            # 检查执行条件
            if rule.condition and not self._evaluate_condition(data, rule.condition):
                return TransformationResult(
                    rule_id=rule.id,
                    rule_name=rule.name,
                    status=TransformationStatus.SKIPPED,
                    message="不满足执行条件",
                    source_field=rule.source_field,
                    target_field=rule.target_field
                )
            
            # 获取源字段值
            source_value = self._get_field_value(data, rule.source_field)
            
            # 根据转换类型执行转换
            if rule.transformation_type == TransformationType.CLEAN:
                transformed_value, status, message = await self._transform_clean(source_value, rule)
            elif rule.transformation_type == TransformationType.NORMALIZE:
                transformed_value, status, message = await self._transform_normalize(source_value, rule)
            elif rule.transformation_type == TransformationType.ENRICH:
                transformed_value, status, message = await self._transform_enrich(source_value, rule, data)
            elif rule.transformation_type == TransformationType.FILTER:
                transformed_value, status, message = await self._transform_filter(source_value, rule)
            elif rule.transformation_type == TransformationType.MAP:
                transformed_value, status, message = await self._transform_map(source_value, rule)
            elif rule.transformation_type == TransformationType.EXTRACT:
                transformed_value, status, message = await self._transform_extract(source_value, rule)
            elif rule.transformation_type == TransformationType.CUSTOM:
                transformed_value, status, message = await self._transform_custom(source_value, rule)
            else:
                return TransformationResult(
                    rule_id=rule.id,
                    rule_name=rule.name,
                    status=TransformationStatus.SKIPPED,
                    message=f"不支持的转换类型: {rule.transformation_type}",
                    source_field=rule.source_field,
                    target_field=rule.target_field,
                    original_value=source_value
                )
            
            # 设置目标字段值
            if status == TransformationStatus.SUCCESS:
                self._set_field_value(data, rule.target_field, transformed_value)
            
            execution_time = int((datetime.now() - start_time).total_seconds() * 1000)
            
            return TransformationResult(
                rule_id=rule.id,
                rule_name=rule.name,
                status=status,
                message=message,
                source_field=rule.source_field,
                target_field=rule.target_field,
                original_value=source_value,
                transformed_value=transformed_value,
                execution_time_ms=execution_time
            )
            
        except Exception as e:
            logger.error(f"规则应用失败: {rule.id}, 错误: {str(e)}")
            execution_time = int((datetime.now() - start_time).total_seconds() * 1000)
            
            return TransformationResult(
                rule_id=rule.id,
                rule_name=rule.name,
                status=TransformationStatus.FAILED,
                message=f"规则执行错误: {str(e)}",
                source_field=rule.source_field,
                target_field=rule.target_field,
                execution_time_ms=execution_time
            )

    def _get_field_value(self, data: StructuredData, field_path: str) -> Any:
        """获取字段值"""
        try:
            data_dict = data.dict()
            keys = field_path.split(".")
            value = data_dict
            
            for key in keys:
                if isinstance(value, dict) and key in value:
                    value = value[key]
                else:
                    return None
                    
            return value
        except Exception:
            return None

    def _set_field_value(self, data: StructuredData, field_path: str, value: Any) -> None:
        """设置字段值"""
        try:
            keys = field_path.split(".")
            
            # 直接修改对象属性
            if len(keys) == 1:
                setattr(data, keys[0], value)
            elif len(keys) == 2:
                parent = getattr(data, keys[0])
                if isinstance(parent, dict):
                    parent[keys[1]] = value
                else:
                    setattr(parent, keys[1], value)
            elif len(keys) == 3:
                parent = getattr(data, keys[0])
                if isinstance(parent, dict) and keys[1] in parent:
                    if isinstance(parent[keys[1]], dict):
                        parent[keys[1]][keys[2]] = value
                    else:
                        setattr(parent[keys[1]], keys[2], value)
                        
        except Exception as e:
            logger.error(f"设置字段值失败: {field_path}, 错误: {str(e)}")

    def _evaluate_condition(self, data: StructuredData, condition: str) -> bool:
        """评估执行条件"""
        try:
            # 简单的条件评估，实际应用中可以使用更复杂的表达式解析器
            # 例如："source_type == 'text'" 或 "quality_score > 0.5"
            
            # 替换字段引用
            condition = condition.replace("source_type", f"'{data.source_type}'")
            condition = condition.replace("quality_score", str(data.quality_score))
            condition = condition.replace("confidence", str(data.confidence))
            
            # 安全评估（仅支持基本比较操作）
            allowed_operators = ['==', '!=', '>', '<', '>=', '<=', 'and', 'or', 'not']
            if any(op in condition for op in ['import', 'exec', 'eval', '__']):
                return False
                
            return eval(condition)
        except Exception:
            return True  # 条件评估失败时默认执行

    async def _transform_clean(self, value: Any, rule: TransformationRule) -> Tuple[Any, TransformationStatus, str]:
        """清洗转换"""
        if value is None:
            return value, TransformationStatus.SKIPPED, "值为空，跳过清洗"
        
        try:
            text = str(value)
            
            # 清理空白字符
            if rule.parameters.get("strip", False):
                text = text.strip()
            
            if rule.parameters.get("normalize_spaces", False):
                text = re.sub(r'\s+', ' ', text)
            
            # 移除HTML标签
            if rule.parameters.get("keep_text", False) and rule.id == "remove_html_tags":
                text = re.sub(r'<[^>]+>', '', text)
            
            return text, TransformationStatus.SUCCESS, "清洗完成"
            
        except Exception as e:
            return value, TransformationStatus.FAILED, f"清洗失败: {str(e)}"

    async def _transform_normalize(self, value: Any, rule: TransformationRule) -> Tuple[Any, TransformationStatus, str]:
        """标准化转换"""
        if value is None:
            return value, TransformationStatus.SKIPPED, "值为空，跳过标准化"
        
        try:
            if rule.id == "normalize_encoding":
                # 编码标准化
                if isinstance(value, str):
                    return value.encode('utf-8').decode('utf-8'), TransformationStatus.SUCCESS, "编码标准化完成"
            
            elif rule.id == "normalize_line_endings":
                # 换行符标准化
                text = str(value)
                line_ending = rule.parameters.get("line_ending", "\n")
                text = text.replace('\r\n', line_ending).replace('\r', line_ending)
                return text, TransformationStatus.SUCCESS, "换行符标准化完成"
            
            elif rule.id == "normalize_entities":
                # 实体标准化
                if isinstance(value, list):
                    normalized_entities = []
                    for entity in value:
                        if isinstance(entity, dict):
                            normalized_entity = entity.copy()
                            if rule.parameters.get("lowercase_types", False) and "type" in normalized_entity:
                                normalized_entity["type"] = normalized_entity["type"].lower()
                            if rule.parameters.get("trim_values", False) and "value" in normalized_entity:
                                normalized_entity["value"] = str(normalized_entity["value"]).strip()
                            normalized_entities.append(normalized_entity)
                    return normalized_entities, TransformationStatus.SUCCESS, "实体标准化完成"
            
            return value, TransformationStatus.SKIPPED, "无匹配的标准化规则"
            
        except Exception as e:
            return value, TransformationStatus.FAILED, f"标准化失败: {str(e)}"

    async def _transform_enrich(self, value: Any, rule: TransformationRule, data: StructuredData) -> Tuple[Any, TransformationStatus, str]:
        """增强转换"""
        try:
            if rule.id == "add_word_count":
                # 添加词数统计
                if isinstance(value, str):
                    word_count = len(value.split())
                    return word_count, TransformationStatus.SUCCESS, f"添加词数统计: {word_count}"
            
            elif rule.id == "add_character_count":
                # 添加字符数统计
                if value is not None:
                    char_count = len(str(value))
                    return char_count, TransformationStatus.SUCCESS, f"添加字符数统计: {char_count}"
            
            elif rule.id == "add_content_hash":
                # 添加内容哈希
                if value is not None:
                    algorithm = rule.parameters.get("algorithm", "md5")
                    content_str = json.dumps(value, sort_keys=True, ensure_ascii=False)
                    
                    if algorithm == "md5":
                        hash_value = hashlib.md5(content_str.encode()).hexdigest()
                    elif algorithm == "sha256":
                        hash_value = hashlib.sha256(content_str.encode()).hexdigest()
                    else:
                        hash_value = hashlib.md5(content_str.encode()).hexdigest()
                    
                    return hash_value, TransformationStatus.SUCCESS, f"添加内容哈希: {hash_value[:8]}..."
            
            return None, TransformationStatus.SKIPPED, "无匹配的增强规则"
            
        except Exception as e:
            return None, TransformationStatus.FAILED, f"增强失败: {str(e)}"

    async def _transform_filter(self, value: Any, rule: TransformationRule) -> Tuple[Any, TransformationStatus, str]:
        """过滤转换"""
        try:
            filter_condition = rule.parameters.get("condition")
            if not filter_condition:
                return value, TransformationStatus.SKIPPED, "未指定过滤条件"
            
            # 简单的过滤逻辑
            if isinstance(value, list):
                filtered_items = []
                for item in value:
                    # 这里应该实现更复杂的过滤逻辑
                    if self._evaluate_filter_condition(item, filter_condition):
                        filtered_items.append(item)
                
                return filtered_items, TransformationStatus.SUCCESS, f"过滤完成，保留 {len(filtered_items)} 项"
            
            return value, TransformationStatus.SKIPPED, "值不是列表，跳过过滤"
            
        except Exception as e:
            return value, TransformationStatus.FAILED, f"过滤失败: {str(e)}"

    async def _transform_map(self, value: Any, rule: TransformationRule) -> Tuple[Any, TransformationStatus, str]:
        """映射转换"""
        try:
            mapping = rule.parameters.get("mapping", {})
            if not mapping:
                return value, TransformationStatus.SKIPPED, "未指定映射规则"
            
            if str(value) in mapping:
                mapped_value = mapping[str(value)]
                return mapped_value, TransformationStatus.SUCCESS, f"映射完成: {value} -> {mapped_value}"
            
            return value, TransformationStatus.SKIPPED, "未找到匹配的映射"
            
        except Exception as e:
            return value, TransformationStatus.FAILED, f"映射失败: {str(e)}"

    async def _transform_extract(self, value: Any, rule: TransformationRule) -> Tuple[Any, TransformationStatus, str]:
        """提取转换"""
        try:
            pattern = rule.parameters.get("pattern")
            if not pattern:
                return value, TransformationStatus.SKIPPED, "未指定提取模式"
            
            if isinstance(value, str):
                matches = re.findall(pattern, value)
                if matches:
                    return matches, TransformationStatus.SUCCESS, f"提取完成，找到 {len(matches)} 个匹配"
                else:
                    return [], TransformationStatus.SUCCESS, "未找到匹配项"
            
            return value, TransformationStatus.SKIPPED, "值不是字符串，跳过提取"
            
        except Exception as e:
            return value, TransformationStatus.FAILED, f"提取失败: {str(e)}"

    async def _transform_custom(self, value: Any, rule: TransformationRule) -> Tuple[Any, TransformationStatus, str]:
        """自定义转换"""
        try:
            if rule.custom_function:
                result = rule.custom_function(value, rule.parameters)
                if isinstance(result, tuple) and len(result) == 3:
                    return result
                else:
                    return result, TransformationStatus.SUCCESS, "自定义转换完成"
            
            return value, TransformationStatus.SKIPPED, "未提供自定义转换函数"
            
        except Exception as e:
            return value, TransformationStatus.FAILED, f"自定义转换失败: {str(e)}"

    def _evaluate_filter_condition(self, item: Any, condition: str) -> bool:
        """评估过滤条件"""
        try:
            # 简单的过滤条件评估
            # 实际应用中应该使用更安全的表达式解析器
            return True  # 暂时返回True
        except Exception:
            return False

    def _generate_summary(self, results: List[TransformationResult]) -> Dict[str, Any]:
        """生成转换摘要"""
        summary = {
            "transformation_time": datetime.now().isoformat(),
            "rules_by_status": {},
            "rules_by_type": {},
            "failed_rules": [],
            "execution_times": []
        }
        
        # 按状态统计
        for status in TransformationStatus:
            count = sum(1 for r in results if r.status == status)
            summary["rules_by_status"][status.value] = count
        
        # 按类型统计
        type_counts = {}
        for result in results:
            rule = self.rules.get(result.rule_id)
            if rule:
                rule_type = rule.transformation_type.value
                type_counts[rule_type] = type_counts.get(rule_type, 0) + 1
        summary["rules_by_type"] = type_counts
        
        # 收集失败的规则
        summary["failed_rules"] = [
            {"rule_id": r.rule_id, "rule_name": r.rule_name, "message": r.message}
            for r in results if r.status == TransformationStatus.FAILED
        ]
        
        # 执行时间统计
        execution_times = [r.execution_time_ms for r in results if r.execution_time_ms is not None]
        if execution_times:
            summary["execution_times"] = {
                "min": min(execution_times),
                "max": max(execution_times),
                "avg": sum(execution_times) / len(execution_times),
                "total": sum(execution_times)
            }
        
        return summary

    async def batch_transform(
        self,
        data_list: List[StructuredData],
        rule_chain: Optional[str] = None
    ) -> List[Tuple[StructuredData, TransformationReport]]:
        """批量转换数据
        
        Args:
            data_list: 结构化数据列表
            rule_chain: 转换链名称
            
        Returns:
            转换结果列表
        """
        results = []
        
        for data in data_list:
            try:
                transformed_data, report = await self.transform(data, rule_chain=rule_chain)
                results.append((transformed_data, report))
            except Exception as e:
                logger.error(f"批量转换失败: {data.id}, 错误: {str(e)}")
                # 创建错误报告
                error_report = TransformationReport(
                    data_id=data.id,
                    total_rules=0,
                    successful_rules=0,
                    failed_rules=1,
                    partial_rules=0,
                    skipped_rules=0,
                    results=[
                        TransformationResult(
                            rule_id="system_error",
                            rule_name="系统错误",
                            status=TransformationStatus.FAILED,
                            message=f"转换过程中发生错误: {str(e)}",
                            source_field="",
                            target_field=""
                        )
                    ]
                )
                results.append((data, error_report))
        
        return results

    def get_rule_chains(self) -> Dict[str, List[str]]:
        """获取所有转换链"""
        return self.rule_chains.copy()

    def get_rules(self) -> Dict[str, TransformationRule]:
        """获取所有规则"""
        return self.rules.copy()

    def get_rules_by_type(self, transformation_type: TransformationType) -> List[TransformationRule]:
        """根据类型获取规则"""
        return [rule for rule in self.rules.values() if rule.transformation_type == transformation_type]