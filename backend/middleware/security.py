"""安全中间件

提供API限流、JWT认证、权限控制等安全功能。
"""

import asyncio
import time
import jwt
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Callable, Any
from dataclasses import dataclass, field
from collections import defaultdict, deque
from fastapi import Request, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import redis.asyncio as redis
import hashlib
import ipaddress

from backend.config.settings import get_settings
from backend.utils.logger import get_logger
from backend.core.base_service import ServiceError

settings = get_settings()
logger = get_logger(__name__)
security = HTTPBearer()


@dataclass
class RateLimitRule:
    """限流规则"""
    requests_per_minute: int = 60
    requests_per_hour: int = 1000
    requests_per_day: int = 10000
    burst_limit: int = 10  # 突发限制


@dataclass
class UserPermissions:
    """用户权限"""
    roles: Set[str] = field(default_factory=set)
    permissions: Set[str] = field(default_factory=set)
    resource_access: Dict[str, Set[str]] = field(default_factory=dict)


class RateLimiter:
    """API限流器"""
    
    def __init__(self, redis_client: Optional[redis.Redis] = None):
        self.redis = redis_client
        self.local_cache: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.rules: Dict[str, RateLimitRule] = {
            "default": RateLimitRule(),
            "premium": RateLimitRule(requests_per_minute=300, requests_per_hour=5000),
            "admin": RateLimitRule(requests_per_minute=1000, requests_per_hour=20000)
        }
    
    async def is_allowed(
        self, 
        key: str, 
        rule_name: str = "default",
        endpoint: Optional[str] = None
    ) -> tuple[bool, Dict[str, Any]]:
        """检查是否允许请求"""
        rule = self.rules.get(rule_name, self.rules["default"])
        current_time = time.time()
        
        # 使用Redis进行分布式限流
        if self.redis:
            return await self._check_redis_rate_limit(key, rule, current_time, endpoint)
        else:
            return await self._check_local_rate_limit(key, rule, current_time)
    
    async def _check_redis_rate_limit(
        self, 
        key: str, 
        rule: RateLimitRule, 
        current_time: float,
        endpoint: Optional[str]
    ) -> tuple[bool, Dict[str, Any]]:
        """Redis分布式限流检查"""
        pipe = self.redis.pipeline()
        
        # 分钟级限流
        minute_key = f"rate_limit:{key}:minute:{int(current_time // 60)}"
        hour_key = f"rate_limit:{key}:hour:{int(current_time // 3600)}"
        day_key = f"rate_limit:{key}:day:{int(current_time // 86400)}"
        
        # 突发限流（滑动窗口）
        burst_key = f"rate_limit:{key}:burst"
        
        try:
            # 检查突发限流
            pipe.zremrangebyscore(burst_key, 0, current_time - 60)  # 清理1分钟前的记录
            pipe.zcard(burst_key)
            pipe.zadd(burst_key, {str(current_time): current_time})
            pipe.expire(burst_key, 60)
            
            # 检查各时间窗口限流
            pipe.incr(minute_key)
            pipe.expire(minute_key, 60)
            pipe.incr(hour_key)
            pipe.expire(hour_key, 3600)
            pipe.incr(day_key)
            pipe.expire(day_key, 86400)
            
            results = await pipe.execute()
            
            burst_count = results[1]
            minute_count = results[4]
            hour_count = results[6]
            day_count = results[8]
            
            # 检查是否超限
            if burst_count > rule.burst_limit:
                return False, {
                    "error": "burst_limit_exceeded",
                    "limit": rule.burst_limit,
                    "current": burst_count,
                    "reset_time": int(current_time + 60)
                }
            
            if minute_count > rule.requests_per_minute:
                return False, {
                    "error": "minute_limit_exceeded",
                    "limit": rule.requests_per_minute,
                    "current": minute_count,
                    "reset_time": int(current_time // 60 + 1) * 60
                }
            
            if hour_count > rule.requests_per_hour:
                return False, {
                    "error": "hour_limit_exceeded",
                    "limit": rule.requests_per_hour,
                    "current": hour_count,
                    "reset_time": int(current_time // 3600 + 1) * 3600
                }
            
            if day_count > rule.requests_per_day:
                return False, {
                    "error": "day_limit_exceeded",
                    "limit": rule.requests_per_day,
                    "current": day_count,
                    "reset_time": int(current_time // 86400 + 1) * 86400
                }
            
            return True, {
                "allowed": True,
                "minute_remaining": rule.requests_per_minute - minute_count,
                "hour_remaining": rule.requests_per_hour - hour_count,
                "day_remaining": rule.requests_per_day - day_count
            }
            
        except Exception as e:
            logger.error(f"Redis限流检查失败: {str(e)}")
            # 降级到本地限流
            return await self._check_local_rate_limit(key, rule, current_time)
    
    async def _check_local_rate_limit(
        self, 
        key: str, 
        rule: RateLimitRule, 
        current_time: float
    ) -> tuple[bool, Dict[str, Any]]:
        """本地内存限流检查"""
        if key not in self.local_cache:
            self.local_cache[key] = deque(maxlen=1000)
        
        request_times = self.local_cache[key]
        
        # 清理过期记录
        while request_times and current_time - request_times[0] > 86400:  # 24小时
            request_times.popleft()
        
        # 统计各时间窗口的请求数
        minute_count = sum(1 for t in request_times if current_time - t <= 60)
        hour_count = sum(1 for t in request_times if current_time - t <= 3600)
        day_count = len(request_times)
        
        # 检查限流
        if minute_count >= rule.requests_per_minute:
            return False, {"error": "minute_limit_exceeded", "limit": rule.requests_per_minute}
        
        if hour_count >= rule.requests_per_hour:
            return False, {"error": "hour_limit_exceeded", "limit": rule.requests_per_hour}
        
        if day_count >= rule.requests_per_day:
            return False, {"error": "day_limit_exceeded", "limit": rule.requests_per_day}
        
        # 记录请求时间
        request_times.append(current_time)
        
        return True, {
            "allowed": True,
            "minute_remaining": rule.requests_per_minute - minute_count,
            "hour_remaining": rule.requests_per_hour - hour_count,
            "day_remaining": rule.requests_per_day - day_count
        }


class JWTManager:
    """JWT管理器"""
    
    def __init__(self, secret_key: str, algorithm: str = "HS256"):
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.blacklist: Set[str] = set()
    
    def create_token(
        self, 
        user_id: str, 
        permissions: UserPermissions,
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """创建JWT令牌"""
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(hours=24)
        
        payload = {
            "sub": user_id,
            "exp": expire,
            "iat": datetime.utcnow(),
            "roles": list(permissions.roles),
            "permissions": list(permissions.permissions),
            "resource_access": {k: list(v) for k, v in permissions.resource_access.items()}
        }
        
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
    
    def verify_token(self, token: str) -> Dict[str, Any]:
        """验证JWT令牌"""
        try:
            if token in self.blacklist:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token已被撤销"
                )
            
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
            
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token已过期"
            )
        except jwt.JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="无效的Token"
            )
    
    def revoke_token(self, token: str) -> None:
        """撤销令牌"""
        self.blacklist.add(token)
    
    def get_user_permissions(self, payload: Dict[str, Any]) -> UserPermissions:
        """从JWT载荷获取用户权限"""
        return UserPermissions(
            roles=set(payload.get("roles", [])),
            permissions=set(payload.get("permissions", [])),
            resource_access={
                k: set(v) for k, v in payload.get("resource_access", {}).items()
            }
        )


class SecurityMiddleware(BaseHTTPMiddleware):
    """安全中间件"""
    
    def __init__(
        self, 
        app,
        rate_limiter: RateLimiter,
        jwt_manager: JWTManager,
        whitelist_ips: Optional[List[str]] = None,
        blacklist_ips: Optional[List[str]] = None
    ):
        super().__init__(app)
        self.rate_limiter = rate_limiter
        self.jwt_manager = jwt_manager
        self.whitelist_ips = self._parse_ip_list(whitelist_ips or [])
        self.blacklist_ips = self._parse_ip_list(blacklist_ips or [])
        
        # 公开端点（不需要认证）
        self.public_endpoints = {
            "/health", "/health/detailed", "/health/readiness", 
            "/health/liveness", "/metrics", "/docs", "/redoc", "/openapi.json"
        }
    
    def _parse_ip_list(self, ip_list: List[str]) -> List:
        """解析IP列表，支持CIDR格式"""
        parsed_ips = []
        for ip_str in ip_list:
            try:
                if "/" in ip_str:
                    parsed_ips.append(ipaddress.ip_network(ip_str, strict=False))
                else:
                    parsed_ips.append(ipaddress.ip_address(ip_str))
            except ValueError:
                logger.warning(f"无效的IP地址: {ip_str}")
        return parsed_ips
    
    def _check_ip_allowed(self, client_ip: str) -> bool:
        """检查IP是否被允许"""
        try:
            ip = ipaddress.ip_address(client_ip)
            
            # 检查黑名单
            for blocked_ip in self.blacklist_ips:
                if isinstance(blocked_ip, ipaddress.IPv4Network) or isinstance(blocked_ip, ipaddress.IPv6Network):
                    if ip in blocked_ip:
                        return False
                elif ip == blocked_ip:
                    return False
            
            # 如果有白名单，检查是否在白名单中
            if self.whitelist_ips:
                for allowed_ip in self.whitelist_ips:
                    if isinstance(allowed_ip, ipaddress.IPv4Network) or isinstance(allowed_ip, ipaddress.IPv6Network):
                        if ip in allowed_ip:
                            return True
                    elif ip == allowed_ip:
                        return True
                return False
            
            return True
            
        except ValueError:
            logger.warning(f"无效的客户端IP: {client_ip}")
            return False
    
    async def dispatch(self, request: Request, call_next):
        """处理请求"""
        start_time = time.time()
        
        # 获取客户端IP
        client_ip = request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
        if not client_ip:
            client_ip = request.headers.get("X-Real-IP", "")
        if not client_ip:
            client_ip = request.client.host if request.client else "unknown"
        
        # IP白名单/黑名单检查
        if not self._check_ip_allowed(client_ip):
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"error": "IP地址被禁止访问", "ip": client_ip}
            )
        
        # 生成限流键
        rate_limit_key = f"ip:{client_ip}"
        user_id = None
        
        # 认证检查（除公开端点外）
        if request.url.path not in self.public_endpoints and not request.url.path.startswith("/auth"):
            try:
                # 提取JWT令牌
                authorization = request.headers.get("Authorization")
                if not authorization or not authorization.startswith("Bearer "):
                    return JSONResponse(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        content={"error": "缺少认证令牌"}
                    )
                
                token = authorization.split(" ")[1]
                payload = self.jwt_manager.verify_token(token)
                user_id = payload.get("sub")
                
                # 将用户信息添加到请求状态
                request.state.user_id = user_id
                request.state.user_permissions = self.jwt_manager.get_user_permissions(payload)
                
                # 使用用户ID作为限流键
                rate_limit_key = f"user:{user_id}"
                
            except HTTPException as e:
                return JSONResponse(
                    status_code=e.status_code,
                    content={"error": e.detail}
                )
        
        # 限流检查
        rule_name = "admin" if hasattr(request.state, "user_permissions") and "admin" in request.state.user_permissions.roles else "default"
        allowed, limit_info = await self.rate_limiter.is_allowed(
            rate_limit_key, 
            rule_name, 
            request.url.path
        )
        
        if not allowed:
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "请求频率超限",
                    "details": limit_info
                },
                headers={
                    "X-RateLimit-Limit": str(limit_info.get("limit", 0)),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(limit_info.get("reset_time", 0))
                }
            )
        
        # 添加限流信息到响应头
        response = await call_next(request)
        
        if "allowed" in limit_info:
            response.headers["X-RateLimit-Remaining-Minute"] = str(limit_info.get("minute_remaining", 0))
            response.headers["X-RateLimit-Remaining-Hour"] = str(limit_info.get("hour_remaining", 0))
            response.headers["X-RateLimit-Remaining-Day"] = str(limit_info.get("day_remaining", 0))
        
        # 添加安全头
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        # 记录请求日志
        process_time = time.time() - start_time
        logger.info(f"请求处理完成", extra={
            "method": request.method,
            "path": request.url.path,
            "client_ip": client_ip,
            "user_id": user_id,
            "status_code": response.status_code,
            "process_time": process_time
        })
        
        return response


def check_permission(required_permission: str):
    """权限检查装饰器"""
    def decorator(func: Callable) -> Callable:
        async def wrapper(*args, **kwargs):
            request = kwargs.get("request") or (args[0] if args else None)
            
            if not hasattr(request.state, "user_permissions"):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="未认证用户"
                )
            
            permissions = request.state.user_permissions
            if required_permission not in permissions.permissions and "admin" not in permissions.roles:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"缺少权限: {required_permission}"
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def check_role(required_role: str):
    """角色检查装饰器"""
    def decorator(func: Callable) -> Callable:
        async def wrapper(*args, **kwargs):
            request = kwargs.get("request") or (args[0] if args else None)
            
            if not hasattr(request.state, "user_permissions"):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="未认证用户"
                )
            
            permissions = request.state.user_permissions
            if required_role not in permissions.roles:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"缺少角色: {required_role}"
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator 