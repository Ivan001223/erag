"""通知数据仓库"""

from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc, asc
from sqlalchemy.exc import SQLAlchemyError
import json
from datetime import datetime

from backend.models.notification import Notification
from backend.utils.logger import get_logger

logger = get_logger(__name__)


class NotificationRepository:
    """通知数据仓库"""
    
    def __init__(self, db: Session):
        self.db = db
    
    async def create_notification(
        self,
        user_id: str,
        title: str,
        content: str,
        notification_type: str = "info",
        priority: int = 1,
        metadata: Optional[Dict[str, Any]] = None,
        expires_at: Optional[datetime] = None
    ) -> str:
        """创建通知"""
        try:
            notification = Notification(
                user_id=user_id,
                title=title,
                content=content,
                notification_type=notification_type,
                priority=priority,
                expires_at=expires_at,
                is_read=False
            )
            
            if metadata:
                notification.set_metadata(metadata)
            
            self.db.add(notification)
            self.db.commit()
            self.db.refresh(notification)
            
            logger.info(f"Created notification: {title} for user {user_id} ({notification.id})")
            return notification.id
            
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Failed to create notification for user {user_id}: {str(e)}")
            raise
    
    async def get_notification_by_id(self, notification_id: str) -> Optional[Dict[str, Any]]:
        """根据ID获取通知"""
        try:
            notification = self.db.query(Notification).filter(
                Notification.id == notification_id,
                Notification.is_deleted == False
            ).first()
            
            if notification:
                return notification.to_dict()
            
            return None
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to get notification {notification_id}: {str(e)}")
            raise
    
    async def get_user_notifications(
        self,
        user_id: str,
        is_read: Optional[bool] = None,
        notification_type: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
        order_by: str = "created_at",
        order_desc: bool = True
    ) -> List[Dict[str, Any]]:
        """获取用户通知列表"""
        try:
            # 构建查询
            query = self.db.query(Notification).filter(
                Notification.user_id == user_id,
                Notification.is_deleted == False,
                or_(
                    Notification.expires_at.is_(None),
                    Notification.expires_at > datetime.utcnow()
                )
            )
            
            # 添加过滤条件
            if is_read is not None:
                query = query.filter(Notification.is_read == is_read)
            
            if notification_type:
                query = query.filter(Notification.notification_type == notification_type)
            
            # 排序
            order_column = getattr(Notification, order_by, Notification.created_at)
            if order_desc:
                query = query.order_by(desc(order_column))
            else:
                query = query.order_by(asc(order_column))
            
            # 分页
            notifications = query.offset(offset).limit(limit).all()
            
            return [notification.to_dict() for notification in notifications]
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to get notifications for user {user_id}: {str(e)}")
            raise
    
    async def mark_notification_as_read(self, notification_id: str) -> bool:
        """标记通知为已读"""
        try:
            notification = self.db.query(Notification).filter(
                Notification.id == notification_id,
                Notification.is_deleted == False
            ).first()
            
            if notification:
                notification.is_read = True
                notification.updated_at = datetime.utcnow()
                self.db.commit()
                
                logger.info(f"Marked notification as read: {notification_id}")
                return True
            
            return False
            
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Failed to mark notification as read {notification_id}: {str(e)}")
            raise
    
    async def mark_user_notifications_as_read(
        self, 
        user_id: str, 
        notification_ids: Optional[List[str]] = None
    ) -> int:
        """批量标记用户通知为已读"""
        try:
            query = self.db.query(Notification).filter(
                Notification.user_id == user_id,
                Notification.is_deleted == False
            )
            
            if notification_ids:
                # 标记指定通知
                query = query.filter(Notification.id.in_(notification_ids))
            else:
                # 标记所有未读通知
                query = query.filter(Notification.is_read == False)
            
            # 批量更新
            count = query.update({
                Notification.is_read: True,
                Notification.updated_at: datetime.utcnow()
            }, synchronize_session=False)
            
            self.db.commit()
            
            logger.info(f"Marked {count} notifications as read for user {user_id}")
            return count
            
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Failed to mark notifications as read for user {user_id}: {str(e)}")
            raise
    
    async def delete_notification(self, notification_id: str) -> bool:
        """删除通知（软删除）"""
        try:
            notification = self.db.query(Notification).filter(
                Notification.id == notification_id
            ).first()
            
            if notification:
                notification.is_deleted = True
                notification.updated_at = datetime.utcnow()
                self.db.commit()
                
                logger.info(f"Deleted notification: {notification_id}")
                return True
            
            return False
            
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Failed to delete notification {notification_id}: {str(e)}")
            raise
    
    async def delete_user_notifications(self, user_id: str) -> int:
        """删除用户所有通知（软删除）"""
        try:
            count = self.db.query(Notification).filter(
                Notification.user_id == user_id
            ).update({
                Notification.is_deleted: True,
                Notification.updated_at: datetime.utcnow()
            }, synchronize_session=False)
            
            self.db.commit()
            
            logger.info(f"Deleted {count} notifications for user {user_id}")
            return count
            
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Failed to delete notifications for user {user_id}: {str(e)}")
            raise
    
    async def get_unread_count(self, user_id: str) -> int:
        """获取用户未读通知数量"""
        try:
            count = self.db.query(Notification).filter(
                Notification.user_id == user_id,
                Notification.is_read == False,
                Notification.is_deleted == False
            ).count()
            
            return count
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to get unread count for user {user_id}: {str(e)}")
            raise
    
    async def cleanup_expired_notifications(self) -> int:
        """清理过期通知"""
        try:
            now = datetime()
            count = self.db.query(Notification).filter(
                Notification.expires_at <= now,
                Notification.is_deleted == False
            ).update({
                Notification.is_deleted: True,
                Notification.updated_at: now
            }, synchronize_session=False)
            
            self.db.commit()
            
            logger.info(f"Cleaned up {count} expired notifications")
            return count
            
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Failed to cleanup expired notifications: {str(e)}")
            raise
    
    async def get_notification_statistics(
        self, 
        user_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """获取通知统计信息"""
        try:
            from sqlalchemy import func
            
            # 构建基础查询
            query = self.db.query(Notification).filter(
                Notification.is_deleted == False
            )
            
            if user_id:
                query = query.filter(Notification.user_id == user_id)
                
            if start_date:
                query = query.filter(Notification.created_at >= start_date)
                
            if end_date:
                query = query.filter(Notification.created_at <= end_date)
            
            # 总数统计
            total_count = query.count()
            
            # 未读数统计
            unread_count = query.filter(Notification.is_read == False).count()
            
            # 按类型统计
            type_stats = dict(
                query.with_entities(
                    Notification.notification_type,
                    func.count(Notification.id)
                ).group_by(Notification.notification_type).all()
            )
            
            # 按优先级统计
            priority_stats = dict(
                query.with_entities(
                    Notification.priority,
                    func.count(Notification.id)
                ).group_by(Notification.priority).all()
            )
            
            return {
                "total_count": total_count,
                "unread_count": unread_count,
                "read_count": total_count - unread_count,
                "type_distribution": type_stats,
                "priority_distribution": priority_stats
            }
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to get notification statistics: {str(e)}")
            raise
    
    async def broadcast_notification(
        self,
        user_ids: List[str],
        title: str,
        content: str,
        notification_type: str = "info",
        priority: int = 1,
        metadata: Optional[Dict[str, Any]] = None,
        expires_at: Optional[datetime] = None
    ) -> int:
        """广播通知给多个用户"""
        try:
            success_count = 0
            
            for user_id in user_ids:
                try:
                    await self.create_notification(
                        user_id=user_id,
                        title=title,
                        content=content,
                        notification_type=notification_type,
                        priority=priority,
                        metadata=metadata,
                        expires_at=expires_at
                    )
                    success_count += 1
                except Exception as e:
                    logger.error(f"Failed to create notification for user {user_id}: {str(e)}")
            
            logger.info(f"Broadcast notification to {success_count}/{len(user_ids)} users")
            return success_count
            
        except Exception as e:
            logger.error(f"Failed to broadcast notification: {str(e)}")
            return 0