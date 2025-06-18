"""任务数据仓库"""

from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc, asc
from sqlalchemy.exc import SQLAlchemyError
import json
from datetime import datetime

from backend.models.task import Task, TaskStatus, TaskPriority, TaskType
from backend.utils.logger import get_logger

logger = get_logger(__name__)


class TaskRepository:
    """任务数据仓库"""
    
    def __init__(self, db: Session):
        self.db = db
    
    async def create_task(
        self,
        task_type: str,
        task_name: str,
        task_data: Dict[str, Any],
        user_id: Optional[str] = None,
        priority: int = 1,
        scheduled_at: Optional[datetime] = None,
        max_retries: int = 3
    ) -> str:
        """创建任务"""
        try:
            # 将字符串转换为枚举
            task_type_enum = TaskType(task_type) if isinstance(task_type, str) else task_type
            priority_enum = TaskPriority.NORMAL  # 默认优先级
            if priority >= 3:
                priority_enum = TaskPriority.HIGH
            elif priority >= 2:
                priority_enum = TaskPriority.NORMAL
            else:
                priority_enum = TaskPriority.LOW
            
            task = Task(
                name=task_name,
                task_type=task_type_enum,
                parameters=json.dumps(task_data),
                user_id=user_id,
                status=TaskStatus.PENDING,
                priority=priority_enum,
                scheduled_at=scheduled_at,
                max_retries=max_retries,
                retry_count=0
            )
            
            self.db.add(task)
            self.db.commit()
            self.db.refresh(task)
            
            logger.info(f"Created task: {task_name} ({task.id})")
            return task.id
            
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Failed to create task {task_name}: {str(e)}")
            raise
    
    async def get_task_by_id(self, task_id: str) -> Optional[Dict[str, Any]]:
        """根据ID获取任务"""
        try:
            task = self.db.query(Task).filter(
                Task.id == task_id,
                Task.is_deleted == False
            ).first()
            
            if task:
                return {
                    'id': task.id,
                    'task_type': task.task_type.value if task.task_type else None,
                    'task_name': task.name,
                    'task_data': json.loads(task.parameters) if task.parameters else {},
                    'user_id': task.user_id,
                    'status': task.status.value if task.status else None,
                    'priority': task.priority.value if task.priority else None,
                    'scheduled_at': task.scheduled_at.isoformat() if task.scheduled_at else None,
                    'max_retries': task.max_retries,
                    'retry_count': task.retry_count,
                    'started_at': task.started_at.isoformat() if task.started_at else None,
                    'completed_at': task.completed_at.isoformat() if task.completed_at else None,
                    'error_message': task.error_message,
                    'result_data': json.loads(task.result) if task.result else None,
                    'created_at': task.created_at.isoformat() if task.created_at else None,
                    'updated_at': task.updated_at.isoformat() if task.updated_at else None
                }
            
            return None
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to get task {task_id}: {str(e)}")
            raise
    
    async def get_pending_tasks(
        self,
        task_type: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """获取待执行任务"""
        try:
            now = datetime()
            query = self.db.query(Task).filter(
                Task.status == TaskStatus.PENDING,
                Task.is_deleted == False,
                or_(Task.scheduled_at.is_(None), Task.scheduled_at <= now)
            )
            
            if task_type:
                task_type_enum = TaskType(task_type) if isinstance(task_type, str) else task_type
                query = query.filter(Task.task_type == task_type_enum)
            
            tasks = query.order_by(
                desc(Task.priority),
                asc(Task.created_at)
            ).limit(limit).all()
            
            result = []
            for task in tasks:
                result.append({
                    'id': task.id,
                    'task_type': task.task_type.value if task.task_type else None,
                    'task_name': task.name,
                    'task_data': json.loads(task.parameters) if task.parameters else {},
                    'user_id': task.user_id,
                    'status': task.status.value if task.status else None,
                    'priority': task.priority.value if task.priority else None,
                    'scheduled_at': task.scheduled_at.isoformat() if task.scheduled_at else None,
                    'max_retries': task.max_retries,
                    'retry_count': task.retry_count,
                    'started_at': task.started_at.isoformat() if task.started_at else None,
                    'completed_at': task.completed_at.isoformat() if task.completed_at else None,
                    'error_message': task.error_message,
                    'result_data': json.loads(task.result) if task.result else None,
                    'created_at': task.created_at.isoformat() if task.created_at else None,
                    'updated_at': task.updated_at.isoformat() if task.updated_at else None
                })
            
            return result
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to get pending tasks: {str(e)}")
            raise
    
    async def update_task_status(
        self,
        task_id: str,
        status: str,
        error_message: Optional[str] = None,
        result_data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """更新任务状态"""
        try:
            # 转换状态为枚举
            task_status = TaskStatus(status) if isinstance(status, str) else status
            
            # 查找任务
            task = self.db.query(Task).filter(
                Task.id == task_id,
                Task.is_deleted == False
            ).first()
            
            if not task:
                return False
            
            # 更新状态和时间戳
            task.status = task_status
            task.updated_at = datetime.utcnow()
            
            # 根据状态更新相应的时间字段
            if task_status == TaskStatus.RUNNING:
                task.started_at = datetime.utcnow()
            elif task_status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
                task.completed_at = datetime.utcnow()
            
            # 添加可选字段
            if error_message is not None:
                task.error_message = error_message
            
            if result_data is not None:
                task.result = json.dumps(result_data)
            
            self.db.commit()
            logger.info(f"Updated task status: {task_id} -> {status}")
            return True
            
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Failed to update task status {task_id}: {str(e)}")
            raise
    
    async def increment_retry_count(self, task_id: str) -> bool:
        """增加重试次数"""
        try:
            # 查找任务
            task = self.db.query(Task).filter(
                Task.id == task_id,
                Task.is_deleted == False
            ).first()
            
            if not task:
                return False
            
            # 增加重试次数
            task.retry_count = (task.retry_count or 0) + 1
            task.updated_at = datetime.utcnow()
            
            self.db.commit()
            logger.info(f"Incremented retry count for task: {task_id}")
            return True
            
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Failed to increment retry count for task {task_id}: {str(e)}")
            raise
    
    async def get_user_tasks(
        self, 
        user_id: int, 
        status: str = None, 
        task_type: str = None,
        page: int = 1, 
        page_size: int = 20,
        order_by: str = 'created_at',
        order_desc: bool = True
    ) -> Dict[str, Any]:
        """
        获取用户任务列表
        
        Args:
            user_id: 用户ID
            status: 状态过滤（可选）
            task_type: 任务类型过滤（可选）
            page: 页码
            page_size: 每页大小
            order_by: 排序字段
            order_desc: 是否降序
            
        Returns:
            Dict: 包含任务列表和分页信息
        """
        try:
            # 构建查询
            query = self.db.query(Task).filter(
                Task.user_id == user_id,
                Task.is_deleted == False
            )
            
            # 添加状态过滤
            if status:
                task_status = TaskStatus(status) if isinstance(status, str) else status
                query = query.filter(Task.status == task_status)
            
            # 添加任务类型过滤
            if task_type:
                task_type_enum = TaskType(task_type) if isinstance(task_type, str) else task_type
                query = query.filter(Task.task_type == task_type_enum)
            
            # 计算总数
            total = query.count()
            
            # 添加排序
            order_field = getattr(Task, order_by, Task.created_at)
            if order_desc:
                query = query.order_by(order_field.desc())
            else:
                query = query.order_by(order_field.asc())
            
            # 添加分页
            offset = (page - 1) * page_size
            tasks = query.offset(offset).limit(page_size).all()
            
            # 转换为字典格式
            task_list = []
            for task in tasks:
                task_data = {
                    'id': task.id,
                    'task_type': task.task_type.value if task.task_type else None,
                    'task_name': task.name,
                    'task_data': json.loads(task.parameters) if task.parameters else {},
                    'user_id': task.user_id,
                    'status': task.status.value if task.status else None,
                    'priority': task.priority.value if task.priority else None,
                    'scheduled_at': task.scheduled_at.isoformat() if task.scheduled_at else None,
                    'max_retries': task.max_retries,
                    'retry_count': task.retry_count,
                    'created_at': task.created_at.isoformat() if task.created_at else None,
                    'updated_at': task.updated_at.isoformat() if task.updated_at else None,
                    'started_at': task.started_at.isoformat() if task.started_at else None,
                    'completed_at': task.completed_at.isoformat() if task.completed_at else None,
                    'error_message': task.error_message,
                    'result_data': json.loads(task.result) if task.result else None
                }
                task_list.append(task_data)
            
            return {
                'tasks': task_list,
                'total': total,
                'page': page,
                'page_size': page_size,
                'total_pages': (total + page_size - 1) // page_size
            }
            
        except Exception as e:
            logger.error(f"获取用户任务失败: {str(e)}")
            return {
                'tasks': [],
                'total': 0,
                'page': page,
                'page_size': page_size,
                'total_pages': 0
            }
    
    async def delete_task(self, task_id: int) -> bool:
        """软删除任务"""
        try:
            # 查找任务
            task = self.db.query(Task).filter(
                Task.id == task_id,
                Task.is_deleted == False
            ).first()
            
            if not task:
                return False
            
            # 软删除任务
            task.is_deleted = True
            task.updated_at = datetime.utcnow()
            
            self.db.commit()
            logger.info(f"Soft deleted task: {task_id}")
            return True
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to delete task {task_id}: {str(e)}")
            return False
    
    async def cleanup_old_tasks(self, days: int = 30) -> int:
        """
        清理旧任务（软删除指定天数前已完成或失败的任务）
        
        Args:
            days: 保留天数
            
        Returns:
            int: 清理的任务数量
        """
        try:
            from datetime import timedelta
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            # 查找需要清理的任务
            tasks_to_cleanup = self.db.query(Task).filter(
                Task.status.in_([TaskStatus.COMPLETED, TaskStatus.FAILED]),
                Task.completed_at < cutoff_date,
                Task.is_deleted == False
            ).all()
            
            count = 0
            for task in tasks_to_cleanup:
                task.is_deleted = True
                task.updated_at = datetime.utcnow()
                count += 1
            
            self.db.commit()
            logger.info(f"清理了 {count} 个旧任务")
            return count
            
        except Exception as e:
            logger.error(f"清理旧任务失败: {str(e)}")
            self.db.rollback()
            return 0
    
    async def get_task_statistics(
        self,
        user_id: Optional[str] = None,
        task_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """获取任务统计信息"""
        try:
            # 构建基础查询条件
            base_query = self.db.query(Task).filter(Task.is_deleted == False)
            
            if user_id:
                base_query = base_query.filter(Task.user_id == user_id)
            
            if task_type:
                task_type_enum = TaskType(task_type) if isinstance(task_type, str) else task_type
                base_query = base_query.filter(Task.task_type == task_type_enum)
            
            # 总任务数
            total_count = base_query.count()
            
            # 按状态统计
            status_stats = self.db.query(
                Task.status,
                func.count(Task.id)
            ).filter(
                Task.is_deleted == False
            )
            
            if user_id:
                status_stats = status_stats.filter(Task.user_id == user_id)
            if task_type:
                task_type_enum = TaskType(task_type) if isinstance(task_type, str) else task_type
                status_stats = status_stats.filter(Task.task_type == task_type_enum)
            
            status_stats = status_stats.group_by(Task.status).all()
            
            # 按类型统计
            type_stats = self.db.query(
                Task.task_type,
                func.count(Task.id)
            ).filter(
                Task.is_deleted == False
            )
            
            if user_id:
                type_stats = type_stats.filter(Task.user_id == user_id)
            if task_type:
                task_type_enum = TaskType(task_type) if isinstance(task_type, str) else task_type
                type_stats = type_stats.filter(Task.task_type == task_type_enum)
            
            type_stats = type_stats.group_by(Task.task_type).all()
            
            # 成功率
            completed_query = base_query.filter(Task.status == TaskStatus.COMPLETED)
            completed_count = completed_query.count()
            
            # 平均执行时间（使用SQLAlchemy的func.extract来计算秒数差）
            avg_duration_query = self.db.query(
                func.avg(
                    func.extract('epoch', Task.completed_at) - func.extract('epoch', Task.started_at)
                )
            ).filter(
                Task.is_deleted == False,
                Task.status == TaskStatus.COMPLETED,
                Task.started_at.isnot(None),
                Task.completed_at.isnot(None)
            )
            
            if user_id:
                avg_duration_query = avg_duration_query.filter(Task.user_id == user_id)
            if task_type:
                task_type_enum = TaskType(task_type) if isinstance(task_type, str) else task_type
                avg_duration_query = avg_duration_query.filter(Task.task_type == task_type_enum)
            
            avg_duration = avg_duration_query.scalar()
            
            return {
                'total_tasks': total_count,
                'completed_tasks': completed_count,
                'success_rate': completed_count / total_count if total_count > 0 else 0,
                'average_duration_seconds': float(avg_duration) if avg_duration else 0,
                'status_distribution': {row[0].value if row[0] else None: row[1] for row in status_stats},
                'type_distribution': {row[0].value if row[0] else None: row[1] for row in type_stats}
            }
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to get task statistics: {str(e)}")
            return {}
    
    async def get_failed_tasks_for_retry(
        self,
        task_type: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """获取可重试的失败任务"""
        try:
            query = self.db.query(Task).filter(
                Task.status == TaskStatus.FAILED,
                Task.retry_count < Task.max_retries,
                Task.is_deleted == False
            )
            
            if task_type:
                task_type_enum = TaskType(task_type) if isinstance(task_type, str) else task_type
                query = query.filter(Task.task_type == task_type_enum)
            
            tasks = query.order_by(
                desc(Task.priority),
                asc(Task.created_at)
            ).limit(limit).all()
            
            result = []
            for task in tasks:
                result.append({
                    'id': task.id,
                    'task_type': task.task_type.value if task.task_type else None,
                    'task_name': task.name,
                    'task_data': json.loads(task.parameters) if task.parameters else {},
                    'user_id': task.user_id,
                    'status': task.status.value if task.status else None,
                    'priority': task.priority.value if task.priority else None,
                    'scheduled_at': task.scheduled_at.isoformat() if task.scheduled_at else None,
                    'max_retries': task.max_retries,
                    'retry_count': task.retry_count,
                    'started_at': task.started_at.isoformat() if task.started_at else None,
                    'completed_at': task.completed_at.isoformat() if task.completed_at else None,
                    'error_message': task.error_message,
                    'result_data': json.loads(task.result) if task.result else None,
                    'created_at': task.created_at.isoformat() if task.created_at else None,
                    'updated_at': task.updated_at.isoformat() if task.updated_at else None
                })
            
            return result
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to get failed tasks for retry: {str(e)}")
            raise
    
    async def reset_task_for_retry(self, task_id: str) -> bool:
        """
        重置任务状态以便重试
        
        Args:
            task_id: 任务ID
            
        Returns:
            bool: 重置是否成功
        """
        try:
            # 查找可重试的失败任务
            task = self.db.query(Task).filter(
                Task.id == task_id,
                Task.status == TaskStatus.FAILED,
                Task.retry_count < Task.max_retries,
                Task.is_deleted == False
            ).first()
            
            if not task:
                return False
            
            # 重置任务状态
            task.status = TaskStatus.PENDING
            task.started_at = None
            task.completed_at = None
            task.error_message = None
            task.updated_at = datetime.utcnow()
            
            self.db.commit()
            logger.info(f"Reset task for retry: {task_id}")
            return True
            
        except Exception as e:
            logger.error(f"重置任务重试失败: {str(e)}")
            self.db.rollback()
            return False