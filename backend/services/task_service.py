"""任务管理服务"""

import asyncio
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Callable
from uuid import uuid4
from enum import Enum

from ..config import get_settings
from ..config.constants import (
    TaskStatus, TaskPriority, TaskCategory, ExecutionMode,
    TASK_MAX_RETRIES, TASK_RETRY_DELAY, TASK_TIMEOUT
)
from ..connectors import RedisClient
from ..models import (
    Task, TaskResult, TaskBatch, RetryPolicy, TaskDependency,
    TaskSchedule, TaskResource, TaskProgress,
    APIResponse, PaginatedResponse, ErrorResponse
)
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from ..utils import get_logger


class TaskExecutor:
    """任务执行器基类"""
    
    async def execute(self, task: Task) -> TaskResult:
        """执行任务"""
        raise NotImplementedError
    
    async def validate(self, task: Task) -> bool:
        """验证任务参数"""
        return True
    
    async def estimate_duration(self, task: Task) -> Optional[float]:
        """估算任务执行时间（秒）"""
        return None


class DocumentProcessingExecutor(TaskExecutor):
    """文档处理任务执行器"""
    
    def __init__(self, document_service):
        self.document_service = document_service
    
    async def execute(self, task: Task) -> TaskResult:
        """执行文档处理任务"""
        try:
            document_id = task.parameters.get("document_id")
            if not document_id:
                raise ValueError("Missing document_id parameter")
            
            # 执行文档处理
            result = await self.document_service.process_document(document_id)
            
            if result.is_success():
                return TaskResult(
                    id=str(uuid4()),
                    task_id=task.id,
                    status=TaskStatus.COMPLETED,
                    result_data=result.data,
                    execution_time=0.0,  # 应该计算实际执行时间
                    metadata={"processing_result": result.dict()}
                )
            else:
                return TaskResult(
                    id=str(uuid4()),
                    task_id=task.id,
                    status=TaskStatus.FAILED,
                    error_message=result.message,
                    execution_time=0.0,
                    metadata={"error_details": result.dict()}
                )
                
        except Exception as e:
            return TaskResult(
                id=str(uuid4()),
                task_id=task.id,
                status=TaskStatus.FAILED,
                error_message=str(e),
                execution_time=0.0,
                metadata={"exception": str(e)}
            )
    
    async def estimate_duration(self, task: Task) -> Optional[float]:
        """估算文档处理时间"""
        # 根据文档大小估算处理时间
        file_size = task.parameters.get("file_size", 0)
        if file_size > 0:
            # 假设每MB需要10秒处理时间
            return max(30, file_size / (1024 * 1024) * 10)
        return 300  # 默认5分钟


class KnowledgeExtractionExecutor(TaskExecutor):
    """知识提取任务执行器"""
    
    def __init__(self, knowledge_service):
        self.knowledge_service = knowledge_service
    
    async def execute(self, task: Task) -> TaskResult:
        """执行知识提取任务"""
        try:
            text = task.parameters.get("text")
            document_id = task.parameters.get("document_id")
            chunk_id = task.parameters.get("chunk_id")
            
            if not text:
                raise ValueError("Missing text parameter")
            
            # 提取实体
            entities_result = await self.knowledge_service.extract_entities_from_text(
                text=text,
                document_id=document_id,
                chunk_id=chunk_id
            )
            
            if not entities_result.is_success():
                raise Exception(f"Entity extraction failed: {entities_result.message}")
            
            # 提取关系
            relations_result = await self.knowledge_service.extract_relations_from_text(
                text=text,
                entities=entities_result.data,
                document_id=document_id,
                chunk_id=chunk_id
            )
            
            if not relations_result.is_success():
                raise Exception(f"Relation extraction failed: {relations_result.message}")
            
            return TaskResult(
                id=str(uuid4()),
                task_id=task.id,
                status=TaskStatus.COMPLETED,
                result_data={
                    "entities": [entity.dict() for entity in entities_result.data],
                    "relations": [relation.dict() for relation in relations_result.data]
                },
                execution_time=0.0,
                metadata={
                    "entities_count": len(entities_result.data),
                    "relations_count": len(relations_result.data)
                }
            )
            
        except Exception as e:
            return TaskResult(
                id=str(uuid4()),
                task_id=task.id,
                status=TaskStatus.FAILED,
                error_message=str(e),
                execution_time=0.0,
                metadata={"exception": str(e)}
            )
    
    async def estimate_duration(self, task: Task) -> Optional[float]:
        """估算知识提取时间"""
        text = task.parameters.get("text", "")
        # 根据文本长度估算处理时间
        text_length = len(text)
        if text_length > 0:
            # 假设每1000字符需要5秒处理时间
            return max(10, text_length / 1000 * 5)
        return 60  # 默认1分钟


class TaskService:
    """任务管理服务"""
    
    def __init__(
        self,
        db: Session,
        redis_client: RedisClient
    ):
        self.db = db
        self.redis = redis_client  # 保留用于任务队列和缓存
        self.settings = get_settings()
        self.logger = get_logger(__name__)
        
        # 任务执行器注册表
        self.executors: Dict[TaskCategory, TaskExecutor] = {}
        
        # 任务队列
        self.task_queues: Dict[TaskPriority, str] = {
            TaskPriority.HIGH: "task_queue:high",
            TaskPriority.MEDIUM: "task_queue:medium",
            TaskPriority.LOW: "task_queue:low"
        }
        
        # 运行中的任务
        self.running_tasks: Dict[str, asyncio.Task] = {}
        
        # 任务统计
        self.task_stats = {
            "total_created": 0,
            "total_completed": 0,
            "total_failed": 0,
            "total_cancelled": 0
        }
    
    def register_executor(self, category: TaskCategory, executor: TaskExecutor):
        """注册任务执行器"""
        self.executors[category] = executor
        self.logger.info(f"Registered executor for category: {category.value}")
    
    async def create_task(
        self,
        name: str,
        category: TaskCategory,
        parameters: Dict[str, Any],
        priority: TaskPriority = TaskPriority.MEDIUM,
        execution_mode: ExecutionMode = ExecutionMode.ASYNC,
        retry_policy: Optional[RetryPolicy] = None,
        schedule: Optional[TaskSchedule] = None,
        dependencies: Optional[List[TaskDependency]] = None,
        resource_requirements: Optional[TaskResource] = None,
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> APIResponse[Task]:
        """创建任务"""
        try:
            # 验证任务类别是否有对应的执行器
            if category not in self.executors:
                return ErrorResponse(
                    message=f"No executor registered for category: {category.value}",
                    error_code="EXECUTOR_NOT_FOUND"
                )
            
            # 创建任务对象
            task = Task(
                id=str(uuid4()),
                name=name,
                category=category,
                status=TaskStatus.PENDING,
                priority=priority,
                execution_mode=execution_mode,
                parameters=parameters,
                retry_policy=retry_policy or RetryPolicy(),
                schedule=schedule,
                dependencies=dependencies or [],
                resource_requirements=resource_requirements or TaskResource(),
                progress=TaskProgress(),
                created_by=user_id,
                metadata=metadata or {}
            )
            
            # 验证任务参数
            executor = self.executors[category]
            if not await executor.validate(task):
                return ErrorResponse(
                    message="Task validation failed",
                    error_code="VALIDATION_FAILED"
                )
            
            # 估算执行时间
            estimated_duration = await executor.estimate_duration(task)
            if estimated_duration:
                task.estimated_duration = estimated_duration
            
            # 保存任务到数据库
            try:
                self.db.add(task)
                self.db.commit()
                self.db.refresh(task)
            except IntegrityError:
                self.db.rollback()
                return ErrorResponse(
                    message="Task creation failed due to constraint violation",
                    error_code="TASK_CREATION_FAILED"
                )
            
            # 如果是立即执行模式，直接执行
            if execution_mode == ExecutionMode.SYNC:
                return await self.execute_task_sync(task.id)
            else:
                # 添加到任务队列
                await self._enqueue_task(task)
                
                self.task_stats["total_created"] += 1
                
                return APIResponse(
                    status="success",
                    message="Task created successfully",
                    data=task
                )
                
        except Exception as e:
            self.logger.error(f"Error creating task: {str(e)}")
            return ErrorResponse(
                message=f"Failed to create task: {str(e)}",
                error_code="TASK_CREATION_FAILED"
            )
    
    async def get_task(self, task_id: str) -> APIResponse[Task]:
        """获取任务"""
        try:
            task = await self._get_task_by_id(task_id)
            if not task:
                return ErrorResponse(
                    message="Task not found",
                    error_code="NOT_FOUND"
                )
            
            return APIResponse(
                status="success",
                message="Task retrieved successfully",
                data=task
            )
            
        except Exception as e:
            self.logger.error(f"Error getting task {task_id}: {str(e)}")
            return ErrorResponse(
                message=f"Failed to get task: {str(e)}",
                error_code="GET_FAILED"
            )
    
    async def list_tasks(
        self,
        status: Optional[TaskStatus] = None,
        category: Optional[TaskCategory] = None,
        priority: Optional[TaskPriority] = None,
        user_id: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> APIResponse[PaginatedResponse[Task]]:
        """列出任务"""
        try:
            # 使用SQLAlchemy查询替代原始SQL
            
            # 构建SQLAlchemy查询
            query = self.db.query(Task).filter(Task.deleted_at.is_(None))
            
            # 应用过滤条件
            if status:
                query = query.filter(Task.status == status)
            if category:
                query = query.filter(Task.category == category)
            if priority:
                query = query.filter(Task.priority == priority)
            if user_id:
                query = query.filter(Task.created_by == user_id)
            
            # 计算总数
            total = query.count()
            
            # 分页查询
            offset = (page - 1) * page_size
            tasks = query.order_by(Task.created_at.desc()).offset(offset).limit(page_size).all()
            
            return APIResponse(
                status="success",
                message=f"Found {len(tasks)} tasks",
                data=PaginatedResponse(
                    items=tasks,
                    total=total,
                    page=page,
                    page_size=page_size,
                    total_pages=(total + page_size - 1) // page_size
                )
            )
            
        except Exception as e:
            self.logger.error(f"Error listing tasks: {str(e)}")
            return ErrorResponse(
                message=f"Failed to list tasks: {str(e)}",
                error_code="LIST_FAILED"
            )
    
    async def execute_task_sync(self, task_id: str) -> APIResponse[TaskResult]:
        """同步执行任务"""
        try:
            task = await self._get_task_by_id(task_id)
            if not task:
                return ErrorResponse(
                    message="Task not found",
                    error_code="NOT_FOUND"
                )
            
            # 检查依赖
            if not await self._check_dependencies(task):
                return ErrorResponse(
                    message="Task dependencies not satisfied",
                    error_code="DEPENDENCIES_NOT_SATISFIED"
                )
            
            # 更新任务状态为运行中
            task.status = TaskStatus.RUNNING
            task.started_at = datetime.now()
            await self._update_task(task)
            
            # 执行任务
            executor = self.executors[task.category]
            start_time = datetime.now()
            
            try:
                result = await asyncio.wait_for(
                    executor.execute(task),
                    timeout=task.timeout or TASK_TIMEOUT
                )
                
                execution_time = (datetime.now() - start_time).total_seconds()
                result.execution_time = execution_time
                
                # 更新任务状态
                task.status = result.status
                task.completed_at = datetime.now()
                task.progress.current_step = task.progress.total_steps
                task.progress.percentage = 100.0
                
                await self._update_task(task)
                await self._save_task_result(result)
                
                if result.status == TaskStatus.COMPLETED:
                    self.task_stats["total_completed"] += 1
                else:
                    self.task_stats["total_failed"] += 1
                
                return APIResponse(
                    status="success",
                    message="Task executed successfully",
                    data=result
                )
                
            except asyncio.TimeoutError:
                # 任务超时
                task.status = TaskStatus.FAILED
                task.completed_at = datetime.now()
                await self._update_task(task)
                
                result = TaskResult(
                    id=str(uuid4()),
                    task_id=task.id,
                    status=TaskStatus.FAILED,
                    error_message="Task execution timeout",
                    execution_time=(datetime.now() - start_time).total_seconds()
                )
                
                await self._save_task_result(result)
                self.task_stats["total_failed"] += 1
                
                return ErrorResponse(
                    message="Task execution timeout",
                    error_code="EXECUTION_TIMEOUT"
                )
                
        except Exception as e:
            self.logger.error(f"Error executing task {task_id}: {str(e)}")
            return ErrorResponse(
                message=f"Failed to execute task: {str(e)}",
                error_code="EXECUTION_FAILED"
            )
    
    async def cancel_task(self, task_id: str, user_id: Optional[str] = None) -> APIResponse[bool]:
        """取消任务"""
        try:
            task = await self._get_task_by_id(task_id)
            if not task:
                return ErrorResponse(
                    message="Task not found",
                    error_code="NOT_FOUND"
                )
            
            # 检查任务状态
            if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                return ErrorResponse(
                    message="Task cannot be cancelled in current status",
                    error_code="INVALID_STATUS"
                )
            
            # 如果任务正在运行，取消异步任务
            if task_id in self.running_tasks:
                self.running_tasks[task_id].cancel()
                del self.running_tasks[task_id]
            
            # 更新任务状态
            task.status = TaskStatus.CANCELLED
            task.completed_at = datetime.now()
            task.updated_by = user_id
            
            await self._update_task(task)
            
            # 从队列中移除
            await self._remove_from_queue(task)
            
            self.task_stats["total_cancelled"] += 1
            
            return APIResponse(
                status="success",
                message="Task cancelled successfully",
                data=True
            )
            
        except Exception as e:
            self.logger.error(f"Error cancelling task {task_id}: {str(e)}")
            return ErrorResponse(
                message=f"Failed to cancel task: {str(e)}",
                error_code="CANCEL_FAILED"
            )
    
    async def retry_task(self, task_id: str, user_id: Optional[str] = None) -> APIResponse[Task]:
        """重试任务"""
        try:
            task = await self._get_task_by_id(task_id)
            if not task:
                return ErrorResponse(
                    message="Task not found",
                    error_code="NOT_FOUND"
                )
            
            # 检查是否可以重试
            if task.status != TaskStatus.FAILED:
                return ErrorResponse(
                    message="Only failed tasks can be retried",
                    error_code="INVALID_STATUS"
                )
            
            if task.retry_count >= task.retry_policy.max_retries:
                return ErrorResponse(
                    message="Maximum retry attempts exceeded",
                    error_code="MAX_RETRIES_EXCEEDED"
                )
            
            # 重置任务状态
            task.status = TaskStatus.PENDING
            task.retry_count += 1
            task.started_at = None
            task.completed_at = None
            task.updated_by = user_id
            task.mark_updated()
            
            # 计算重试延迟
            delay = task.retry_policy.delay_seconds * (task.retry_policy.backoff_multiplier ** (task.retry_count - 1))
            task.scheduled_at = datetime.now() + timedelta(seconds=delay)
            
            await self._update_task(task)
            
            # 重新加入队列
            await self._enqueue_task(task)
            
            return APIResponse(
                status="success",
                message="Task scheduled for retry",
                data=task
            )
            
        except Exception as e:
            self.logger.error(f"Error retrying task {task_id}: {str(e)}")
            return ErrorResponse(
                message=f"Failed to retry task: {str(e)}",
                error_code="RETRY_FAILED"
            )
    
    async def get_task_result(self, task_id: str) -> APIResponse[TaskResult]:
        """获取任务结果"""
        try:
            # 先从缓存获取
            cached_result = await self.redis.get(f"task_result:{task_id}")
            if cached_result:
                result = TaskResult.parse_raw(cached_result)
                return APIResponse(
                    status="success",
                    message="Task result retrieved from cache",
                    data=result
                )
            
            # 从数据库查询
            task_result = self.db.query(TaskResult).filter(
                TaskResult.task_id == task_id
            ).order_by(TaskResult.created_at.desc()).first()
            
            if not task_result:
                return ErrorResponse(
                    message="Task result not found",
                    error_code="NOT_FOUND"
                )
            
            result = task_result
            
            # 缓存结果
            await self.redis.set(
                f"task_result:{task_id}",
                result.json(),
                expire=3600
            )
            
            return APIResponse(
                status="success",
                message="Task result retrieved successfully",
                data=result
            )
            
        except Exception as e:
            self.logger.error(f"Error getting task result for {task_id}: {str(e)}")
            return ErrorResponse(
                message=f"Failed to get task result: {str(e)}",
                error_code="GET_RESULT_FAILED"
            )
    
    async def get_task_statistics(self) -> APIResponse[Dict[str, Any]]:
        """获取任务统计信息"""
        try:
            # 从缓存获取
            cached_stats = await self.redis.get("task_statistics")
            if cached_stats:
                return APIResponse(
                    status="success",
                    message="Task statistics retrieved from cache",
                    data=eval(cached_stats)
                )
            
            # 计算统计信息
            stats = await self._calculate_task_statistics()
            
            # 缓存结果（1分钟）
            await self.redis.set("task_statistics", str(stats), expire=60)
            
            return APIResponse(
                status="success",
                message="Task statistics calculated successfully",
                data=stats
            )
            
        except Exception as e:
            self.logger.error(f"Error getting task statistics: {str(e)}")
            return ErrorResponse(
                message=f"Failed to get task statistics: {str(e)}",
                error_code="STATS_FAILED"
            )
    
    async def start_task_worker(self, worker_id: str = None):
        """启动任务工作器"""
        worker_id = worker_id or f"worker_{uuid4().hex[:8]}"
        self.logger.info(f"Starting task worker: {worker_id}")
        
        while True:
            try:
                # 按优先级处理任务
                for priority in [TaskPriority.HIGH, TaskPriority.MEDIUM, TaskPriority.LOW]:
                    queue_name = self.task_queues[priority]
                    
                    # 从队列获取任务
                    task_data = await self.redis.list_pop_right(queue_name)
                    if task_data:
                        task_id = task_data
                        
                        # 异步执行任务
                        async_task = asyncio.create_task(
                            self._execute_task_async(task_id, worker_id)
                        )
                        self.running_tasks[task_id] = async_task
                        
                        # 不等待任务完成，继续处理下一个任务
                        break
                
                # 短暂休眠避免CPU占用过高
                await asyncio.sleep(1)
                
            except Exception as e:
                self.logger.error(f"Error in task worker {worker_id}: {str(e)}")
                await asyncio.sleep(5)  # 错误时等待更长时间
    
    # 私有方法
    
    async def _save_task(self, task: Task) -> None:
        """保存任务到数据库"""
        self.db.add(task)
        self.db.commit()
        
        # 缓存到Redis
        await self.redis.set(
            f"task:{task.id}",
            task.json(),
            expire=3600
        )
    
    async def _update_task(self, task: Task) -> None:
        """更新任务"""
        self.db.merge(task)
        self.db.commit()
        
        # 更新缓存
        await self.redis.set(
            f"task:{task.id}",
            task.json(),
            expire=3600
        )
    
    async def _get_task_by_id(self, task_id: str) -> Optional[Task]:
        """根据ID获取任务"""
        # 先从Redis缓存获取
        cached_task = await self.redis.get(f"task:{task_id}")
        if cached_task:
            return Task.parse_raw(cached_task)
        
        # 从数据库查询
        task = self.db.query(Task).filter(
            Task.id == task_id,
            Task.deleted_at.is_(None)
        ).first()
        
        if task:
            # 缓存到Redis
            await self.redis.set(
                f"task:{task_id}",
                task.json(),
                expire=3600
            )
            return task
        
        return None
    
    async def _enqueue_task(self, task: Task) -> None:
        """将任务加入队列"""
        queue_name = self.task_queues[task.priority]
        await self.redis.list_push_left(queue_name, task.id)
        
        self.logger.info(f"Task {task.id} enqueued to {queue_name}")
    
    async def _remove_from_queue(self, task: Task) -> None:
        """从队列中移除任务"""
        for queue_name in self.task_queues.values():
            # Redis没有直接的移除列表元素的方法，这里简化处理
            # 实际应该使用更复杂的逻辑来移除特定元素
            pass
    
    async def _check_dependencies(self, task: Task) -> bool:
        """检查任务依赖"""
        if not task.dependencies:
            return True
        
        for dependency in task.dependencies:
            dep_task = await self._get_task_by_id(dependency.task_id)
            if not dep_task:
                return False
            
            if dependency.dependency_type == "completion" and dep_task.status != TaskStatus.COMPLETED:
                return False
            elif dependency.dependency_type == "success" and dep_task.status != TaskStatus.COMPLETED:
                return False
        
        return True
    
    async def _execute_task_async(self, task_id: str, worker_id: str) -> None:
        """异步执行任务"""
        try:
            task = await self._get_task_by_id(task_id)
            if not task:
                self.logger.error(f"Task {task_id} not found")
                return
            
            # 检查依赖
            if not await self._check_dependencies(task):
                self.logger.warning(f"Task {task_id} dependencies not satisfied, re-queuing")
                await self._enqueue_task(task)
                return
            
            # 更新任务状态
            task.status = TaskStatus.RUNNING
            task.started_at = datetime.now()
            await self._update_task(task)
            
            # 执行任务
            executor = self.executors[task.category]
            start_time = datetime.now()
            
            try:
                result = await asyncio.wait_for(
                    executor.execute(task),
                    timeout=task.timeout or TASK_TIMEOUT
                )
                
                execution_time = (datetime.now() - start_time).total_seconds()
                result.execution_time = execution_time
                
                # 更新任务状态
                task.status = result.status
                task.completed_at = datetime.now()
                task.progress.current_step = task.progress.total_steps
                task.progress.percentage = 100.0
                
                await self._update_task(task)
                await self._save_task_result(result)
                
                if result.status == TaskStatus.COMPLETED:
                    self.task_stats["total_completed"] += 1
                    self.logger.info(f"Task {task_id} completed successfully by worker {worker_id}")
                else:
                    self.task_stats["total_failed"] += 1
                    self.logger.warning(f"Task {task_id} failed: {result.error_message}")
                    
                    # 检查是否需要重试
                    if task.retry_count < task.retry_policy.max_retries:
                        await asyncio.sleep(task.retry_policy.delay_seconds)
                        await self.retry_task(task_id)
                
            except asyncio.TimeoutError:
                # 任务超时
                task.status = TaskStatus.FAILED
                task.completed_at = datetime.now()
                await self._update_task(task)
                
                result = TaskResult(
                    id=str(uuid4()),
                    task_id=task.id,
                    status=TaskStatus.FAILED,
                    error_message="Task execution timeout",
                    execution_time=(datetime.now() - start_time).total_seconds()
                )
                
                await self._save_task_result(result)
                self.task_stats["total_failed"] += 1
                
                self.logger.error(f"Task {task_id} timed out")
                
        except Exception as e:
            self.logger.error(f"Error executing task {task_id}: {str(e)}")
        finally:
            # 清理运行中的任务记录
            if task_id in self.running_tasks:
                del self.running_tasks[task_id]
    
    async def _save_task_result(self, result: TaskResult) -> None:
        """保存任务结果"""
        self.db.add(result)
        self.db.commit()
        
        # 缓存结果
        await self.redis.set(
            f"task_result:{result.task_id}",
            result.json(),
            expire=3600
        )
    
    async def _calculate_task_statistics(self) -> Dict[str, Any]:
        """计算任务统计信息"""
        from sqlalchemy import func
        stats = {}
        
        # 总任务数
        total_tasks = self.db.query(func.count(Task.id)).filter(
            Task.deleted_at.is_(None)
        ).scalar()
        stats["total_tasks"] = total_tasks or 0
        
        # 按状态统计
        status_stats = self.db.query(
            Task.status, func.count(Task.id)
        ).filter(
            Task.deleted_at.is_(None)
        ).group_by(Task.status).all()
        stats["tasks_by_status"] = {status: count for status, count in status_stats}
        
        # 按类别统计
        category_stats = self.db.query(
            Task.category, func.count(Task.id)
        ).filter(
            Task.deleted_at.is_(None)
        ).group_by(Task.category).all()
        stats["tasks_by_category"] = {category: count for category, count in category_stats}
        
        # 按优先级统计
        priority_stats = self.db.query(
            Task.priority, func.count(Task.id)
        ).filter(
            Task.deleted_at.is_(None)
        ).group_by(Task.priority).all()
        stats["tasks_by_priority"] = {priority: count for priority, count in priority_stats}
        
        # 平均执行时间
        avg_time = self.db.query(
            func.avg(TaskResult.execution_time)
        ).filter(
            TaskResult.status == TaskStatus.COMPLETED
        ).scalar()
        stats["average_execution_time"] = float(avg_time) if avg_time else 0.0
        
        # 成功率
        completed_count = self.db.query(func.count(Task.id)).filter(
            Task.deleted_at.is_(None),
            Task.status == TaskStatus.COMPLETED
        ).scalar()
        
        total_finished = self.db.query(func.count(Task.id)).filter(
            Task.deleted_at.is_(None),
            Task.status.in_([TaskStatus.COMPLETED, TaskStatus.FAILED])
        ).scalar()
        
        if total_finished and total_finished > 0:
             completed = completed_count or 0
             stats["success_rate"] = (completed / total_finished) * 100
        else:
            stats["success_rate"] = 0
        
        # 运行时统计
        stats["runtime_stats"] = self.task_stats.copy()
        stats["running_tasks_count"] = len(self.running_tasks)
        
        return stats