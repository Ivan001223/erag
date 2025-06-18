from typing import Dict, Any, Optional, List, Union, Type
from datetime import datetime
import json
import os
from pathlib import Path
from enum import Enum
import yaml
from dataclasses import dataclass, field

from backend.connectors.redis_client import RedisClient
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from backend.models.base import BaseModel
from backend.models.config import ConfigModel, ConfigHistoryModel, ConfigTemplateModel
from backend.utils.logger import get_logger

logger = get_logger(__name__)


class ConfigType(str, Enum):
    """配置类型枚举"""
    SYSTEM = "system"
    USER = "user"
    APPLICATION = "application"
    FEATURE = "feature"
    SECURITY = "security"
    PERFORMANCE = "performance"
    INTEGRATION = "integration"
    NOTIFICATION = "notification"


class ConfigScope(str, Enum):
    """配置作用域枚举"""
    GLOBAL = "global"
    TENANT = "tenant"
    USER = "user"
    SESSION = "session"


class ConfigDataType(str, Enum):
    """配置数据类型枚举"""
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    JSON = "json"
    LIST = "list"
    DICT = "dict"


class ConfigStatus(str, Enum):
    """配置状态枚举"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    DEPRECATED = "deprecated"
    DRAFT = "draft"


@dataclass
class ConfigValidation:
    """配置验证规则"""
    required: bool = False
    min_value: Optional[Union[int, float]] = None
    max_value: Optional[Union[int, float]] = None
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    pattern: Optional[str] = None
    allowed_values: Optional[List[Any]] = None
    custom_validator: Optional[str] = None


class ConfigItem(BaseModel):
    """配置项模型"""
    key: str
    value: Any
    data_type: ConfigDataType
    config_type: ConfigType
    scope: ConfigScope
    scope_id: Optional[str] = None  # tenant_id, user_id等
    description: Optional[str] = None
    default_value: Optional[Any] = None
    validation: Optional[ConfigValidation] = None
    is_sensitive: bool = False
    is_readonly: bool = False
    status: ConfigStatus = ConfigStatus.ACTIVE
    version: int = 1
    created_by: str
    updated_by: str
    created_at: datetime
    updated_at: datetime
    tags: List[str] = []
    metadata: Dict[str, Any] = {}


class ConfigHistory(BaseModel):
    """配置历史记录模型"""
    id: str
    config_key: str
    old_value: Any
    new_value: Any
    scope: ConfigScope
    scope_id: Optional[str] = None
    change_type: str  # create, update, delete
    changed_by: str
    change_reason: Optional[str] = None
    timestamp: datetime
    metadata: Dict[str, Any] = {}


class ConfigTemplate(BaseModel):
    """配置模板模型"""
    id: str
    name: str
    description: Optional[str] = None
    config_type: ConfigType
    template_data: Dict[str, Any]
    schema: Dict[str, Any]  # JSON Schema
    version: str
    is_default: bool = False
    created_by: str
    created_at: datetime
    updated_at: datetime
    tags: List[str] = []


class ConfigExport(BaseModel):
    """配置导出模型"""
    export_id: str
    export_type: str  # full, partial, template
    filters: Dict[str, Any]
    format: str  # json, yaml, env
    include_sensitive: bool = False
    created_by: str
    created_at: datetime
    file_path: Optional[str] = None
    status: str = "pending"


class ConfigService:
    """配置服务"""
    
    def __init__(
        self,
        redis_client: RedisClient,
        db: Session,
        config_file_path: Optional[str] = None
    ):
        self.redis = redis_client
        self.db = db
        self.config_file_path = config_file_path or "config/app_config.yaml"
        
        # 配置缓存
        self.config_cache: Dict[str, Any] = {}
        self.cache_ttl = 300  # 5分钟
        
        # 配置验证器
        self.validators: Dict[str, callable] = {}
        
        # 配置监听器
        self.listeners: Dict[str, List[callable]] = {}
        
        # 默认配置
        self.default_configs: Dict[str, Any] = {}
        
    async def initialize(self):
        """初始化配置服务"""
        try:
            # 创建配置相关表
            await self._create_config_tables()
            
            # 加载默认配置
            await self._load_default_configs()
            
            # 注册内置验证器
            await self._register_builtin_validators()
            
            # 加载文件配置
            if os.path.exists(self.config_file_path):
                await self._load_file_configs()
            
            logger.info("Config service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize config service: {str(e)}")
            raise
    
    async def get_config(
        self,
        key: str,
        scope: ConfigScope = ConfigScope.GLOBAL,
        scope_id: Optional[str] = None,
        default: Any = None,
        use_cache: bool = True
    ) -> Any:
        """获取配置值"""
        try:
            cache_key = self._get_cache_key(key, scope, scope_id)
            
            # 尝试从缓存获取
            if use_cache:
                cached_value = await self.redis.get(cache_key)
                if cached_value is not None:
                    return json.loads(cached_value)
            
            # 从数据库获取
            config_item = await self._get_config_from_db(key, scope, scope_id)
            
            if config_item:
                value = self._deserialize_value(config_item.value, config_item.data_type)
                
                # 缓存结果
                if use_cache:
                    await self.redis.setex(
                        cache_key,
                        self.cache_ttl,
                        json.dumps(value, default=str)
                    )
                
                return value
            
            # 返回默认值
            return default
            
        except Exception as e:
            logger.error(f"Failed to get config {key}: {str(e)}")
            return default
    
    async def set_config(
        self,
        key: str,
        value: Any,
        scope: ConfigScope = ConfigScope.GLOBAL,
        scope_id: Optional[str] = None,
        data_type: Optional[ConfigDataType] = None,
        config_type: ConfigType = ConfigType.APPLICATION,
        description: Optional[str] = None,
        updated_by: str = "system",
        validate: bool = True
    ) -> bool:
        """设置配置值"""
        try:
            # 自动推断数据类型
            if data_type is None:
                data_type = self._infer_data_type(value)
            
            # 验证配置值
            if validate:
                await self._validate_config_value(key, value, data_type)
            
            # 获取现有配置
            existing_config = await self._get_config_from_db(key, scope, scope_id)
            
            if existing_config:
                # 更新配置
                old_value = existing_config.value
                await self._update_config(
                    key, value, scope, scope_id, data_type, updated_by
                )
                
                # 记录历史
                await self._record_config_history(
                    key, old_value, value, scope, scope_id, "update", updated_by
                )
            else:
                # 创建新配置
                await self._create_config(
                    key, value, data_type, config_type, scope, scope_id,
                    description, updated_by
                )
                
                # 记录历史
                await self._record_config_history(
                    key, None, value, scope, scope_id, "create", updated_by
                )
            
            # 清除缓存
            cache_key = self._get_cache_key(key, scope, scope_id)
            await self.redis.delete(cache_key)
            
            # 触发监听器
            await self._trigger_listeners(key, value, scope, scope_id)
            
            logger.info(f"Config set: {key} = {value}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to set config {key}: {str(e)}")
            return False
    
    async def delete_config(
        self,
        key: str,
        scope: ConfigScope = ConfigScope.GLOBAL,
        scope_id: Optional[str] = None,
        deleted_by: str = "system"
    ) -> bool:
        """删除配置"""
        try:
            # 获取现有配置
            existing_config = await self._get_config_from_db(key, scope, scope_id)
            
            if not existing_config:
                return False
            
            # 检查是否为只读配置
            if existing_config.is_readonly:
                raise ValueError(f"Cannot delete readonly config: {key}")
            
            # 删除配置
            await self._delete_config_from_db(key, scope, scope_id)
            
            # 记录历史
            await self._record_config_history(
                key, existing_config.value, None, scope, scope_id, "delete", deleted_by
            )
            
            # 清除缓存
            cache_key = self._get_cache_key(key, scope, scope_id)
            await self.redis.delete(cache_key)
            
            logger.info(f"Config deleted: {key}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete config {key}: {str(e)}")
            return False
    
    async def list_configs(
        self,
        config_type: Optional[ConfigType] = None,
        scope: Optional[ConfigScope] = None,
        scope_id: Optional[str] = None,
        status: Optional[ConfigStatus] = None,
        search: Optional[str] = None,
        tags: Optional[List[str]] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[ConfigItem]:
        """列出配置项"""
        try:
            return await self._list_configs_from_db(
                config_type, scope, scope_id, status, search, tags, limit, offset
            )
            
        except Exception as e:
            logger.error(f"Failed to list configs: {str(e)}")
            return []
    
    async def get_config_history(
        self,
        key: Optional[str] = None,
        scope: Optional[ConfigScope] = None,
        scope_id: Optional[str] = None,
        changed_by: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[ConfigHistory]:
        """获取配置历史记录"""
        try:
            return await self._get_config_history_from_db(
                key, scope, scope_id, changed_by, start_time, end_time, limit, offset
            )
            
        except Exception as e:
            logger.error(f"Failed to get config history: {str(e)}")
            return []
    
    async def create_template(
        self,
        name: str,
        config_type: ConfigType,
        template_data: Dict[str, Any],
        schema: Dict[str, Any],
        created_by: str,
        description: Optional[str] = None,
        version: str = "1.0",
        is_default: bool = False
    ) -> str:
        """创建配置模板"""
        try:
            template_id = f"template_{int(datetime.now().timestamp())}"
            
            template = ConfigTemplate(
                id=template_id,
                name=name,
                description=description,
                config_type=config_type,
                template_data=template_data,
                schema=schema,
                version=version,
                is_default=is_default,
                created_by=created_by,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
            await self._save_template(template)
            
            logger.info(f"Config template created: {template_id}")
            return template_id
            
        except Exception as e:
            logger.error(f"Failed to create config template: {str(e)}")
            raise
    
    async def apply_template(
        self,
        template_id: str,
        scope: ConfigScope = ConfigScope.GLOBAL,
        scope_id: Optional[str] = None,
        overrides: Optional[Dict[str, Any]] = None,
        applied_by: str = "system"
    ) -> bool:
        """应用配置模板"""
        try:
            # 获取模板
            template = await self._get_template(template_id)
            if not template:
                raise ValueError(f"Template not found: {template_id}")
            
            # 合并覆盖值
            template_data = template.template_data.copy()
            if overrides:
                template_data.update(overrides)
            
            # 验证模板数据
            await self._validate_template_data(template_data, template.schema)
            
            # 应用配置
            for key, value in template_data.items():
                await self.set_config(
                    key, value, scope, scope_id,
                    config_type=template.config_type,
                    updated_by=applied_by
                )
            
            logger.info(f"Template applied: {template_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to apply template {template_id}: {str(e)}")
            return False
    
    async def export_configs(
        self,
        export_type: str = "full",
        filters: Optional[Dict[str, Any]] = None,
        format: str = "json",
        include_sensitive: bool = False,
        exported_by: str = "system"
    ) -> str:
        """导出配置"""
        try:
            export_id = f"export_{int(datetime.now().timestamp())}"
            
            # 创建导出记录
            export_record = ConfigExport(
                export_id=export_id,
                export_type=export_type,
                filters=filters or {},
                format=format,
                include_sensitive=include_sensitive,
                created_by=exported_by,
                created_at=datetime.now()
            )
            
            # 获取配置数据
            configs = await self._get_configs_for_export(filters, include_sensitive)
            
            # 格式化数据
            if format == "json":
                export_data = json.dumps(configs, indent=2, default=str)
            elif format == "yaml":
                export_data = yaml.dump(configs, default_flow_style=False)
            elif format == "env":
                export_data = self._format_as_env(configs)
            else:
                raise ValueError(f"Unsupported export format: {format}")
            
            # 保存到文件
            export_file = f"exports/{export_id}.{format}"
            os.makedirs(os.path.dirname(export_file), exist_ok=True)
            
            with open(export_file, 'w', encoding='utf-8') as f:
                f.write(export_data)
            
            export_record.file_path = export_file
            export_record.status = "completed"
            
            await self._save_export_record(export_record)
            
            logger.info(f"Configs exported: {export_id}")
            return export_id
            
        except Exception as e:
            logger.error(f"Failed to export configs: {str(e)}")
            raise
    
    async def import_configs(
        self,
        file_path: str,
        format: str = "json",
        scope: ConfigScope = ConfigScope.GLOBAL,
        scope_id: Optional[str] = None,
        overwrite: bool = False,
        imported_by: str = "system"
    ) -> Dict[str, Any]:
        """导入配置"""
        try:
            # 读取文件
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 解析数据
            if format == "json":
                import_data = json.loads(content)
            elif format == "yaml":
                import_data = yaml.safe_load(content)
            elif format == "env":
                import_data = self._parse_env_format(content)
            else:
                raise ValueError(f"Unsupported import format: {format}")
            
            # 导入配置
            results = {
                "imported": 0,
                "skipped": 0,
                "failed": 0,
                "errors": []
            }
            
            for key, value in import_data.items():
                try:
                    # 检查是否已存在
                    existing = await self._get_config_from_db(key, scope, scope_id)
                    if existing and not overwrite:
                        results["skipped"] += 1
                        continue
                    
                    # 设置配置
                    success = await self.set_config(
                        key, value, scope, scope_id, updated_by=imported_by
                    )
                    
                    if success:
                        results["imported"] += 1
                    else:
                        results["failed"] += 1
                        
                except Exception as e:
                    results["failed"] += 1
                    results["errors"].append(f"{key}: {str(e)}")
            
            logger.info(f"Configs imported: {results}")
            return results
            
        except Exception as e:
            logger.error(f"Failed to import configs: {str(e)}")
            raise
    
    async def register_validator(self, key: str, validator: callable):
        """注册配置验证器"""
        self.validators[key] = validator
        logger.info(f"Validator registered: {key}")
    
    async def add_listener(self, key: str, listener: callable):
        """添加配置监听器"""
        if key not in self.listeners:
            self.listeners[key] = []
        self.listeners[key].append(listener)
        logger.info(f"Listener added for config: {key}")
    
    async def remove_listener(self, key: str, listener: callable):
        """移除配置监听器"""
        if key in self.listeners and listener in self.listeners[key]:
            self.listeners[key].remove(listener)
            logger.info(f"Listener removed for config: {key}")
    
    async def reload_config(self, key: Optional[str] = None):
        """重新加载配置"""
        try:
            if key:
                # 重新加载特定配置
                cache_key = f"config:*:{key}:*"
                keys = await self.redis.keys(cache_key)
                if keys:
                    await self.redis.delete(*keys)
            else:
                # 重新加载所有配置
                cache_pattern = "config:*"
                keys = await self.redis.keys(cache_pattern)
                if keys:
                    await self.redis.delete(*keys)
                
                # 重新加载文件配置
                if os.path.exists(self.config_file_path):
                    await self._load_file_configs()
            
            logger.info(f"Config reloaded: {key or 'all'}")
            
        except Exception as e:
            logger.error(f"Failed to reload config: {str(e)}")
            raise
    
    async def get_config_stats(self) -> Dict[str, Any]:
        """获取配置统计信息"""
        try:
            stats = await self._get_config_stats_from_db()
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get config stats: {str(e)}")
            return {}
    
    def _get_cache_key(
        self,
        key: str,
        scope: ConfigScope,
        scope_id: Optional[str]
    ) -> str:
        """生成缓存键"""
        return f"config:{scope.value}:{key}:{scope_id or 'global'}"
    
    def _infer_data_type(self, value: Any) -> ConfigDataType:
        """推断数据类型"""
        if isinstance(value, bool):
            return ConfigDataType.BOOLEAN
        elif isinstance(value, int):
            return ConfigDataType.INTEGER
        elif isinstance(value, float):
            return ConfigDataType.FLOAT
        elif isinstance(value, list):
            return ConfigDataType.LIST
        elif isinstance(value, dict):
            return ConfigDataType.DICT
        else:
            return ConfigDataType.STRING
    
    def _serialize_value(self, value: Any, data_type: ConfigDataType) -> str:
        """序列化配置值"""
        if data_type in [ConfigDataType.JSON, ConfigDataType.LIST, ConfigDataType.DICT]:
            return json.dumps(value)
        else:
            return str(value)
    
    def _deserialize_value(self, value: str, data_type: ConfigDataType) -> Any:
        """反序列化配置值"""
        try:
            if data_type == ConfigDataType.BOOLEAN:
                return value.lower() in ('true', '1', 'yes', 'on')
            elif data_type == ConfigDataType.INTEGER:
                return int(value)
            elif data_type == ConfigDataType.FLOAT:
                return float(value)
            elif data_type in [ConfigDataType.JSON, ConfigDataType.LIST, ConfigDataType.DICT]:
                return json.loads(value)
            else:
                return value
        except (ValueError, json.JSONDecodeError):
            return value
    
    def _format_as_env(self, configs: Dict[str, Any]) -> str:
        """格式化为环境变量格式"""
        lines = []
        for key, value in configs.items():
            env_key = key.upper().replace('.', '_').replace('-', '_')
            if isinstance(value, (dict, list)):
                env_value = json.dumps(value)
            else:
                env_value = str(value)
            lines.append(f"{env_key}={env_value}")
        return '\n'.join(lines)
    
    def _parse_env_format(self, content: str) -> Dict[str, Any]:
        """解析环境变量格式"""
        configs = {}
        for line in content.strip().split('\n'):
            if '=' in line and not line.startswith('#'):
                key, value = line.split('=', 1)
                key = key.strip().lower().replace('_', '.')
                value = value.strip()
                
                # 尝试解析JSON
                try:
                    configs[key] = json.loads(value)
                except json.JSONDecodeError:
                    configs[key] = value
        
        return configs
    
    async def _validate_config_value(
        self,
        key: str,
        value: Any,
        data_type: ConfigDataType
    ):
        """验证配置值"""
        try:
            # 获取验证规则
            config_item = await self._get_config_from_db(key, ConfigScope.GLOBAL, None)
            validation = config_item.validation if config_item else None
            
            if validation:
                # 必填验证
                if validation.required and value is None:
                    raise ValueError(f"Config {key} is required")
                
                # 数值范围验证
                if data_type in [ConfigDataType.INTEGER, ConfigDataType.FLOAT]:
                    if validation.min_value is not None and value < validation.min_value:
                        raise ValueError(f"Config {key} value {value} is below minimum {validation.min_value}")
                    if validation.max_value is not None and value > validation.max_value:
                        raise ValueError(f"Config {key} value {value} is above maximum {validation.max_value}")
                
                # 字符串长度验证
                if data_type == ConfigDataType.STRING:
                    if validation.min_length is not None and len(str(value)) < validation.min_length:
                        raise ValueError(f"Config {key} value length is below minimum {validation.min_length}")
                    if validation.max_length is not None and len(str(value)) > validation.max_length:
                        raise ValueError(f"Config {key} value length is above maximum {validation.max_length}")
                
                # 允许值验证
                if validation.allowed_values and value not in validation.allowed_values:
                    raise ValueError(f"Config {key} value {value} is not in allowed values {validation.allowed_values}")
                
                # 自定义验证器
                if validation.custom_validator and validation.custom_validator in self.validators:
                    validator = self.validators[validation.custom_validator]
                    if not await validator(key, value):
                        raise ValueError(f"Config {key} failed custom validation")
            
            # 全局验证器
            if key in self.validators:
                validator = self.validators[key]
                if not await validator(key, value):
                    raise ValueError(f"Config {key} failed validation")
            
        except Exception as e:
            logger.error(f"Config validation failed for {key}: {str(e)}")
            raise
    
    async def _validate_template_data(self, data: Dict[str, Any], schema: Dict[str, Any]):
        """验证模板数据"""
        try:
            # TODO: 实现JSON Schema验证
            pass
            
        except Exception as e:
            logger.error(f"Template data validation failed: {str(e)}")
            raise
    
    async def _trigger_listeners(self, key: str, value: Any, scope: ConfigScope, scope_id: Optional[str]):
        """触发配置监听器"""
        try:
            if key in self.listeners:
                for listener in self.listeners[key]:
                    try:
                        await listener(key, value, scope, scope_id)
                    except Exception as e:
                        logger.error(f"Config listener failed for {key}: {str(e)}")
            
        except Exception as e:
            logger.error(f"Failed to trigger listeners for {key}: {str(e)}")
    
    async def _load_default_configs(self):
        """加载默认配置"""
        try:
            self.default_configs = {
                # 系统配置
                "system.name": "ERAG System",
                "system.version": "1.0.0",
                "system.debug": False,
                "system.log_level": "INFO",
                
                # 数据库配置
                "database.pool_size": 10,
                "database.timeout": 30,
                "database.retry_count": 3,
                
                # 缓存配置
                "cache.ttl": 300,
                "cache.max_size": 1000,
                
                # 向量搜索配置
                "vector.similarity_threshold": 0.7,
                "vector.max_results": 50,
                
                # LLM配置
                "llm.default_model": "gpt-3.5-turbo",
                "llm.max_tokens": 4000,
                "llm.temperature": 0.7,
                
                # 文档处理配置
                "document.max_file_size": 100 * 1024 * 1024,  # 100MB
                "document.supported_formats": ["pdf", "docx", "txt", "md"],
                
                # 安全配置
                "security.session_timeout": 3600,
                "security.max_login_attempts": 5,
                "security.password_min_length": 8,
                
                # 通知配置
                "notification.email_enabled": True,
                "notification.sms_enabled": False,
                "notification.webhook_enabled": True,
            }
            
            logger.info("Default configs loaded")
            
        except Exception as e:
            logger.error(f"Failed to load default configs: {str(e)}")
            raise
    
    async def _load_file_configs(self):
        """加载文件配置"""
        try:
            with open(self.config_file_path, 'r', encoding='utf-8') as f:
                if self.config_file_path.endswith('.yaml') or self.config_file_path.endswith('.yml'):
                    file_configs = yaml.safe_load(f)
                else:
                    file_configs = json.load(f)
            
            # 将文件配置设置到系统中
            for key, value in file_configs.items():
                await self.set_config(
                    key, value,
                    config_type=ConfigType.SYSTEM,
                    updated_by="file_loader",
                    validate=False
                )
            
            logger.info(f"File configs loaded from {self.config_file_path}")
            
        except Exception as e:
            logger.error(f"Failed to load file configs: {str(e)}")
            raise
    
    async def _register_builtin_validators(self):
        """注册内置验证器"""
        try:
            # 邮箱验证器
            async def email_validator(key: str, value: str) -> bool:
                import re
                pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
                return bool(re.match(pattern, value))
            
            # URL验证器
            async def url_validator(key: str, value: str) -> bool:
                import re
                pattern = r'^https?://[^\s/$.?#].[^\s]*$'
                return bool(re.match(pattern, value))
            
            # 端口验证器
            async def port_validator(key: str, value: int) -> bool:
                return 1 <= value <= 65535
            
            await self.register_validator("email", email_validator)
            await self.register_validator("url", url_validator)
            await self.register_validator("port", port_validator)
            
            logger.info("Builtin validators registered")
            
        except Exception as e:
            logger.error(f"Failed to register builtin validators: {str(e)}")
            raise
    
    async def _create_config_tables(self):
        """创建配置相关表"""
        try:
            # 使用SQLAlchemy ORM创建表
            from backend.models.base import Base
            from sqlalchemy import create_engine
            
            # 注意：这里应该使用实际的数据库引擎
            # 由于这是StarRocks，可能需要特殊处理
            # 这里仅作为示例，实际实现可能需要调整
            
            # 创建表结构（如果使用SQLAlchemy，通常在应用启动时创建）
            # ConfigModel.__table__.create(engine, checkfirst=True)
            # ConfigHistoryModel.__table__.create(engine, checkfirst=True)
            # ConfigTemplateModel.__table__.create(engine, checkfirst=True)
            
            logger.info("Config tables created successfully using SQLAlchemy models")
            
        except Exception as e:
            logger.error(f"Failed to create config tables: {str(e)}")
            raise
    
    async def _get_config_from_db(
        self,
        key: str,
        scope: ConfigScope,
        scope_id: Optional[str]
    ) -> Optional[ConfigItem]:
        """从数据库获取配置"""
        try:
            # 使用SQLAlchemy ORM查询
            config = self.db.query(ConfigModel).filter(
                ConfigModel.config_key == key,
                ConfigModel.scope == scope.value,
                ConfigModel.scope_id == (scope_id or ""),
                ConfigModel.status == 'active'
            ).order_by(ConfigModel.version.desc()).first()
            
            if config:
                # 将数据库记录转换为ConfigItem对象
                return ConfigItem(
                    key=config.config_key,
                    value=config.value,
                    data_type=ConfigDataType(config.data_type),
                    config_type=ConfigType(config.config_type),
                    scope=ConfigScope(config.scope),
                    scope_id=config.scope_id,
                    description=config.description,
                    default_value=config.default_value,
                    validation=config.validation_rules,
                    is_sensitive=config.is_sensitive,
                    is_readonly=config.is_readonly,
                    status=ConfigStatus(config.status),
                    version=config.version,
                    created_by=config.created_by,
                    updated_by=config.updated_by,
                    created_at=config.created_at,
                    updated_at=config.updated_at,
                    tags=config.tags or [],
                    metadata=config.metadata or {}
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get config from DB: {str(e)}")
            return None
    
    async def _create_config(
        self,
        key: str,
        value: Any,
        data_type: ConfigDataType,
        config_type: ConfigType,
        scope: ConfigScope,
        scope_id: Optional[str],
        description: Optional[str],
        created_by: str
    ):
        """创建新配置"""
        try:
            config_id = f"config_{int(datetime.now().timestamp())}"
            serialized_value = self._serialize_value(value, data_type)
            
            from backend.models.config import ConfigModel
            from backend.config.database import get_async_session
            
            async with get_async_session() as session:
                new_config = ConfigModel(
                    id=config_id,
                    config_key=key,
                    value=serialized_value,
                    data_type=data_type.value,
                    config_type=config_type.value,
                    scope=scope.value,
                    scope_id=scope_id or "",
                    description=description,
                    created_by=created_by,
                    updated_by=created_by,
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                )
                
                session.add(new_config)
                await session.commit()
            
        except Exception as e:
            logger.error(f"Failed to create config: {str(e)}")
            raise
    
    async def _update_config(
        self,
        key: str,
        value: Any,
        scope: ConfigScope,
        scope_id: Optional[str],
        data_type: ConfigDataType,
        updated_by: str
    ):
        """更新配置"""
        try:
            serialized_value = self._serialize_value(value, data_type)
            
            # 使用SQLAlchemy ORM更新
            config = self.db.query(ConfigModel).filter(
                ConfigModel.config_key == key,
                ConfigModel.scope == scope.value,
                ConfigModel.scope_id == (scope_id or "")
            ).first()
            
            if config:
                config.value = serialized_value
                config.data_type = data_type.value
                config.updated_by = updated_by
                config.updated_at = datetime.now()
                config.version = config.version + 1
                
                self.db.commit()
            
        except Exception as e:
            logger.error(f"Failed to update config: {str(e)}")
            raise
    
    async def _delete_config_from_db(
        self,
        key: str,
        scope: ConfigScope,
        scope_id: Optional[str]
    ):
        """从数据库删除配置"""
        try:
            # 使用SQLAlchemy ORM软删除（设置状态为inactive）
            config = self.db.query(ConfigModel).filter(
                ConfigModel.config_key == key,
                ConfigModel.scope == scope.value,
                ConfigModel.scope_id == (scope_id or "")
            ).first()
            
            if config:
                config.status = 'inactive'
                config.updated_at = datetime.now()
                
                self.db.commit()
            
        except Exception as e:
            logger.error(f"Failed to delete config from DB: {str(e)}")
            raise
    
    async def _record_config_history(
        self,
        key: str,
        old_value: Any,
        new_value: Any,
        scope: ConfigScope,
        scope_id: Optional[str],
        change_type: str,
        changed_by: str
    ):
        """记录配置历史"""
        try:
            history_id = f"history_{int(datetime.now().timestamp())}"
            
            from backend.models.config import ConfigHistoryModel
            from backend.config.database import get_async_session
            
            async with get_async_session() as session:
                new_history = ConfigHistoryModel(
                    id=history_id,
                    config_key=key,
                    old_value=json.dumps(old_value, default=str),
                    new_value=json.dumps(new_value, default=str),
                    scope=scope.value,
                    scope_id=scope_id or "",
                    change_type=change_type,
                    changed_by=changed_by,
                    timestamp=datetime.now()
                )
                
                session.add(new_history)
                await session.commit()
            
        except Exception as e:
            logger.error(f"Failed to record config history: {str(e)}")
            raise
    
    async def _list_configs_from_db(
        self,
        config_type: Optional[ConfigType],
        scope: Optional[ConfigScope],
        scope_id: Optional[str],
        status: Optional[ConfigStatus],
        search: Optional[str],
        tags: Optional[List[str]],
        limit: int,
        offset: int
    ) -> List[ConfigItem]:
        """从数据库列出配置"""
        try:
            # TODO: 实现配置列表查询
            return []
            
        except Exception as e:
            logger.error(f"Failed to list configs from DB: {str(e)}")
            return []
    
    async def _get_config_history_from_db(
        self,
        key: Optional[str],
        scope: Optional[ConfigScope],
        scope_id: Optional[str],
        changed_by: Optional[str],
        start_time: Optional[datetime],
        end_time: Optional[datetime],
        limit: int,
        offset: int
    ) -> List[ConfigHistory]:
        """从数据库获取配置历史"""
        try:
            # TODO: 实现配置历史查询
            return []
            
        except Exception as e:
            logger.error(f"Failed to get config history from DB: {str(e)}")
            return []
    
    async def _save_template(self, template: ConfigTemplate):
        """保存配置模板"""
        try:
            from backend.models.config import ConfigTemplateModel
            from backend.config.database import get_async_session
            
            async with get_async_session() as session:
                new_template = ConfigTemplateModel(
                    id=template.id,
                    name=template.name,
                    description=template.description,
                    config_type=template.config_type.value,
                    template_data=json.dumps(template.template_data),
                    schema=json.dumps(template.schema),
                    version=template.version,
                    is_default=template.is_default,
                    created_by=template.created_by,
                    created_at=template.created_at,
                    updated_at=template.updated_at
                )
                
                session.add(new_template)
                await session.commit()
            
        except Exception as e:
            logger.error(f"Failed to save template: {str(e)}")
            raise
    
    async def _get_template(self, template_id: str) -> Optional[ConfigTemplate]:
        """获取配置模板"""
        try:
            from backend.models.database import ConfigTemplateModel
            from sqlalchemy import select
            
            stmt = select(ConfigTemplateModel).where(ConfigTemplateModel.id == template_id)
            result = await self.db.fetch_one(stmt)
            
            if result:
                # 将SQLAlchemy结果转换为ConfigTemplate对象
                template_dict = {column.name: getattr(result, column.name) for column in ConfigTemplateModel.__table__.columns}
                return ConfigTemplate(**template_dict)
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get template: {str(e)}")
            return None
    
    async def _get_configs_for_export(
        self,
        filters: Optional[Dict[str, Any]],
        include_sensitive: bool
    ) -> Dict[str, Any]:
        """获取用于导出的配置"""
        try:
            # TODO: 实现配置导出查询
            return {}
            
        except Exception as e:
            logger.error(f"Failed to get configs for export: {str(e)}")
            return {}
    
    async def _save_export_record(self, export_record: ConfigExport):
        """保存导出记录"""
        try:
            # TODO: 实现导出记录保存
            pass
            
        except Exception as e:
            logger.error(f"Failed to save export record: {str(e)}")
            raise
    
    async def _get_config_stats_from_db(self) -> Dict[str, Any]:
        """从数据库获取配置统计"""
        try:
            # TODO: 实现配置统计查询
            return {
                "total_configs": 0,
                "active_configs": 0,
                "config_types": {},
                "scopes": {},
                "recent_changes": 0
            }
            
        except Exception as e:
            logger.error(f"Failed to get config stats from DB: {str(e)}")
            return {}