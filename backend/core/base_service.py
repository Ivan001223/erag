"""基础服务类

提供所有服务的通用功能，包括错误处理、日志记录、缓存和监控。
"""

import asyncio
import functools
import time
import traceback
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional, TypeVar, Generic
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta

from backend.utils.logger import get_logger
from backend.config.settings import get_settings

T = TypeVar('T')


@dataclass
class ServiceMetrics:
    """服务指标"""
    total_calls: int = 0
    success_calls: int = 0
    error_calls: int = 0
    average_response_time_ms: float = 0.0
    last_call_time: Optional[datetime] = None
    last_error_time: Optional[datetime] = None
    error_rate: float = 0.0


class ServiceError(Exception):
    """服务异常基类"""
    def __init__(self, message: str, error_code: str = "SERVICE_ERROR", details: Optional[Dict] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        self.timestamp = datetime.now()


class ValidationError(ServiceError):
    """数据验证异常"""
    def __init__(self, message: str, field: Optional[str] = None, value: Optional[Any] = None):
        super().__init__(message, "VALIDATION_ERROR", {"field": field, "value": value})


class NotFoundError(ServiceError):
    """资源未找到异常"""
    def __init__(self, resource: str, identifier: str):
        super().__init__(f"{resource} not found: {identifier}", "NOT_FOUND", 
                        {"resource": resource, "identifier": identifier})


class ConflictError(ServiceError):
    """资源冲突异常"""
    def __init__(self, message: str, resource: Optional[str] = None):
        super().__init__(message, "CONFLICT", {"resource": resource})


class ExternalServiceError(ServiceError):
    """外部服务异常"""
    def __init__(self, service: str, message: str, status_code: Optional[int] = None):
        super().__init__(f"External service error from {service}: {message}", 
                        "EXTERNAL_SERVICE_ERROR", {"service": service, "status_code": status_code})


class BaseService(ABC):
    """基础服务类
    
    提供所有服务的通用功能，包括：
    - 统一的错误处理
    - 日志记录
    - 性能监控
    - 缓存管理
    - 重试机制
    """
    
    def __init__(self, service_name: Optional[str] = None):
        self.service_name = service_name or self.__class__.__name__
        self.logger = get_logger(f"service.{self.service_name}")
        self.settings = get_settings()
        self.metrics = ServiceMetrics()
        self._cache: Dict[str, Any] = {}
        self._cache_ttl: Dict[str, datetime] = {}
        
    @staticmethod
    def with_error_handling(func: Callable) -> Callable:
        """错误处理装饰器"""
        @functools.wraps(func)
        async def wrapper(self, *args, **kwargs):
            start_time = time.time()
            method_name = func.__name__
            
            try:
                self.logger.debug(f"调用方法: {method_name}", extra={
                    "method": method_name,
                    "args_count": len(args),
                    "kwargs_keys": list(kwargs.keys())
                })
                
                result = await func(self, *args, **kwargs)
                
                # 更新成功指标
                self._update_metrics(True, time.time() - start_time)
                
                self.logger.debug(f"方法执行成功: {method_name}", extra={
                    "method": method_name,
                    "duration_ms": (time.time() - start_time) * 1000
                })
                
                return result
                
            except ServiceError as e:
                # 更新错误指标
                self._update_metrics(False, time.time() - start_time)
                
                self.logger.error(f"服务异常: {method_name} - {e.message}", extra={
                    "method": method_name,
                    "error_code": e.error_code,
                    "error_details": e.details,
                    "duration_ms": (time.time() - start_time) * 1000
                })
                raise
                
            except Exception as e:
                # 更新错误指标
                self._update_metrics(False, time.time() - start_time)
                
                self.logger.error(f"未处理异常: {method_name} - {str(e)}", extra={
                    "method": method_name,
                    "error_type": type(e).__name__,
                    "traceback": traceback.format_exc(),
                    "duration_ms": (time.time() - start_time) * 1000
                })
                
                # 将未处理异常包装为服务异常
                raise ServiceError(f"服务内部错误: {str(e)}", "INTERNAL_ERROR", {
                    "original_error": str(e),
                    "error_type": type(e).__name__
                })
        
        return wrapper
    
    @staticmethod
    def with_retry(max_attempts: int = 3, delay: float = 1.0, backoff: float = 2.0):
        """重试装饰器"""
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            async def wrapper(self, *args, **kwargs):
                last_exception = None
                
                for attempt in range(max_attempts):
                    try:
                        return await func(self, *args, **kwargs)
                    except ServiceError as e:
                        # 某些错误不应该重试
                        if e.error_code in ["VALIDATION_ERROR", "NOT_FOUND", "CONFLICT"]:
                            raise
                        
                        last_exception = e
                        if attempt < max_attempts - 1:
                            wait_time = delay * (backoff ** attempt)
                            self.logger.warning(f"方法 {func.__name__} 第 {attempt + 1} 次尝试失败，{wait_time}秒后重试", extra={
                                "method": func.__name__,
                                "attempt": attempt + 1,
                                "max_attempts": max_attempts,
                                "wait_time": wait_time,
                                "error": str(e)
                            })
                            await asyncio.sleep(wait_time)
                        else:
                            self.logger.error(f"方法 {func.__name__} 所有重试都失败", extra={
                                "method": func.__name__,
                                "max_attempts": max_attempts,
                                "final_error": str(e)
                            })
                    except Exception as e:
                        last_exception = ServiceError(f"重试过程中发生未预期错误: {str(e)}", "RETRY_ERROR")
                        break
                
                raise last_exception
                
            return wrapper
        return decorator
    
    @staticmethod
    def cached(ttl_seconds: int = 300, key_func: Optional[Callable] = None):
        """缓存装饰器"""
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            async def wrapper(self, *args, **kwargs):
                # 生成缓存键
                if key_func:
                    cache_key = key_func(self, *args, **kwargs)
                else:
                    cache_key = f"{func.__name__}:{hash(str(args) + str(kwargs))}"
                
                # 检查缓存
                cached_value = self._get_cached_value(cache_key)
                if cached_value is not None:
                    self.logger.debug(f"缓存命中: {cache_key}")
                    return cached_value
                
                # 执行函数并缓存结果
                result = await func(self, *args, **kwargs)
                self._set_cached_value(cache_key, result, ttl_seconds)
                
                self.logger.debug(f"缓存设置: {cache_key}")
                return result
                
            return wrapper
        return decorator
    
    def _update_metrics(self, success: bool, duration_seconds: float):
        """更新服务指标"""
        self.metrics.total_calls += 1
        self.metrics.last_call_time = datetime.now()
        
        if success:
            self.metrics.success_calls += 1
        else:
            self.metrics.error_calls += 1
            self.metrics.last_error_time = datetime.now()
        
        # 更新平均响应时间（使用移动平均）
        if self.metrics.total_calls == 1:
            self.metrics.average_response_time_ms = duration_seconds * 1000
        else:
            alpha = 0.1  # 平滑因子
            self.metrics.average_response_time_ms = (
                alpha * duration_seconds * 1000 + 
                (1 - alpha) * self.metrics.average_response_time_ms
            )
        
        # 更新错误率
        self.metrics.error_rate = self.metrics.error_calls / self.metrics.total_calls
    
    def _get_cached_value(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        if key not in self._cache:
            return None
        
        # 检查是否过期
        ttl = self._cache_ttl.get(key)
        if ttl and datetime.now() > ttl:
            del self._cache[key]
            del self._cache_ttl[key]
            return None
        
        return self._cache[key]
    
    def _set_cached_value(self, key: str, value: Any, ttl_seconds: int):
        """设置缓存值"""
        self._cache[key] = value
        self._cache_ttl[key] = datetime.now() + timedelta(seconds=ttl_seconds)
    
    def clear_cache(self, pattern: Optional[str] = None):
        """清除缓存"""
        if pattern:
            keys_to_remove = [k for k in self._cache.keys() if pattern in k]
            for key in keys_to_remove:
                del self._cache[key]
                if key in self._cache_ttl:
                    del self._cache_ttl[key]
        else:
            self._cache.clear()
            self._cache_ttl.clear()
    
    def get_metrics(self) -> ServiceMetrics:
        """获取服务指标"""
        return self.metrics
    
    def get_health_status(self) -> Dict[str, Any]:
        """获取健康状态"""
        return {
            "service_name": self.service_name,
            "status": "healthy" if self.metrics.error_rate < 0.1 else "degraded",
            "metrics": {
                "total_calls": self.metrics.total_calls,
                "success_calls": self.metrics.success_calls,
                "error_calls": self.metrics.error_calls,
                "error_rate": self.metrics.error_rate,
                "average_response_time_ms": self.metrics.average_response_time_ms,
                "last_call_time": self.metrics.last_call_time.isoformat() if self.metrics.last_call_time else None,
                "last_error_time": self.metrics.last_error_time.isoformat() if self.metrics.last_error_time else None
            },
            "cache_size": len(self._cache)
        }
    
    @abstractmethod
    async def initialize(self) -> None:
        """初始化服务"""
        pass
    
    @abstractmethod
    async def cleanup(self) -> None:
        """清理服务资源"""
        pass


class AsyncServiceRegistry:
    """异步服务注册表"""
    
    def __init__(self):
        self._services: Dict[str, BaseService] = {}
        self._initialized = False
    
    def register(self, service: BaseService, name: Optional[str] = None):
        """注册服务"""
        service_name = name or service.service_name
        self._services[service_name] = service
    
    def get_service(self, name: str) -> Optional[BaseService]:
        """获取服务"""
        return self._services.get(name)
    
    async def initialize_all(self):
        """初始化所有服务"""
        if self._initialized:
            return
        
        logger = get_logger("service_registry")
        logger.info("开始初始化服务...")
        
        for name, service in self._services.items():
            try:
                await service.initialize()
                logger.info(f"服务初始化成功: {name}")
            except Exception as e:
                logger.error(f"服务初始化失败: {name} - {str(e)}")
                raise
        
        self._initialized = True
        logger.info("所有服务初始化完成")
    
    async def cleanup_all(self):
        """清理所有服务"""
        logger = get_logger("service_registry")
        logger.info("开始清理服务...")
        
        for name, service in self._services.items():
            try:
                await service.cleanup()
                logger.info(f"服务清理成功: {name}")
            except Exception as e:
                logger.error(f"服务清理失败: {name} - {str(e)}")
        
        self._initialized = False
        logger.info("所有服务清理完成")
    
    def get_all_health_status(self) -> Dict[str, Dict[str, Any]]:
        """获取所有服务的健康状态"""
        return {name: service.get_health_status() for name, service in self._services.items()}


# 全局服务注册表
service_registry = AsyncServiceRegistry() 