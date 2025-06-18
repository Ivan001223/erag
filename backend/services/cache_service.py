"""缓存服务"""

import asyncio
import json
import pickle
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union, Callable
from uuid import uuid4
import hashlib

from ..config import get_settings
from ..connectors import RedisClient
from ..utils import get_logger


class CacheService:
    """缓存服务"""
    
    def __init__(self, redis_client: RedisClient):
        self.redis = redis_client
        self.settings = get_settings()
        self.logger = get_logger(__name__)
        
        # 默认过期时间（秒）
        self.default_ttl = {
            "short": 300,      # 5分钟
            "medium": 3600,    # 1小时
            "long": 86400,     # 1天
            "persistent": 604800  # 7天
        }
    
    async def get(
        self,
        key: str,
        default: Any = None,
        deserialize: bool = True
    ) -> Any:
        """获取缓存值"""
        try:
            value = await self.redis.get(key)
            if value is None:
                return default
            
            if deserialize:
                try:
                    # 尝试JSON反序列化
                    return json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    try:
                        # 尝试pickle反序列化
                        return pickle.loads(value)
                    except:
                        # 返回原始字符串
                        return value
            else:
                return value
                
        except Exception as e:
            self.logger.error(f"Error getting cache key {key}: {str(e)}")
            return default
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Union[int, str] = "medium",
        serialize: bool = True
    ) -> bool:
        """设置缓存值"""
        try:
            # 处理过期时间
            if isinstance(ttl, str):
                expire_seconds = self.default_ttl.get(ttl, self.default_ttl["medium"])
            else:
                expire_seconds = ttl
            
            # 序列化值
            if serialize:
                try:
                    # 尝试JSON序列化
                    serialized_value = json.dumps(value, default=str)
                except (TypeError, ValueError):
                    # 使用pickle序列化
                    serialized_value = pickle.dumps(value)
            else:
                serialized_value = value
            
            await self.redis.set(key, serialized_value, expire=expire_seconds)
            return True
            
        except Exception as e:
            self.logger.error(f"Error setting cache key {key}: {str(e)}")
            return False
    
    async def delete(self, key: str) -> bool:
        """删除缓存键"""
        try:
            result = await self.redis.delete(key)
            return result > 0
        except Exception as e:
            self.logger.error(f"Error deleting cache key {key}: {str(e)}")
            return False
    
    async def exists(self, key: str) -> bool:
        """检查键是否存在"""
        try:
            return await self.redis.exists(key)
        except Exception as e:
            self.logger.error(f"Error checking cache key {key}: {str(e)}")
            return False
    
    async def expire(self, key: str, ttl: Union[int, str]) -> bool:
        """设置键的过期时间"""
        try:
            if isinstance(ttl, str):
                expire_seconds = self.default_ttl.get(ttl, self.default_ttl["medium"])
            else:
                expire_seconds = ttl
            
            return await self.redis.expire(key, expire_seconds)
        except Exception as e:
            self.logger.error(f"Error setting expiry for cache key {key}: {str(e)}")
            return False
    
    async def ttl(self, key: str) -> int:
        """获取键的剩余生存时间"""
        try:
            return await self.redis.ttl(key)
        except Exception as e:
            self.logger.error(f"Error getting TTL for cache key {key}: {str(e)}")
            return -1
    
    async def increment(self, key: str, amount: int = 1) -> int:
        """递增计数器"""
        try:
            return await self.redis.incr(key, amount)
        except Exception as e:
            self.logger.error(f"Error incrementing cache key {key}: {str(e)}")
            return 0
    
    async def decrement(self, key: str, amount: int = 1) -> int:
        """递减计数器"""
        try:
            return await self.redis.decr(key, amount)
        except Exception as e:
            self.logger.error(f"Error decrementing cache key {key}: {str(e)}")
            return 0
    
    async def get_or_set(
        self,
        key: str,
        factory: Callable,
        ttl: Union[int, str] = "medium",
        *args,
        **kwargs
    ) -> Any:
        """获取缓存值，如果不存在则通过工厂函数生成并缓存"""
        try:
            # 尝试从缓存获取
            value = await self.get(key)
            if value is not None:
                return value
            
            # 生成新值
            if asyncio.iscoroutinefunction(factory):
                value = await factory(*args, **kwargs)
            else:
                value = factory(*args, **kwargs)
            
            # 缓存新值
            if value is not None:
                await self.set(key, value, ttl)
            
            return value
            
        except Exception as e:
            self.logger.error(f"Error in get_or_set for key {key}: {str(e)}")
            # 如果缓存操作失败，直接调用工厂函数
            try:
                if asyncio.iscoroutinefunction(factory):
                    return await factory(*args, **kwargs)
                else:
                    return factory(*args, **kwargs)
            except Exception as factory_error:
                self.logger.error(f"Error in factory function: {str(factory_error)}")
                return None
    
    async def mget(self, keys: List[str]) -> Dict[str, Any]:
        """批量获取缓存值"""
        try:
            values = await self.redis.mget(keys)
            result = {}
            
            for i, key in enumerate(keys):
                if i < len(values) and values[i] is not None:
                    try:
                        result[key] = json.loads(values[i])
                    except (json.JSONDecodeError, TypeError):
                        try:
                            result[key] = pickle.loads(values[i])
                        except:
                            result[key] = values[i]
                else:
                    result[key] = None
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error in mget for keys {keys}: {str(e)}")
            return {key: None for key in keys}
    
    async def mset(
        self,
        mapping: Dict[str, Any],
        ttl: Union[int, str] = "medium"
    ) -> bool:
        """批量设置缓存值"""
        try:
            # 序列化所有值
            serialized_mapping = {}
            for key, value in mapping.items():
                try:
                    serialized_mapping[key] = json.dumps(value, default=str)
                except (TypeError, ValueError):
                    serialized_mapping[key] = pickle.dumps(value)
            
            # 批量设置
            await self.redis.mset(serialized_mapping)
            
            # 设置过期时间
            if isinstance(ttl, str):
                expire_seconds = self.default_ttl.get(ttl, self.default_ttl["medium"])
            else:
                expire_seconds = ttl
            
            if expire_seconds > 0:
                tasks = [self.redis.expire(key, expire_seconds) for key in mapping.keys()]
                await asyncio.gather(*tasks, return_exceptions=True)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error in mset: {str(e)}")
            return False
    
    async def delete_pattern(self, pattern: str) -> int:
        """删除匹配模式的所有键"""
        try:
            keys = await self.redis.keys(pattern)
            if keys:
                deleted = await self.redis.delete(*keys)
                return deleted
            return 0
        except Exception as e:
            self.logger.error(f"Error deleting pattern {pattern}: {str(e)}")
            return 0
    
    async def clear_namespace(self, namespace: str) -> int:
        """清除命名空间下的所有缓存"""
        pattern = f"{namespace}:*"
        return await self.delete_pattern(pattern)
    
    # 列表操作
    
    async def lpush(self, key: str, *values: Any) -> int:
        """从左侧推入列表"""
        try:
            serialized_values = []
            for value in values:
                try:
                    serialized_values.append(json.dumps(value, default=str))
                except (TypeError, ValueError):
                    serialized_values.append(pickle.dumps(value))
            
            return await self.redis.lpush(key, *serialized_values)
        except Exception as e:
            self.logger.error(f"Error in lpush for key {key}: {str(e)}")
            return 0
    
    async def rpush(self, key: str, *values: Any) -> int:
        """从右侧推入列表"""
        try:
            serialized_values = []
            for value in values:
                try:
                    serialized_values.append(json.dumps(value, default=str))
                except (TypeError, ValueError):
                    serialized_values.append(pickle.dumps(value))
            
            return await self.redis.rpush(key, *serialized_values)
        except Exception as e:
            self.logger.error(f"Error in rpush for key {key}: {str(e)}")
            return 0
    
    async def lpop(self, key: str) -> Any:
        """从左侧弹出列表元素"""
        try:
            value = await self.redis.lpop(key)
            if value is None:
                return None
            
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                try:
                    return pickle.loads(value)
                except:
                    return value
        except Exception as e:
            self.logger.error(f"Error in lpop for key {key}: {str(e)}")
            return None
    
    async def rpop(self, key: str) -> Any:
        """从右侧弹出列表元素"""
        try:
            value = await self.redis.rpop(key)
            if value is None:
                return None
            
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                try:
                    return pickle.loads(value)
                except:
                    return value
        except Exception as e:
            self.logger.error(f"Error in rpop for key {key}: {str(e)}")
            return None
    
    async def llen(self, key: str) -> int:
        """获取列表长度"""
        try:
            return await self.redis.llen(key)
        except Exception as e:
            self.logger.error(f"Error in llen for key {key}: {str(e)}")
            return 0
    
    async def lrange(self, key: str, start: int = 0, end: int = -1) -> List[Any]:
        """获取列表范围内的元素"""
        try:
            values = await self.redis.lrange(key, start, end)
            result = []
            
            for value in values:
                try:
                    result.append(json.loads(value))
                except (json.JSONDecodeError, TypeError):
                    try:
                        result.append(pickle.loads(value))
                    except:
                        result.append(value)
            
            return result
        except Exception as e:
            self.logger.error(f"Error in lrange for key {key}: {str(e)}")
            return []
    
    # 集合操作
    
    async def sadd(self, key: str, *members: Any) -> int:
        """添加集合成员"""
        try:
            serialized_members = []
            for member in members:
                try:
                    serialized_members.append(json.dumps(member, default=str))
                except (TypeError, ValueError):
                    serialized_members.append(pickle.dumps(member))
            
            return await self.redis.sadd(key, *serialized_members)
        except Exception as e:
            self.logger.error(f"Error in sadd for key {key}: {str(e)}")
            return 0
    
    async def srem(self, key: str, *members: Any) -> int:
        """删除集合成员"""
        try:
            serialized_members = []
            for member in members:
                try:
                    serialized_members.append(json.dumps(member, default=str))
                except (TypeError, ValueError):
                    serialized_members.append(pickle.dumps(member))
            
            return await self.redis.srem(key, *serialized_members)
        except Exception as e:
            self.logger.error(f"Error in srem for key {key}: {str(e)}")
            return 0
    
    async def smembers(self, key: str) -> List[Any]:
        """获取集合所有成员"""
        try:
            members = await self.redis.smembers(key)
            result = []
            
            for member in members:
                try:
                    result.append(json.loads(member))
                except (json.JSONDecodeError, TypeError):
                    try:
                        result.append(pickle.loads(member))
                    except:
                        result.append(member)
            
            return result
        except Exception as e:
            self.logger.error(f"Error in smembers for key {key}: {str(e)}")
            return []
    
    async def sismember(self, key: str, member: Any) -> bool:
        """检查是否为集合成员"""
        try:
            try:
                serialized_member = json.dumps(member, default=str)
            except (TypeError, ValueError):
                serialized_member = pickle.dumps(member)
            
            return await self.redis.sismember(key, serialized_member)
        except Exception as e:
            self.logger.error(f"Error in sismember for key {key}: {str(e)}")
            return False
    
    # 哈希操作
    
    async def hget(self, key: str, field: str) -> Any:
        """获取哈希字段值"""
        try:
            value = await self.redis.hget(key, field)
            if value is None:
                return None
            
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                try:
                    return pickle.loads(value)
                except:
                    return value
        except Exception as e:
            self.logger.error(f"Error in hget for key {key}, field {field}: {str(e)}")
            return None
    
    async def hset(self, key: str, field: str, value: Any) -> bool:
        """设置哈希字段值"""
        try:
            try:
                serialized_value = json.dumps(value, default=str)
            except (TypeError, ValueError):
                serialized_value = pickle.dumps(value)
            
            result = await self.redis.hset(key, field, serialized_value)
            return result >= 0
        except Exception as e:
            self.logger.error(f"Error in hset for key {key}, field {field}: {str(e)}")
            return False
    
    async def hdel(self, key: str, *fields: str) -> int:
        """删除哈希字段"""
        try:
            return await self.redis.hdel(key, *fields)
        except Exception as e:
            self.logger.error(f"Error in hdel for key {key}: {str(e)}")
            return 0
    
    async def hgetall(self, key: str) -> Dict[str, Any]:
        """获取哈希所有字段和值"""
        try:
            hash_data = await self.redis.hgetall(key)
            result = {}
            
            for field, value in hash_data.items():
                try:
                    result[field] = json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    try:
                        result[field] = pickle.loads(value)
                    except:
                        result[field] = value
            
            return result
        except Exception as e:
            self.logger.error(f"Error in hgetall for key {key}: {str(e)}")
            return {}
    
    async def hmset(self, key: str, mapping: Dict[str, Any]) -> bool:
        """批量设置哈希字段"""
        try:
            serialized_mapping = {}
            for field, value in mapping.items():
                try:
                    serialized_mapping[field] = json.dumps(value, default=str)
                except (TypeError, ValueError):
                    serialized_mapping[field] = pickle.dumps(value)
            
            await self.redis.hmset(key, serialized_mapping)
            return True
        except Exception as e:
            self.logger.error(f"Error in hmset for key {key}: {str(e)}")
            return False
    
    # 缓存统计和监控
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        try:
            info = await self.redis.info()
            
            stats = {
                "memory_used": info.get("used_memory_human", "N/A"),
                "memory_peak": info.get("used_memory_peak_human", "N/A"),
                "connected_clients": info.get("connected_clients", 0),
                "total_commands_processed": info.get("total_commands_processed", 0),
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0),
                "expired_keys": info.get("expired_keys", 0),
                "evicted_keys": info.get("evicted_keys", 0)
            }
            
            # 计算命中率
            hits = stats["keyspace_hits"]
            misses = stats["keyspace_misses"]
            total_requests = hits + misses
            
            if total_requests > 0:
                stats["hit_rate"] = round((hits / total_requests) * 100, 2)
            else:
                stats["hit_rate"] = 0.0
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Error getting cache stats: {str(e)}")
            return {}
    
    async def health_check(self) -> Dict[str, Any]:
        """缓存健康检查"""
        try:
            start_time = datetime.now()
            
            # 测试基本操作
            test_key = f"health_check:{uuid4()}"
            test_value = {"timestamp": start_time.isoformat(), "test": True}
            
            # 写入测试
            await self.set(test_key, test_value, ttl=60)
            
            # 读取测试
            retrieved_value = await self.get(test_key)
            
            # 删除测试
            await self.delete(test_key)
            
            end_time = datetime.now()
            response_time = (end_time - start_time).total_seconds() * 1000
            
            # 验证数据一致性
            data_consistent = (
                retrieved_value is not None and
                retrieved_value.get("test") == True
            )
            
            return {
                "status": "healthy" if data_consistent else "unhealthy",
                "response_time_ms": round(response_time, 2),
                "data_consistent": data_consistent,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Cache health check failed: {str(e)}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    # 工具方法
    
    def generate_cache_key(self, *parts: str, namespace: str = "default") -> str:
        """生成缓存键"""
        key_parts = [namespace] + list(parts)
        return ":".join(str(part) for part in key_parts)
    
    def hash_key(self, data: Union[str, Dict, List]) -> str:
        """生成数据哈希键"""
        if isinstance(data, str):
            content = data
        else:
            content = json.dumps(data, sort_keys=True, default=str)
        
        return hashlib.md5(content.encode()).hexdigest()