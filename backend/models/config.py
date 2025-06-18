from sqlalchemy import Column, String, Text, DateTime, Boolean, Integer
from sqlalchemy import Column, String, Text, Boolean, Integer, DateTime, JSON, Index
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from .base import Base, FullModel
from typing import Optional, Any
import json
from datetime import datetime


class SystemConfig(Base):
    """系统配置表模型"""
    __tablename__ = 'system_config'
    
    config_key: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True, comment='配置键')
    config_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment='配置值')
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment='配置描述')
    
    def __repr__(self):
        return f"<SystemConfig(key='{self.config_key}', value='{self.config_value[:50]}...')>"
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            'id': self.id,
            'config_key': self.config_key,
            'config_value': self.config_value,
            'description': self.description,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'is_deleted': self.is_deleted
        }
    
    def get_parsed_value(self) -> Any:
        """获取解析后的配置值"""
        if not self.config_value:
            return None
        
        try:
            # 尝试解析为JSON
            return json.loads(self.config_value)
        except (json.JSONDecodeError, TypeError):
            # 如果不是JSON，返回原始字符串
            return self.config_value
    
    def set_value(self, value: Any) -> None:
        """设置配置值"""
        if value is None:
            self.config_value = None
        elif isinstance(value, (dict, list)):
            self.config_value = json.dumps(value, ensure_ascii=False)
        else:
            self.config_value = str(value)


class ConfigModel(Base):
    """配置项模型"""
    __tablename__ = 'system_configs'
    
    config_key: Mapped[str] = mapped_column(String(255), nullable=False, index=True, comment='配置键')
    value: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment='配置值')
    data_type: Mapped[str] = mapped_column(String(50), nullable=False, comment='数据类型')
    config_type: Mapped[str] = mapped_column(String(50), nullable=False, comment='配置类型')
    scope: Mapped[str] = mapped_column(String(50), nullable=False, comment='作用域')
    scope_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, comment='作用域ID')
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment='描述')
    default_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment='默认值')
    validation_rules: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True, comment='验证规则')
    is_sensitive: Mapped[bool] = mapped_column(Boolean, default=False, comment='是否敏感')
    is_readonly: Mapped[bool] = mapped_column(Boolean, default=False, comment='是否只读')
    status: Mapped[str] = mapped_column(String(50), default='active', comment='状态')
    version: Mapped[int] = mapped_column(Integer, default=1, comment='版本')
    created_by: Mapped[str] = mapped_column(String(255), nullable=False, comment='创建者')
    updated_by: Mapped[str] = mapped_column(String(255), nullable=False, comment='更新者')
    tags: Mapped[Optional[list]] = mapped_column(JSON, nullable=True, comment='标签')
    model_metadata: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True, comment='元数据')
    
    __table_args__ = (
        Index('uk_config', 'config_key', 'scope', 'scope_id', unique=True),
    )
    
    def __repr__(self):
        return f"<ConfigModel(key='{self.config_key}', scope='{self.scope}')>"


class ConfigHistoryModel(Base):
    """配置历史记录模型"""
    __tablename__ = 'system_config_history'
    
    config_key: Mapped[str] = mapped_column(String(255), nullable=False, index=True, comment='配置键')
    old_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment='旧值')
    new_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment='新值')
    scope: Mapped[str] = mapped_column(String(50), nullable=False, comment='作用域')
    scope_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, comment='作用域ID')
    change_type: Mapped[str] = mapped_column(String(50), nullable=False, comment='变更类型')
    changed_by: Mapped[str] = mapped_column(String(255), nullable=False, comment='更新者')
    change_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment='变更原因')
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=func.now(), comment='时间戳')
    model_metadata: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True, comment='元数据')
    
    def __repr__(self):
        return f"<ConfigHistoryModel(key='{self.config_key}', type='{self.change_type}')>"


class ConfigTemplateModel(Base):
    """配置模板模型"""
    __tablename__ = 'system_config_templates'
    
    name: Mapped[str] = mapped_column(String(255), nullable=False, comment='模板名称')
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment='描述')
    config_type: Mapped[str] = mapped_column(String(50), nullable=False, comment='配置类型')
    template_data: Mapped[dict] = mapped_column(JSON, nullable=False, comment='模板数据')
    schema: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True, comment='JSON Schema')
    version: Mapped[str] = mapped_column(String(50), nullable=False, comment='版本')
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, comment='是否默认')
    created_by: Mapped[str] = mapped_column(String(255), nullable=False, comment='创建者')
    tags: Mapped[Optional[list]] = mapped_column(JSON, nullable=True, comment='标签')
    
    def __repr__(self):
        return f"<ConfigTemplateModel(name='{self.name}', version='{self.version}')>"