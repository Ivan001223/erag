"""Neo4j 数据库客户端"""

import asyncio
from typing import Dict, List, Any, Optional, Union
from contextlib import asynccontextmanager

from neo4j import AsyncGraphDatabase, AsyncDriver, AsyncSession
from neo4j.exceptions import ServiceUnavailable, TransientError

from backend.utils.logger import get_logger
from backend.config.constants import EntityType, RelationType


class Neo4jClient:
    """Neo4j 异步客户端"""
    
    def __init__(
        self,
        uri: str,
        user: str,
        password: str,
        database: str = "neo4j",
        max_connection_lifetime: int = 3600,
        max_connection_pool_size: int = 50,
        connection_acquisition_timeout: int = 60
    ):
        self.uri = uri
        self.user = user
        self.password = password
        self.database = database
        self.driver: Optional[AsyncDriver] = None
        self.logger = get_logger(__name__)
        
        # 连接配置
        self.config = {
            "max_connection_lifetime": max_connection_lifetime,
            "max_connection_pool_size": max_connection_pool_size,
            "connection_acquisition_timeout": connection_acquisition_timeout,
            "encrypted": False  # 开发环境，生产环境应设为 True
        }
    
    async def connect(self) -> None:
        """建立数据库连接"""
        try:
            self.driver = AsyncGraphDatabase.driver(
                self.uri,
                auth=(self.user, self.password),
                **self.config
            )
            
            # 验证连接
            await self.driver.verify_connectivity()
            self.logger.info(f"Neo4j 连接成功: {self.uri}")
            
            # 创建索引和约束
            await self._initialize_schema()
            
        except Exception as e:
            self.logger.error(f"Neo4j 连接失败: {str(e)}")
            raise
    
    async def close(self) -> None:
        """关闭数据库连接"""
        if self.driver:
            await self.driver.close()
            self.logger.info("Neo4j 连接已关闭")
    
    @asynccontextmanager
    async def session(self, **kwargs):
        """获取数据库会话"""
        if not self.driver:
            raise RuntimeError("数据库未连接")
        
        session = self.driver.session(database=self.database, **kwargs)
        try:
            yield session
        finally:
            await session.close()
    
    async def _initialize_schema(self) -> None:
        """创建索引和约束"""
        # Neo4j的约束和索引创建语句没有SQLAlchemy等价物，保留原生Cypher查询
        # 这些是数据库架构定义语句，不是数据操作语句
        constraints_and_indexes = [
            # 实体约束和索引
            "CREATE CONSTRAINT entity_id_unique IF NOT EXISTS FOR (e:Entity) REQUIRE e.id IS UNIQUE",
            "CREATE INDEX entity_name_index IF NOT EXISTS FOR (e:Entity) ON (e.name)",
            "CREATE INDEX entity_type_index IF NOT EXISTS FOR (e:Entity) ON (e.type)",
            "CREATE INDEX entity_created_at_index IF NOT EXISTS FOR (e:Entity) ON (e.created_at)",
            
            # 文档约束和索引
            "CREATE CONSTRAINT document_id_unique IF NOT EXISTS FOR (d:Document) REQUIRE d.id IS UNIQUE",
            "CREATE INDEX document_title_index IF NOT EXISTS FOR (d:Document) ON (d.title)",
            "CREATE INDEX document_type_index IF NOT EXISTS FOR (d:Document) ON (d.type)",
            "CREATE INDEX document_created_at_index IF NOT EXISTS FOR (d:Document) ON (d.created_at)",
            
            # 关系索引
            "CREATE INDEX relation_type_index IF NOT EXISTS FOR ()-[r]-() ON (r.type)",
            "CREATE INDEX relation_confidence_index IF NOT EXISTS FOR ()-[r]-() ON (r.confidence)",
            "CREATE INDEX relation_created_at_index IF NOT EXISTS FOR ()-[r]-() ON (r.created_at)",
        ]
        
        async with self.session() as session:
            for query in constraints_and_indexes:
                try:
                    await session.run(query)
                    self.logger.debug(f"执行约束/索引: {query}")
                except Exception as e:
                    self.logger.warning(f"创建约束/索引失败: {query}, 错误: {str(e)}")
    
    async def execute_query(
        self,
        query: str,
        parameters: Optional[Dict[str, Any]] = None,
        timeout: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """执行查询并返回结果"""
        if parameters is None:
            parameters = {}
        
        async with self.session() as session:
            try:
                result = await session.run(query, parameters, timeout=timeout)
                records = await result.data()
                self.logger.debug(f"查询执行成功，返回 {len(records)} 条记录")
                return records
            except Exception as e:
                self.logger.error(f"查询执行失败: {str(e)}, 查询: {query}")
                raise
    
    async def execute_write_query(
        self,
        query: str,
        parameters: Optional[Dict[str, Any]] = None,
        timeout: Optional[int] = None
    ) -> Dict[str, Any]:
        """执行写入查询"""
        if parameters is None:
            parameters = {}
        
        async with self.session() as session:
            try:
                result = await session.run(query, parameters, timeout=timeout)
                summary = await result.consume()
                
                return {
                    "nodes_created": summary.counters.nodes_created,
                    "nodes_deleted": summary.counters.nodes_deleted,
                    "relationships_created": summary.counters.relationships_created,
                    "relationships_deleted": summary.counters.relationships_deleted,
                    "properties_set": summary.counters.properties_set
                }
            except Exception as e:
                self.logger.error(f"写入查询执行失败: {str(e)}, 查询: {query}")
                raise
    
    async def create_entity(
        self,
        entity_id: str,
        name: str,
        entity_type: EntityType,
        properties: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """创建实体"""
        if properties is None:
            properties = {}
        
        query = """
        CREATE (e:Entity {
            id: $entity_id,
            name: $name,
            type: $entity_type,
            created_at: datetime(),
            updated_at: datetime()
        })
        SET e += $properties
        RETURN e
        """
        
        parameters = {
            "entity_id": entity_id,
            "name": name,
            "entity_type": entity_type.value,
            "properties": properties
        }
        
        result = await self.execute_query(query, parameters)
        return result[0]["e"] if result else None
    
    async def create_relation(
        self,
        from_entity_id: str,
        to_entity_id: str,
        relation_type: RelationType,
        properties: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """创建关系"""
        if properties is None:
            properties = {}
        
        query = f"""
        MATCH (from:Entity {{id: $from_entity_id}})
        MATCH (to:Entity {{id: $to_entity_id}})
        CREATE (from)-[r:{relation_type.value} {{
            type: $relation_type,
            created_at: datetime(),
            updated_at: datetime()
        }}]->(to)
        SET r += $properties
        RETURN r
        """
        
        parameters = {
            "from_entity_id": from_entity_id,
            "to_entity_id": to_entity_id,
            "relation_type": relation_type.value,
            "properties": properties
        }
        
        result = await self.execute_query(query, parameters)
        return result[0]["r"] if result else None
    
    async def find_entity_by_id(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """根据ID查找实体"""
        query = "MATCH (e:Entity {id: $entity_id}) RETURN e"
        result = await self.execute_query(query, {"entity_id": entity_id})
        return result[0]["e"] if result else None
    
    async def find_entities_by_type(
        self,
        entity_type: EntityType,
        limit: int = 100,
        skip: int = 0
    ) -> List[Dict[str, Any]]:
        """根据类型查找实体"""
        query = """
        MATCH (e:Entity {type: $entity_type})
        RETURN e
        ORDER BY e.created_at DESC
        SKIP $skip
        LIMIT $limit
        """
        
        parameters = {
            "entity_type": entity_type.value,
            "limit": limit,
            "skip": skip
        }
        
        result = await self.execute_query(query, parameters)
        return [record["e"] for record in result]
    
    async def find_related_entities(
        self,
        entity_id: str,
        relation_types: Optional[List[RelationType]] = None,
        max_depth: int = 2
    ) -> List[Dict[str, Any]]:
        """查找相关实体"""
        if relation_types:
            relation_filter = "|".join([rt.value for rt in relation_types])
            relation_pattern = f"[r:{relation_filter}*1..{max_depth}]"
        else:
            relation_pattern = f"[r*1..{max_depth}]"
        
        query = f"""
        MATCH (start:Entity {{id: $entity_id}})-{relation_pattern}-(related:Entity)
        WHERE start <> related
        RETURN DISTINCT related, r
        LIMIT 100
        """
        
        result = await self.execute_query(query, {"entity_id": entity_id})
        return result
    
    async def search_entities(
        self,
        search_term: str,
        entity_types: Optional[List[EntityType]] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """搜索实体"""
        type_filter = ""
        parameters = {"search_term": f".*{search_term}.*", "limit": limit}
        
        if entity_types:
            type_filter = "AND e.type IN $entity_types"
            parameters["entity_types"] = [et.value for et in entity_types]
        
        query = f"""
        MATCH (e:Entity)
        WHERE e.name =~ $search_term {type_filter}
        RETURN e
        ORDER BY e.name
        LIMIT $limit
        """
        
        result = await self.execute_query(query, parameters)
        return [record["e"] for record in result]
    
    async def get_entity_statistics(self) -> Dict[str, Any]:
        """获取实体统计信息"""
        queries = {
            "total_entities": "MATCH (e:Entity) RETURN count(e) as count",
            "total_relations": "MATCH ()-[r]->() RETURN count(r) as count",
            "entities_by_type": """
                MATCH (e:Entity)
                RETURN e.type as type, count(e) as count
                ORDER BY count DESC
            """,
            "relations_by_type": """
                MATCH ()-[r]->()
                RETURN r.type as type, count(r) as count
                ORDER BY count DESC
            """
        }
        
        statistics = {}
        
        for key, query in queries.items():
            result = await self.execute_query(query)
            if key in ["total_entities", "total_relations"]:
                statistics[key] = result[0]["count"] if result else 0
            else:
                statistics[key] = result
        
        return statistics
    
    async def delete_entity(self, entity_id: str) -> bool:
        """删除实体及其所有关系"""
        query = """
        MATCH (e:Entity {id: $entity_id})
        DETACH DELETE e
        RETURN count(e) as deleted_count
        """
        
        result = await self.execute_query(query, {"entity_id": entity_id})
        deleted_count = result[0]["deleted_count"] if result else 0
        return deleted_count > 0
    
    async def update_entity(
        self,
        entity_id: str,
        properties: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """更新实体属性"""
        query = """
        MATCH (e:Entity {id: $entity_id})
        SET e += $properties, e.updated_at = datetime()
        RETURN e
        """
        
        parameters = {
            "entity_id": entity_id,
            "properties": properties
        }
        
        result = await self.execute_query(query, parameters)
        return result[0]["e"] if result else None
    
    async def batch_create_entities(
        self,
        entities: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """批量创建实体"""
        query = """
        UNWIND $entities as entity
        CREATE (e:Entity {
            id: entity.id,
            name: entity.name,
            type: entity.type,
            created_at: datetime(),
            updated_at: datetime()
        })
        SET e += entity.properties
        """
        
        return await self.execute_write_query(query, {"entities": entities})
    
    async def batch_create_relations(
        self,
        relations: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """批量创建关系"""
        query = """
        UNWIND $relations as rel
        MATCH (from:Entity {id: rel.from_id})
        MATCH (to:Entity {id: rel.to_id})
        CALL apoc.create.relationship(from, rel.type, {
            type: rel.type,
            created_at: datetime(),
            updated_at: datetime()
        } + rel.properties, to) YIELD rel as r
        RETURN count(r)
        """
        
        return await self.execute_write_query(query, {"relations": relations})
    
    async def health_check(self) -> bool:
        """健康检查"""
        try:
            result = await self.execute_query("RETURN 1 as health")
            return len(result) > 0 and result[0]["health"] == 1
        except Exception as e:
            self.logger.error(f"Neo4j 健康检查失败: {str(e)}")
            return False