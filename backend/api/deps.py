"""API 依赖项

提供 FastAPI 路由的通用依赖项，包括：
- 数据库连接
- 认证和授权
- 分页参数
- 请求验证
- 缓存管理
"""

from typing import Optional, Generator, Dict, Any
from fastapi import Depends, HTTPException, status, Query, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import time
import hashlib
import json
from functools import wraps

from backend.connectors.neo4j_client import Neo4jClient
from backend.connectors.redis_client import RedisClient
from backend.connectors.minio_client import MinIOClient
from backend.config.settings import get_settings
from backend.config.database import get_db
from backend.utils.logger import get_logger
from backend.models.base import PaginationParams
from backend.models.response import ErrorResponse
from sqlalchemy.orm import Session

# 配置和日志
settings = get_settings()
logger = get_logger(__name__)

# 安全认证
security = HTTPBearer(auto_error=False)

# 全局连接器存储
_connectors: Dict[str, Any] = {}


def set_connectors(connectors: Dict[str, Any]):
    """设置全局连接器实例"""
    global _connectors
    _connectors = connectors


def get_connectors() -> Dict[str, Any]:
    """获取所有连接器实例"""
    return _connectors


# 数据库连接依赖
def get_database() -> Session:
    """获取 SQLAlchemy 数据库会话"""
    return next(get_db())


# 传统数据库客户端依赖（保留用于特定场景）
def get_neo4j_client() -> Neo4jClient:
    """获取 Neo4j 客户端"""
    client = _connectors.get("neo4j")
    if not client:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Neo4j 服务不可用"
        )
    return client


def get_redis_client() -> RedisClient:
    """获取 Redis 客户端"""
    client = _connectors.get("redis")
    if not client:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Redis 服务不可用"
        )
    return client


# StarRocks客户端已移除，核心业务模型已迁移到SQLAlchemy
# 如需大数据分析功能，请使用专门的分析服务


def get_minio_client() -> MinIOClient:
    """获取 MinIO 客户端"""
    client = _connectors.get("minio")
    if not client:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="MinIO 服务不可用"
        )
    return client


# 认证依赖
async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[Dict[str, Any]]:
    """获取当前用户信息
    
    Args:
        credentials: HTTP Bearer 认证凭据
        
    Returns:
        用户信息字典，如果未认证则返回 None
        
    Raises:
        HTTPException: 认证失败时抛出
    """
    if not credentials:
        # 如果没有提供认证信息，返回匿名用户
        return {
            "user_id": "anonymous",
            "username": "anonymous",
            "roles": ["guest"],
            "permissions": ["read"]
        }
    
    token = credentials.credentials
    
    # 这里应该实现真正的 JWT 验证逻辑
    # 目前为了演示，使用简单的 token 验证
    if token == "demo-token":
        return {
            "user_id": "demo-user",
            "username": "demo",
            "roles": ["admin"],
            "permissions": ["read", "write", "delete"]
        }
    
    # 验证失败
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无效的认证凭据",
        headers={"WWW-Authenticate": "Bearer"}
    )


def require_permissions(required_permissions: list[str]):
    """权限检查装饰器
    
    Args:
        required_permissions: 需要的权限列表
        
    Returns:
        装饰器函数
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 从 kwargs 中获取当前用户
            current_user = kwargs.get('current_user')
            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="需要认证"
                )
            
            user_permissions = current_user.get("permissions", [])
            
            # 检查权限
            if not any(perm in user_permissions for perm in required_permissions):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="权限不足"
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator


# 分页依赖
def get_pagination_params(
    page: int = Query(1, ge=1, description="页码，从1开始"),
    size: int = Query(20, ge=1, le=100, description="每页大小，最大100")
) -> PaginationParams:
    """获取分页参数
    
    Args:
        page: 页码
        size: 每页大小
        
    Returns:
        分页参数对象
    """
    return PaginationParams(
        page=page,
        size=size,
        offset=(page - 1) * size
    )


# 请求验证依赖
def validate_request_size(request: Request):
    """验证请求大小
    
    Args:
        request: FastAPI 请求对象
        
    Raises:
        HTTPException: 请求过大时抛出
    """
    content_length = request.headers.get("content-length")
    if content_length:
        content_length = int(content_length)
        max_size = settings.max_request_size  # 默认 10MB
        if content_length > max_size:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"请求体过大，最大允许 {max_size} 字节"
            )


# 缓存依赖
class CacheManager:
    """缓存管理器"""
    
    def __init__(self, redis_client: RedisClient):
        self.redis_client = redis_client
        self.default_ttl = 3600  # 1小时
    
    def _generate_cache_key(self, prefix: str, **kwargs) -> str:
        """生成缓存键
        
        Args:
            prefix: 缓存键前缀
            **kwargs: 用于生成键的参数
            
        Returns:
            缓存键字符串
        """
        # 将参数排序并序列化
        sorted_params = sorted(kwargs.items())
        params_str = json.dumps(sorted_params, sort_keys=True)
        
        # 生成哈希
        hash_obj = hashlib.md5(params_str.encode())
        hash_str = hash_obj.hexdigest()[:16]
        
        return f"{prefix}:{hash_str}"
    
    async def get(self, key: str) -> Optional[Any]:
        """获取缓存值
        
        Args:
            key: 缓存键
            
        Returns:
            缓存值，如果不存在则返回 None
        """
        try:
            value = await self.redis_client.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.warning(f"获取缓存失败: {e}")
            return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """设置缓存值
        
        Args:
            key: 缓存键
            value: 缓存值
            ttl: 过期时间（秒），默认使用 default_ttl
            
        Returns:
            是否设置成功
        """
        try:
            ttl = ttl or self.default_ttl
            serialized_value = json.dumps(value, ensure_ascii=False)
            await self.redis_client.setex(key, ttl, serialized_value)
            return True
        except Exception as e:
            logger.warning(f"设置缓存失败: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """删除缓存
        
        Args:
            key: 缓存键
            
        Returns:
            是否删除成功
        """
        try:
            await self.redis_client.delete(key)
            return True
        except Exception as e:
            logger.warning(f"删除缓存失败: {e}")
            return False
    
    def cache_key(self, prefix: str, **kwargs) -> str:
        """生成缓存键的便捷方法
        
        Args:
            prefix: 缓存键前缀
            **kwargs: 用于生成键的参数
            
        Returns:
            缓存键字符串
        """
        return self._generate_cache_key(prefix, **kwargs)


def get_cache_manager(
    redis_client: RedisClient = Depends(get_redis_client)
) -> CacheManager:
    """获取缓存管理器
    
    Args:
        redis_client: Redis 客户端
        
    Returns:
        缓存管理器实例
    """
    return CacheManager(redis_client)


# 请求限流依赖
class RateLimiter:
    """请求限流器"""
    
    def __init__(self, redis_client: RedisClient):
        self.redis_client = redis_client
    
    async def is_allowed(
        self,
        key: str,
        limit: int,
        window: int
    ) -> tuple[bool, Dict[str, Any]]:
        """检查是否允许请求
        
        Args:
            key: 限流键
            limit: 限制次数
            window: 时间窗口（秒）
            
        Returns:
            (是否允许, 限流信息)
        """
        try:
            current_time = int(time.time())
            window_start = current_time - window
            
            # 使用 Redis 的 ZSET 实现滑动窗口限流
            pipe = self.redis_client.pipeline()
            
            # 移除过期的请求记录
            pipe.zremrangebyscore(key, 0, window_start)
            
            # 获取当前窗口内的请求数
            pipe.zcard(key)
            
            # 添加当前请求
            pipe.zadd(key, {str(current_time): current_time})
            
            # 设置过期时间
            pipe.expire(key, window)
            
            results = await pipe.execute()
            current_count = results[1]
            
            # 检查是否超过限制
            if current_count >= limit:
                return False, {
                    "allowed": False,
                    "limit": limit,
                    "remaining": 0,
                    "reset_time": current_time + window
                }
            
            return True, {
                "allowed": True,
                "limit": limit,
                "remaining": limit - current_count - 1,
                "reset_time": current_time + window
            }
            
        except Exception as e:
            logger.warning(f"限流检查失败: {e}")
            # 限流器故障时允许请求通过
            return True, {
                "allowed": True,
                "limit": limit,
                "remaining": limit - 1,
                "reset_time": current_time + window
            }


def get_rate_limiter(
    redis_client: RedisClient = Depends(get_redis_client)
) -> RateLimiter:
    """获取限流器
    
    Args:
        redis_client: Redis 客户端
        
    Returns:
        限流器实例
    """
    return RateLimiter(redis_client)


def rate_limit(limit: int = 100, window: int = 60):
    """限流装饰器
    
    Args:
        limit: 限制次数
        window: 时间窗口（秒）
        
    Returns:
        装饰器函数
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            # 获取限流器
            rate_limiter = get_rate_limiter()
            
            # 生成限流键（基于 IP 地址）
            client_ip = request.client.host if request.client else "unknown"
            rate_limit_key = f"rate_limit:{client_ip}:{func.__name__}"
            
            # 检查限流
            allowed, info = await rate_limiter.is_allowed(
                rate_limit_key, limit, window
            )
            
            if not allowed:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="请求过于频繁，请稍后重试",
                    headers={
                        "X-RateLimit-Limit": str(info["limit"]),
                        "X-RateLimit-Remaining": str(info["remaining"]),
                        "X-RateLimit-Reset": str(info["reset_time"])
                    }
                )
            
            # 在响应头中添加限流信息
            response = await func(request, *args, **kwargs)
            if hasattr(response, 'headers'):
                response.headers["X-RateLimit-Limit"] = str(info["limit"])
                response.headers["X-RateLimit-Remaining"] = str(info["remaining"])
                response.headers["X-RateLimit-Reset"] = str(info["reset_time"])
            
            return response
        return wrapper
    return decorator


# 健康检查依赖
async def check_service_health() -> Dict[str, str]:
    """检查服务健康状态
    
    Returns:
        服务健康状态字典
    """
    health_status = {}
    
    # 检查各个连接器的健康状态
    for name, connector in _connectors.items():
        try:
            if hasattr(connector, 'health_check'):
                await connector.health_check()
                health_status[name] = "healthy"
            else:
                health_status[name] = "unknown"
        except Exception as e:
            logger.warning(f"{name} 健康检查失败: {e}")
            health_status[name] = "unhealthy"
    
    return health_status


# 请求 ID 生成
def generate_request_id() -> str:
    """生成请求 ID
    
    Returns:
        唯一的请求 ID
    """
    import uuid
    return str(uuid.uuid4())


def get_request_id(request: Request) -> str:
    """获取或生成请求 ID
    
    Args:
        request: FastAPI 请求对象
        
    Returns:
        请求 ID
    """
    # 尝试从请求头获取
    request_id = request.headers.get("X-Request-ID")
    if not request_id:
        # 生成新的请求 ID
        request_id = generate_request_id()
        # 存储到请求状态中
        request.state.request_id = request_id
    
    return request_id