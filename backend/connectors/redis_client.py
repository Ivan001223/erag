"""Redis 缓存客户端"""

import json
import pickle
from typing import Any, Dict, List, Optional, Union
from datetime import timedelta

import redis.asyncio as redis
from redis.asyncio import Redis
from redis.exceptions import RedisError, ConnectionError

from backend.utils.logger import get_logger
from backend.config.constants import CacheKeyPrefix


class RedisClient:
    """Redis 异步客户端"""
    
    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        password: Optional[str] = None,
        db: int = 0,
        max_connections: int = 20,
        socket_timeout: int = 5,
        socket_connect_timeout: int = 5,
        retry_on_timeout: bool = True,
        health_check_interval: int = 30
    ):
        self.host = host
        self.port = port
        self.password = password
        self.db = db
        self.client: Optional[Redis] = None
        self.logger = get_logger(__name__)
        
        # 连接池配置
        self.pool_config = {
            "host": host,
            "port": port,
            "password": password,
            "db": db,
            "max_connections": max_connections,
            "socket_timeout": socket_timeout,
            "socket_connect_timeout": socket_connect_timeout,
            "retry_on_timeout": retry_on_timeout,
            "health_check_interval": health_check_interval,
            "decode_responses": True
        }
    
    async def connect(self) -> None:
        """建立Redis连接"""
        try:
            self.client = redis.Redis(**self.pool_config)
            
            # 测试连接
            await self.client.ping()
            self.logger.info(f"Redis 连接成功: {self.host}:{self.port}")
            
        except Exception as e:
            self.logger.error(f"Redis 连接失败: {str(e)}")
            raise
    
    async def close(self) -> None:
        """关闭Redis连接"""
        if self.client:
            await self.client.close()
            self.logger.info("Redis 连接已关闭")
    
    def _get_key(self, prefix: CacheKeyPrefix, key: str) -> str:
        """生成缓存键"""
        return f"{prefix.value}:{key}"
    
    async def set(
        self,
        key: str,
        value: Any,
        prefix: CacheKeyPrefix = CacheKeyPrefix.DEFAULT,
        expire: Optional[Union[int, timedelta]] = None,
        serialize: bool = True
    ) -> bool:
        """设置缓存值"""
        if not self.client:
            raise RuntimeError("Redis 未连接")
        
        try:
            cache_key = self._get_key(prefix, key)
            
            if serialize:
                if isinstance(value, (dict, list, tuple)):
                    serialized_value = json.dumps(value, ensure_ascii=False)
                else:
                    serialized_value = pickle.dumps(value)
            else:
                serialized_value = str(value)
            
            result = await self.client.set(cache_key, serialized_value, ex=expire)
            
            if result:
                self.logger.debug(f"缓存设置成功: {cache_key}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"设置缓存失败: {str(e)}")
            return False
    
    async def get(
        self,
        key: str,
        prefix: CacheKeyPrefix = CacheKeyPrefix.DEFAULT,
        deserialize: bool = True
    ) -> Optional[Any]:
        """获取缓存值"""
        if not self.client:
            raise RuntimeError("Redis 未连接")
        
        try:
            cache_key = self._get_key(prefix, key)
            value = await self.client.get(cache_key)
            
            if value is None:
                return None
            
            if deserialize:
                try:
                    # 尝试JSON反序列化
                    return json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    try:
                        # 尝试pickle反序列化
                        return pickle.loads(value.encode() if isinstance(value, str) else value)
                    except (pickle.PickleError, TypeError):
                        # 返回原始字符串
                        return value
            else:
                return value
                
        except Exception as e:
            self.logger.error(f"获取缓存失败: {str(e)}")
            return None
    
    async def delete(
        self,
        key: str,
        prefix: CacheKeyPrefix = CacheKeyPrefix.DEFAULT
    ) -> bool:
        """删除缓存"""
        if not self.client:
            raise RuntimeError("Redis 未连接")
        
        try:
            cache_key = self._get_key(prefix, key)
            result = await self.client.delete(cache_key)
            
            if result:
                self.logger.debug(f"缓存删除成功: {cache_key}")
            
            return result > 0
            
        except Exception as e:
            self.logger.error(f"删除缓存失败: {str(e)}")
            return False
    
    async def exists(
        self,
        key: str,
        prefix: CacheKeyPrefix = CacheKeyPrefix.DEFAULT
    ) -> bool:
        """检查缓存是否存在"""
        if not self.client:
            raise RuntimeError("Redis 未连接")
        
        try:
            cache_key = self._get_key(prefix, key)
            result = await self.client.exists(cache_key)
            return result > 0
            
        except Exception as e:
            self.logger.error(f"检查缓存存在性失败: {str(e)}")
            return False
    
    async def expire(
        self,
        key: str,
        seconds: int,
        prefix: CacheKeyPrefix = CacheKeyPrefix.DEFAULT
    ) -> bool:
        """设置缓存过期时间"""
        if not self.client:
            raise RuntimeError("Redis 未连接")
        
        try:
            cache_key = self._get_key(prefix, key)
            result = await self.client.expire(cache_key, seconds)
            return result
            
        except Exception as e:
            self.logger.error(f"设置缓存过期时间失败: {str(e)}")
            return False
    
    async def ttl(
        self,
        key: str,
        prefix: CacheKeyPrefix = CacheKeyPrefix.DEFAULT
    ) -> int:
        """获取缓存剩余生存时间"""
        if not self.client:
            raise RuntimeError("Redis 未连接")
        
        try:
            cache_key = self._get_key(prefix, key)
            return await self.client.ttl(cache_key)
            
        except Exception as e:
            self.logger.error(f"获取缓存TTL失败: {str(e)}")
            return -1
    
    async def keys(
        self,
        pattern: str = "*",
        prefix: Optional[CacheKeyPrefix] = None
    ) -> List[str]:
        """获取匹配的键列表"""
        if not self.client:
            raise RuntimeError("Redis 未连接")
        
        try:
            if prefix:
                search_pattern = f"{prefix.value}:{pattern}"
            else:
                search_pattern = pattern
            
            keys = await self.client.keys(search_pattern)
            return [key.decode() if isinstance(key, bytes) else key for key in keys]
            
        except Exception as e:
            self.logger.error(f"获取键列表失败: {str(e)}")
            return []
    
    async def flush_db(self) -> bool:
        """清空当前数据库"""
        if not self.client:
            raise RuntimeError("Redis 未连接")
        
        try:
            await self.client.flushdb()
            self.logger.info("Redis 数据库已清空")
            return True
            
        except Exception as e:
            self.logger.error(f"清空数据库失败: {str(e)}")
            return False
    
    async def flush_pattern(
        self,
        pattern: str,
        prefix: Optional[CacheKeyPrefix] = None
    ) -> int:
        """删除匹配模式的所有键"""
        if not self.client:
            raise RuntimeError("Redis 未连接")
        
        try:
            keys = await self.keys(pattern, prefix)
            if not keys:
                return 0
            
            deleted_count = await self.client.delete(*keys)
            self.logger.info(f"删除了 {deleted_count} 个匹配的键")
            return deleted_count
            
        except Exception as e:
            self.logger.error(f"批量删除键失败: {str(e)}")
            return 0
    
    # Hash 操作
    async def hset(
        self,
        key: str,
        field: str,
        value: Any,
        prefix: CacheKeyPrefix = CacheKeyPrefix.DEFAULT,
        serialize: bool = True
    ) -> bool:
        """设置哈希字段值"""
        if not self.client:
            raise RuntimeError("Redis 未连接")
        
        try:
            cache_key = self._get_key(prefix, key)
            
            if serialize and not isinstance(value, str):
                if isinstance(value, (dict, list, tuple)):
                    serialized_value = json.dumps(value, ensure_ascii=False)
                else:
                    serialized_value = pickle.dumps(value)
            else:
                serialized_value = str(value)
            
            result = await self.client.hset(cache_key, field, serialized_value)
            return result > 0
            
        except Exception as e:
            self.logger.error(f"设置哈希字段失败: {str(e)}")
            return False
    
    async def hget(
        self,
        key: str,
        field: str,
        prefix: CacheKeyPrefix = CacheKeyPrefix.DEFAULT,
        deserialize: bool = True
    ) -> Optional[Any]:
        """获取哈希字段值"""
        if not self.client:
            raise RuntimeError("Redis 未连接")
        
        try:
            cache_key = self._get_key(prefix, key)
            value = await self.client.hget(cache_key, field)
            
            if value is None:
                return None
            
            if deserialize:
                try:
                    return json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    try:
                        return pickle.loads(value.encode() if isinstance(value, str) else value)
                    except (pickle.PickleError, TypeError):
                        return value
            else:
                return value
                
        except Exception as e:
            self.logger.error(f"获取哈希字段失败: {str(e)}")
            return None
    
    async def hgetall(
        self,
        key: str,
        prefix: CacheKeyPrefix = CacheKeyPrefix.DEFAULT,
        deserialize: bool = True
    ) -> Dict[str, Any]:
        """获取哈希所有字段"""
        if not self.client:
            raise RuntimeError("Redis 未连接")
        
        try:
            cache_key = self._get_key(prefix, key)
            hash_data = await self.client.hgetall(cache_key)
            
            if not hash_data:
                return {}
            
            if deserialize:
                result = {}
                for field, value in hash_data.items():
                    try:
                        result[field] = json.loads(value)
                    except (json.JSONDecodeError, TypeError):
                        try:
                            result[field] = pickle.loads(value.encode() if isinstance(value, str) else value)
                        except (pickle.PickleError, TypeError):
                            result[field] = value
                return result
            else:
                return dict(hash_data)
                
        except Exception as e:
            self.logger.error(f"获取哈希所有字段失败: {str(e)}")
            return {}
    
    async def hdel(
        self,
        key: str,
        field: str,
        prefix: CacheKeyPrefix = CacheKeyPrefix.DEFAULT
    ) -> bool:
        """删除哈希字段"""
        if not self.client:
            raise RuntimeError("Redis 未连接")
        
        try:
            cache_key = self._get_key(prefix, key)
            result = await self.client.hdel(cache_key, field)
            return result > 0
            
        except Exception as e:
            self.logger.error(f"删除哈希字段失败: {str(e)}")
            return False
    
    # List 操作
    async def lpush(
        self,
        key: str,
        value: Any,
        prefix: CacheKeyPrefix = CacheKeyPrefix.DEFAULT,
        serialize: bool = True
    ) -> int:
        """从左侧推入列表"""
        if not self.client:
            raise RuntimeError("Redis 未连接")
        
        try:
            cache_key = self._get_key(prefix, key)
            
            if serialize and not isinstance(value, str):
                if isinstance(value, (dict, list, tuple)):
                    serialized_value = json.dumps(value, ensure_ascii=False)
                else:
                    serialized_value = pickle.dumps(value)
            else:
                serialized_value = str(value)
            
            return await self.client.lpush(cache_key, serialized_value)
            
        except Exception as e:
            self.logger.error(f"列表左推失败: {str(e)}")
            return 0
    
    async def rpop(
        self,
        key: str,
        prefix: CacheKeyPrefix = CacheKeyPrefix.DEFAULT,
        deserialize: bool = True
    ) -> Optional[Any]:
        """从右侧弹出列表元素"""
        if not self.client:
            raise RuntimeError("Redis 未连接")
        
        try:
            cache_key = self._get_key(prefix, key)
            value = await self.client.rpop(cache_key)
            
            if value is None:
                return None
            
            if deserialize:
                try:
                    return json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    try:
                        return pickle.loads(value.encode() if isinstance(value, str) else value)
                    except (pickle.PickleError, TypeError):
                        return value
            else:
                return value
                
        except Exception as e:
            self.logger.error(f"列表右弹失败: {str(e)}")
            return None
    
    async def llen(
        self,
        key: str,
        prefix: CacheKeyPrefix = CacheKeyPrefix.DEFAULT
    ) -> int:
        """获取列表长度"""
        if not self.client:
            raise RuntimeError("Redis 未连接")
        
        try:
            cache_key = self._get_key(prefix, key)
            return await self.client.llen(cache_key)
            
        except Exception as e:
            self.logger.error(f"获取列表长度失败: {str(e)}")
            return 0
    
    # Set 操作
    async def sadd(
        self,
        key: str,
        value: Any,
        prefix: CacheKeyPrefix = CacheKeyPrefix.DEFAULT,
        serialize: bool = True
    ) -> int:
        """添加集合成员"""
        if not self.client:
            raise RuntimeError("Redis 未连接")
        
        try:
            cache_key = self._get_key(prefix, key)
            
            if serialize and not isinstance(value, str):
                if isinstance(value, (dict, list, tuple)):
                    serialized_value = json.dumps(value, ensure_ascii=False)
                else:
                    serialized_value = pickle.dumps(value)
            else:
                serialized_value = str(value)
            
            return await self.client.sadd(cache_key, serialized_value)
            
        except Exception as e:
            self.logger.error(f"添加集合成员失败: {str(e)}")
            return 0
    
    async def smembers(
        self,
        key: str,
        prefix: CacheKeyPrefix = CacheKeyPrefix.DEFAULT,
        deserialize: bool = True
    ) -> List[Any]:
        """获取集合所有成员"""
        if not self.client:
            raise RuntimeError("Redis 未连接")
        
        try:
            cache_key = self._get_key(prefix, key)
            members = await self.client.smembers(cache_key)
            
            if not members:
                return []
            
            if deserialize:
                result = []
                for member in members:
                    try:
                        result.append(json.loads(member))
                    except (json.JSONDecodeError, TypeError):
                        try:
                            result.append(pickle.loads(member.encode() if isinstance(member, str) else member))
                        except (pickle.PickleError, TypeError):
                            result.append(member)
                return result
            else:
                return list(members)
                
        except Exception as e:
            self.logger.error(f"获取集合成员失败: {str(e)}")
            return []
    
    async def srem(
        self,
        key: str,
        value: Any,
        prefix: CacheKeyPrefix = CacheKeyPrefix.DEFAULT,
        serialize: bool = True
    ) -> int:
        """删除集合成员"""
        if not self.client:
            raise RuntimeError("Redis 未连接")
        
        try:
            cache_key = self._get_key(prefix, key)
            
            if serialize and not isinstance(value, str):
                if isinstance(value, (dict, list, tuple)):
                    serialized_value = json.dumps(value, ensure_ascii=False)
                else:
                    serialized_value = pickle.dumps(value)
            else:
                serialized_value = str(value)
            
            return await self.client.srem(cache_key, serialized_value)
            
        except Exception as e:
            self.logger.error(f"删除集合成员失败: {str(e)}")
            return 0
    
    async def get_info(self) -> Dict[str, Any]:
        """获取Redis服务器信息"""
        if not self.client:
            raise RuntimeError("Redis 未连接")
        
        try:
            info = await self.client.info()
            return {
                "version": info.get("redis_version"),
                "used_memory": info.get("used_memory_human"),
                "connected_clients": info.get("connected_clients"),
                "total_commands_processed": info.get("total_commands_processed"),
                "keyspace_hits": info.get("keyspace_hits"),
                "keyspace_misses": info.get("keyspace_misses"),
                "uptime_in_seconds": info.get("uptime_in_seconds")
            }
            
        except Exception as e:
            self.logger.error(f"获取Redis信息失败: {str(e)}")
            return {}
    
    async def health_check(self) -> bool:
        """健康检查"""
        try:
            if not self.client:
                return False
            
            pong = await self.client.ping()
            return pong is True
            
        except Exception as e:
            self.logger.error(f"Redis 健康检查失败: {str(e)}")
            return False