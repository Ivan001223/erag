"""性能监控和优化工具

提供性能监控、缓存管理、异步任务优化等功能。
"""

import asyncio
import time
import functools
import weakref
from typing import Any, Callable, Dict, List, Optional, Union, TypeVar, Generic
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict, deque
from concurrent.futures import ThreadPoolExecutor
import threading
import gc
import psutil

from backend.utils.logger import get_logger

T = TypeVar('T')

logger = get_logger(__name__)


@dataclass
class PerformanceMetrics:
    """性能指标"""
    function_name: str
    call_count: int = 0
    total_time: float = 0.0
    min_time: float = float('inf')
    max_time: float = 0.0
    avg_time: float = 0.0
    error_count: int = 0
    last_call_time: Optional[datetime] = None
    recent_times: deque = field(default_factory=lambda: deque(maxlen=100))


class PerformanceMonitor:
    """性能监控器"""
    
    def __init__(self):
        self.metrics: Dict[str, PerformanceMetrics] = {}
        self.lock = threading.Lock()
        self.enabled = True
    
    def record_call(self, function_name: str, execution_time: float, success: bool = True):
        """记录函数调用性能"""
        if not self.enabled:
            return
        
        with self.lock:
            if function_name not in self.metrics:
                self.metrics[function_name] = PerformanceMetrics(function_name=function_name)
            
            metric = self.metrics[function_name]
            metric.call_count += 1
            metric.total_time += execution_time
            metric.min_time = min(metric.min_time, execution_time)
            metric.max_time = max(metric.max_time, execution_time)
            metric.avg_time = metric.total_time / metric.call_count
            metric.last_call_time = datetime.now()
            metric.recent_times.append(execution_time)
            
            if not success:
                metric.error_count += 1
    
    def get_metrics(self, function_name: Optional[str] = None) -> Union[PerformanceMetrics, Dict[str, PerformanceMetrics]]:
        """获取性能指标"""
        with self.lock:
            if function_name:
                return self.metrics.get(function_name)
            return self.metrics.copy()
    
    def get_slow_functions(self, threshold: float = 1.0) -> List[PerformanceMetrics]:
        """获取慢函数列表"""
        with self.lock:
            return [
                metric for metric in self.metrics.values()
                if metric.avg_time > threshold
            ]
    
    def reset_metrics(self):
        """重置指标"""
        with self.lock:
            self.metrics.clear()
    
    def enable(self):
        """启用监控"""
        self.enabled = True
    
    def disable(self):
        """禁用监控"""
        self.enabled = False


# 全局性能监控器
performance_monitor = PerformanceMonitor()


def monitor_performance(func_name: Optional[str] = None):
    """性能监控装饰器"""
    def decorator(func: Callable) -> Callable:
        name = func_name or f"{func.__module__}.{func.__name__}"
        
        if asyncio.iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                start_time = time.time()
                success = True
                try:
                    result = await func(*args, **kwargs)
                    return result
                except Exception as e:
                    success = False
                    raise
                finally:
                    execution_time = time.time() - start_time
                    performance_monitor.record_call(name, execution_time, success)
            return async_wrapper
        else:
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                start_time = time.time()
                success = True
                try:
                    result = func(*args, **kwargs)
                    return result
                except Exception as e:
                    success = False
                    raise
                finally:
                    execution_time = time.time() - start_time
                    performance_monitor.record_call(name, execution_time, success)
            return sync_wrapper
    
    return decorator


class LRUCache(Generic[T]):
    """LRU缓存实现"""
    
    def __init__(self, maxsize: int = 128, ttl: Optional[int] = None):
        self.maxsize = maxsize
        self.ttl = ttl
        self.cache: Dict[str, T] = {}
        self.access_times: Dict[str, float] = {}
        self.creation_times: Dict[str, float] = {}
        self.lock = threading.Lock()
    
    def get(self, key: str, default: T = None) -> T:
        """获取缓存值"""
        with self.lock:
            current_time = time.time()
            
            if key not in self.cache:
                return default
            
            # 检查TTL
            if self.ttl and current_time - self.creation_times[key] > self.ttl:
                self._remove_key(key)
                return default
            
            # 更新访问时间
            self.access_times[key] = current_time
            return self.cache[key]
    
    def put(self, key: str, value: T) -> None:
        """设置缓存值"""
        with self.lock:
            current_time = time.time()
            
            # 如果key已存在，更新值和时间
            if key in self.cache:
                self.cache[key] = value
                self.access_times[key] = current_time
                self.creation_times[key] = current_time
                return
            
            # 如果缓存已满，移除最久未使用的项
            if len(self.cache) >= self.maxsize:
                self._evict_lru()
            
            # 添加新项
            self.cache[key] = value
            self.access_times[key] = current_time
            self.creation_times[key] = current_time
    
    def remove(self, key: str) -> bool:
        """移除缓存项"""
        with self.lock:
            if key in self.cache:
                self._remove_key(key)
                return True
            return False
    
    def clear(self) -> None:
        """清空缓存"""
        with self.lock:
            self.cache.clear()
            self.access_times.clear()
            self.creation_times.clear()
    
    def size(self) -> int:
        """获取缓存大小"""
        with self.lock:
            return len(self.cache)
    
    def _remove_key(self, key: str):
        """移除指定key的所有信息"""
        del self.cache[key]
        del self.access_times[key]
        del self.creation_times[key]
    
    def _evict_lru(self):
        """移除最久未使用的项"""
        if not self.cache:
            return
        
        # 找到最久未访问的key
        lru_key = min(self.access_times.keys(), key=lambda k: self.access_times[k])
        self._remove_key(lru_key)
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        with self.lock:
            current_time = time.time()
            expired_count = 0
            
            if self.ttl:
                expired_count = sum(
                    1 for creation_time in self.creation_times.values()
                    if current_time - creation_time > self.ttl
                )
            
            return {
                "size": len(self.cache),
                "maxsize": self.maxsize,
                "hit_rate": getattr(self, '_hit_count', 0) / max(getattr(self, '_total_count', 1), 1),
                "expired_count": expired_count,
                "ttl": self.ttl
            }


class AsyncTaskPool:
    """异步任务池"""
    
    def __init__(self, max_workers: int = 10, max_queue_size: int = 100):
        self.max_workers = max_workers
        self.max_queue_size = max_queue_size
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.task_queue = asyncio.Queue(maxsize=max_queue_size)
        self.active_tasks = set()
        self.completed_tasks = 0
        self.failed_tasks = 0
        self.running = False
    
    async def start(self):
        """启动任务池"""
        if self.running:
            return
        
        self.running = True
        # 启动工作协程
        for _ in range(self.max_workers):
            task = asyncio.create_task(self._worker())
            self.active_tasks.add(task)
    
    async def stop(self):
        """停止任务池"""
        self.running = False
        
        # 等待队列清空
        await self.task_queue.join()
        
        # 取消所有活动任务
        for task in self.active_tasks:
            task.cancel()
        
        # 等待所有任务完成
        await asyncio.gather(*self.active_tasks, return_exceptions=True)
        
        # 关闭线程池
        self.executor.shutdown(wait=True)
    
    async def submit_task(self, coro, priority: int = 0):
        """提交任务"""
        if not self.running:
            raise RuntimeError("任务池未启动")
        
        await self.task_queue.put((priority, time.time(), coro))
    
    async def _worker(self):
        """工作协程"""
        while self.running:
            try:
                # 获取任务（优先级队列）
                priority, timestamp, coro = await asyncio.wait_for(
                    self.task_queue.get(), timeout=1.0
                )
                
                try:
                    # 执行任务
                    await coro
                    self.completed_tasks += 1
                except Exception as e:
                    self.failed_tasks += 1
                    logger.error(f"任务执行失败: {str(e)}")
                finally:
                    self.task_queue.task_done()
                    
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"工作协程错误: {str(e)}")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取任务池统计信息"""
        return {
            "max_workers": self.max_workers,
            "queue_size": self.task_queue.qsize(),
            "max_queue_size": self.max_queue_size,
            "active_tasks": len(self.active_tasks),
            "completed_tasks": self.completed_tasks,
            "failed_tasks": self.failed_tasks,
            "running": self.running
        }


class ResourceMonitor:
    """资源监控器"""
    
    def __init__(self):
        self.process = psutil.Process()
        self.start_time = time.time()
        self.peak_memory = 0
        self.gc_collections = {0: 0, 1: 0, 2: 0}
    
    def get_memory_usage(self) -> Dict[str, Any]:
        """获取内存使用情况"""
        try:
            memory_info = self.process.memory_info()
            memory_percent = self.process.memory_percent()
            
            current_memory = memory_info.rss
            if current_memory > self.peak_memory:
                self.peak_memory = current_memory
            
            return {
                "rss_mb": memory_info.rss / 1024 / 1024,
                "vms_mb": memory_info.vms / 1024 / 1024,
                "percent": memory_percent,
                "peak_mb": self.peak_memory / 1024 / 1024,
                "available_mb": psutil.virtual_memory().available / 1024 / 1024
            }
        except Exception as e:
            return {"error": str(e)}
    
    def get_cpu_usage(self) -> Dict[str, Any]:
        """获取CPU使用情况"""
        try:
            cpu_percent = self.process.cpu_percent()
            cpu_times = self.process.cpu_times()
            
            return {
                "percent": cpu_percent,
                "user_time": cpu_times.user,
                "system_time": cpu_times.system,
                "cpu_count": psutil.cpu_count(),
                "load_average": psutil.getloadavg() if hasattr(psutil, 'getloadavg') else None
            }
        except Exception as e:
            return {"error": str(e)}
    
    def get_gc_stats(self) -> Dict[str, Any]:
        """获取垃圾回收统计"""
        try:
            current_collections = {i: gc.get_count()[i] for i in range(3)}
            
            # 计算自上次检查以来的垃圾回收次数
            new_collections = {}
            for generation in range(3):
                new_collections[generation] = (
                    current_collections[generation] - self.gc_collections[generation]
                )
                self.gc_collections[generation] = current_collections[generation]
            
            return {
                "collections": current_collections,
                "new_collections": new_collections,
                "thresholds": gc.get_threshold(),
                "objects": len(gc.get_objects())
            }
        except Exception as e:
            return {"error": str(e)}
    
    def get_uptime(self) -> float:
        """获取运行时间（秒）"""
        return time.time() - self.start_time
    
    def get_all_stats(self) -> Dict[str, Any]:
        """获取所有资源统计"""
        return {
            "memory": self.get_memory_usage(),
            "cpu": self.get_cpu_usage(),
            "gc": self.get_gc_stats(),
            "uptime_seconds": self.get_uptime(),
            "timestamp": datetime.now().isoformat()
        }


class MemoryPool:
    """内存池管理器"""
    
    def __init__(self, block_size: int = 1024, pool_size: int = 100):
        self.block_size = block_size
        self.pool_size = pool_size
        self.available_blocks = deque()
        self.used_blocks = weakref.WeakSet()
        self.allocated_count = 0
        self.recycled_count = 0
        self.lock = threading.Lock()
        
        # 预分配内存块
        self._preallocate()
    
    def _preallocate(self):
        """预分配内存块"""
        for _ in range(self.pool_size):
            block = bytearray(self.block_size)
            self.available_blocks.append(block)
    
    def acquire(self) -> bytearray:
        """获取内存块"""
        with self.lock:
            if self.available_blocks:
                block = self.available_blocks.popleft()
                self.recycled_count += 1
            else:
                block = bytearray(self.block_size)
                self.allocated_count += 1
            
            self.used_blocks.add(block)
            return block
    
    def release(self, block: bytearray):
        """释放内存块"""
        with self.lock:
            if block in self.used_blocks:
                # 清空内存块
                block[:] = b'\x00' * self.block_size
                self.available_blocks.append(block)
    
    def get_stats(self) -> Dict[str, Any]:
        """获取内存池统计"""
        with self.lock:
            return {
                "block_size": self.block_size,
                "pool_size": self.pool_size,
                "available_blocks": len(self.available_blocks),
                "used_blocks": len(self.used_blocks),
                "allocated_count": self.allocated_count,
                "recycled_count": self.recycled_count,
                "memory_usage_mb": (
                    (self.allocated_count * self.block_size) / 1024 / 1024
                )
            }


# 全局实例
resource_monitor = ResourceMonitor()
task_pool = AsyncTaskPool()
memory_pool = MemoryPool()


def optimize_gc():
    """优化垃圾回收设置"""
    # 调整垃圾回收阈值
    gc.set_threshold(1000, 15, 15)
    
    # 启用垃圾回收调试
    if logger.level <= 10:  # DEBUG级别
        gc.set_debug(gc.DEBUG_STATS)


def batch_processor(batch_size: int = 100, timeout: float = 1.0):
    """批处理装饰器"""
    def decorator(func: Callable) -> Callable:
        batch_queue = []
        last_process_time = time.time()
        lock = threading.Lock()
        
        @functools.wraps(func)
        async def wrapper(item):
            nonlocal batch_queue, last_process_time
            
            with lock:
                batch_queue.append(item)
                current_time = time.time()
                
                should_process = (
                    len(batch_queue) >= batch_size or
                    current_time - last_process_time >= timeout
                )
                
                if should_process:
                    items_to_process = batch_queue[:]
                    batch_queue.clear()
                    last_process_time = current_time
                else:
                    return None
            
            if items_to_process:
                return await func(items_to_process)
        
        return wrapper
    return decorator


async def warm_up_cache(cache_func: Callable, warm_up_data: List[Any]):
    """缓存预热"""
    logger.info(f"开始预热缓存，数据量: {len(warm_up_data)}")
    
    tasks = []
    for data in warm_up_data:
        task = asyncio.create_task(cache_func(data))
        tasks.append(task)
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    success_count = sum(1 for r in results if not isinstance(r, Exception))
    logger.info(f"缓存预热完成，成功: {success_count}/{len(warm_up_data)}")


def profile_memory(func: Callable) -> Callable:
    """内存分析装饰器"""
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        # 强制垃圾回收
        gc.collect()
        
        # 记录初始内存
        initial_memory = psutil.Process().memory_info().rss
        
        try:
            result = await func(*args, **kwargs)
            return result
        finally:
            # 记录最终内存
            gc.collect()
            final_memory = psutil.Process().memory_info().rss
            memory_diff = final_memory - initial_memory
            
            if memory_diff > 1024 * 1024:  # 超过1MB
                logger.warning(
                    f"函数 {func.__name__} 内存使用增加: {memory_diff / 1024 / 1024:.2f}MB"
                )
    
    return wrapper 