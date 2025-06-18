from datetime import datetime
from typing import Optional, Any, Dict, Generic, List, TypeVar
from uuid import uuid4
from datetime import datetime

from sqlalchemy import Column, String, DateTime, Boolean, Text
from sqlalchemy.dialects.mysql import CHAR
from sqlalchemy.ext.declarative import as_declarative, declared_attr
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from pydantic import BaseModel as PydanticBaseModel, Field, ConfigDict

# 定义泛型类型变量
T = TypeVar('T')


@as_declarative()
class Base:
    """SQLAlchemy基础模型类"""
    
    __allow_unmapped__ = True
    
    # 自动生成表名
    @declared_attr
    def __tablename__(cls) -> str:
        return cls.__name__.lower()
    
    # 通用字段
    id: Mapped[str] = mapped_column(
        CHAR(36),
        primary_key=True,
        default=lambda: str(uuid4()),
        comment="主键ID"
    )
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="创建时间"
    )
    
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="更新时间"
    )
    
    is_deleted: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="是否删除"
    )
    
    def to_dict(self, exclude_none: bool = True) -> Dict[str, Any]:
        """转换为字典"""
        result = {}
        for column in self.__table__.columns:
            value = getattr(self, column.name)
            if exclude_none and value is None:
                continue
            if isinstance(value, datetime):
                value = value.isoformat()
            result[column.name] = value
        return result
    
    def update_from_dict(self, data: Dict[str, Any]) -> None:
        """从字典更新属性"""
        for key, value in data.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(id={self.id})>"


class BaseModel(PydanticBaseModel):
    """Pydantic基础模型类（用于API请求/响应）"""
    
    model_config = ConfigDict(
        # 允许使用别名
        populate_by_name=True,
        # 验证赋值
        validate_assignment=True,
        # 使用枚举值
        use_enum_values=True,
        # 序列化时排除未设置的字段
        exclude_unset=True,
        # 序列化时排除None值
        exclude_none=True,
        # 允许额外字段
        extra="forbid",
        # JSON编码器
        json_encoders={
            datetime: lambda v: v.isoformat() if v else None
        }
    )
    
    def to_dict(self, exclude_none: bool = True, by_alias: bool = True) -> Dict[str, Any]:
        """转换为字典"""
        return self.model_dump(
            exclude_none=exclude_none,
            by_alias=by_alias
        )
    
    def to_json(self, exclude_none: bool = True, by_alias: bool = True) -> str:
        """转换为JSON字符串"""
        return self.model_dump_json(
            exclude_none=exclude_none,
            by_alias=by_alias
        )
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BaseModel":
        """从字典创建实例"""
        return cls(**data)


class FullModel(BaseModel):
    """完整模型类（包含通用字段）"""
    
    id: Optional[str] = Field(
        default=None,
        description="主键ID"
    )
    
    created_at: Optional[datetime] = Field(
        default=None,
        description="创建时间"
    )
    
    updated_at: Optional[datetime] = Field(
        default=None,
        description="更新时间"
    )
    
    is_deleted: Optional[bool] = Field(
        default=False,
        description="是否删除"
    )


class PaginationParams(BaseModel):
    """分页参数模型"""
    
    page: int = Field(
        default=1,
        ge=1,
        description="页码"
    )
    
    size: int = Field(
        default=20,
        ge=1,
        le=100,
        description="每页大小"
    )


class PaginatedResponse(BaseModel, Generic[T]):
    """分页响应模型"""
    
    items: List[T] = Field(
        ...,
        description="数据项列表"
    )
    
    total: int = Field(
        ...,
        description="总数量"
    )
    
    page: int = Field(
        ...,
        description="当前页码"
    )
    
    size: int = Field(
        ...,
        description="每页大小"
    )
    
    pages: int = Field(
        ...,
        description="总页数"
    )
    
    @property
    def offset(self) -> int:
        """计算偏移量"""
        return (self.page - 1) * self.size