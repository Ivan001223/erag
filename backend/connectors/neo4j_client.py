"""Neo4j 连接客户端

优化后的Neo4j客户端，提供连接池管理、错误处理和健康检查功能。
"""

import asyncio
import time
from typing import Dict, List, Any, Optional, Union
from contextlib import asynccontextmanager
from datetime import datetime

from neo4j import GraphDatabase, AsyncSession
from neo4j.exceptions import (
    ServiceUnavailable, SessionError, TransientError,
    ClientError, DatabaseError
)

from backend.utils.logger import get_logger
from backend.config.settings import get_settings


class Neo4jConnectionError(Exception):
    """Neo4j连接异常"""
    pass


class Neo4jQueryError(Exception):
    """Neo4j查询异常"""
    pass


class Neo4jClient:
    """Neo4j 异步客户端
    
    提供完整的Neo4j数据库操作功能，包括：
    - 连接池管理
    - 自动重试机制
    - 事务支持
    - 健康检查
    - 性能监控
    """
    
    def __init__(
        self,
        uri: str,
        user: str,
        password: str,
        database: str = "neo4j",
        max_connection_lifetime: int = 3600,
        max_connection_pool_size: int = 50,
        connection_acquisition_timeout: int = 60,
        encrypted: bool = False
    ):
        """初始化Neo4j客户端
        
        Args:
            uri: Neo4j数据库URI
            user: 用户名
            password: 密码
            database: 数据库名称
            max_connection_lifetime: 连接最大生命周期（秒）
            max_connection_pool_size: 连接池最大大小
            connection_acquisition_timeout: 连接获取超时时间（秒）
            encrypted: 是否使用加密连接
        """
        self.uri = uri
        self.user = user
        self.password = password
        self.database = database
        
        self.logger = get_logger(__name__)
        self.settings = get_settings()
        
        # 连接配置
        self._driver = None
        self._max_connection_lifetime = max_connection_lifetime
        self._max_connection_pool_size = max_connection_pool_size
        self._connection_acquisition_timeout = connection_acquisition_timeout
        self._encrypted = encrypted
        
        # 状态跟踪
        self._connected = False
        self._connection_errors = 0
        self._last_health_check = None
        self._query_count = 0
        self._error_count = 0
    
    async def connect(self) -> None:
        """建立连接"""
        try:
            self.logger.info(f"正在连接到Neo4j数据库: {self.uri}")
            
            self._driver = GraphDatabase.driver(
                self.uri,
                auth=(self.user, self.password),
                max_connection_lifetime=self._max_connection_lifetime,
                max_connection_pool_size=self._max_connection_pool_size,
                connection_acquisition_timeout=self._connection_acquisition_timeout,
                encrypted=self._encrypted
            )
            
            # 验证连接
            await self.verify_connectivity()
            
            self._connected = True
            self._connection_errors = 0
            
            self.logger.info("Neo4j连接建立成功")
            
        except Exception as e:
            self._connected = False
            self._connection_errors += 1
            self.logger.error(f"Neo4j连接失败: {str(e)}")
            raise Neo4jConnectionError(f"无法连接到Neo4j数据库: {str(e)}")
    
    async def close(self) -> None:
        """关闭连接"""
        if self._driver:
            try:
                await self._driver.close()
                self._connected = False
                self.logger.info("Neo4j连接已关闭")
            except Exception as e:
                self.logger.error(f"关闭Neo4j连接时出错: {str(e)}")
    
    async def verify_connectivity(self) -> bool:
        """验证连接"""
        try:
            async with self._driver.session(database=self.database) as session:
                result = await session.run("RETURN 1 as test")
                record = await result.single()
                
                if record and record["test"] == 1:
                    self._last_health_check = datetime.now()
                    return True
                else:
                    raise Neo4jConnectionError("连接验证失败")
                    
        except Exception as e:
            self.logger.error(f"Neo4j连接验证失败: {str(e)}")
            raise Neo4jConnectionError(f"连接验证失败: {str(e)}")
    
    @asynccontextmanager
    async def session(self, **kwargs):
        """获取数据库会话"""
        if not self._connected or not self._driver:
            await self.connect()
        
        session = None
        try:
            session = self._driver.session(database=self.database, **kwargs)
            yield session
        except Exception as e:
            self._error_count += 1
            self.logger.error(f"Neo4j会话错误: {str(e)}")
            raise
        finally:
            if session:
                await session.close()
    
    async def run(
        self,
        cypher: str,
        parameters: Optional[Dict[str, Any]] = None,
        retry_count: int = 3,
        timeout: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """执行Cypher查询
        
        Args:
            cypher: Cypher查询语句
            parameters: 查询参数
            retry_count: 重试次数
            timeout: 查询超时时间
            
        Returns:
            查询结果列表
            
        Raises:
            Neo4jQueryError: 查询错误
        """
        if not cypher.strip():
            raise ValueError("Cypher查询不能为空")
        
        parameters = parameters or {}
        
        for attempt in range(retry_count + 1):
            try:
                start_time = time.time()
                
                async with self.session() as session:
                    if timeout:
                        result = await asyncio.wait_for(
                            session.run(cypher, parameters),
                            timeout=timeout
                        )
                    else:
                        result = await session.run(cypher, parameters)
                    
                    records = []
                    async for record in result:
                        records.append(dict(record))
                    
                    # 更新统计
                    self._query_count += 1
                    execution_time = time.time() - start_time
                    
                    self.logger.debug(f"Cypher查询执行成功", extra={
                        "cypher": cypher[:200] + "..." if len(cypher) > 200 else cypher,
                        "parameters": parameters,
                        "result_count": len(records),
                        "execution_time": execution_time,
                        "attempt": attempt + 1
                    })
                    
                    return records
                    
            except (ServiceUnavailable, SessionError, TransientError) as e:
                # 可重试的错误
                if attempt < retry_count:
                    wait_time = 2 ** attempt  # 指数退避
                    self.logger.warning(f"Neo4j查询失败，{wait_time}秒后重试", extra={
                        "error": str(e),
                        "attempt": attempt + 1,
                        "max_attempts": retry_count + 1,
                        "wait_time": wait_time
                    })
                    await asyncio.sleep(wait_time)
                    
                    # 尝试重新连接
                    try:
                        await self.verify_connectivity()
                    except:
                        pass
                else:
                    self._error_count += 1
                    self.logger.error(f"Neo4j查询最终失败: {str(e)}")
                    raise Neo4jQueryError(f"查询失败: {str(e)}")
                    
            except (ClientError, DatabaseError) as e:
                # 不可重试的错误
                self._error_count += 1
                self.logger.error(f"Neo4j查询错误: {str(e)}", extra={
                    "cypher": cypher,
                    "parameters": parameters
                })
                raise Neo4jQueryError(f"查询错误: {str(e)}")
                
            except Exception as e:
                self._error_count += 1
                self.logger.error(f"Neo4j查询未知错误: {str(e)}")
                raise Neo4jQueryError(f"未知错误: {str(e)}")
        
        # 如果所有重试都失败了
        raise Neo4jQueryError("查询重试次数已用完")
    
    async def run_transaction(
        self,
        transaction_func,
        *args,
        retry_count: int = 3,
        **kwargs
    ) -> Any:
        """执行事务
        
        Args:
            transaction_func: 事务函数
            *args: 事务函数参数
            retry_count: 重试次数
            **kwargs: 事务函数关键字参数
            
        Returns:
            事务函数返回值
        """
        for attempt in range(retry_count + 1):
            try:
                async with self.session() as session:
                    result = await session.execute_write(
                        transaction_func, *args, **kwargs
                    )
                    
                    self.logger.debug(f"事务执行成功", extra={
                        "function": transaction_func.__name__,
                        "attempt": attempt + 1
                    })
                    
                    return result
                    
            except (ServiceUnavailable, SessionError, TransientError) as e:
                if attempt < retry_count:
                    wait_time = 2 ** attempt
                    self.logger.warning(f"事务执行失败，{wait_time}秒后重试", extra={
                        "error": str(e),
                        "attempt": attempt + 1,
                        "wait_time": wait_time
                    })
                    await asyncio.sleep(wait_time)
                else:
                    self._error_count += 1
                    raise Neo4jQueryError(f"事务执行失败: {str(e)}")
                    
            except Exception as e:
                self._error_count += 1
                self.logger.error(f"事务执行错误: {str(e)}")
                raise Neo4jQueryError(f"事务错误: {str(e)}")
    
    async def create_node(
        self,
        labels: Union[str, List[str]],
        properties: Dict[str, Any],
        unique_properties: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """创建节点
        
        Args:
            labels: 节点标签
            properties: 节点属性
            unique_properties: 唯一属性（用于MERGE）
            
        Returns:
            创建的节点信息
        """
        if isinstance(labels, str):
            labels = [labels]
        
        label_str = ":".join(labels)
        
        if unique_properties:
            # 使用MERGE确保唯一性
            merge_props = {k: properties[k] for k in unique_properties if k in properties}
            set_props = {k: v for k, v in properties.items() if k not in unique_properties}
            
            cypher = f"""
            MERGE (n:{label_str} {{{', '.join([f'{k}: ${k}' for k in merge_props.keys()])}}})
            """
            if set_props:
                cypher += f"""
                SET n += $set_props
                """
            cypher += " RETURN n"
            
            params = {**merge_props}
            if set_props:
                params["set_props"] = set_props
        else:
            # 直接创建
            cypher = f"""
            CREATE (n:{label_str} $properties)
            RETURN n
            """
            params = {"properties": properties}
        
        results = await self.run(cypher, params)
        return results[0]["n"] if results else {}
    
    async def create_relationship(
        self,
        source_node_id: str,
        target_node_id: str,
        relationship_type: str,
        properties: Optional[Dict[str, Any]] = None,
        source_label: str = "Entity",
        target_label: str = "Entity"
    ) -> Dict[str, Any]:
        """创建关系
        
        Args:
            source_node_id: 源节点ID
            target_node_id: 目标节点ID
            relationship_type: 关系类型
            properties: 关系属性
            source_label: 源节点标签
            target_label: 目标节点标签
            
        Returns:
            创建的关系信息
        """
        properties = properties or {}
        
        cypher = f"""
        MATCH (source:{source_label} {{id: $source_id}})
        MATCH (target:{target_label} {{id: $target_id}})
        CREATE (source)-[r:{relationship_type} $properties]->(target)
        RETURN r
        """
        
        params = {
            "source_id": source_node_id,
            "target_id": target_node_id,
            "properties": properties
        }
        
        results = await self.run(cypher, params)
        return results[0]["r"] if results else {}
    
    async def find_nodes(
        self,
        labels: Optional[Union[str, List[str]]] = None,
        properties: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """查找节点
        
        Args:
            labels: 节点标签过滤
            properties: 属性过滤
            limit: 结果数量限制
            
        Returns:
            匹配的节点列表
        """
        cypher = "MATCH (n"
        
        if labels:
            if isinstance(labels, str):
                labels = [labels]
            cypher += ":" + ":".join(labels)
        
        cypher += ")"
        
        if properties:
            where_conditions = []
            for key, value in properties.items():
                where_conditions.append(f"n.{key} = ${key}")
            
            if where_conditions:
                cypher += " WHERE " + " AND ".join(where_conditions)
        
        cypher += " RETURN n"
        
        if limit:
            cypher += f" LIMIT {limit}"
        
        results = await self.run(cypher, properties or {})
        return [result["n"] for result in results]
    
    async def get_health_status(self) -> Dict[str, Any]:
        """获取健康状态"""
        try:
            # 执行健康检查查询
            start_time = time.time()
            await self.verify_connectivity()
            response_time = time.time() - start_time
            
            # 获取数据库信息
            db_info = await self.run("CALL dbms.components() YIELD name, versions, edition")
            
            return {
                "status": "healthy",
                "connected": self._connected,
                "response_time_ms": response_time * 1000,
                "query_count": self._query_count,
                "error_count": self._error_count,
                "error_rate": self._error_count / max(self._query_count, 1),
                "last_health_check": self._last_health_check.isoformat() if self._last_health_check else None,
                "database_info": db_info[0] if db_info else {},
                "connection_config": {
                    "uri": self.uri,
                    "database": self.database,
                    "max_pool_size": self._max_connection_pool_size,
                    "connection_lifetime": self._max_connection_lifetime
                }
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "connected": False,
                "error": str(e),
                "query_count": self._query_count,
                "error_count": self._error_count,
                "connection_errors": self._connection_errors
            }
    
    async def get_statistics(self) -> Dict[str, Any]:
        """获取数据库统计信息"""
        try:
            # 节点统计
            node_stats = await self.run("""
                MATCH (n)
                RETURN 
                    count(n) as total_nodes,
                    collect(DISTINCT labels(n)[0]) as node_labels
            """)
            
            # 关系统计
            rel_stats = await self.run("""
                MATCH ()-[r]->()
                RETURN 
                    count(r) as total_relationships,
                    collect(DISTINCT type(r)) as relationship_types
            """)
            
            # 按标签统计节点
            label_stats = await self.run("""
                MATCH (n)
                WITH labels(n)[0] as label
                RETURN label, count(*) as count
                ORDER BY count DESC
            """)
            
            # 按类型统计关系
            type_stats = await self.run("""
                MATCH ()-[r]->()
                WITH type(r) as rel_type
                RETURN rel_type, count(*) as count
                ORDER BY count DESC
            """)
            
            return {
                "nodes": {
                    "total": node_stats[0]["total_nodes"] if node_stats else 0,
                    "labels": node_stats[0]["node_labels"] if node_stats else [],
                    "by_label": {item["label"]: item["count"] for item in label_stats}
                },
                "relationships": {
                    "total": rel_stats[0]["total_relationships"] if rel_stats else 0,
                    "types": rel_stats[0]["relationship_types"] if rel_stats else [],
                    "by_type": {item["rel_type"]: item["count"] for item in type_stats}
                },
                "performance": {
                    "query_count": self._query_count,
                    "error_count": self._error_count,
                    "error_rate": self._error_count / max(self._query_count, 1)
                }
            }
            
        except Exception as e:
            self.logger.error(f"获取Neo4j统计信息失败: {str(e)}")
            return {
                "error": str(e),
                "nodes": {"total": 0, "labels": [], "by_label": {}},
                "relationships": {"total": 0, "types": [], "by_type": {}},
                "performance": {
                    "query_count": self._query_count,
                    "error_count": self._error_count,
                    "error_rate": self._error_count / max(self._query_count, 1)
                }
            }
    
    async def clear_database(self, confirm: bool = False) -> bool:
        """清空数据库（危险操作）
        
        Args:
            confirm: 确认标志
            
        Returns:
            是否成功清空
        """
        if not confirm:
            raise ValueError("必须明确确认才能清空数据库")
        
        try:
            # 删除所有关系
            await self.run("MATCH ()-[r]-() DELETE r")
            
            # 删除所有节点
            await self.run("MATCH (n) DELETE n")
            
            self.logger.warning("Neo4j数据库已清空")
            return True
            
        except Exception as e:
            self.logger.error(f"清空Neo4j数据库失败: {str(e)}")
            return False