from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Union
from enum import Enum

from sqlalchemy import Column, String, Text, Boolean, DateTime, Integer, Float, Enum as SQLEnum, JSON, ForeignKey
from sqlalchemy.dialects.mysql import VARCHAR, TEXT, LONGTEXT
from sqlalchemy.orm import relationship, Mapped, mapped_column
from pydantic import Field, validator, BaseModel as PydanticBaseModel

from .base import Base, BaseModel, FullModel


class TaskType(str, Enum):
    """任务类型"""
    DOCUMENT_UPLOAD = "document_upload"
    DOCUMENT_PROCESS = "document_process"
    DOCUMENT_ANALYSIS = "document_analysis"
    KNOWLEDGE_EXTRACTION = "knowledge_extraction"
    VECTOR_INDEXING = "vector_indexing"
    GRAPH_BUILDING = "graph_building"
    DATA_MIGRATION = "data_migration"
    SYSTEM_MAINTENANCE = "system_maintenance"
    USER_OPERATION = "user_operation"
    BATCH_PROCESSING = "batch_processing"
    SCHEDULED_TASK = "scheduled_task"
    WEBHOOK_TASK = "webhook_task"
    CUSTOM = "custom"


class TaskStatus(str, Enum):
    """任务状态"""
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"
    RETRY = "retry"
    SKIPPED = "skipped"


class TaskPriority(str, Enum):
    """任务优先级"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"
    CRITICAL = "critical"


class TaskCategory(str, Enum):
    """任务分类"""
    SYSTEM = "system"
    USER = "user"
    SCHEDULED = "scheduled"
    WEBHOOK = "webhook"
    BATCH = "batch"
    MAINTENANCE = "maintenance"


class TaskCategory(str, Enum):
    """任务分类"""
    DOCUMENT = "document"
    KNOWLEDGE = "knowledge"
    SEARCH = "search"
    ANALYSIS = "analysis"
    MAINTENANCE = "maintenance"
    INTEGRATION = "integration"
    NOTIFICATION = "notification"
    BACKUP = "backup"
    MONITORING = "monitoring"
    OTHER = "other"


class Task(Base):
    """任务SQLAlchemy模型"""
    

    __allow_unmapped__ = True
    __tablename__ = "task_queue"
    
    name: Any = Column(
        VARCHAR(200),
        nullable=False,
        comment="任务名称"
    )
    
    description: Any = Column(
        TEXT,
        nullable=True,
        comment="任务描述"
    )
    
    task_type: Any = Column(
        SQLEnum(TaskType),
        nullable=False,
        comment="任务类型"
    )
    
    category: Any = Column(
        SQLEnum(TaskCategory),
        default=TaskCategory.OTHER,
        nullable=False,
        comment="任务分类"
    )
    
    status: Any = Column(
        SQLEnum(TaskStatus),
        default=TaskStatus.PENDING,
        nullable=False,
        index=True,
        comment="任务状态"
    )
    
    priority: Any = Column(
        SQLEnum(TaskPriority),
        default=TaskPriority.NORMAL,
        nullable=False,
        comment="任务优先级"
    )
    
    user_id: Any = Column(
        String(36),
        nullable=False,
        index=True,
        comment="创建用户ID"
    )
    
    assigned_to: Any = Column(
        String(36),
        nullable=True,
        comment="分配给用户ID"
    )
    
    parent_task_id: Any = Column(
        String(36),
        ForeignKey('task_queue.id'),
        nullable=True,
        comment="父任务ID"
    )
    
    # 任务执行信息
    started_at: Any = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="开始时间"
    )
    
    completed_at: Any = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="完成时间"
    )
    
    scheduled_at: Any = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="计划执行时间"
    )
    
    deadline: Any = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="截止时间"
    )
    
    # 进度和结果
    progress: Any = Column(
        Float,
        default=0.0,
        nullable=False,
        comment="进度百分比(0-100)"
    )
    
    result: Any = Column(
        LONGTEXT,
        nullable=True,
        comment="任务结果(JSON)"
    )
    
    error_message: Any = Column(
        TEXT,
        nullable=True,
        comment="错误信息"
    )
    
    error_details: Any = Column(
        LONGTEXT,
        nullable=True,
        comment="错误详情(JSON)"
    )
    
    # 重试和超时
    retry_count: Any = Column(
        Integer,
        default=0,
        nullable=False,
        comment="重试次数"
    )
    
    max_retries: Any = Column(
        Integer,
        default=3,
        nullable=False,
        comment="最大重试次数"
    )
    
    timeout_seconds: Any = Column(
        Integer,
        nullable=True,
        comment="超时时间(秒)"
    )
    
    # 任务配置和参数
    parameters: Any = Column(
        LONGTEXT,
        nullable=True,
        comment="任务参数(JSON)"
    )
    
    configuration: Any = Column(
        LONGTEXT,
        nullable=True,
        comment="任务配置(JSON)"
    )
    
    # 资源和依赖
    resource_requirements: Any = Column(
        TEXT,
        nullable=True,
        comment="资源需求(JSON)"
    )
    
    dependencies: Any = Column(
        TEXT,
        nullable=True,
        comment="依赖任务ID列表(JSON)"
    )
    
    # 标签和元数据
    tags: Any = Column(
        TEXT,
        nullable=True,
        comment="标签列表(JSON)"
    )
    
    task_metadata: Any = Column(
        LONGTEXT,
        nullable=True,
        comment="元数据(JSON)"
    )
    
    # 关联关系
    parent_task = relationship(
        "Task",
        remote_side="Task.id",
        backref="subtasks"
    )
    
    # 任务结果关系
    results = relationship("TaskResult", back_populates="task", cascade="all, delete-orphan")
    
    def is_pending(self) -> bool:
        """是否待处理"""
        return self.status == TaskStatus.PENDING
    
    def is_running(self) -> bool:
        """是否运行中"""
        return self.status == TaskStatus.RUNNING
    
    def is_completed(self) -> bool:
        """是否已完成"""
        return self.status == TaskStatus.COMPLETED
    
    def is_failed(self) -> bool:
        """是否失败"""
        return self.status == TaskStatus.FAILED
    
    def is_cancelled(self) -> bool:
        """是否已取消"""
        return self.status == TaskStatus.CANCELLED
    
    def is_finished(self) -> bool:
        """是否已结束"""
        return self.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]
    
    def can_retry(self) -> bool:
        """是否可以重试"""
        return self.is_failed() and self.retry_count < self.max_retries
    
    def is_overdue(self) -> bool:
        """是否超期"""
        if self.deadline is None:
            return False
        return datetime.now() > self.deadline and not self.is_finished()
    
    def get_duration(self) -> Optional[timedelta]:
        """获取执行时长"""
        if self.started_at is None:
            return None
        end_time = self.completed_at or datetime.now()
        return end_time - self.started_at
    
    def get_remaining_time(self) -> Optional[timedelta]:
        """获取剩余时间"""
        if self.deadline is None:
            return None
        if self.is_finished():
            return timedelta(0)
        return self.deadline - datetime.now()
    
    def start(self) -> None:
        """开始任务"""
        self.status = TaskStatus.RUNNING
        self.started_at = datetime.now()
    
    def complete(self, result: Optional[Dict[str, Any]] = None) -> None:
        """完成任务"""
        self.status = TaskStatus.COMPLETED
        self.completed_at = datetime.now()
        self.progress = 100.0
        if result:
            import json
            self.result = json.dumps(result)
    
    def fail(self, error_message: str, error_details: Optional[Dict[str, Any]] = None) -> None:
        """任务失败"""
        self.status = TaskStatus.FAILED
        self.completed_at = datetime.now()
        self.error_message = error_message
        if error_details:
            import json
            self.error_details = json.dumps(error_details)
    
    def cancel(self, reason: Optional[str] = None) -> None:
        """取消任务"""
        self.status = TaskStatus.CANCELLED
        self.completed_at = datetime.now()
        if reason:
            self.error_message = f"任务已取消: {reason}"
    
    def pause(self) -> None:
        """暂停任务"""
        if self.is_running():
            self.status = TaskStatus.PAUSED
    
    def resume(self) -> None:
        """恢复任务"""
        if self.status == TaskStatus.PAUSED:
            self.status = TaskStatus.RUNNING
    
    def retry(self) -> None:
        """重试任务"""
        if self.can_retry():
            self.status = TaskStatus.RETRY
            self.retry_count += 1
            self.error_message = None
            self.error_details = None
    
    def update_progress(self, progress: float) -> None:
        """更新进度"""
        self.progress = max(0.0, min(100.0, progress))


class TaskLog(Base):
    """任务日志SQLAlchemy模型"""
    

    __allow_unmapped__ = True
    __tablename__ = "task_logs"
    
    task_id: Any = Column(
        String(36),
        ForeignKey('task_queue.id'),
        nullable=False,
        index=True,
        comment="任务ID"
    )
    
    level: Any = Column(
        VARCHAR(20),
        nullable=False,
        comment="日志级别"
    )
    
    message: Any = Column(
        TEXT,
        nullable=False,
        comment="日志消息"
    )
    
    details: Any = Column(
        LONGTEXT,
        nullable=True,
        comment="详细信息(JSON)"
    )
    
    timestamp: Any = Column(
        DateTime(timezone=True),
        default=datetime.now,
        nullable=False,
        comment="时间戳"
    )
    
    # 关联关系
    task = relationship("Task", backref="logs")


class TaskDependency(Base):
    """任务依赖SQLAlchemy模型"""
    

    __allow_unmapped__ = True
    __tablename__ = "task_dependencies"
    
    task_id: Any = Column(
        String(36),
        ForeignKey('task_queue.id'),
        nullable=False,
        comment="任务ID"
    )
    
    depends_on_task_id: Any = Column(
        String(36),
        ForeignKey('task_queue.id'),
        nullable=False,
        comment="依赖的任务ID"
    )
    
    dependency_type: Any = Column(
        VARCHAR(50),
        default="finish_to_start",
        nullable=False,
        comment="依赖类型"
    )
    
    # 关联关系
    task = relationship(
        "Task",
        foreign_keys=[task_id],
        backref="task_dependencies"
    )
    
    depends_on_task = relationship(
        "Task",
        foreign_keys=[depends_on_task_id]
    )


# Pydantic模型用于API
class TaskBase(BaseModel):
    """任务基础模型"""
    
    name: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="任务名称"
    )
    
    description: Optional[str] = Field(
        default=None,
        description="任务描述"
    )
    
    task_type: TaskType = Field(
        ...,
        description="任务类型"
    )
    
    category: TaskCategory = Field(
        default=TaskCategory.OTHER,
        description="任务分类"
    )
    
    priority: TaskPriority = Field(
        default=TaskPriority.NORMAL,
        description="任务优先级"
    )
    
    assigned_to: Optional[str] = Field(
        default=None,
        description="分配给用户ID"
    )
    
    parent_task_id: Optional[str] = Field(
        default=None,
        description="父任务ID"
    )
    
    scheduled_at: Optional[datetime] = Field(
        default=None,
        description="计划执行时间"
    )
    
    deadline: Optional[datetime] = Field(
        default=None,
        description="截止时间"
    )
    
    max_retries: int = Field(
        default=3,
        ge=0,
        le=10,
        description="最大重试次数"
    )
    
    timeout_seconds: Optional[int] = Field(
        default=None,
        ge=1,
        description="超时时间(秒)"
    )
    
    parameters: Optional[Dict[str, Any]] = Field(
        default=None,
        description="任务参数"
    )
    
    configuration: Optional[Dict[str, Any]] = Field(
        default=None,
        description="任务配置"
    )
    
    tags: Optional[List[str]] = Field(
        default=None,
        description="标签列表"
    )

class TaskBatch(BaseModel):
    """任务批次模型"""
    id: Optional[str] = Field(default=None, description="批次ID")
    name: str = Field(..., description="批次名称")
    description: Optional[str] = Field(default=None, description="批次描述")
    task_ids: List[str] = Field(default_factory=list, description="任务ID列表")
    status: TaskStatus = Field(default=TaskStatus.PENDING, description="批次状态")
    created_at: Optional[datetime] = Field(default=None, description="创建时间")
    updated_at: Optional[datetime] = Field(default=None, description="更新时间")

class RetryPolicy(BaseModel):
    """重试策略模型"""
    max_retries: int = Field(default=3, description="最大重试次数")
    retry_delay: int = Field(default=60, description="重试延迟（秒）")
    backoff_factor: float = Field(default=2.0, description="退避因子")
    max_delay: int = Field(default=3600, description="最大延迟（秒）")

class TaskSchedule(BaseModel):
    """任务调度模型"""
    id: Optional[str] = Field(default=None, description="调度ID")
    task_id: str = Field(..., description="任务ID")
    cron_expression: str = Field(..., description="Cron表达式")
    timezone: str = Field(default="UTC", description="时区")
    enabled: bool = Field(default=True, description="是否启用")
    next_run: Optional[datetime] = Field(default=None, description="下次运行时间")

class TaskResource(BaseModel):
    """任务资源模型"""
    cpu_limit: Optional[float] = Field(default=None, description="CPU限制")
    memory_limit: Optional[int] = Field(default=None, description="内存限制（MB）")
    disk_limit: Optional[int] = Field(default=None, description="磁盘限制（MB）")
    gpu_required: bool = Field(default=False, description="是否需要GPU")

class TaskProgress(BaseModel):
    """任务进度模型"""
    task_id: str = Field(..., description="任务ID")
    current_step: int = Field(default=0, description="当前步骤")
    total_steps: int = Field(default=1, description="总步骤数")
    percentage: float = Field(default=0.0, description="完成百分比")
    message: Optional[str] = Field(default=None, description="进度消息")
    updated_at: Optional[datetime] = Field(default=None, description="更新时间")


class TaskCreate(TaskBase):
    """创建任务模型"""
    pass


class TaskUpdate(BaseModel):
    """更新任务模型"""
    
    name: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=200,
        description="任务名称"
    )
    
    description: Optional[str] = Field(
        default=None,
        description="任务描述"
    )
    
    status: Optional[TaskStatus] = Field(
        default=None,
        description="任务状态"
    )
    
    priority: Optional[TaskPriority] = Field(
        default=None,
        description="任务优先级"
    )
    
    assigned_to: Optional[str] = Field(
        default=None,
        description="分配给用户ID"
    )
    
    scheduled_at: Optional[datetime] = Field(
        default=None,
        description="计划执行时间"
    )
    
    deadline: Optional[datetime] = Field(
        default=None,
        description="截止时间"
    )
    
    progress: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=100.0,
        description="进度百分比"
    )
    
    parameters: Optional[Dict[str, Any]] = Field(
        default=None,
        description="任务参数"
    )
    
    configuration: Optional[Dict[str, Any]] = Field(
        default=None,
        description="任务配置"
    )
    
    tags: Optional[List[str]] = Field(
        default=None,
        description="标签列表"
    )


class TaskResponse(FullModel):
    """任务响应模型"""
    
    name: str = Field(
        ...,
        description="任务名称"
    )
    
    description: Optional[str] = Field(
        default=None,
        description="任务描述"
    )
    
    task_type: TaskType = Field(
        ...,
        description="任务类型"
    )
    
    category: TaskCategory = Field(
        ...,
        description="任务分类"
    )
    
    status: TaskStatus = Field(
        ...,
        description="任务状态"
    )
    
    priority: TaskPriority = Field(
        ...,
        description="任务优先级"
    )
    
    user_id: str = Field(
        ...,
        description="创建用户ID"
    )
    
    assigned_to: Optional[str] = Field(
        default=None,
        description="分配给用户ID"
    )
    
    parent_task_id: Optional[str] = Field(
        default=None,
        description="父任务ID"
    )
    
    started_at: Optional[datetime] = Field(
        default=None,
        description="开始时间"
    )
    
    completed_at: Optional[datetime] = Field(
        default=None,
        description="完成时间"
    )
    
    scheduled_at: Optional[datetime] = Field(
        default=None,
        description="计划执行时间"
    )
    
    deadline: Optional[datetime] = Field(
        default=None,
        description="截止时间"
    )
    
    progress: float = Field(
        default=0.0,
        description="进度百分比"
    )
    
    retry_count: int = Field(
        default=0,
        description="重试次数"
    )
    
    max_retries: int = Field(
        default=3,
        description="最大重试次数"
    )
    
    timeout_seconds: Optional[int] = Field(
        default=None,
        description="超时时间(秒)"
    )
    
    error_message: Optional[str] = Field(
        default=None,
        description="错误信息"
    )
    
    result: Optional[Dict[str, Any]] = Field(
        default=None,
        description="任务结果"
    )
    
    parameters: Optional[Dict[str, Any]] = Field(
        default=None,
        description="任务参数"
    )
    
    tags: Optional[List[str]] = Field(
        default=None,
        description="标签列表"
    )


class TaskLogCreate(BaseModel):
    """创建任务日志模型"""
    
    task_id: str = Field(
        ...,
        description="任务ID"
    )
    
    level: str = Field(
        ...,
        description="日志级别"
    )
    
    message: str = Field(
        ...,
        description="日志消息"
    )
    
    details: Optional[Dict[str, Any]] = Field(
        default=None,
        description="详细信息"
    )


class TaskLogResponse(FullModel):
    """任务日志响应模型"""
    
    task_id: str = Field(
        ...,
        description="任务ID"
    )
    
    level: str = Field(
        ...,
        description="日志级别"
    )
    
    message: str = Field(
        ...,
        description="日志消息"
    )
    
    details: Optional[Dict[str, Any]] = Field(
        default=None,
        description="详细信息"
    )
    
    timestamp: datetime = Field(
        ...,
        description="时间戳"
    )


class TaskStats(BaseModel):
    """任务统计模型"""
    
    total_tasks: int = Field(
        default=0,
        description="总任务数"
    )
    
    pending_tasks: int = Field(
        default=0,
        description="待处理任务数"
    )
    
    running_tasks: int = Field(
        default=0,
        description="运行中任务数"
    )
    
    completed_tasks: int = Field(
        default=0,
        description="已完成任务数"
    )
    
    failed_tasks: int = Field(
        default=0,
        description="失败任务数"
    )
    
    cancelled_tasks: int = Field(
        default=0,
        description="已取消任务数"
    )
    
    success_rate: float = Field(
        default=0.0,
        description="成功率"
    )
    
    average_duration: Optional[float] = Field(
        default=None,
        description="平均执行时长(秒)"
    )


class TaskFilter(BaseModel):
    """任务过滤模型"""
    
    task_type: Optional[TaskType] = Field(
        default=None,
        description="任务类型"
    )
    
    category: Optional[TaskCategory] = Field(
        default=None,
        description="任务分类"
    )
    
    status: Optional[TaskStatus] = Field(
        default=None,
        description="任务状态"
    )
    
    priority: Optional[TaskPriority] = Field(
        default=None,
        description="任务优先级"
    )
    
    user_id: Optional[str] = Field(
        default=None,
        description="创建用户ID"
    )
    
    assigned_to: Optional[str] = Field(
        default=None,
        description="分配给用户ID"
    )
    
    created_after: Optional[datetime] = Field(
        default=None,
        description="创建时间之后"
    )


class TaskResult(Base):
    """任务结果模型"""
    
    __tablename__ = "task_results"
    
    task_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("task_queue.id"),
        nullable=False,
        comment="任务ID"
    )
    
    result_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="结果类型"
    )
    
    result_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
        comment="结果数据"
    )
    
    file_path: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="结果文件路径"
    )
    
    file_size: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="文件大小"
    )
    
    checksum: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
        comment="文件校验和"
    )
    
    # 关系
    task = relationship("Task", back_populates="results")
    
    created_before: Optional[datetime] = Field(
        default=None,
        description="创建时间之前"
    )
    
    tags: Optional[List[str]] = Field(
        default=None,
        description="标签列表"
    )