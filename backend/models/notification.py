from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum

from sqlalchemy import Column, String, Text, Boolean, DateTime, Integer, JSON, Index, ForeignKey
from sqlalchemy.dialects.mysql import VARCHAR, TEXT, CHAR
from pydantic import Field
import json
from sqlalchemy.sql import func

from .base import Base, BaseModel, FullModel


class NotificationType(str, Enum):
    """通知类型"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    SUCCESS = "success"
    SYSTEM = "system"
    USER = "user"


class Notification(Base):
    """通知SQLAlchemy模型"""
    
    __tablename__ = "notifications"
    
    user_id: Any = Column(CHAR(36), nullable=False, index=True, comment="用户ID")
    title: Any = Column(VARCHAR(200), nullable=False, comment="通知标题")
    content: Any = Column(TEXT, nullable=False, comment="通知内容")
    notification_type: Any = Column(VARCHAR(50), nullable=False, default="info", comment="通知类型")
    priority: Any = Column(Integer, nullable=False, default=1, comment="优先级")
    meta_data: Any = Column(TEXT, nullable=True, comment="元数据JSON")
    is_read: Any = Column(Boolean, nullable=False, default=False, comment="是否已读")
    expires_at: Any = Column(DateTime, nullable=True, comment="过期时间")
    
    # 索引
    __table_args__ = (
        Index('idx_user_id', 'user_id'),
        Index('idx_is_read', 'is_read'),
        Index('idx_notification_type', 'notification_type'),
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'title': self.title,
            'content': self.content,
            'notification_type': self.notification_type,
            'priority': self.priority,
            'metadata': json.loads(self.meta_data) if self.meta_data else None,
            'is_read': self.is_read,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def get_metadata(self) -> Optional[Dict[str, Any]]:
        """获取解析后的元数据"""
        if self.meta_data:
            try:
                return json.loads(self.meta_data)
            except (json.JSONDecodeError, TypeError):
                return None
        return None
    
    def set_metadata(self, metadata: Optional[Dict[str, Any]]) -> None:
        """设置元数据"""
        if metadata is not None:
            self.meta_data = json.dumps(metadata)
        else:
            self.meta_data = None
    
    def __repr__(self):
        return f"<Notification(id='{self.id}', title='{self.title}', type='{self.notification_type}')>"


class NotificationPreferenceModel(Base):
    """通知偏好表模型"""

    __allow_unmapped__ = True
    __tablename__ = 'notification_preferences'
    
    user_id: Any = Column(
        String(36),
        nullable=False,
        index=True,
        comment="用户ID"
    )
    
    channel: Any = Column(
        VARCHAR(50),
        nullable=False,
        comment="通知渠道"
    )
    
    enabled: Any = Column(
        Boolean,
        default=True,
        comment="是否启用"
    )
    
    types: Any = Column(
        JSON,
        comment="通知类型列表"
    )
    
    quiet_hours_start: Any = Column(
        VARCHAR(10),
        comment="静默时间开始"
    )
    
    quiet_hours_end: Any = Column(
        VARCHAR(10),
        comment="静默时间结束"
    )
    
    frequency_limit: Any = Column(
        Integer,
        comment="频率限制"
    )
    
    # 索引
    __table_args__ = (
        Index('idx_user_channel', 'user_id', 'channel'),
    )
    
    def __repr__(self):
        return f"<NotificationPreference(user_id='{self.user_id}', channel='{self.channel}')>"


# Pydantic模型用于API
class NotificationBase(BaseModel):
    """通知基础模型"""
    
    title: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="通知标题"
    )
    
    content: str = Field(
        ...,
        min_length=1,
        description="通知内容"
    )
    
    notification_type: NotificationType = Field(
        default=NotificationType.INFO,
        description="通知类型"
    )
    
    priority: int = Field(
        default=1,
        ge=1,
        le=5,
        description="优先级(1-5)"
    )
    
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="元数据"
    )
    
    expires_at: Optional[datetime] = Field(
        default=None,
        description="过期时间"
    )


class NotificationCreate(NotificationBase):
    """创建通知模型"""
    
    user_id: str = Field(
        ...,
        description="用户ID"
    )


class NotificationUpdate(BaseModel):
    """更新通知模型"""
    
    title: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=200,
        description="通知标题"
    )
    
    content: Optional[str] = Field(
        default=None,
        min_length=1,
        description="通知内容"
    )
    
    notification_type: Optional[NotificationType] = Field(
        default=None,
        description="通知类型"
    )
    
    priority: Optional[int] = Field(
        default=None,
        ge=1,
        le=5,
        description="优先级(1-5)"
    )
    
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="元数据"
    )
    
    is_read: Optional[bool] = Field(
        default=None,
        description="是否已读"
    )
    
    expires_at: Optional[datetime] = Field(
        default=None,
        description="过期时间"
    )


class NotificationResponse(FullModel):
    """通知响应模型"""
    
    user_id: str = Field(
        ...,
        description="用户ID"
    )
    
    title: str = Field(
        ...,
        description="通知标题"
    )
    
    content: str = Field(
        ...,
        description="通知内容"
    )
    
    notification_type: NotificationType = Field(
        ...,
        description="通知类型"
    )
    
    priority: int = Field(
        ...,
        description="优先级"
    )
    
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="元数据"
    )
    
    is_read: bool = Field(
        ...,
        description="是否已读"
    )
    
    expires_at: Optional[datetime] = Field(
        default=None,
        description="过期时间"
    )


class NotificationStats(BaseModel):
    """通知统计模型"""
    
    total_notifications: int = Field(
        default=0,
        description="总通知数"
    )
    
    unread_notifications: int = Field(
        default=0,
        description="未读通知数"
    )
    
    read_rate: float = Field(
        default=0.0,
        description="已读率"
    )
    
    type_distribution: Dict[str, int] = Field(
        default_factory=dict,
        description="类型分布"
    )
    
    priority_distribution: Dict[int, int] = Field(
        default_factory=dict,
        description="优先级分布"
    )