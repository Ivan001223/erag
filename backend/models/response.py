"""响应相关数据模型"""

from datetime import datetime
from typing import Optional, List, Dict, Any, Generic, TypeVar, Union
from enum import Enum

from pydantic import Field, validator
from pydantic.generics import GenericModel

from .base import BaseModel


T = TypeVar('T')


class ResponseStatus(str, Enum):
    """响应状态"""
    SUCCESS = "success"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class ErrorCode(str, Enum):
    """错误代码"""
    # 通用错误
    UNKNOWN_ERROR = "UNKNOWN_ERROR"
    INTERNAL_SERVER_ERROR = "INTERNAL_SERVER_ERROR"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    
    # 请求错误
    BAD_REQUEST = "BAD_REQUEST"
    INVALID_PARAMETER = "INVALID_PARAMETER"
    MISSING_PARAMETER = "MISSING_PARAMETER"
    INVALID_FORMAT = "INVALID_FORMAT"
    REQUEST_TOO_LARGE = "REQUEST_TOO_LARGE"
    
    # 认证和授权错误
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    INVALID_TOKEN = "INVALID_TOKEN"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"
    INSUFFICIENT_PERMISSIONS = "INSUFFICIENT_PERMISSIONS"
    
    # 资源错误
    NOT_FOUND = "NOT_FOUND"
    RESOURCE_EXISTS = "RESOURCE_EXISTS"
    RESOURCE_CONFLICT = "RESOURCE_CONFLICT"
    RESOURCE_LOCKED = "RESOURCE_LOCKED"
    
    # 业务逻辑错误
    VALIDATION_ERROR = "VALIDATION_ERROR"
    BUSINESS_RULE_VIOLATION = "BUSINESS_RULE_VIOLATION"
    OPERATION_NOT_ALLOWED = "OPERATION_NOT_ALLOWED"
    QUOTA_EXCEEDED = "QUOTA_EXCEEDED"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    
    # 数据错误
    DATA_INTEGRITY_ERROR = "DATA_INTEGRITY_ERROR"
    DUPLICATE_ENTRY = "DUPLICATE_ENTRY"
    FOREIGN_KEY_CONSTRAINT = "FOREIGN_KEY_CONSTRAINT"
    
    # 文件错误
    FILE_NOT_FOUND = "FILE_NOT_FOUND"
    FILE_TOO_LARGE = "FILE_TOO_LARGE"
    INVALID_FILE_TYPE = "INVALID_FILE_TYPE"
    FILE_UPLOAD_FAILED = "FILE_UPLOAD_FAILED"
    
    # 外部服务错误
    EXTERNAL_SERVICE_ERROR = "EXTERNAL_SERVICE_ERROR"
    NETWORK_ERROR = "NETWORK_ERROR"
    TIMEOUT_ERROR = "TIMEOUT_ERROR"
    
    # 任务错误
    TASK_NOT_FOUND = "TASK_NOT_FOUND"
    TASK_ALREADY_RUNNING = "TASK_ALREADY_RUNNING"
    TASK_FAILED = "TASK_FAILED"
    TASK_CANCELLED = "TASK_CANCELLED"


class ErrorDetail(BaseModel):
    """错误详情"""
    
    field: Optional[str] = Field(
        default=None,
        description="错误字段"
    )
    message: str = Field(
        ...,
        description="错误消息"
    )
    code: Optional[str] = Field(
        default=None,
        description="错误代码"
    )
    value: Optional[Any] = Field(
        default=None,
        description="错误值"
    )
    context: Optional[Dict[str, Any]] = Field(
        default=None,
        description="错误上下文"
    )


class APIResponse(GenericModel, Generic[T]):
    """通用API响应模型"""
    
    status: ResponseStatus = Field(
        ...,
        description="响应状态"
    )
    message: str = Field(
        ...,
        description="响应消息"
    )
    data: Optional[T] = Field(
        default=None,
        description="响应数据"
    )
    error_code: Optional[ErrorCode] = Field(
        default=None,
        description="错误代码"
    )
    error_details: Optional[List[ErrorDetail]] = Field(
        default=None,
        description="错误详情列表"
    )
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="响应时间戳"
    )
    request_id: Optional[str] = Field(
        default=None,
        description="请求ID"
    )
    trace_id: Optional[str] = Field(
        default=None,
        description="追踪ID"
    )
    execution_time: Optional[float] = Field(
        default=None,
        ge=0,
        description="执行时间（秒）"
    )
    
    class Config:
        arbitrary_types_allowed = True
    
    def is_success(self) -> bool:
        """是否成功"""
        return self.status == ResponseStatus.SUCCESS
    
    def is_error(self) -> bool:
        """是否错误"""
        return self.status == ResponseStatus.ERROR
    
    def add_error_detail(self, field: Optional[str], message: str, code: Optional[str] = None, value: Optional[Any] = None, context: Optional[Dict[str, Any]] = None) -> None:
        """添加错误详情"""
        if self.error_details is None:
            self.error_details = []
        
        error_detail = ErrorDetail(
            field=field,
            message=message,
            code=code,
            value=value,
            context=context
        )
        self.error_details.append(error_detail)
    
    def get_error_messages(self) -> List[str]:
        """获取所有错误消息"""
        if not self.error_details:
            return []
        return [detail.message for detail in self.error_details]
    
    def get_field_errors(self, field: str) -> List[ErrorDetail]:
        """获取指定字段的错误"""
        if not self.error_details:
            return []
        return [detail for detail in self.error_details if detail.field == field]


class PaginationMeta(BaseModel):
    """分页元数据"""
    
    page: int = Field(
        ...,
        ge=1,
        description="当前页码"
    )
    page_size: int = Field(
        ...,
        ge=1,
        le=1000,
        description="每页大小"
    )
    total_items: int = Field(
        ...,
        ge=0,
        description="总项目数"
    )
    total_pages: int = Field(
        ...,
        ge=0,
        description="总页数"
    )
    has_next: bool = Field(
        ...,
        description="是否有下一页"
    )
    has_prev: bool = Field(
        ...,
        description="是否有上一页"
    )
    next_page: Optional[int] = Field(
        default=None,
        description="下一页页码"
    )
    prev_page: Optional[int] = Field(
        default=None,
        description="上一页页码"
    )
    
    @validator('total_pages', always=True)
    def calculate_total_pages(cls, v, values):
        """计算总页数"""
        page_size = values.get('page_size', 1)
        total_items = values.get('total_items', 0)
        if page_size <= 0:
            return 0
        return (total_items + page_size - 1) // page_size
    
    @validator('has_next', always=True)
    def calculate_has_next(cls, v, values):
        """计算是否有下一页"""
        page = values.get('page', 1)
        total_pages = values.get('total_pages', 0)
        return page < total_pages
    
    @validator('has_prev', always=True)
    def calculate_has_prev(cls, v, values):
        """计算是否有上一页"""
        page = values.get('page', 1)
        return page > 1
    
    @validator('next_page', always=True)
    def calculate_next_page(cls, v, values):
        """计算下一页页码"""
        page = values.get('page', 1)
        has_next = values.get('has_next', False)
        return page + 1 if has_next else None
    
    @validator('prev_page', always=True)
    def calculate_prev_page(cls, v, values):
        """计算上一页页码"""
        page = values.get('page', 1)
        has_prev = values.get('has_prev', False)
        return page - 1 if has_prev else None
    
    def get_offset(self) -> int:
        """获取偏移量"""
        return (self.page - 1) * self.page_size
    
    def get_limit(self) -> int:
        """获取限制数量"""
        return self.page_size


class PaginatedResponse(GenericModel, Generic[T]):
    """分页响应模型"""
    
    status: ResponseStatus = Field(
        default=ResponseStatus.SUCCESS,
        description="响应状态"
    )
    message: str = Field(
        default="Success",
        description="响应消息"
    )
    data: List[T] = Field(
        default_factory=list,
        description="数据列表"
    )
    pagination: PaginationMeta = Field(
        ...,
        description="分页信息"
    )
    error_code: Optional[ErrorCode] = Field(
        default=None,
        description="错误代码"
    )
    error_details: Optional[List[ErrorDetail]] = Field(
        default=None,
        description="错误详情列表"
    )
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="响应时间戳"
    )
    request_id: Optional[str] = Field(
        default=None,
        description="请求ID"
    )
    trace_id: Optional[str] = Field(
        default=None,
        description="追踪ID"
    )
    execution_time: Optional[float] = Field(
        default=None,
        ge=0,
        description="执行时间（秒）"
    )
    
    class Config:
        arbitrary_types_allowed = True
    
    def is_success(self) -> bool:
        """是否成功"""
        return self.status == ResponseStatus.SUCCESS
    
    def is_empty(self) -> bool:
        """是否为空"""
        return len(self.data) == 0
    
    def get_item_count(self) -> int:
        """获取当前页项目数"""
        return len(self.data)


class SuccessResponse(APIResponse[T]):
    """成功响应"""
    
    status: ResponseStatus = Field(
        default=ResponseStatus.SUCCESS,
        description="响应状态"
    )
    
    def __init__(self, data: Optional[T] = None, message: str = "Success", **kwargs):
        super().__init__(
            status=ResponseStatus.SUCCESS,
            message=message,
            data=data,
            **kwargs
        )


class ErrorResponse(APIResponse[None]):
    """错误响应"""
    
    status: ResponseStatus = Field(
        default=ResponseStatus.ERROR,
        description="响应状态"
    )
    data: None = Field(
        default=None,
        description="数据（错误响应无数据）"
    )
    
    def __init__(self, message: str, error_code: Optional[ErrorCode] = None, error_details: Optional[List[ErrorDetail]] = None, **kwargs):
        super().__init__(
            status=ResponseStatus.ERROR,
            message=message,
            data=None,
            error_code=error_code,
            error_details=error_details,
            **kwargs
        )


class WarningResponse(APIResponse[T]):
    """警告响应"""
    
    status: ResponseStatus = Field(
        default=ResponseStatus.WARNING,
        description="响应状态"
    )
    
    def __init__(self, data: Optional[T] = None, message: str = "Warning", **kwargs):
        super().__init__(
            status=ResponseStatus.WARNING,
            message=message,
            data=data,
            **kwargs
        )


class InfoResponse(APIResponse[T]):
    """信息响应"""
    
    status: ResponseStatus = Field(
        default=ResponseStatus.INFO,
        description="响应状态"
    )
    
    def __init__(self, data: Optional[T] = None, message: str = "Info", **kwargs):
        super().__init__(
            status=ResponseStatus.INFO,
            message=message,
            data=data,
            **kwargs
        )


class HealthCheckResponse(BaseModel):
    """健康检查响应"""
    
    status: str = Field(
        ...,
        description="服务状态"
    )
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="检查时间"
    )
    version: Optional[str] = Field(
        default=None,
        description="服务版本"
    )
    uptime: Optional[float] = Field(
        default=None,
        description="运行时间（秒）"
    )
    dependencies: Dict[str, Dict[str, Any]] = Field(
        default_factory=dict,
        description="依赖服务状态"
    )
    metrics: Dict[str, Any] = Field(
        default_factory=dict,
        description="性能指标"
    )
    
    def add_dependency(self, name: str, status: str, details: Optional[Dict[str, Any]] = None) -> None:
        """添加依赖服务状态"""
        self.dependencies[name] = {
            "status": status,
            "details": details or {}
        }
    
    def add_metric(self, name: str, value: Any) -> None:
        """添加性能指标"""
        self.metrics[name] = value
    
    def is_healthy(self) -> bool:
        """是否健康"""
        if self.status.lower() != "healthy":
            return False
        
        # 检查依赖服务
        for dep_name, dep_info in self.dependencies.items():
            if dep_info.get("status", "").lower() not in ["healthy", "ok", "up"]:
                return False
        
        return True


class BatchResponse(BaseModel):
    """批量操作响应"""
    
    total_count: int = Field(
        ...,
        ge=0,
        description="总数量"
    )
    success_count: int = Field(
        ...,
        ge=0,
        description="成功数量"
    )
    failed_count: int = Field(
        ...,
        ge=0,
        description="失败数量"
    )
    skipped_count: int = Field(
        default=0,
        ge=0,
        description="跳过数量"
    )
    results: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="详细结果"
    )
    errors: List[ErrorDetail] = Field(
        default_factory=list,
        description="错误列表"
    )
    execution_time: Optional[float] = Field(
        default=None,
        ge=0,
        description="执行时间（秒）"
    )
    
    @validator('failed_count', always=True)
    def calculate_failed_count(cls, v, values):
        """计算失败数量"""
        total = values.get('total_count', 0)
        success = values.get('success_count', 0)
        skipped = values.get('skipped_count', 0)
        return total - success - skipped
    
    def get_success_rate(self) -> float:
        """获取成功率"""
        if self.total_count == 0:
            return 0.0
        return (self.success_count / self.total_count) * 100
    
    def get_failure_rate(self) -> float:
        """获取失败率"""
        if self.total_count == 0:
            return 0.0
        return (self.failed_count / self.total_count) * 100
    
    def is_all_success(self) -> bool:
        """是否全部成功"""
        return self.failed_count == 0 and self.success_count == self.total_count
    
    def is_partial_success(self) -> bool:
        """是否部分成功"""
        return self.success_count > 0 and self.failed_count > 0
    
    def add_result(self, item_id: str, status: str, data: Optional[Any] = None, error: Optional[str] = None) -> None:
        """添加结果"""
        result = {
            "item_id": item_id,
            "status": status,
            "data": data,
            "error": error
        }
        self.results.append(result)
    
    def add_error(self, item_id: str, message: str, code: Optional[str] = None) -> None:
        """添加错误"""
        error = ErrorDetail(
            field=item_id,
            message=message,
            code=code
        )
        self.errors.append(error)


# 便捷函数
def success_response(data: Optional[T] = None, message: str = "Success", **kwargs) -> SuccessResponse[T]:
    """创建成功响应"""
    return SuccessResponse(data=data, message=message, **kwargs)


def error_response(message: str, error_code: Optional[ErrorCode] = None, error_details: Optional[List[ErrorDetail]] = None, **kwargs) -> ErrorResponse:
    """创建错误响应"""
    return ErrorResponse(
        message=message,
        error_code=error_code,
        error_details=error_details,
        **kwargs
    )


def warning_response(data: Optional[T] = None, message: str = "Warning", **kwargs) -> WarningResponse[T]:
    """创建警告响应"""
    return WarningResponse(data=data, message=message, **kwargs)


def info_response(data: Optional[T] = None, message: str = "Info", **kwargs) -> InfoResponse[T]:
    """创建信息响应"""
    return InfoResponse(data=data, message=message, **kwargs)


def paginated_response(data: List[T], pagination: PaginationMeta, message: str = "Success", **kwargs) -> PaginatedResponse[T]:
    """创建分页响应"""
    return PaginatedResponse(
        data=data,
        pagination=pagination,
        message=message,
        **kwargs
    )


def validation_error_response(errors: List[ErrorDetail], message: str = "Validation failed") -> ErrorResponse:
    """创建验证错误响应"""
    return ErrorResponse(
        message=message,
        error_code=ErrorCode.VALIDATION_ERROR,
        error_details=errors
    )


def not_found_response(resource: str = "Resource", resource_id: Optional[str] = None) -> ErrorResponse:
    """创建资源未找到响应"""
    message = f"{resource} not found"
    if resource_id:
        message += f" (ID: {resource_id})"
    
    return ErrorResponse(
        message=message,
        error_code=ErrorCode.NOT_FOUND
    )


def unauthorized_response(message: str = "Unauthorized access") -> ErrorResponse:
    """创建未授权响应"""
    return ErrorResponse(
        message=message,
        error_code=ErrorCode.UNAUTHORIZED
    )


def forbidden_response(message: str = "Access forbidden") -> ErrorResponse:
    """创建禁止访问响应"""
    return ErrorResponse(
        message=message,
        error_code=ErrorCode.FORBIDDEN
    )


def internal_error_response(message: str = "Internal server error") -> ErrorResponse:
    """创建内部错误响应"""
    return ErrorResponse(
        message=message,
        error_code=ErrorCode.INTERNAL_SERVER_ERROR
    )