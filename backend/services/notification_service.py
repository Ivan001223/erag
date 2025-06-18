from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import asyncio
import json
from enum import Enum

from backend.connectors.redis_client import RedisClient
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from backend.models.base import BaseModel
from backend.utils.logger import get_logger

logger = get_logger(__name__)


class NotificationType(str, Enum):
    """通知类型枚举"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    SUCCESS = "success"
    TASK_COMPLETE = "task_complete"
    TASK_FAILED = "task_failed"
    DOCUMENT_PROCESSED = "document_processed"
    KNOWLEDGE_UPDATED = "knowledge_updated"
    SYSTEM_ALERT = "system_alert"


class NotificationChannel(str, Enum):
    """通知渠道枚举"""
    EMAIL = "email"
    SMS = "sms"
    WEBHOOK = "webhook"
    IN_APP = "in_app"
    PUSH = "push"


class NotificationPriority(str, Enum):
    """通知优先级枚举"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class NotificationStatus(str, Enum):
    """通知状态枚举"""
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"
    READ = "read"


class Notification(BaseModel):
    """通知模型"""
    id: str
    user_id: str
    title: str
    content: str
    type: NotificationType
    priority: NotificationPriority = NotificationPriority.NORMAL
    channels: List[NotificationChannel]
    status: NotificationStatus = NotificationStatus.PENDING
    metadata: Dict[str, Any] = {}
    scheduled_at: Optional[datetime] = None
    sent_at: Optional[datetime] = None
    read_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    retry_count: int = 0
    max_retries: int = 3
    created_at: datetime
    updated_at: datetime


class NotificationTemplate(BaseModel):
    """通知模板模型"""
    id: str
    name: str
    type: NotificationType
    title_template: str
    content_template: str
    channels: List[NotificationChannel]
    priority: NotificationPriority = NotificationPriority.NORMAL
    variables: List[str] = []
    is_active: bool = True
    created_at: datetime
    updated_at: datetime


class NotificationPreference(BaseModel):
    """用户通知偏好模型"""
    user_id: str
    channel: NotificationChannel
    enabled: bool = True
    types: List[NotificationType] = []
    quiet_hours_start: Optional[str] = None  # HH:MM format
    quiet_hours_end: Optional[str] = None    # HH:MM format
    frequency_limit: Optional[int] = None    # Max notifications per hour
    created_at: datetime
    updated_at: datetime


class NotificationService:
    """通知服务"""
    
    def __init__(self, redis_client: RedisClient, db: Session):
        self.redis = redis_client
        self.db = db
        self.notification_queue = "notifications:queue"
        self.template_cache_prefix = "notification:template:"
        self.preference_cache_prefix = "notification:preference:"
        
    async def send_notification(
        self,
        user_id: str,
        title: str,
        content: str,
        notification_type: NotificationType,
        channels: List[NotificationChannel],
        priority: NotificationPriority = NotificationPriority.NORMAL,
        metadata: Dict[str, Any] = None,
        scheduled_at: Optional[datetime] = None
    ) -> str:
        """发送通知"""
        try:
            notification_id = f"notif_{int(datetime.now().timestamp() * 1000)}"
            
            notification = Notification(
                id=notification_id,
                user_id=user_id,
                title=title,
                content=content,
                type=notification_type,
                priority=priority,
                channels=channels,
                metadata=metadata or {},
                scheduled_at=scheduled_at,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
            # 检查用户偏好
            filtered_channels = await self._filter_channels_by_preference(
                user_id, channels, notification_type
            )
            
            if not filtered_channels:
                logger.info(f"No enabled channels for user {user_id}, notification {notification_id}")
                return notification_id
                
            notification.channels = filtered_channels
            
            # 保存通知
            await self._save_notification(notification)
            
            # 如果是立即发送
            if scheduled_at is None or scheduled_at <= datetime.now():
                await self._queue_notification(notification)
            else:
                # 调度延迟发送
                await self._schedule_notification(notification)
                
            logger.info(f"Notification {notification_id} created for user {user_id}")
            return notification_id
            
        except Exception as e:
            logger.error(f"Failed to send notification: {str(e)}")
            raise
    
    async def send_from_template(
        self,
        user_id: str,
        template_name: str,
        variables: Dict[str, Any],
        channels: Optional[List[NotificationChannel]] = None,
        priority: Optional[NotificationPriority] = None,
        scheduled_at: Optional[datetime] = None
    ) -> str:
        """使用模板发送通知"""
        try:
            template = await self.get_template(template_name)
            if not template:
                raise ValueError(f"Template {template_name} not found")
                
            # 渲染模板
            title = self._render_template(template.title_template, variables)
            content = self._render_template(template.content_template, variables)
            
            # 使用模板设置或覆盖参数
            final_channels = channels or template.channels
            final_priority = priority or template.priority
            
            return await self.send_notification(
                user_id=user_id,
                title=title,
                content=content,
                notification_type=template.type,
                channels=final_channels,
                priority=final_priority,
                metadata={"template_name": template_name, "variables": variables},
                scheduled_at=scheduled_at
            )
            
        except Exception as e:
            logger.error(f"Failed to send notification from template: {str(e)}")
            raise
    
    async def get_notifications(
        self,
        user_id: str,
        status: Optional[NotificationStatus] = None,
        notification_type: Optional[NotificationType] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Notification]:
        """获取用户通知列表"""
        try:
            query = self.db.query(Notification).filter(
                Notification.user_id == user_id
            )
            
            if status:
                query = query.filter(Notification.status == status)
                
            if notification_type:
                query = query.filter(Notification.type == notification_type)
                
            notifications = query.order_by(
                Notification.created_at.desc()
            ).offset(offset).limit(limit).all()
                
            return notifications
            
        except Exception as e:
            logger.error(f"Failed to get notifications: {str(e)}")
            raise
    
    async def mark_as_read(self, notification_id: str, user_id: str) -> bool:
        """标记通知为已读"""
        try:
            notification = self.db.query(Notification).filter(
                Notification.id == notification_id,
                Notification.user_id == user_id
            ).first()
            
            if notification:
                notification.status = NotificationStatus.read
                notification.read_at = datetime.now()
                notification.updated_at = datetime.now()
                self.db.commit()
                    
                # 清除缓存
                await self.redis.delete(f"notification:{notification_id}")
                
                logger.info(f"Notification {notification_id} marked as read")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to mark notification as read: {str(e)}")
            self.db.rollback()
            return False
    
    async def get_unread_count(self, user_id: str) -> int:
        """获取未读通知数量"""
        try:
            # 先尝试从缓存获取
            cache_key = f"unread_count:{user_id}"
            cached_count = await self.redis.get(cache_key)
            
            if cached_count is not None:
                return int(cached_count)
                
            from sqlalchemy import func
            
            count = self.db.query(func.count(Notification.id)).filter(
                Notification.user_id == user_id,
                Notification.status != NotificationStatus.read
            ).scalar()
                    
            # 缓存结果
            await self.redis.setex(cache_key, 300, count)  # 5分钟缓存
            
            return count
            
        except Exception as e:
            logger.error(f"Failed to get unread count: {str(e)}")
            return 0
    
    async def create_template(
        self,
        name: str,
        notification_type: NotificationType,
        title_template: str,
        content_template: str,
        channels: List[NotificationChannel],
        priority: NotificationPriority = NotificationPriority.NORMAL,
        variables: List[str] = None
    ) -> str:
        """创建通知模板"""
        try:
            template_id = f"template_{int(datetime.now().timestamp() * 1000)}"
            
            template = NotificationTemplate(
                id=template_id,
                name=name,
                type=notification_type,
                title_template=title_template,
                content_template=content_template,
                channels=channels,
                priority=priority,
                variables=variables or [],
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
            await self._save_template(template)
            
            logger.info(f"Template {name} created with ID {template_id}")
            return template_id
            
        except Exception as e:
            logger.error(f"Failed to create template: {str(e)}")
            raise
    
    async def get_template(self, name: str) -> Optional[NotificationTemplate]:
        """获取通知模板"""
        try:
            # 先从缓存获取
            cache_key = f"{self.template_cache_prefix}{name}"
            cached_template = await self.redis.get(cache_key)
            
            if cached_template:
                return NotificationTemplate(**json.loads(cached_template))
                
            template = self.db.query(NotificationTemplate).filter(
                NotificationTemplate.name == name,
                NotificationTemplate.is_active == True
            ).first()
                
            if not template:
                return None
            
            # 缓存模板
            await self.redis.setex(cache_key, 3600, template.json())  # 1小时缓存
            
            return template
            
        except Exception as e:
            logger.error(f"Failed to get template: {str(e)}")
            return None
    
    async def set_user_preference(
        self,
        user_id: str,
        channel: NotificationChannel,
        enabled: bool = True,
        types: List[NotificationType] = None,
        quiet_hours_start: Optional[str] = None,
        quiet_hours_end: Optional[str] = None,
        frequency_limit: Optional[int] = None
    ) -> bool:
        """设置用户通知偏好"""
        try:
            preference = NotificationPreference(
                user_id=user_id,
                channel=channel,
                enabled=enabled,
                types=types or [],
                quiet_hours_start=quiet_hours_start,
                quiet_hours_end=quiet_hours_end,
                frequency_limit=frequency_limit,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
            await self._save_preference(preference)
            
            # 清除缓存
            cache_key = f"{self.preference_cache_prefix}{user_id}:{channel.value}"
            await self.redis.delete(cache_key)
            
            logger.info(f"Preference set for user {user_id}, channel {channel.value}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to set user preference: {str(e)}")
            return False
    
    async def process_notification_queue(self):
        """处理通知队列"""
        try:
            while True:
                # 从队列获取通知
                notification_data = await self.redis.blpop(self.notification_queue, timeout=1)
                
                if notification_data:
                    notification = Notification(**json.loads(notification_data[1]))
                    await self._deliver_notification(notification)
                    
                await asyncio.sleep(0.1)
                
        except Exception as e:
            logger.error(f"Error processing notification queue: {str(e)}")
    
    async def _filter_channels_by_preference(
        self,
        user_id: str,
        channels: List[NotificationChannel],
        notification_type: NotificationType
    ) -> List[NotificationChannel]:
        """根据用户偏好过滤通知渠道"""
        filtered_channels = []
        
        for channel in channels:
            preference = await self._get_user_preference(user_id, channel)
            
            if preference and preference.enabled:
                # 检查类型过滤
                if not preference.types or notification_type in preference.types:
                    # 检查静默时间
                    if not self._is_in_quiet_hours(preference):
                        # 检查频率限制
                        if await self._check_frequency_limit(user_id, channel, preference):
                            filtered_channels.append(channel)
                            
        return filtered_channels or channels  # 如果没有偏好设置，使用原始渠道
    
    async def _get_user_preference(
        self,
        user_id: str,
        channel: NotificationChannel
    ) -> Optional[NotificationPreference]:
        """获取用户通知偏好"""
        try:
            cache_key = f"{self.preference_cache_prefix}{user_id}:{channel.value}"
            cached_preference = await self.redis.get(cache_key)
            
            if cached_preference:
                return NotificationPreference(**json.loads(cached_preference))
                
            # 使用SQLAlchemy ORM查询通知偏好
            from backend.models.notification import NotificationPreferenceModel
            
            preference = self.db.query(NotificationPreferenceModel).filter(
                NotificationPreferenceModel.user_id == user_id,
                NotificationPreferenceModel.channel == channel.value
            ).first()
            
            if not preference:
                return None
            
            # 缓存偏好
            await self.redis.setex(cache_key, 1800, preference.json())  # 30分钟缓存
            
            return preference
            
        except Exception as e:
            logger.error(f"Failed to get user preference: {str(e)}")
            return None
    
    def _is_in_quiet_hours(self, preference: NotificationPreference) -> bool:
        """检查是否在静默时间内"""
        if not preference.quiet_hours_start or not preference.quiet_hours_end:
            return False
            
        now = datetime.now().time()
        start_time = datetime.strptime(preference.quiet_hours_start, "%H:%M").time()
        end_time = datetime.strptime(preference.quiet_hours_end, "%H:%M").time()
        
        if start_time <= end_time:
            return start_time <= now <= end_time
        else:  # 跨天的情况
            return now >= start_time or now <= end_time
    
    async def _check_frequency_limit(
        self,
        user_id: str,
        channel: NotificationChannel,
        preference: NotificationPreference
    ) -> bool:
        """检查频率限制"""
        if not preference.frequency_limit:
            return True
            
        # 检查过去一小时的通知数量
        key = f"frequency:{user_id}:{channel.value}:{datetime.now().strftime('%Y%m%d%H')}"
        count = await self.redis.get(key)
        
        if count and int(count) >= preference.frequency_limit:
            return False
            
        return True
    
    async def _save_notification(self, notification: Notification):
        """保存通知到数据库"""
        from backend.models.notification import NotificationModel
        from backend.config.database import get_async_session
        
        async with get_async_session() as session:
            new_notification = NotificationModel(
                id=notification.id,
                user_id=notification.user_id,
                title=notification.title,
                content=notification.content,
                type=notification.type.value,
                priority=notification.priority.value,
                channels=json.dumps([c.value for c in notification.channels]),
                status=notification.status.value,
                metadata=json.dumps(notification.model_metadata),
                scheduled_at=notification.scheduled_at,
                created_at=notification.created_at,
                updated_at=notification.updated_at,
                retry_count=notification.retry_count,
                max_retries=notification.max_retries
            )
            
            session.add(new_notification)
            await session.commit()
    
    async def _save_template(self, template: NotificationTemplate):
        """保存通知模板"""
        from backend.models.notification import NotificationTemplateModel
        from backend.config.database import get_async_session
        
        async with get_async_session() as session:
            new_template = NotificationTemplateModel(
                id=template.id,
                name=template.name,
                type=template.type.value,
                title_template=template.title_template,
                content_template=template.content_template,
                channels=json.dumps([c.value for c in template.channels]),
                priority=template.priority.value,
                variables=json.dumps(template.variables),
                is_active=template.is_active,
                created_at=template.created_at,
                updated_at=template.updated_at
            )
            
            session.add(new_template)
            await session.commit()
    
    async def _save_preference(self, preference: NotificationPreference):
        """保存用户偏好"""
        from backend.models.notification import NotificationPreferenceModel
        from backend.config.database import get_async_session
        from sqlalchemy import select
        
        async with get_async_session() as session:
            # 检查是否已存在
            stmt = select(NotificationPreferenceModel).where(
                NotificationPreferenceModel.user_id == preference.user_id,
                NotificationPreferenceModel.channel == preference.channel.value
            )
            existing = await session.execute(stmt)
            existing_pref = existing.scalar_one_or_none()
            
            if existing_pref:
                # 更新现有记录
                existing_pref.enabled = preference.enabled
                existing_pref.types = json.dumps([t.value for t in preference.types])
                existing_pref.quiet_hours_start = preference.quiet_hours_start
                existing_pref.quiet_hours_end = preference.quiet_hours_end
                existing_pref.frequency_limit = preference.frequency_limit
                existing_pref.updated_at = preference.updated_at
            else:
                # 创建新记录
                new_preference = NotificationPreferenceModel(
                    user_id=preference.user_id,
                    channel=preference.channel.value,
                    enabled=preference.enabled,
                    types=json.dumps([t.value for t in preference.types]),
                    quiet_hours_start=preference.quiet_hours_start,
                    quiet_hours_end=preference.quiet_hours_end,
                    frequency_limit=preference.frequency_limit,
                    created_at=preference.created_at,
                    updated_at=preference.updated_at
                )
                session.add(new_preference)
            
            await session.commit()
        
        async with self.starrocks.get_connection() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(query, [
                    preference.user_id,
                    preference.channel.value,
                    preference.enabled,
                    json.dumps([t.value for t in preference.types]),
                    preference.quiet_hours_start,
                    preference.quiet_hours_end,
                    preference.frequency_limit,
                    preference.created_at,
                    preference.updated_at
                ])
    
    async def _queue_notification(self, notification: Notification):
        """将通知加入队列"""
        await self.redis.rpush(self.notification_queue, notification.json())
    
    async def _schedule_notification(self, notification: Notification):
        """调度延迟通知"""
        # 使用Redis的延迟队列功能
        delay = int((notification.scheduled_at - datetime.now()).total_seconds())
        await self.redis.zadd(
            "notifications:scheduled",
            {notification.json(): notification.scheduled_at.timestamp()}
        )
    
    async def _deliver_notification(self, notification: Notification):
        """投递通知"""
        try:
            success = False
            
            for channel in notification.channels:
                if channel == NotificationChannel.EMAIL:
                    success = await self._send_email(notification)
                elif channel == NotificationChannel.SMS:
                    success = await self._send_sms(notification)
                elif channel == NotificationChannel.WEBHOOK:
                    success = await self._send_webhook(notification)
                elif channel == NotificationChannel.IN_APP:
                    success = await self._send_in_app(notification)
                elif channel == NotificationChannel.PUSH:
                    success = await self._send_push(notification)
                    
            if success:
                await self._update_notification_status(
                    notification.id,
                    NotificationStatus.SENT
                )
                # 更新频率计数
                await self._update_frequency_count(notification)
            else:
                await self._handle_delivery_failure(notification)
                
        except Exception as e:
            logger.error(f"Failed to deliver notification {notification.id}: {str(e)}")
            await self._handle_delivery_failure(notification)
    
    async def _send_email(self, notification: Notification) -> bool:
        """发送邮件通知"""
        # TODO: 实现邮件发送逻辑
        logger.info(f"Sending email notification {notification.id}")
        return True
    
    async def _send_sms(self, notification: Notification) -> bool:
        """发送短信通知"""
        # TODO: 实现短信发送逻辑
        logger.info(f"Sending SMS notification {notification.id}")
        return True
    
    async def _send_webhook(self, notification: Notification) -> bool:
        """发送Webhook通知"""
        # TODO: 实现Webhook发送逻辑
        logger.info(f"Sending webhook notification {notification.id}")
        return True
    
    async def _send_in_app(self, notification: Notification) -> bool:
        """发送应用内通知"""
        # 应用内通知通过WebSocket或SSE推送
        logger.info(f"Sending in-app notification {notification.id}")
        return True
    
    async def _send_push(self, notification: Notification) -> bool:
        """发送推送通知"""
        # TODO: 实现推送通知逻辑
        logger.info(f"Sending push notification {notification.id}")
        return True
    
    async def _update_notification_status(
        self,
        notification_id: str,
        status: NotificationStatus
    ):
        """更新通知状态"""
        # 使用SQLAlchemy ORM更新通知状态
        from backend.models.notification import Notification
        
        notification = self.db.query(Notification).filter(
            Notification.id == notification_id
        ).first()
        
        if notification:
            notification.status = status.value
            notification.sent_at = datetime.now() if status == NotificationStatus.SENT else None
            notification.updated_at = datetime.now()
            self.db.commit()
    
    async def _update_frequency_count(self, notification: Notification):
        """更新频率计数"""
        for channel in notification.channels:
            key = f"frequency:{notification.user_id}:{channel.value}:{datetime.now().strftime('%Y%m%d%H')}"
            await self.redis.incr(key)
            await self.redis.expire(key, 3600)  # 1小时过期
    
    async def _handle_delivery_failure(self, notification: Notification):
        """处理投递失败"""
        notification.retry_count += 1
        
        if notification.retry_count < notification.max_retries:
            # 重新加入队列，延迟重试
            delay = min(300, 60 * (2 ** notification.retry_count))  # 指数退避，最大5分钟
            await self.redis.zadd(
                "notifications:retry",
                {notification.json(): (datetime.now() + timedelta(seconds=delay)).timestamp()}
            )
        else:
            # 标记为失败
            await self._update_notification_status(
                notification.id,
                NotificationStatus.FAILED
            )
    
    def _render_template(self, template: str, variables: Dict[str, Any]) -> str:
        """渲染模板"""
        try:
            # 简单的模板渲染，可以替换为更复杂的模板引擎
            result = template
            for key, value in variables.items():
                result = result.replace(f"{{{key}}}", str(value))
            return result
        except Exception as e:
            logger.error(f"Failed to render template: {str(e)}")
            return template