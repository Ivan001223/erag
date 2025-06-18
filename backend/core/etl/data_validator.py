"""数据验证器

负责验证数据质量、完整性和一致性，确保数据符合预定义的规则和标准。
"""

import re
import json
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional, Union, Callable
from enum import Enum
from dataclasses import dataclass

from pydantic import BaseModel, Field, validator

from backend.utils.logger import get_logger
from .data_structurer import StructuredData, DataType

logger = get_logger(__name__)


class ValidationLevel(str, Enum):
    """验证级别枚举"""
    STRICT = "strict"  # 严格验证，任何错误都会失败
    MODERATE = "moderate"  # 中等验证，允许警告
    LENIENT = "lenient"  # 宽松验证，只检查关键错误


class ValidationStatus(str, Enum):
    """验证状态枚举"""
    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"
    SKIPPED = "skipped"


class ValidationRuleType(str, Enum):
    """验证规则类型枚举"""
    REQUIRED = "required"  # 必填字段
    FORMAT = "format"  # 格式验证
    RANGE = "range"  # 范围验证
    LENGTH = "length"  # 长度验证
    PATTERN = "pattern"  # 正则表达式验证
    CUSTOM = "custom"  # 自定义验证
    UNIQUENESS = "uniqueness"  # 唯一性验证
    REFERENCE = "reference"  # 引用完整性验证
    CONSISTENCY = "consistency"  # 一致性验证


@dataclass
class ValidationRule:
    """验证规则"""
    id: str
    name: str
    rule_type: ValidationRuleType
    field_path: str  # 字段路径，支持嵌套，如 "content.text"
    parameters: Dict[str, Any]
    error_message: str
    warning_message: Optional[str] = None
    enabled: bool = True
    severity: ValidationLevel = ValidationLevel.MODERATE
    custom_validator: Optional[Callable] = None


class ValidationResult(BaseModel):
    """验证结果"""
    rule_id: str
    rule_name: str
    field_path: str
    status: ValidationStatus
    message: str
    actual_value: Any = None
    expected_value: Any = None
    severity: ValidationLevel
    timestamp: datetime = Field(default_factory=datetime.now)


class DataValidationReport(BaseModel):
    """数据验证报告"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    data_id: str
    validation_level: ValidationLevel
    overall_status: ValidationStatus
    total_rules: int
    passed_rules: int
    failed_rules: int
    warning_rules: int
    skipped_rules: int
    results: List[ValidationResult]
    summary: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)
    duration_ms: Optional[int] = None


class DataValidator:
    """数据验证器
    
    提供灵活的数据验证功能，支持多种验证规则和自定义验证逻辑。
    """

    def __init__(self, validation_level: ValidationLevel = ValidationLevel.MODERATE):
        """初始化数据验证器
        
        Args:
            validation_level: 验证级别
        """
        self.validation_level = validation_level
        self.rules: Dict[str, ValidationRule] = {}
        self.rule_sets: Dict[str, List[str]] = {}  # 规则集合
        self._initialize_default_rules()
        
    def _initialize_default_rules(self) -> None:
        """初始化默认验证规则"""
        # 基本数据完整性规则
        self.add_rule(ValidationRule(
            id="required_content",
            name="内容必填",
            rule_type=ValidationRuleType.REQUIRED,
            field_path="content",
            parameters={},
            error_message="内容字段不能为空"
        ))
        
        self.add_rule(ValidationRule(
            id="required_source_id",
            name="源ID必填",
            rule_type=ValidationRuleType.REQUIRED,
            field_path="source_id",
            parameters={},
            error_message="源ID不能为空"
        ))
        
        # 文本长度验证
        self.add_rule(ValidationRule(
            id="text_min_length",
            name="文本最小长度",
            rule_type=ValidationRuleType.LENGTH,
            field_path="content.text",
            parameters={"min_length": 1},
            error_message="文本内容不能为空",
            warning_message="文本内容过短"
        ))
        
        self.add_rule(ValidationRule(
            id="text_max_length",
            name="文本最大长度",
            rule_type=ValidationRuleType.LENGTH,
            field_path="content.text",
            parameters={"max_length": 1000000},
            error_message="文本内容过长",
            severity=ValidationLevel.LENIENT
        ))
        
        # 质量分数验证
        self.add_rule(ValidationRule(
            id="quality_score_range",
            name="质量分数范围",
            rule_type=ValidationRuleType.RANGE,
            field_path="quality_score",
            parameters={"min_value": 0.0, "max_value": 1.0},
            error_message="质量分数必须在0-1之间"
        ))
        
        # 置信度验证
        self.add_rule(ValidationRule(
            id="confidence_range",
            name="置信度范围",
            rule_type=ValidationRuleType.RANGE,
            field_path="confidence",
            parameters={"min_value": 0.0, "max_value": 1.0},
            error_message="置信度必须在0-1之间"
        ))
        
        # 邮箱格式验证
        self.add_rule(ValidationRule(
            id="email_format",
            name="邮箱格式",
            rule_type=ValidationRuleType.PATTERN,
            field_path="entities[*].value",
            parameters={
                "pattern": r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",
                "entity_type": "email"
            },
            error_message="邮箱格式不正确",
            severity=ValidationLevel.LENIENT
        ))
        
        # 电话号码格式验证
        self.add_rule(ValidationRule(
            id="phone_format",
            name="电话号码格式",
            rule_type=ValidationRuleType.PATTERN,
            field_path="entities[*].value",
            parameters={
                "pattern": r"^(?:\+?86)?\s*1[3-9]\d{9}$",
                "entity_type": "phone"
            },
            error_message="电话号码格式不正确",
            severity=ValidationLevel.LENIENT
        ))
        
        # 创建默认规则集
        self.rule_sets["basic"] = [
            "required_content", "required_source_id", 
            "quality_score_range", "confidence_range"
        ]
        
        self.rule_sets["text"] = [
            "text_min_length", "text_max_length"
        ]
        
        self.rule_sets["entities"] = [
            "email_format", "phone_format"
        ]
        
        self.rule_sets["complete"] = [
            "required_content", "required_source_id", "text_min_length", 
            "text_max_length", "quality_score_range", "confidence_range",
            "email_format", "phone_format"
        ]

    def add_rule(self, rule: ValidationRule) -> None:
        """添加验证规则
        
        Args:
            rule: 验证规则
        """
        self.rules[rule.id] = rule
        logger.debug(f"添加验证规则: {rule.name}")

    def remove_rule(self, rule_id: str) -> None:
        """移除验证规则
        
        Args:
            rule_id: 规则ID
        """
        if rule_id in self.rules:
            del self.rules[rule_id]
            logger.debug(f"移除验证规则: {rule_id}")

    def create_rule_set(self, name: str, rule_ids: List[str]) -> None:
        """创建规则集
        
        Args:
            name: 规则集名称
            rule_ids: 规则ID列表
        """
        self.rule_sets[name] = rule_ids
        logger.debug(f"创建规则集: {name}, 包含 {len(rule_ids)} 个规则")

    async def validate(
        self,
        data: StructuredData,
        rule_set: Optional[str] = None,
        rule_ids: Optional[List[str]] = None
    ) -> DataValidationReport:
        """验证数据
        
        Args:
            data: 结构化数据
            rule_set: 规则集名称
            rule_ids: 特定规则ID列表
            
        Returns:
            验证报告
        """
        start_time = datetime.now()
        
        try:
            logger.info(f"开始验证数据: {data.id}")
            
            # 确定要使用的规则
            if rule_ids:
                rules_to_apply = rule_ids
            elif rule_set and rule_set in self.rule_sets:
                rules_to_apply = self.rule_sets[rule_set]
            else:
                rules_to_apply = self.rule_sets.get("basic", list(self.rules.keys()))
            
            # 执行验证
            results = []
            for rule_id in rules_to_apply:
                if rule_id in self.rules:
                    rule = self.rules[rule_id]
                    if rule.enabled:
                        result = await self._apply_rule(data, rule)
                        results.append(result)
            
            # 统计结果
            passed = sum(1 for r in results if r.status == ValidationStatus.PASSED)
            failed = sum(1 for r in results if r.status == ValidationStatus.FAILED)
            warning = sum(1 for r in results if r.status == ValidationStatus.WARNING)
            skipped = sum(1 for r in results if r.status == ValidationStatus.SKIPPED)
            
            # 确定整体状态
            if failed > 0:
                overall_status = ValidationStatus.FAILED
            elif warning > 0:
                overall_status = ValidationStatus.WARNING
            else:
                overall_status = ValidationStatus.PASSED
            
            # 创建报告
            duration = int((datetime.now() - start_time).total_seconds() * 1000)
            
            report = DataValidationReport(
                data_id=data.id,
                validation_level=self.validation_level,
                overall_status=overall_status,
                total_rules=len(results),
                passed_rules=passed,
                failed_rules=failed,
                warning_rules=warning,
                skipped_rules=skipped,
                results=results,
                duration_ms=duration,
                summary=self._generate_summary(results)
            )
            
            logger.info(
                f"数据验证完成: {data.id}, 状态: {overall_status}, "
                f"通过: {passed}, 失败: {failed}, 警告: {warning}"
            )
            
            return report
            
        except Exception as e:
            logger.error(f"数据验证失败: {data.id}, 错误: {str(e)}")
            raise

    async def _apply_rule(
        self,
        data: StructuredData,
        rule: ValidationRule
    ) -> ValidationResult:
        """应用验证规则
        
        Args:
            data: 结构化数据
            rule: 验证规则
            
        Returns:
            验证结果
        """
        try:
            # 获取字段值
            field_value = self._get_field_value(data, rule.field_path)
            
            # 根据规则类型执行验证
            if rule.rule_type == ValidationRuleType.REQUIRED:
                status, message = self._validate_required(field_value, rule)
            elif rule.rule_type == ValidationRuleType.LENGTH:
                status, message = self._validate_length(field_value, rule)
            elif rule.rule_type == ValidationRuleType.RANGE:
                status, message = self._validate_range(field_value, rule)
            elif rule.rule_type == ValidationRuleType.PATTERN:
                status, message = self._validate_pattern(field_value, rule, data)
            elif rule.rule_type == ValidationRuleType.FORMAT:
                status, message = self._validate_format(field_value, rule)
            elif rule.rule_type == ValidationRuleType.CUSTOM:
                status, message = self._validate_custom(field_value, rule)
            else:
                status = ValidationStatus.SKIPPED
                message = f"不支持的验证规则类型: {rule.rule_type}"
            
            return ValidationResult(
                rule_id=rule.id,
                rule_name=rule.name,
                field_path=rule.field_path,
                status=status,
                message=message,
                actual_value=field_value,
                severity=rule.severity
            )
            
        except Exception as e:
            logger.error(f"规则应用失败: {rule.id}, 错误: {str(e)}")
            return ValidationResult(
                rule_id=rule.id,
                rule_name=rule.name,
                field_path=rule.field_path,
                status=ValidationStatus.FAILED,
                message=f"规则执行错误: {str(e)}",
                severity=rule.severity
            )

    def _get_field_value(self, data: StructuredData, field_path: str) -> Any:
        """获取字段值
        
        Args:
            data: 结构化数据
            field_path: 字段路径
            
        Returns:
            字段值
        """
        try:
            # 将数据转换为字典
            data_dict = data.model_dump()
            
            # 处理数组索引，如 "entities[*].value"
            if "[*]" in field_path:
                parts = field_path.split("[*]")
                base_path = parts[0]
                sub_path = parts[1].lstrip(".")
                
                # 获取数组
                array_value = self._get_nested_value(data_dict, base_path)
                if isinstance(array_value, list):
                    if sub_path:
                        return [self._get_nested_value(item, sub_path) for item in array_value]
                    else:
                        return array_value
                else:
                    return None
            else:
                return self._get_nested_value(data_dict, field_path)
                
        except Exception as e:
            logger.debug(f"获取字段值失败: {field_path}, 错误: {str(e)}")
            return None

    def _get_nested_value(self, data: Dict[str, Any], path: str) -> Any:
        """获取嵌套字段值"""
        keys = path.split(".")
        value = data
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return None
                
        return value

    def _validate_required(self, value: Any, rule: ValidationRule) -> Tuple[ValidationStatus, str]:
        """验证必填字段"""
        if value is None or (isinstance(value, str) and not value.strip()):
            return ValidationStatus.FAILED, rule.error_message
        return ValidationStatus.PASSED, "字段验证通过"

    def _validate_length(self, value: Any, rule: ValidationRule) -> Tuple[ValidationStatus, str]:
        """验证长度"""
        if value is None:
            return ValidationStatus.SKIPPED, "字段为空，跳过长度验证"
        
        length = len(str(value)) if value is not None else 0
        min_length = rule.parameters.get("min_length")
        max_length = rule.parameters.get("max_length")
        
        if min_length is not None and length < min_length:
            if rule.warning_message and rule.severity == ValidationLevel.LENIENT:
                return ValidationStatus.WARNING, rule.warning_message
            return ValidationStatus.FAILED, rule.error_message
        
        if max_length is not None and length > max_length:
            return ValidationStatus.FAILED, rule.error_message
        
        return ValidationStatus.PASSED, "长度验证通过"

    def _validate_range(self, value: Any, rule: ValidationRule) -> Tuple[ValidationStatus, str]:
        """验证范围"""
        if value is None:
            return ValidationStatus.SKIPPED, "字段为空，跳过范围验证"
        
        try:
            numeric_value = float(value)
            min_value = rule.parameters.get("min_value")
            max_value = rule.parameters.get("max_value")
            
            if min_value is not None and numeric_value < min_value:
                return ValidationStatus.FAILED, rule.error_message
            
            if max_value is not None and numeric_value > max_value:
                return ValidationStatus.FAILED, rule.error_message
            
            return ValidationStatus.PASSED, "范围验证通过"
            
        except (ValueError, TypeError):
            return ValidationStatus.FAILED, "无法转换为数值进行范围验证"

    def _validate_pattern(
        self,
        value: Any,
        rule: ValidationRule,
        data: StructuredData
    ) -> Tuple[ValidationStatus, str]:
        """验证正则表达式模式"""
        pattern = rule.parameters.get("pattern")
        if not pattern:
            return ValidationStatus.SKIPPED, "未指定验证模式"
        
        # 特殊处理实体验证
        entity_type = rule.parameters.get("entity_type")
        if entity_type and isinstance(value, list):
            # 过滤特定类型的实体
            entities_to_check = [
                entity.get("value") for entity in data.entities
                if entity.get("type") == entity_type
            ]
            
            if not entities_to_check:
                return ValidationStatus.SKIPPED, f"未找到类型为 {entity_type} 的实体"
            
            failed_entities = []
            for entity_value in entities_to_check:
                if entity_value and not re.match(pattern, str(entity_value)):
                    failed_entities.append(entity_value)
            
            if failed_entities:
                return ValidationStatus.FAILED, f"{rule.error_message}: {failed_entities}"
            else:
                return ValidationStatus.PASSED, f"{entity_type} 格式验证通过"
        
        # 普通字符串模式验证
        if value is None:
            return ValidationStatus.SKIPPED, "字段为空，跳过模式验证"
        
        if not re.match(pattern, str(value)):
            return ValidationStatus.FAILED, rule.error_message
        
        return ValidationStatus.PASSED, "模式验证通过"

    def _validate_format(self, value: Any, rule: ValidationRule) -> Tuple[ValidationStatus, str]:
        """验证格式"""
        format_type = rule.parameters.get("format")
        
        if format_type == "email":
            email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
            if value and not re.match(email_pattern, str(value)):
                return ValidationStatus.FAILED, rule.error_message
        elif format_type == "url":
            url_pattern = r"^https?://[^\s/$.?#].[^\s]*$"
            if value and not re.match(url_pattern, str(value)):
                return ValidationStatus.FAILED, rule.error_message
        elif format_type == "date":
            date_pattern = r"^\d{4}-\d{2}-\d{2}$"
            if value and not re.match(date_pattern, str(value)):
                return ValidationStatus.FAILED, rule.error_message
        
        return ValidationStatus.PASSED, "格式验证通过"

    def _validate_custom(self, value: Any, rule: ValidationRule) -> Tuple[ValidationStatus, str]:
        """自定义验证"""
        if rule.custom_validator:
            try:
                result = rule.custom_validator(value, rule.parameters)
                if result is True:
                    return ValidationStatus.PASSED, "自定义验证通过"
                elif result is False:
                    return ValidationStatus.FAILED, rule.error_message
                elif isinstance(result, tuple):
                    return result
                else:
                    return ValidationStatus.FAILED, str(result)
            except Exception as e:
                return ValidationStatus.FAILED, f"自定义验证执行错误: {str(e)}"
        
        return ValidationStatus.SKIPPED, "未提供自定义验证函数"

    def _generate_summary(self, results: List[ValidationResult]) -> Dict[str, Any]:
        """生成验证摘要"""
        summary = {
            "validation_time": datetime.now().isoformat(),
            "rules_by_status": {},
            "rules_by_severity": {},
            "failed_rules": [],
            "warning_rules": []
        }
        
        # 按状态统计
        for status in ValidationStatus:
            count = sum(1 for r in results if r.status == status)
            summary["rules_by_status"][status.value] = count
        
        # 按严重程度统计
        for severity in ValidationLevel:
            count = sum(1 for r in results if r.severity == severity)
            summary["rules_by_severity"][severity.value] = count
        
        # 收集失败和警告的规则
        summary["failed_rules"] = [
            {"rule_id": r.rule_id, "rule_name": r.rule_name, "message": r.message}
            for r in results if r.status == ValidationStatus.FAILED
        ]
        
        summary["warning_rules"] = [
            {"rule_id": r.rule_id, "rule_name": r.rule_name, "message": r.message}
            for r in results if r.status == ValidationStatus.WARNING
        ]
        
        return summary

    async def batch_validate(
        self,
        data_list: List[StructuredData],
        rule_set: Optional[str] = None
    ) -> List[DataValidationReport]:
        """批量验证数据
        
        Args:
            data_list: 结构化数据列表
            rule_set: 规则集名称
            
        Returns:
            验证报告列表
        """
        reports = []
        
        for data in data_list:
            try:
                report = await self.validate(data, rule_set=rule_set)
                reports.append(report)
            except Exception as e:
                logger.error(f"批量验证失败: {data.id}, 错误: {str(e)}")
                # 创建错误报告
                error_report = DataValidationReport(
                    data_id=data.id,
                    validation_level=self.validation_level,
                    overall_status=ValidationStatus.FAILED,
                    total_rules=0,
                    passed_rules=0,
                    failed_rules=1,
                    warning_rules=0,
                    skipped_rules=0,
                    results=[
                        ValidationResult(
                            rule_id="system_error",
                            rule_name="系统错误",
                            field_path="",
                            status=ValidationStatus.FAILED,
                            message=f"验证过程中发生错误: {str(e)}",
                            severity=ValidationLevel.STRICT
                        )
                    ]
                )
                reports.append(error_report)
        
        return reports

    def get_rule_sets(self) -> Dict[str, List[str]]:
        """获取所有规则集"""
        return self.rule_sets.copy()

    def get_rules(self) -> Dict[str, ValidationRule]:
        """获取所有规则"""
        return self.rules.copy()

    def set_validation_level(self, level: ValidationLevel) -> None:
        """设置验证级别"""
        self.validation_level = level
        logger.info(f"验证级别已设置为: {level}")