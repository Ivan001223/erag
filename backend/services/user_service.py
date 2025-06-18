"""用户管理服务"""

import asyncio
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from uuid import uuid4
import hashlib
import secrets
import jwt
from passlib.context import CryptContext

from ..config import get_settings
from ..config.constants import (
    UserRole, UserStatus, AuthProvider,
    JWT_ALGORITHM, JWT_ACCESS_TOKEN_EXPIRE_MINUTES, JWT_REFRESH_TOKEN_EXPIRE_DAYS
)
from ..connectors import RedisClient
from ..models import (
    User, UserSession, UserActivity, UserProfile, UserStats, UserPreferences,
    Permission, APIResponse, PaginatedResponse, ErrorResponse
)
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from ..utils import get_logger


class UserService:
    """用户管理服务"""
    
    def __init__(
        self,
        db: Session,
        redis_client: RedisClient
    ):
        self.db = db
        self.redis = redis_client  # 保留用于缓存和会话管理
        self.settings = get_settings()
        self.logger = get_logger(__name__)
        
        # 密码加密上下文
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        
        # 权限定义
        self.permissions = {
            UserRole.ADMIN: [
                "user:create", "user:read", "user:update", "user:delete",
                "document:create", "document:read", "document:update", "document:delete",
                "knowledge:create", "knowledge:read", "knowledge:update", "knowledge:delete",
                "task:create", "task:read", "task:update", "task:delete",
                "system:read", "system:update", "system:manage"
            ],
            UserRole.EDITOR: [
                "user:read",
                "document:create", "document:read", "document:update", "document:delete",
                "knowledge:create", "knowledge:read", "knowledge:update",
                "task:create", "task:read", "task:update"
            ],
            UserRole.VIEWER: [
                "user:read",
                "document:read",
                "knowledge:read",
                "task:read"
            ],
            UserRole.GUEST: [
                "document:read",
                "knowledge:read"
            ]
        }
    
    async def create_user(
        self,
        username: str,
        email: str,
        password: str,
        full_name: Optional[str] = None,
        role: UserRole = UserRole.VIEWER,
        auth_provider: AuthProvider = AuthProvider.LOCAL,
        created_by: Optional[str] = None
    ) -> APIResponse[User]:
        """创建用户"""
        try:
            # 检查用户名和邮箱是否已存在
            existing_user = await self._get_user_by_username_or_email(username, email)
            if existing_user:
                return ErrorResponse(
                    message="Username or email already exists",
                    error_code="USER_ALREADY_EXISTS"
                )
            
            # 验证密码强度
            if not self._validate_password_strength(password):
                return ErrorResponse(
                    message="Password does not meet security requirements",
                    error_code="WEAK_PASSWORD"
                )
            
            # 加密密码
            hashed_password = self.pwd_context.hash(password)
            
            # 创建用户对象
            user = User(
                id=str(uuid4()),
                username=username,
                email=email,
                password_hash=hashed_password,
                full_name=full_name or username,
                role=role,
                status=UserStatus.ACTIVE,
                auth_provider=auth_provider,
                profile=UserProfile(),
                preferences=UserPreferences(),
                stats=UserStats(),
                created_by=created_by
            )
            
            # 保存用户到数据库
            try:
                self.db.add(user)
                self.db.commit()
                self.db.refresh(user)
            except IntegrityError:
                self.db.rollback()
                return ErrorResponse(
                    message="Username or email already exists",
                    error_code="USER_ALREADY_EXISTS"
                )
            
            # 记录用户活动
            await self._log_user_activity(
                user_id=user.id,
                action="user_created",
                details={"created_by": created_by}
            )
            
            # 返回用户信息（不包含密码）
            user_dict = user.dict()
            user_dict.pop("password_hash", None)
            
            self.logger.info(f"User created: {username} ({user.id})")
            return APIResponse(
                status="success",
                message="User created successfully",
                data=User(**user_dict)
            )
            
        except Exception as e:
            self.logger.error(f"Error creating user: {str(e)}")
            return ErrorResponse(
                message=f"Failed to create user: {str(e)}",
                error_code="USER_CREATION_FAILED"
            )
    
    async def authenticate_user(
        self,
        username: str,
        password: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> APIResponse[Dict[str, Any]]:
        """用户认证"""
        try:
            # 获取用户
            user = await self._get_user_by_username_or_email(username)
            if not user:
                return ErrorResponse(
                    message="Invalid username or password",
                    error_code="AUTHENTICATION_FAILED"
                )
            
            # 检查用户状态
            if user.status != UserStatus.ACTIVE:
                return ErrorResponse(
                    message="User account is not active",
                    error_code="ACCOUNT_INACTIVE"
                )
            
            # 验证密码
            if not self.pwd_context.verify(password, user.password_hash):
                # 记录失败的登录尝试
                await self._log_failed_login_attempt(username, ip_address)
                return ErrorResponse(
                    message="Invalid username or password",
                    error_code="AUTHENTICATION_FAILED"
                )
            
            # 检查账户是否被锁定
            if await self._is_account_locked(user.id):
                return ErrorResponse(
                    message="Account is temporarily locked due to multiple failed login attempts",
                    error_code="ACCOUNT_LOCKED"
                )
            
            # 生成访问令牌和刷新令牌
            access_token = self._generate_access_token(user)
            refresh_token = self._generate_refresh_token(user)
            
            # 创建用户会话
            session = UserSession(
                id=str(uuid4()),
                user_id=user.id,
                access_token=access_token,
                refresh_token=refresh_token,
                ip_address=ip_address,
                user_agent=user_agent,
                expires_at=datetime.now() + timedelta(minutes=JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
            )
            
            await self._save_user_session(session)
            
            # 更新用户最后登录时间
            user.last_login_at = datetime.now()
            user.stats.login_count += 1
            await self._update_user(user)
            
            # 记录用户活动
            await self._log_user_activity(
                user_id=user.id,
                action="user_login",
                details={
                    "ip_address": ip_address,
                    "user_agent": user_agent
                }
            )
            
            # 清除失败的登录尝试记录
            await self._clear_failed_login_attempts(username)
            
            self.logger.info(f"User authenticated: {username} ({user.id})")
            return APIResponse(
                status="success",
                message="Authentication successful",
                data={
                    "user": user.dict(exclude={"password_hash"}),
                    "access_token": access_token,
                    "refresh_token": refresh_token,
                    "token_type": "bearer",
                    "expires_in": JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60
                }
            )
            
        except Exception as e:
            self.logger.error(f"Error authenticating user: {str(e)}")
            return ErrorResponse(
                message=f"Authentication failed: {str(e)}",
                error_code="AUTHENTICATION_ERROR"
            )
    
    async def refresh_token(self, refresh_token: str) -> APIResponse[Dict[str, Any]]:
        """刷新访问令牌"""
        try:
            # 验证刷新令牌
            payload = jwt.decode(
                refresh_token,
                self.settings.SECRET_KEY,
                algorithms=[JWT_ALGORITHM]
            )
            
            user_id = payload.get("sub")
            if not user_id:
                return ErrorResponse(
                    message="Invalid refresh token",
                    error_code="INVALID_TOKEN"
                )
            
            # 获取用户
            user = await self._get_user_by_id(user_id)
            if not user or user.status != UserStatus.ACTIVE:
                return ErrorResponse(
                    message="User not found or inactive",
                    error_code="USER_NOT_FOUND"
                )
            
            # 检查会话是否存在
            session = await self._get_session_by_refresh_token(refresh_token)
            if not session or session.is_expired():
                return ErrorResponse(
                    message="Session expired or not found",
                    error_code="SESSION_EXPIRED"
                )
            
            # 生成新的访问令牌
            new_access_token = self._generate_access_token(user)
            
            # 更新会话
            session.access_token = new_access_token
            session.expires_at = datetime.now() + timedelta(minutes=JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
            session.mark_updated()
            
            await self._update_user_session(session)
            
            return APIResponse(
                status="success",
                message="Token refreshed successfully",
                data={
                    "access_token": new_access_token,
                    "token_type": "bearer",
                    "expires_in": JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60
                }
            )
            
        except jwt.ExpiredSignatureError:
            return ErrorResponse(
                message="Refresh token expired",
                error_code="TOKEN_EXPIRED"
            )
        except jwt.InvalidTokenError:
            return ErrorResponse(
                message="Invalid refresh token",
                error_code="INVALID_TOKEN"
            )
        except Exception as e:
            self.logger.error(f"Error refreshing token: {str(e)}")
            return ErrorResponse(
                message=f"Token refresh failed: {str(e)}",
                error_code="TOKEN_REFRESH_FAILED"
            )
    
    async def logout_user(self, access_token: str) -> APIResponse[bool]:
        """用户登出"""
        try:
            # 验证访问令牌
            payload = jwt.decode(
                access_token,
                self.settings.SECRET_KEY,
                algorithms=[JWT_ALGORITHM]
            )
            
            user_id = payload.get("sub")
            if not user_id:
                return ErrorResponse(
                    message="Invalid access token",
                    error_code="INVALID_TOKEN"
                )
            
            # 获取并删除会话
            session = await self._get_session_by_access_token(access_token)
            if session:
                await self._delete_user_session(session.id)
            
            # 将令牌加入黑名单
            await self._blacklist_token(access_token)
            
            # 记录用户活动
            await self._log_user_activity(
                user_id=user_id,
                action="user_logout"
            )
            
            self.logger.info(f"User logged out: {user_id}")
            return APIResponse(
                status="success",
                message="Logout successful",
                data=True
            )
            
        except jwt.InvalidTokenError:
            return ErrorResponse(
                message="Invalid access token",
                error_code="INVALID_TOKEN"
            )
        except Exception as e:
            self.logger.error(f"Error logging out user: {str(e)}")
            return ErrorResponse(
                message=f"Logout failed: {str(e)}",
                error_code="LOGOUT_FAILED"
            )
    
    async def get_user(self, user_id: str) -> APIResponse[User]:
        """获取用户信息"""
        try:
            user = await self._get_user_by_id(user_id)
            if not user:
                return ErrorResponse(
                    message="User not found",
                    error_code="NOT_FOUND"
                )
            
            # 返回用户信息（不包含密码）
            user_dict = user.dict()
            user_dict.pop("password_hash", None)
            
            return APIResponse(
                status="success",
                message="User retrieved successfully",
                data=User(**user_dict)
            )
            
        except Exception as e:
            self.logger.error(f"Error getting user {user_id}: {str(e)}")
            return ErrorResponse(
                message=f"Failed to get user: {str(e)}",
                error_code="GET_FAILED"
            )
    
    async def update_user(
        self,
        user_id: str,
        updates: Dict[str, Any],
        updated_by: Optional[str] = None
    ) -> APIResponse[User]:
        """更新用户信息"""
        try:
            user = await self._get_user_by_id(user_id)
            if not user:
                return ErrorResponse(
                    message="User not found",
                    error_code="NOT_FOUND"
                )
            
            # 验证更新字段
            allowed_fields = {
                "full_name", "email", "role", "status", "profile", "preferences"
            }
            
            invalid_fields = set(updates.keys()) - allowed_fields
            if invalid_fields:
                return ErrorResponse(
                    message=f"Invalid fields: {', '.join(invalid_fields)}",
                    error_code="INVALID_FIELDS"
                )
            
            # 检查邮箱是否已被其他用户使用
            if "email" in updates and updates["email"] != user.email:
                existing_user = await self._get_user_by_email(updates["email"])
                if existing_user and existing_user.id != user_id:
                    return ErrorResponse(
                        message="Email already in use",
                        error_code="EMAIL_IN_USE"
                    )
            
            # 应用更新
            for field, value in updates.items():
                if hasattr(user, field):
                    setattr(user, field, value)
            
            user.updated_by = updated_by
            user.mark_updated()
            
            await self._update_user(user)
            
            # 记录用户活动
            await self._log_user_activity(
                user_id=user_id,
                action="user_updated",
                details={
                    "updated_fields": list(updates.keys()),
                    "updated_by": updated_by
                }
            )
            
            # 返回更新后的用户信息（不包含密码）
            user_dict = user.dict()
            user_dict.pop("password_hash", None)
            
            self.logger.info(f"User updated: {user_id}")
            return APIResponse(
                status="success",
                message="User updated successfully",
                data=User(**user_dict)
            )
            
        except Exception as e:
            self.logger.error(f"Error updating user {user_id}: {str(e)}")
            return ErrorResponse(
                message=f"Failed to update user: {str(e)}",
                error_code="UPDATE_FAILED"
            )
    
    async def change_password(
        self,
        user_id: str,
        current_password: str,
        new_password: str
    ) -> APIResponse[bool]:
        """修改密码"""
        try:
            user = await self._get_user_by_id(user_id)
            if not user:
                return ErrorResponse(
                    message="User not found",
                    error_code="NOT_FOUND"
                )
            
            # 验证当前密码
            if not self.pwd_context.verify(current_password, user.password_hash):
                return ErrorResponse(
                    message="Current password is incorrect",
                    error_code="INVALID_PASSWORD"
                )
            
            # 验证新密码强度
            if not self._validate_password_strength(new_password):
                return ErrorResponse(
                    message="New password does not meet security requirements",
                    error_code="WEAK_PASSWORD"
                )
            
            # 检查新密码是否与当前密码相同
            if self.pwd_context.verify(new_password, user.password_hash):
                return ErrorResponse(
                    message="New password must be different from current password",
                    error_code="SAME_PASSWORD"
                )
            
            # 更新密码
            user.password_hash = self.pwd_context.hash(new_password)
            user.mark_updated()
            
            await self._update_user(user)
            
            # 记录用户活动
            await self._log_user_activity(
                user_id=user_id,
                action="password_changed"
            )
            
            # 使所有现有会话失效
            await self._invalidate_user_sessions(user_id)
            
            self.logger.info(f"Password changed for user: {user_id}")
            return APIResponse(
                status="success",
                message="Password changed successfully",
                data=True
            )
            
        except Exception as e:
            self.logger.error(f"Error changing password for user {user_id}: {str(e)}")
            return ErrorResponse(
                message=f"Failed to change password: {str(e)}",
                error_code="PASSWORD_CHANGE_FAILED"
            )
    
    async def list_users(
        self,
        role: Optional[UserRole] = None,
        status: Optional[UserStatus] = None,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> APIResponse[PaginatedResponse[User]]:
        """列出用户"""
        try:
            # 使用SQLAlchemy查询替代原始SQL
            
            # 构建SQLAlchemy查询
            query = self.db.query(User).filter(User.deleted_at.is_(None))
            
            # 应用过滤条件
            if role:
                query = query.filter(User.role == role)
            if status:
                query = query.filter(User.status == status)
            if search:
                search_pattern = f"%{search}%"
                query = query.filter(
                    (User.username.like(search_pattern)) |
                    (User.email.like(search_pattern)) |
                    (User.full_name.like(search_pattern))
                )
            
            # 计算总数
            total = query.count()
            
            # 分页查询
            offset = (page - 1) * page_size
            users = query.order_by(User.created_at.desc()).offset(offset).limit(page_size).all()
            
            # 移除密码哈希
            user_list = []
            for user in users:
                user_dict = user.__dict__.copy()
                user_dict.pop("password_hash", None)
                user_dict.pop("_sa_instance_state", None)
                user_list.append(User(**user_dict))
            
            return APIResponse(
                status="success",
                message=f"Found {len(user_list)} users",
                data=PaginatedResponse(
                    items=user_list,
                    total=total,
                    page=page,
                    page_size=page_size,
                    total_pages=(total + page_size - 1) // page_size
                )
            )
            
        except Exception as e:
            self.logger.error(f"Error listing users: {str(e)}")
            return ErrorResponse(
                message=f"Failed to list users: {str(e)}",
                error_code="LIST_FAILED"
            )
    
    async def delete_user(
        self,
        user_id: str,
        deleted_by: Optional[str] = None
    ) -> APIResponse[bool]:
        """删除用户（软删除）"""
        try:
            user = await self._get_user_by_id(user_id)
            if not user:
                return ErrorResponse(
                    message="User not found",
                    error_code="NOT_FOUND"
                )
            
            # 软删除用户
            user.status = UserStatus.DELETED
            user.deleted_at = datetime.now()
            user.updated_by = deleted_by
            user.mark_updated()
            
            await self._update_user(user)
            
            # 使所有会话失效
            await self._invalidate_user_sessions(user_id)
            
            # 记录用户活动
            await self._log_user_activity(
                user_id=user_id,
                action="user_deleted",
                details={"deleted_by": deleted_by}
            )
            
            self.logger.info(f"User deleted: {user_id}")
            return APIResponse(
                status="success",
                message="User deleted successfully",
                data=True
            )
            
        except Exception as e:
            self.logger.error(f"Error deleting user {user_id}: {str(e)}")
            return ErrorResponse(
                message=f"Failed to delete user: {str(e)}",
                error_code="DELETE_FAILED"
            )
    
    async def check_permission(
        self,
        user_id: str,
        permission: str
    ) -> APIResponse[bool]:
        """检查用户权限"""
        try:
            user = await self._get_user_by_id(user_id)
            if not user or user.status != UserStatus.ACTIVE:
                return APIResponse(
                    status="success",
                    message="Permission denied",
                    data=False
                )
            
            # 检查角色权限
            user_permissions = self.permissions.get(user.role, [])
            has_permission = permission in user_permissions
            
            return APIResponse(
                status="success",
                message="Permission checked",
                data=has_permission
            )
            
        except Exception as e:
            self.logger.error(f"Error checking permission for user {user_id}: {str(e)}")
            return APIResponse(
                status="success",
                message="Permission denied",
                data=False
            )
    
    async def get_user_activities(
        self,
        user_id: str,
        action: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> APIResponse[PaginatedResponse[UserActivity]]:
        """获取用户活动记录"""
        try:
            # 使用SQLAlchemy查询替代原始SQL
            
            # 构建SQLAlchemy查询
            query = self.db.query(UserActivity)
            
            # 应用过滤条件
            if user_id:
                query = query.filter(UserActivity.user_id == user_id)
            if activity_type:
                query = query.filter(UserActivity.activity_type == activity_type)
            if start_date:
                query = query.filter(UserActivity.created_at >= start_date)
            if end_date:
                query = query.filter(UserActivity.created_at <= end_date)
            
            # 计算总数
            total = query.count()
            
            # 分页查询
            offset = (page - 1) * page_size
            activities = query.order_by(UserActivity.created_at.desc()).offset(offset).limit(page_size).all()
            
            return APIResponse(
                status="success",
                message=f"Found {len(activities)} activities",
                data=PaginatedResponse(
                    items=activities,
                    total=total,
                    page=page,
                    page_size=page_size,
                    total_pages=(total + page_size - 1) // page_size
                )
            )
            
        except Exception as e:
            self.logger.error(f"Error getting user activities: {str(e)}")
            return ErrorResponse(
                message=f"Failed to get user activities: {str(e)}",
                error_code="GET_ACTIVITIES_FAILED"
            )
    
    # 私有方法
    
    def _validate_password_strength(self, password: str) -> bool:
        """验证密码强度"""
        if len(password) < 8:
            return False
        
        has_upper = any(c.isupper() for c in password)
        has_lower = any(c.islower() for c in password)
        has_digit = any(c.isdigit() for c in password)
        has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password)
        
        return sum([has_upper, has_lower, has_digit, has_special]) >= 3
    
    def _generate_access_token(self, user: User) -> str:
        """生成访问令牌"""
        payload = {
            "sub": user.id,
            "username": user.username,
            "role": user.role.value,
            "exp": datetime.utcnow() + timedelta(minutes=JWT_ACCESS_TOKEN_EXPIRE_MINUTES),
            "iat": datetime.utcnow(),
            "type": "access"
        }
        
        return jwt.encode(payload, self.settings.SECRET_KEY, algorithm=JWT_ALGORITHM)
    
    def _generate_refresh_token(self, user: User) -> str:
        """生成刷新令牌"""
        payload = {
            "sub": user.id,
            "exp": datetime.utcnow() + timedelta(days=JWT_REFRESH_TOKEN_EXPIRE_DAYS),
            "iat": datetime.utcnow(),
            "type": "refresh"
        }
        
        return jwt.encode(payload, self.settings.SECRET_KEY, algorithm=JWT_ALGORITHM)
    
    async def _save_user(self, user: User) -> None:
        """保存用户"""
        try:
            self.db.add(user)
            self.db.commit()
            self.db.refresh(user)
        except IntegrityError as e:
            self.db.rollback()
            raise e
        
        # 缓存用户信息（不包含密码）
        user_dict = user.__dict__.copy()
        user_dict.pop("password_hash", None)
        user_dict.pop("_sa_instance_state", None)
        await self.redis.set(
            f"user:{user.id}",
            User(**user_dict).json(),
            expire=3600
        )
    
    async def _update_user(self, user: User) -> None:
        """更新用户"""
        try:
            self.db.merge(user)
            self.db.commit()
        except IntegrityError as e:
            self.db.rollback()
            raise e
        
        # 更新缓存
        user_dict = user.__dict__.copy()
        user_dict.pop("password_hash", None)
        user_dict.pop("_sa_instance_state", None)
        await self.redis.set(
            f"user:{user.id}",
            User(**user_dict).json(),
            expire=3600
        )
    
    async def _get_user_by_id(self, user_id: str) -> Optional[User]:
        """根据ID获取用户"""
        # 先从Redis缓存获取
        cached_user = await self.redis.get(f"user:{user_id}")
        if cached_user:
            # 从数据库获取完整信息（包含密码哈希）
            user = self.db.query(User).filter(
                User.id == user_id,
                User.deleted_at.is_(None)
            ).first()
            return user
        
        # 从数据库查询
        user = self.db.query(User).filter(
            User.id == user_id,
            User.deleted_at.is_(None)
        ).first()
        
        if user:
            # 缓存用户信息（不包含密码）
            user_dict = user.dict()
            user_dict.pop("password_hash", None)
            await self.redis.set(
                f"user:{user_id}",
                User(**user_dict).json(),
                expire=3600
            )
            return user
        
        return None
    
    async def _get_user_by_username_or_email(
        self,
        username: str,
        email: Optional[str] = None
    ) -> Optional[User]:
        """根据用户名或邮箱获取用户"""
        if email:
            user = self.db.query(User).filter(
                (User.username == username) | (User.email == email),
                User.deleted_at.is_(None)
            ).first()
        else:
            user = self.db.query(User).filter(
                (User.username == username) | (User.email == username),
                User.deleted_at.is_(None)
            ).first()
        
        return user
    
    async def _get_user_by_email(self, email: str) -> Optional[User]:
        """根据邮箱获取用户"""
        user = self.db.query(User).filter(
            User.email == email,
            User.deleted_at.is_(None)
        ).first()
        
        return user
    
    async def _save_user_session(self, session: UserSession) -> None:
        """保存用户会话"""
        self.db.add(session)
        self.db.commit()
        
        # 缓存会话信息
        await self.redis.set(
            f"session:{session.id}",
            session.json(),
            expire=int(session.expires_at.timestamp() - datetime.now().timestamp())
        )
    
    async def _update_user_session(self, session: UserSession) -> None:
        """更新用户会话"""
        self.db.merge(session)
        self.db.commit()
        
        # 更新缓存
        await self.redis.set(
            f"session:{session.id}",
            session.json(),
            expire=int(session.expires_at.timestamp() - datetime.now().timestamp())
        )
    
    async def _get_session_by_access_token(self, access_token: str) -> Optional[UserSession]:
        """根据访问令牌获取会话"""
        session = self.db.query(UserSession).filter(
            UserSession.access_token == access_token,
            UserSession.deleted_at.is_(None)
        ).first()
        
        return session
    
    async def _get_session_by_refresh_token(self, refresh_token: str) -> Optional[UserSession]:
        """根据刷新令牌获取会话"""
        session = self.db.query(UserSession).filter(
            UserSession.refresh_token == refresh_token,
            UserSession.deleted_at.is_(None)
        ).first()
        
        return session
    
    async def _delete_user_session(self, session_id: str) -> None:
        """删除用户会话"""
        # 软删除数据库记录
        session = self.db.query(UserSession).filter(UserSession.id == session_id).first()
        if session:
            session.deleted_at = datetime.now()
            self.db.commit()
        
        # 删除缓存
        await self.redis.delete(f"session:{session_id}")
    
    async def _invalidate_user_sessions(self, user_id: str) -> None:
        """使用户所有会话失效"""
        # 软删除所有会话
        sessions = self.db.query(UserSession).filter(
            UserSession.user_id == user_id,
            UserSession.deleted_at.is_(None)
        ).all()
        
        for session in sessions:
            session.deleted_at = datetime.now()
            # 删除相关缓存
            await self.redis.delete(f"session:{session.id}")
        
        self.db.commit()
    
    async def _blacklist_token(self, token: str) -> None:
        """将令牌加入黑名单"""
        try:
            # 解析令牌获取过期时间
            payload = jwt.decode(
                token,
                self.settings.SECRET_KEY,
                algorithms=[JWT_ALGORITHM],
                options={"verify_exp": False}
            )
            
            exp = payload.get("exp")
            if exp:
                expire_time = datetime.fromtimestamp(exp)
                ttl = int((expire_time - datetime.now()).total_seconds())
                if ttl > 0:
                    await self.redis.set(f"blacklist:{token}", "1", expire=ttl)
        except:
            # 如果解析失败，设置默认过期时间
            await self.redis.set(f"blacklist:{token}", "1", expire=3600)
    
    async def _log_failed_login_attempt(self, username: str, ip_address: Optional[str]) -> None:
        """记录失败的登录尝试"""
        key = f"failed_login:{username}"
        count = await self.redis.get(key)
        count = int(count) + 1 if count else 1
        
        await self.redis.set(key, str(count), expire=3600)  # 1小时过期
        
        # 记录详细信息
        await self._log_user_activity(
            user_id=None,
            action="failed_login_attempt",
            details={
                "username": username,
                "ip_address": ip_address,
                "attempt_count": count
            }
        )
    
    async def _clear_failed_login_attempts(self, username: str) -> None:
        """清除失败的登录尝试记录"""
        await self.redis.delete(f"failed_login:{username}")
    
    async def _is_account_locked(self, user_id: str) -> bool:
        """检查账户是否被锁定"""
        # 这里可以实现更复杂的锁定逻辑
        # 例如：连续失败次数超过阈值时锁定账户
        return False
    
    async def _log_user_activity(
        self,
        user_id: Optional[str],
        action: str,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """记录用户活动"""
        try:
            activity = UserActivity(
                id=str(uuid4()),
                user_id=user_id,
                action=action,
                details=details or {},
                ip_address=details.get("ip_address") if details else None,
                user_agent=details.get("user_agent") if details else None
            )
            
            # 保存用户活动到数据库
            self.db.add(activity)
            self.db.commit()
            
        except Exception as e:
            self.logger.error(f"Error logging user activity: {str(e)}")