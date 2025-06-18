from typing import Dict, List, Optional, Any, Union, Callable
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
import json
import re
import logging
from pathlib import Path
from jinja2 import Template, Environment, FileSystemLoader, meta
import yaml

logger = logging.getLogger(__name__)


class PromptType(Enum):
    """提示类型"""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    FUNCTION = "function"
    TEMPLATE = "template"
    CHAIN = "chain"


class PromptCategory(Enum):
    """提示分类"""
    GENERAL = "general"
    SUMMARIZATION = "summarization"
    TRANSLATION = "translation"
    QUESTION_ANSWERING = "question_answering"
    ENTITY_EXTRACTION = "entity_extraction"
    RELATION_EXTRACTION = "relation_extraction"
    CLASSIFICATION = "classification"
    CODE_GENERATION = "code_generation"
    CREATIVE_WRITING = "creative_writing"
    ANALYSIS = "analysis"
    REASONING = "reasoning"
    CONVERSATION = "conversation"


class PromptFormat(Enum):
    """提示格式"""
    PLAIN_TEXT = "plain_text"
    JINJA2 = "jinja2"
    F_STRING = "f_string"
    JSON = "json"
    YAML = "yaml"
    MARKDOWN = "markdown"


@dataclass
class PromptVariable:
    """提示变量"""
    name: str
    type: str  # str, int, float, bool, list, dict
    description: str
    required: bool = True
    default_value: Optional[Any] = None
    validation_pattern: Optional[str] = None
    choices: Optional[List[Any]] = None
    min_length: Optional[int] = None
    max_length: Optional[int] = None


@dataclass
class PromptTemplate:
    """提示模板"""
    id: str
    name: str
    description: str
    content: str
    type: PromptType
    category: PromptCategory
    format: PromptFormat = PromptFormat.PLAIN_TEXT
    variables: List[PromptVariable] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    version: str = "1.0.0"
    author: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    usage_count: int = 0
    rating: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    examples: List[Dict[str, Any]] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    is_active: bool = True


@dataclass
class PromptChain:
    """提示链"""
    id: str
    name: str
    description: str
    steps: List[Dict[str, Any]]  # [{"template_id": str, "variables": dict, "condition": str}]
    variables: List[PromptVariable] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    is_active: bool = True


@dataclass
class PromptExecution:
    """提示执行记录"""
    id: str
    template_id: str
    variables: Dict[str, Any]
    rendered_content: str
    execution_time: float
    success: bool
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


class PromptValidator:
    """提示验证器"""
    
    @staticmethod
    def validate_variable(variable: PromptVariable, value: Any) -> tuple[bool, Optional[str]]:
        """验证变量值"""
        try:
            # 检查必需性
            if variable.required and (value is None or value == ""):
                return False, f"变量 '{variable.name}' 是必需的"
            
            # 如果值为空且不是必需的，使用默认值
            if value is None or value == "":
                if variable.default_value is not None:
                    value = variable.default_value
                else:
                    return True, None
            
            # 类型检查
            if variable.type == "str":
                if not isinstance(value, str):
                    try:
                        value = str(value)
                    except:
                        return False, f"变量 '{variable.name}' 必须是字符串类型"
                
                # 长度检查
                if variable.min_length and len(value) < variable.min_length:
                    return False, f"变量 '{variable.name}' 长度不能少于 {variable.min_length}"
                
                if variable.max_length and len(value) > variable.max_length:
                    return False, f"变量 '{variable.name}' 长度不能超过 {variable.max_length}"
                
                # 模式验证
                if variable.validation_pattern:
                    if not re.match(variable.validation_pattern, value):
                        return False, f"变量 '{variable.name}' 不符合模式要求"
            
            elif variable.type == "int":
                if not isinstance(value, int):
                    try:
                        value = int(value)
                    except:
                        return False, f"变量 '{variable.name}' 必须是整数类型"
            
            elif variable.type == "float":
                if not isinstance(value, (int, float)):
                    try:
                        value = float(value)
                    except:
                        return False, f"变量 '{variable.name}' 必须是数字类型"
            
            elif variable.type == "bool":
                if not isinstance(value, bool):
                    if isinstance(value, str):
                        value = value.lower() in ('true', '1', 'yes', 'on')
                    else:
                        return False, f"变量 '{variable.name}' 必须是布尔类型"
            
            elif variable.type == "list":
                if not isinstance(value, list):
                    return False, f"变量 '{variable.name}' 必须是列表类型"
            
            elif variable.type == "dict":
                if not isinstance(value, dict):
                    return False, f"变量 '{variable.name}' 必须是字典类型"
            
            # 选择检查
            if variable.choices and value not in variable.choices:
                return False, f"变量 '{variable.name}' 必须是以下值之一: {variable.choices}"
            
            return True, None
            
        except Exception as e:
            return False, f"验证变量 '{variable.name}' 时出错: {str(e)}"
    
    @staticmethod
    def validate_template(template: PromptTemplate) -> tuple[bool, List[str]]:
        """验证模板"""
        errors = []
        
        # 检查基本字段
        if not template.id:
            errors.append("模板ID不能为空")
        
        if not template.name:
            errors.append("模板名称不能为空")
        
        if not template.content:
            errors.append("模板内容不能为空")
        
        # 检查格式特定的语法
        if template.format == PromptFormat.JINJA2:
            try:
                Template(template.content)
            except Exception as e:
                errors.append(f"Jinja2模板语法错误: {str(e)}")
        
        elif template.format == PromptFormat.JSON:
            try:
                json.loads(template.content)
            except Exception as e:
                errors.append(f"JSON格式错误: {str(e)}")
        
        elif template.format == PromptFormat.YAML:
            try:
                yaml.safe_load(template.content)
            except Exception as e:
                errors.append(f"YAML格式错误: {str(e)}")
        
        # 检查变量定义与模板内容的一致性
        if template.format == PromptFormat.JINJA2:
            try:
                env = Environment()
                ast = env.parse(template.content)
                template_vars = meta.find_undeclared_variables(ast)
                defined_vars = {var.name for var in template.variables}
                
                # 检查未定义的变量
                undefined_vars = template_vars - defined_vars
                if undefined_vars:
                    errors.append(f"模板中使用了未定义的变量: {undefined_vars}")
                
                # 检查未使用的变量
                unused_vars = defined_vars - template_vars
                if unused_vars:
                    errors.append(f"定义了但未使用的变量: {unused_vars}")
                    
            except Exception as e:
                errors.append(f"分析模板变量时出错: {str(e)}")
        
        return len(errors) == 0, errors


class PromptRenderer:
    """提示渲染器"""
    
    def __init__(self):
        self.jinja_env = Environment(
            trim_blocks=True,
            lstrip_blocks=True,
            keep_trailing_newline=True
        )
        
        # 添加自定义过滤器
        self.jinja_env.filters['truncate_words'] = self._truncate_words
        self.jinja_env.filters['format_list'] = self._format_list
        self.jinja_env.filters['json_pretty'] = self._json_pretty
    
    def render(self, template: PromptTemplate, variables: Dict[str, Any]) -> str:
        """渲染模板"""
        try:
            # 验证变量
            for var in template.variables:
                value = variables.get(var.name)
                is_valid, error_msg = PromptValidator.validate_variable(var, value)
                if not is_valid:
                    raise ValueError(error_msg)
                
                # 设置默认值
                if var.name not in variables and var.default_value is not None:
                    variables[var.name] = var.default_value
            
            # 根据格式渲染
            if template.format == PromptFormat.PLAIN_TEXT:
                return template.content
            
            elif template.format == PromptFormat.JINJA2:
                jinja_template = self.jinja_env.from_string(template.content)
                return jinja_template.render(**variables)
            
            elif template.format == PromptFormat.F_STRING:
                return template.content.format(**variables)
            
            elif template.format == PromptFormat.JSON:
                # 先渲染JSON中的变量，然后解析
                content = template.content
                for key, value in variables.items():
                    content = content.replace(f"{{{key}}}", str(value))
                return content
            
            elif template.format == PromptFormat.YAML:
                # 类似JSON处理
                content = template.content
                for key, value in variables.items():
                    content = content.replace(f"{{{key}}}", str(value))
                return content
            
            elif template.format == PromptFormat.MARKDOWN:
                # 使用Jinja2渲染Markdown
                jinja_template = self.jinja_env.from_string(template.content)
                return jinja_template.render(**variables)
            
            else:
                raise ValueError(f"不支持的模板格式: {template.format}")
                
        except Exception as e:
            logger.error(f"渲染模板失败: {str(e)}")
            raise
    
    def _truncate_words(self, text: str, count: int) -> str:
        """截断单词"""
        words = text.split()
        if len(words) <= count:
            return text
        return ' '.join(words[:count]) + '...'
    
    def _format_list(self, items: List[Any], separator: str = ", ") -> str:
        """格式化列表"""
        return separator.join(str(item) for item in items)
    
    def _json_pretty(self, obj: Any, indent: int = 2) -> str:
        """美化JSON"""
        return json.dumps(obj, indent=indent, ensure_ascii=False)


class PromptManager:
    """提示管理器"""
    
    def __init__(self, templates_dir: Optional[str] = None):
        self.templates: Dict[str, PromptTemplate] = {}
        self.chains: Dict[str, PromptChain] = {}
        self.executions: List[PromptExecution] = []
        self.renderer = PromptRenderer()
        self.templates_dir = Path(templates_dir) if templates_dir else None
        
        # 加载默认模板
        self._load_default_templates()
        
        # 如果指定了模板目录，加载文件中的模板
        if self.templates_dir and self.templates_dir.exists():
            self._load_templates_from_files()
    
    def _load_default_templates(self):
        """加载默认模板"""
        default_templates = [
            PromptTemplate(
                id="general_chat",
                name="通用聊天",
                description="通用的聊天对话模板",
                content="你是一个有用的AI助手。请回答用户的问题：{{question}}",
                type=PromptType.USER,
                category=PromptCategory.CONVERSATION,
                format=PromptFormat.JINJA2,
                variables=[
                    PromptVariable(
                        name="question",
                        type="str",
                        description="用户的问题",
                        required=True
                    )
                ]
            ),
            PromptTemplate(
                id="summarization",
                name="文本摘要",
                description="生成文本摘要的模板",
                content="请为以下文本生成一个简洁的摘要：\n\n{{text}}\n\n摘要长度应该控制在{{max_length}}字以内。",
                type=PromptType.USER,
                category=PromptCategory.SUMMARIZATION,
                format=PromptFormat.JINJA2,
                variables=[
                    PromptVariable(
                        name="text",
                        type="str",
                        description="要摘要的文本",
                        required=True
                    ),
                    PromptVariable(
                        name="max_length",
                        type="int",
                        description="摘要最大长度",
                        default_value=200
                    )
                ]
            ),
            PromptTemplate(
                id="entity_extraction",
                name="实体提取",
                description="从文本中提取实体的模板",
                content="""请从以下文本中提取{{entity_types|format_list}}实体：

{{text}}

请以JSON格式返回结果，格式如下：
{
  "entities": [
    {
      "text": "实体文本",
      "type": "实体类型",
      "start": 开始位置,
      "end": 结束位置
    }
  ]
}""",
                type=PromptType.USER,
                category=PromptCategory.ENTITY_EXTRACTION,
                format=PromptFormat.JINJA2,
                variables=[
                    PromptVariable(
                        name="text",
                        type="str",
                        description="要提取实体的文本",
                        required=True
                    ),
                    PromptVariable(
                        name="entity_types",
                        type="list",
                        description="要提取的实体类型列表",
                        default_value=["人名", "地名", "组织名"]
                    )
                ]
            ),
            PromptTemplate(
                id="relation_extraction",
                name="关系提取",
                description="从文本中提取实体关系的模板",
                content="""请从以下文本中提取实体之间的关系：

{{text}}

已识别的实体：
{% for entity in entities %}
- {{entity.text}} ({{entity.type}})
{% endfor %}

请以JSON格式返回关系，格式如下：
{
  "relations": [
    {
      "subject": "主体实体",
      "predicate": "关系类型",
      "object": "客体实体",
      "confidence": 置信度
    }
  ]
}""",
                type=PromptType.USER,
                category=PromptCategory.RELATION_EXTRACTION,
                format=PromptFormat.JINJA2,
                variables=[
                    PromptVariable(
                        name="text",
                        type="str",
                        description="要提取关系的文本",
                        required=True
                    ),
                    PromptVariable(
                        name="entities",
                        type="list",
                        description="已识别的实体列表",
                        required=True
                    )
                ]
            )
        ]
        
        for template in default_templates:
            self.templates[template.id] = template
    
    def _load_templates_from_files(self):
        """从文件加载模板"""
        try:
            for file_path in self.templates_dir.glob("*.yaml"):
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)
                    
                    if 'templates' in data:
                        for template_data in data['templates']:
                            template = self._dict_to_template(template_data)
                            self.templates[template.id] = template
                            
            logger.info(f"从 {self.templates_dir} 加载了模板文件")
            
        except Exception as e:
            logger.error(f"加载模板文件失败: {str(e)}")
    
    def _dict_to_template(self, data: Dict[str, Any]) -> PromptTemplate:
        """将字典转换为模板对象"""
        variables = []
        if 'variables' in data:
            for var_data in data['variables']:
                variables.append(PromptVariable(**var_data))
        
        return PromptTemplate(
            id=data['id'],
            name=data['name'],
            description=data['description'],
            content=data['content'],
            type=PromptType(data.get('type', 'user')),
            category=PromptCategory(data.get('category', 'general')),
            format=PromptFormat(data.get('format', 'jinja2')),
            variables=variables,
            tags=data.get('tags', []),
            version=data.get('version', '1.0.0'),
            author=data.get('author'),
            metadata=data.get('metadata', {}),
            examples=data.get('examples', []),
            dependencies=data.get('dependencies', [])
        )
    
    def add_template(self, template: PromptTemplate) -> bool:
        """添加模板"""
        try:
            # 验证模板
            is_valid, errors = PromptValidator.validate_template(template)
            if not is_valid:
                logger.error(f"模板验证失败: {errors}")
                return False
            
            # 检查ID冲突
            if template.id in self.templates:
                logger.warning(f"模板ID已存在，将覆盖: {template.id}")
            
            self.templates[template.id] = template
            logger.info(f"已添加模板: {template.id}")
            return True
            
        except Exception as e:
            logger.error(f"添加模板失败: {str(e)}")
            return False
    
    def get_template(self, template_id: str) -> Optional[PromptTemplate]:
        """获取模板"""
        return self.templates.get(template_id)
    
    def list_templates(self, 
                      category: Optional[PromptCategory] = None,
                      tags: Optional[List[str]] = None,
                      search: Optional[str] = None) -> List[PromptTemplate]:
        """列出模板"""
        templates = list(self.templates.values())
        
        # 按分类过滤
        if category:
            templates = [t for t in templates if t.category == category]
        
        # 按标签过滤
        if tags:
            templates = [t for t in templates if any(tag in t.tags for tag in tags)]
        
        # 按搜索词过滤
        if search:
            search_lower = search.lower()
            templates = [
                t for t in templates 
                if search_lower in t.name.lower() 
                or search_lower in t.description.lower()
                or search_lower in t.content.lower()
            ]
        
        # 按使用次数排序
        templates.sort(key=lambda t: t.usage_count, reverse=True)
        
        return templates
    
    def update_template(self, template_id: str, updates: Dict[str, Any]) -> bool:
        """更新模板"""
        try:
            if template_id not in self.templates:
                logger.error(f"模板不存在: {template_id}")
                return False
            
            template = self.templates[template_id]
            
            # 更新字段
            for key, value in updates.items():
                if hasattr(template, key):
                    setattr(template, key, value)
            
            template.updated_at = datetime.now()
            
            # 重新验证
            is_valid, errors = PromptValidator.validate_template(template)
            if not is_valid:
                logger.error(f"更新后的模板验证失败: {errors}")
                return False
            
            logger.info(f"已更新模板: {template_id}")
            return True
            
        except Exception as e:
            logger.error(f"更新模板失败: {str(e)}")
            return False
    
    def delete_template(self, template_id: str) -> bool:
        """删除模板"""
        try:
            if template_id not in self.templates:
                logger.error(f"模板不存在: {template_id}")
                return False
            
            del self.templates[template_id]
            logger.info(f"已删除模板: {template_id}")
            return True
            
        except Exception as e:
            logger.error(f"删除模板失败: {str(e)}")
            return False
    
    def render_template(self, template_id: str, variables: Dict[str, Any]) -> str:
        """渲染模板"""
        try:
            template = self.get_template(template_id)
            if not template:
                raise ValueError(f"模板不存在: {template_id}")
            
            if not template.is_active:
                raise ValueError(f"模板已禁用: {template_id}")
            
            # 记录使用
            template.usage_count += 1
            
            # 渲染
            start_time = datetime.now()
            rendered_content = self.renderer.render(template, variables)
            execution_time = (datetime.now() - start_time).total_seconds()
            
            # 记录执行
            execution = PromptExecution(
                id=f"{template_id}_{int(datetime.now().timestamp())}",
                template_id=template_id,
                variables=variables.copy(),
                rendered_content=rendered_content,
                execution_time=execution_time,
                success=True
            )
            self.executions.append(execution)
            
            return rendered_content
            
        except Exception as e:
            logger.error(f"渲染模板失败: {str(e)}")
            
            # 记录失败的执行
            execution = PromptExecution(
                id=f"{template_id}_{int(datetime.now().timestamp())}",
                template_id=template_id,
                variables=variables.copy(),
                rendered_content="",
                execution_time=0.0,
                success=False,
                error_message=str(e)
            )
            self.executions.append(execution)
            
            raise
    
    def add_chain(self, chain: PromptChain) -> bool:
        """添加提示链"""
        try:
            # 验证链中的模板是否存在
            for step in chain.steps:
                template_id = step.get('template_id')
                if template_id and template_id not in self.templates:
                    logger.error(f"链中引用的模板不存在: {template_id}")
                    return False
            
            self.chains[chain.id] = chain
            logger.info(f"已添加提示链: {chain.id}")
            return True
            
        except Exception as e:
            logger.error(f"添加提示链失败: {str(e)}")
            return False
    
    def execute_chain(self, chain_id: str, variables: Dict[str, Any]) -> List[str]:
        """执行提示链"""
        try:
            chain = self.chains.get(chain_id)
            if not chain:
                raise ValueError(f"提示链不存在: {chain_id}")
            
            if not chain.is_active:
                raise ValueError(f"提示链已禁用: {chain_id}")
            
            results = []
            context = variables.copy()
            
            for i, step in enumerate(chain.steps):
                template_id = step.get('template_id')
                step_variables = step.get('variables', {})
                condition = step.get('condition')
                
                # 检查条件
                if condition:
                    try:
                        # 简单的条件评估（实际应该使用更安全的方法）
                        if not eval(condition, {"__builtins__": {}}, context):
                            continue
                    except:
                        logger.warning(f"条件评估失败: {condition}")
                        continue
                
                # 合并变量
                merged_variables = {**context, **step_variables}
                
                # 渲染模板
                result = self.render_template(template_id, merged_variables)
                results.append(result)
                
                # 更新上下文
                context[f'step_{i}_result'] = result
            
            return results
            
        except Exception as e:
            logger.error(f"执行提示链失败: {str(e)}")
            raise
    
    def get_execution_history(self, 
                             template_id: Optional[str] = None,
                             limit: int = 100) -> List[PromptExecution]:
        """获取执行历史"""
        executions = self.executions
        
        if template_id:
            executions = [e for e in executions if e.template_id == template_id]
        
        # 按时间倒序排列
        executions.sort(key=lambda e: e.timestamp, reverse=True)
        
        return executions[:limit]
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        total_templates = len(self.templates)
        total_executions = len(self.executions)
        successful_executions = len([e for e in self.executions if e.success])
        
        # 按分类统计
        category_stats = {}
        for template in self.templates.values():
            category = template.category.value
            if category not in category_stats:
                category_stats[category] = 0
            category_stats[category] += 1
        
        # 最常用的模板
        popular_templates = sorted(
            self.templates.values(),
            key=lambda t: t.usage_count,
            reverse=True
        )[:5]
        
        return {
            "total_templates": total_templates,
            "total_executions": total_executions,
            "successful_executions": successful_executions,
            "success_rate": successful_executions / total_executions if total_executions > 0 else 0,
            "category_distribution": category_stats,
            "popular_templates": [
                {"id": t.id, "name": t.name, "usage_count": t.usage_count}
                for t in popular_templates
            ]
        }
    
    def export_templates(self, file_path: str, template_ids: Optional[List[str]] = None):
        """导出模板"""
        try:
            templates_to_export = []
            
            if template_ids:
                for template_id in template_ids:
                    if template_id in self.templates:
                        templates_to_export.append(self.templates[template_id])
            else:
                templates_to_export = list(self.templates.values())
            
            # 转换为字典格式
            export_data = {
                "templates": [
                    {
                        "id": t.id,
                        "name": t.name,
                        "description": t.description,
                        "content": t.content,
                        "type": t.type.value,
                        "category": t.category.value,
                        "format": t.format.value,
                        "variables": [
                            {
                                "name": v.name,
                                "type": v.type,
                                "description": v.description,
                                "required": v.required,
                                "default_value": v.default_value,
                                "validation_pattern": v.validation_pattern,
                                "choices": v.choices,
                                "min_length": v.min_length,
                                "max_length": v.max_length
                            }
                            for v in t.variables
                        ],
                        "tags": t.tags,
                        "version": t.version,
                        "author": t.author,
                        "metadata": t.metadata,
                        "examples": t.examples,
                        "dependencies": t.dependencies
                    }
                    for t in templates_to_export
                ]
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                yaml.dump(export_data, f, default_flow_style=False, allow_unicode=True)
            
            logger.info(f"已导出 {len(templates_to_export)} 个模板到 {file_path}")
            
        except Exception as e:
            logger.error(f"导出模板失败: {str(e)}")
            raise
    
    def import_templates(self, file_path: str, overwrite: bool = False) -> int:
        """导入模板"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            
            imported_count = 0
            
            if 'templates' in data:
                for template_data in data['templates']:
                    template = self._dict_to_template(template_data)
                    
                    # 检查是否已存在
                    if template.id in self.templates and not overwrite:
                        logger.warning(f"模板已存在，跳过: {template.id}")
                        continue
                    
                    if self.add_template(template):
                        imported_count += 1
            
            logger.info(f"从 {file_path} 导入了 {imported_count} 个模板")
            return imported_count
            
        except Exception as e:
            logger.error(f"导入模板失败: {str(e)}")
            raise
    
    def clear_execution_history(self):
        """清除执行历史"""
        self.executions.clear()
        logger.info("已清除执行历史")
    
    def cleanup(self):
        """清理资源"""
        # 清除执行历史（保留最近100条）
        if len(self.executions) > 100:
            self.executions = self.executions[-100:]
        
        logger.info("提示管理器资源已清理")