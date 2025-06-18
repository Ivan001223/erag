from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from enum import Enum

from sqlalchemy import Column, String, Text, Boolean, DateTime, Integer, Enum as SQLEnum, ForeignKey
from sqlalchemy.dialects.mysql import VARCHAR, TEXT
from sqlalchemy.orm import relationship, Mapped, mapped_column
from pydantic import Field, validator, EmailStr

from .base import Base, BaseModel, FullModel


class UserRole(str, Enum):
    """用户角色"""
    ADMIN = "admin"
    USER = "user"
    GUEST = "guest"
    VIEWER = "viewer"
    EDITOR = "editor"
    MANAGER = "manager"


class UserStatus(str, Enum):
    """用户状态"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING = "pending"
    BANNED = "banned"


class AuthProvider(str, Enum):
    """认证提供商"""
    LOCAL = "local"
    OAUTH2 = "oauth2"
    LDAP = "ldap"
    SSO = "sso"
    GOOGLE = "google"
    GITHUB = "github"
    MICROSOFT = "microsoft"


class User(Base):
    """用户SQLAlchemy模型"""
    
    __tablename__ = "users"
    __allow_unmapped__ = True
    
    username: Mapped[str] = mapped_column(
        VARCHAR(50),
        unique=True,
        nullable=False,
        index=True,
        comment="用户名"
    )
    
    email: Mapped[str] = mapped_column(
        VARCHAR(255),
        unique=True,
        nullable=False,
        index=True,
        comment="邮箱"
    )
    
    password_hash: Mapped[Optional[str]] = mapped_column(
        VARCHAR(255),
        nullable=True,
        comment="密码哈希"
    )
    
    full_name: Mapped[Optional[str]] = mapped_column(
        VARCHAR(100),
        nullable=True,
        comment="全名"
    )
    
    avatar_url: Mapped[Optional[str]] = mapped_column(
        VARCHAR(500),
        nullable=True,
        comment="头像URL"
    )
    
    phone: Mapped[Optional[str]] = mapped_column(
        VARCHAR(20),
        nullable=True,
        comment="电话号码"
    )
    
    role: Mapped[UserRole] = mapped_column(
        SQLEnum(UserRole),
        default=UserRole.USER,
        nullable=False,
        comment="用户角色"
    )
    
    status: Mapped[UserStatus] = mapped_column(
        SQLEnum(UserStatus),
        default=UserStatus.PENDING,
        nullable=False,
        comment="用户状态"
    )
    
    auth_provider: Mapped[AuthProvider] = mapped_column(
        SQLEnum(AuthProvider),
        default=AuthProvider.LOCAL,
        nullable=False,
        comment="认证提供商"
    )
    
    external_id: Mapped[Optional[str]] = mapped_column(
        VARCHAR(255),
        nullable=True,
        comment="外部ID"
    )
    
    last_login_at: Mapped[Optional[Any]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="最后登录时间"
    )
    
    login_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="登录次数"
    )
    
    failed_login_attempts: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="失败登录次数"
    )
    
    locked_until: Mapped[Optional[Any]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="锁定到期时间"
    )
    
    email_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="邮箱是否验证"
    )
    
    email_verified_at: Mapped[Optional[Any]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="邮箱验证时间"
    )
    
    preferences: Mapped[Optional[str]] = mapped_column(
        TEXT,
        nullable=True,
        comment="用户偏好设置(JSON)"
    )
    
    model_metadata: Mapped[Optional[str]] = mapped_column(
        TEXT,
        nullable=True,
        comment="元数据(JSON)"
    )
    
    def is_active(self) -> bool:
        """是否激活"""
        return self.status == UserStatus.ACTIVE
    
    def is_locked(self) -> bool:
        """是否被锁定"""
        if self.locked_until is None:
            return False
        return datetime.now() < self.locked_until
    
    def can_login(self) -> bool:
        """是否可以登录"""
        return self.is_active() and not self.is_locked()
    
    def increment_login_count(self) -> None:
        """增加登录次数"""
        self.login_count += 1
        self.last_login_at = datetime.now()
        self.failed_login_attempts = 0
    
    def increment_failed_login(self) -> None:
        """增加失败登录次数"""
        self.failed_login_attempts += 1
        if self.failed_login_attempts >= 5:
            self.locked_until = datetime.now() + timedelta(minutes=30)


class UserProfile(Base):
    """用户档案SQLAlchemy模型"""
    
    __allow_unmapped__ = True
    
    __tablename__ = "user_profiles"
    
    user_id: Any = Column(
        String(36),
        nullable=False,
        unique=True,
        index=True,
        comment="用户ID"
    )
    
    bio: Any = Column(
        TEXT,
        nullable=True,
        comment="个人简介"
    )
    
    company: Any = Column(
        VARCHAR(100),
        nullable=True,
        comment="公司"
    )
    
    department: Any = Column(
        VARCHAR(100),
        nullable=True,
        comment="部门"
    )
    
    position: Any = Column(
        VARCHAR(100),
        nullable=True,
        comment="职位"
    )
    
    location: Any = Column(
        VARCHAR(100),
        nullable=True,
        comment="位置"
    )
    
    timezone: Any = Column(
        VARCHAR(50),
        default="Asia/Shanghai",
        nullable=False,
        comment="时区"
    )
    
    language: Any = Column(
        VARCHAR(10),
        default="zh",
        nullable=False,
        comment="语言"
    )
    
    theme: Any = Column(
        VARCHAR(20),
        default="light",
        nullable=False,
        comment="主题"
    )
    
    notification_settings: Any = Column(
        TEXT,
        nullable=True,
        comment="通知设置(JSON)"
    )


# Pydantic模型用于API
class Permission(BaseModel):
    """权限模型"""
    
    resource: str = Field(
        ...,
        description="资源名称"
    )
    actions: List[str] = Field(
        default_factory=list,
        description="操作列表"
    )


class UserBase(BaseModel):
    """用户基础模型"""
    
    username: str = Field(
        ...,
        min_length=3,
        max_length=50,
        pattern=r"^[a-zA-Z0-9_-]+$",
        description="用户名"
    )
    
    email: EmailStr = Field(
        ...,
        description="邮箱地址"
    )
    
    full_name: Optional[str] = Field(
        default=None,
        max_length=100,
        description="全名"
    )
    
    phone: Optional[str] = Field(
        default=None,
        pattern=r"^\+?[1-9]\d{1,14}$",
        description="电话号码"
    )
    
    role: UserRole = Field(
        default=UserRole.USER,
        description="用户角色"
    )


class UserCreate(UserBase):
    """创建用户模型"""
    
    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="密码"
    )
    
    confirm_password: str = Field(
        ...,
        description="确认密码"
    )
    
    @validator('confirm_password')
    def passwords_match(cls, v, values):
        if 'password' in values and v != values['password']:
            raise ValueError('密码不匹配')
        return v


class UserUpdate(BaseModel):
    """更新用户模型"""
    
    full_name: Optional[str] = Field(
        default=None,
        max_length=100,
        description="全名"
    )
    
    phone: Optional[str] = Field(
        default=None,
        pattern=r"^\+?[1-9]\d{1,14}$",
        description="电话号码"
    )
    
    avatar_url: Optional[str] = Field(
        default=None,
        description="头像URL"
    )
    
    role: Optional[UserRole] = Field(
        default=None,
        description="用户角色"
    )
    
    status: Optional[UserStatus] = Field(
        default=None,
        description="用户状态"
    )


class UserResponse(FullModel):
    """用户响应模型"""
    
    username: str = Field(
        ...,
        description="用户名"
    )
    
    email: str = Field(
        ...,
        description="邮箱地址"
    )
    
    full_name: Optional[str] = Field(
        default=None,
        description="全名"
    )
    
    avatar_url: Optional[str] = Field(
        default=None,
        description="头像URL"
    )
    
    phone: Optional[str] = Field(
        default=None,
        description="电话号码"
    )
    
    role: UserRole = Field(
        ...,
        description="用户角色"
    )
    
    status: UserStatus = Field(
        ...,
        description="用户状态"
    )
    
    auth_provider: AuthProvider = Field(
        ...,
        description="认证提供商"
    )
    
    last_login_at: Optional[datetime] = Field(
        default=None,
        description="最后登录时间"
    )
    
    login_count: int = Field(
        default=0,
        description="登录次数"
    )
    
    email_verified: bool = Field(
        default=False,
        description="邮箱是否验证"
    )
    
    email_verified_at: Optional[datetime] = Field(
        default=None,
        description="邮箱验证时间"
    )


class UserLogin(BaseModel):
    """用户登录模型"""
    
    username: str = Field(
        ...,
        description="用户名或邮箱"
    )
    
    password: str = Field(
        ...,
        description="密码"
    )
    
    remember_me: bool = Field(
        default=False,
        description="记住我"
    )


class PasswordChange(BaseModel):
    """密码修改模型"""
    
    current_password: str = Field(
        ...,
        description="当前密码"
    )
    
    new_password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="新密码"
    )
    
    confirm_password: str = Field(
        ...,
        description="确认新密码"
    )
    
    @validator('confirm_password')
    def passwords_match(cls, v, values):
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('新密码不匹配')
        return v


class UserSession(Base):
    """用户会话SQLAlchemy模型"""
    
    __tablename__ = "user_sessions"
    __allow_unmapped__ = True
    
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
        comment="用户ID"
    )
    
    session_token: Mapped[str] = mapped_column(
        VARCHAR(255),
        nullable=False,
        unique=True,
        comment="会话令牌"
    )
    
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="过期时间"
    )
    
    ip_address: Mapped[Optional[str]] = mapped_column(
        VARCHAR(45),
        nullable=True,
        comment="IP地址"
    )
    
    user_agent: Mapped[Optional[str]] = mapped_column(
        TEXT,
        nullable=True,
        comment="用户代理"
    )


class UserActivity(Base):
    """用户活动SQLAlchemy模型"""
    
    __tablename__ = "user_activities"
    __allow_unmapped__ = True
    
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
        comment="用户ID"
    )
    
    activity_type: Mapped[str] = mapped_column(
        VARCHAR(50),
        nullable=False,
        comment="活动类型"
    )
    
    description: Mapped[Optional[str]] = mapped_column(
        TEXT,
        nullable=True,
        comment="活动描述"
    )
    
    ip_address: Mapped[Optional[str]] = mapped_column(
        VARCHAR(45),
        nullable=True,
        comment="IP地址"
    )
    
    user_agent: Mapped[Optional[str]] = mapped_column(
        TEXT,
        nullable=True,
        comment="用户代理"
    )


class UserStats(BaseModel):
    """用户统计模型"""
    
    total_users: int = Field(
        ...,
        description="总用户数"
    )
    
    active_users: int = Field(
        ...,
        description="活跃用户数"
    )
    
    new_users_today: int = Field(
        ...,
        description="今日新增用户数"
    )
    
    new_users_this_week: int = Field(
        ...,
        description="本周新增用户数"
    )
    
    new_users_this_month: int = Field(
        ...,
        description="本月新增用户数"
    )


class UserPreferences(BaseModel):
    """用户偏好设置模型"""
    
    language: str = Field(
        default="zh-CN",
        description="语言设置"
    )
    
    theme: str = Field(
        default="light",
        description="主题设置"
    )
    
    timezone: str = Field(
        default="Asia/Shanghai",
        description="时区设置"
    )
    
    notifications: dict = Field(
        default_factory=dict,
        description="通知设置"
    )
    
    privacy: dict = Field(
        default_factory=dict,
        description="隐私设置"
    )


class PasswordReset(BaseModel):
    """密码重置模型"""
    
    email: EmailStr = Field(
        ...,
        description="邮箱地址"
    )


class PasswordResetConfirm(BaseModel):
    """密码重置确认模型"""
    
    token: str = Field(
        ...,
        description="重置令牌"
    )
    
    new_password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="新密码"
    )
    
    confirm_password: str = Field(
        ...,
        description="确认新密码"
    )
    
    @validator('confirm_password')
    def passwords_match(cls, v, values):
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('新密码不匹配')
        return v