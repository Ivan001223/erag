"""MySQL CDC 客户端

专门用于管理MySQL到Flink CDC的连接和配置
"""

import asyncio
import json
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
from dataclasses import dataclass, field

import aiomysql
from backend.utils.logger import get_logger
from backend.connectors.flink_client import FlinkClient


@dataclass
class MySQLCDCConfig:
    """MySQL CDC配置"""
    # MySQL连接配置
    hostname: str = "mysql"
    port: int = 3306
    username: str = "root"
    password: str = "rootpass"
    database: str = "erag"
    
    # CDC配置
    server_id: str = "5400-5404"
    server_name: str = "mysql-server"
    
    # 监控配置
    tables: List[str] = field(default_factory=list)
    table_whitelist: Optional[str] = None
    table_blacklist: Optional[str] = None
    
    # 性能配置
    scan_incremental_snapshot_enabled: bool = True
    scan_incremental_snapshot_chunk_size: int = 8096
    scan_startup_mode: str = "initial"  # initial, earliest-offset, latest-offset, specific-offset
    
    # 容错配置
    connect_timeout: int = 30
    connect_max_retries: int = 3
    connection_pool_size: int = 20
    
    # 元数据
    created_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


class MySQLCDCClient:
    """MySQL CDC 客户端"""
    
    def __init__(self, config: MySQLCDCConfig, flink_client: FlinkClient):
        """初始化MySQL CDC客户端
        
        Args:
            config: MySQL CDC配置
            flink_client: Flink客户端
        """
        self.config = config
        self.flink_client = flink_client
        self.logger = get_logger(__name__)
        self.connection_pool: Optional[aiomysql.Pool] = None
        
    async def connect(self) -> None:
        """建立MySQL连接池"""
        try:
            self.connection_pool = await aiomysql.create_pool(
                host=self.config.hostname,
                port=self.config.port,
                user=self.config.username,
                password=self.config.password,
                db=self.config.database,
                minsize=1,
                maxsize=self.config.connection_pool_size,
                autocommit=True
            )
            
            # 测试连接
            await self._test_connection()
            self.logger.info(f"MySQL CDC 连接成功: {self.config.hostname}:{self.config.port}")
            
        except Exception as e:
            self.logger.error(f"MySQL CDC 连接失败: {str(e)}")
            raise
    
    async def close(self) -> None:
        """关闭MySQL连接池"""
        if self.connection_pool:
            self.connection_pool.close()
            await self.connection_pool.wait_closed()
            self.logger.info("MySQL CDC 连接已关闭")
    
    async def _test_connection(self) -> None:
        """测试MySQL连接"""
        if not self.connection_pool:
            raise RuntimeError("MySQL连接池未初始化")
        
        try:
            async with self.connection_pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute("SELECT 1")
                    result = await cursor.fetchone()
                    if result[0] != 1:
                        raise ConnectionError("MySQL连接测试失败")
        except Exception as e:
            raise ConnectionError(f"MySQL连接测试失败: {str(e)}")
    
    async def validate_mysql_binlog_config(self) -> Dict[str, Any]:
        """验证MySQL binlog配置"""
        if not self.connection_pool:
            raise RuntimeError("MySQL连接池未初始化")
        
        validation_result = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "config": {}
        }
        
        try:
            async with self.connection_pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    # 检查binlog是否启用
                    await cursor.execute("SHOW VARIABLES LIKE 'log_bin'")
                    result = await cursor.fetchone()
                    if not result or result[1].lower() != 'on':
                        validation_result["valid"] = False
                        validation_result["errors"].append("MySQL binlog未启用，请设置log_bin=ON")
                    
                    # 检查binlog格式
                    await cursor.execute("SHOW VARIABLES LIKE 'binlog_format'")
                    result = await cursor.fetchone()
                    if result:
                        binlog_format = result[1].upper()
                        validation_result["config"]["binlog_format"] = binlog_format
                        if binlog_format != 'ROW':
                            validation_result["errors"].append(f"binlog格式应为ROW，当前为{binlog_format}")
                            validation_result["valid"] = False
                    
                    # 检查binlog row image
                    await cursor.execute("SHOW VARIABLES LIKE 'binlog_row_image'")
                    result = await cursor.fetchone()
                    if result:
                        row_image = result[1].upper()
                        validation_result["config"]["binlog_row_image"] = row_image
                        if row_image != 'FULL':
                            validation_result["warnings"].append(f"建议设置binlog_row_image=FULL，当前为{row_image}")
                    
                    # 检查server_id
                    await cursor.execute("SHOW VARIABLES LIKE 'server_id'")
                    result = await cursor.fetchone()
                    if result:
                        server_id = result[1]
                        validation_result["config"]["server_id"] = server_id
                        if server_id == '0':
                            validation_result["errors"].append("server_id不能为0")
                            validation_result["valid"] = False
                    
                    # 检查gtid模式
                    await cursor.execute("SHOW VARIABLES LIKE 'gtid_mode'")
                    result = await cursor.fetchone()
                    if result:
                        gtid_mode = result[1].upper()
                        validation_result["config"]["gtid_mode"] = gtid_mode
                        if gtid_mode == 'ON':
                            validation_result["config"]["supports_gtid"] = True
                        else:
                            validation_result["warnings"].append("建议启用GTID模式以获得更好的容错性")
                    
        except Exception as e:
            validation_result["valid"] = False
            validation_result["errors"].append(f"验证过程出错: {str(e)}")
        
        return validation_result
    
    async def create_cdc_job(
        self,
        job_name: str,
        source_tables: List[str],
        sink_config: Dict[str, Any],
        transform_config: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """创建MySQL CDC作业"""
        try:
            # 验证MySQL配置
            validation = await self.validate_mysql_binlog_config()
            if not validation["valid"]:
                raise ValueError(f"MySQL配置验证失败: {validation['errors']}")
            
            # 构建Flink SQL语句
            sql_statements = []
            
            # 创建MySQL CDC源表
            source_sql = self._build_mysql_cdc_source_sql(source_tables)
            sql_statements.append(source_sql)
            
            # 创建StarRocks目标表
            sink_sql = self._build_starrocks_sink_sql(sink_config)
            sql_statements.append(sink_sql)
            
            # 创建数据转换和插入语句
            transform_sql = self._build_transform_sql(transform_config or {})
            sql_statements.append(transform_sql)
            
            # 提交Flink作业
            job_id = await self.flink_client.submit_sql_job(
                sql_statements,
                job_name=job_name
            )
            
            if job_id:
                self.logger.info(f"MySQL CDC作业创建成功: {job_name}, 作业ID: {job_id}")
            
            return job_id
            
        except Exception as e:
            self.logger.error(f"创建MySQL CDC作业失败: {str(e)}")
            raise
    
    def _build_mysql_cdc_source_sql(self, source_tables: List[str]) -> str:
        """构建MySQL CDC源表SQL"""
        table_list = ",".join(source_tables) if source_tables else ".*"
        
        return f"""
        CREATE TABLE mysql_cdc_source (
            id BIGINT,
            title STRING,
            content STRING,
            doc_type STRING,
            file_path STRING,
            file_size BIGINT,
            created_at TIMESTAMP(3),
            updated_at TIMESTAMP(3),
            deleted_at TIMESTAMP(3),
            __op STRING METADATA FROM 'op' VIRTUAL,
            __source_ts TIMESTAMP(3) METADATA FROM 'source.timestamp' VIRTUAL,
            __source_file STRING METADATA FROM 'source.file' VIRTUAL,
            __source_pos BIGINT METADATA FROM 'source.pos' VIRTUAL,
            __source_row INT METADATA FROM 'source.row' VIRTUAL,
            __source_server_id BIGINT METADATA FROM 'source.server_id' VIRTUAL,
            __source_gtid STRING METADATA FROM 'source.gtid' VIRTUAL,
            WATERMARK FOR updated_at AS updated_at - INTERVAL '5' SECOND
        ) WITH (
            'connector' = 'mysql-cdc',
            'hostname' = '{self.config.hostname}',
            'port' = '{self.config.port}',
            'username' = '{self.config.username}',
            'password' = '{self.config.password}',
            'database-name' = '{self.config.database}',
            'table-name' = '{table_list}',
            'server-id' = '{self.config.server_id}',
            'server-time-zone' = 'Asia/Shanghai',
            'scan.incremental.snapshot.enabled' = '{str(self.config.scan_incremental_snapshot_enabled).lower()}',
            'scan.incremental.snapshot.chunk.size' = '{self.config.scan_incremental_snapshot_chunk_size}',
            'scan.startup.mode' = '{self.config.scan_startup_mode}',
            'connect.timeout' = '{self.config.connect_timeout}s',
            'connect.max-retries' = '{self.config.connect_max_retries}',
            'connection.pool.size' = '{self.config.connection_pool_size}',
            'heartbeat.interval' = '30s',
            'chunk-meta.group.size' = '1000',
            'chunk-key.even-distribution.factor.upper-bound' = '1000.0d',
            'chunk-key.even-distribution.factor.lower-bound' = '0.05d'
        )
        """
    
    def _build_starrocks_sink_sql(self, sink_config: Dict[str, Any]) -> str:
        """构建StarRocks目标表SQL"""
        return f"""
        CREATE TABLE starrocks_sink (
            id BIGINT,
            title STRING,
            content STRING,
            doc_type STRING,
            file_path STRING,
            file_size BIGINT,
            created_at TIMESTAMP(3),
            updated_at TIMESTAMP(3),
            deleted_at TIMESTAMP(3),
            op_type STRING,
            source_timestamp TIMESTAMP(3),
            source_file STRING,
            source_position BIGINT,
            processed_at TIMESTAMP(3)
        ) WITH (
            'connector' = 'starrocks',
            'jdbc-url' = '{sink_config.get('jdbc-url', 'jdbc:mysql://starrocks:9030')}',
            'load-url' = '{sink_config.get('load-url', 'starrocks:8030')}',
            'database-name' = '{sink_config.get('database', 'erag')}',
            'table-name' = '{sink_config.get('table', 'cdc_documents')}',
            'username' = '{sink_config.get('username', 'root')}',
            'password' = '{sink_config.get('password', '')}',
            'sink.properties.format' = 'json',
            'sink.properties.strip_outer_array' = 'true',
            'sink.properties.ignore_json_size' = 'true',
            'sink.buffer-flush.max-rows' = '1000',
            'sink.buffer-flush.max-bytes' = '1048576',
            'sink.buffer-flush.interval' = '5s',
            'sink.max-retries' = '3'
        )
        """
    
    def _build_transform_sql(self, transform_config: Dict[str, Any]) -> str:
        """构建数据转换SQL"""
        return """
        INSERT INTO starrocks_sink
        SELECT 
            id,
            title,
            content,
            doc_type,
            file_path,
            file_size,
            created_at,
            updated_at,
            deleted_at,
            __op as op_type,
            __source_ts as source_timestamp,
            __source_file as source_file,
            __source_pos as source_position,
            CURRENT_TIMESTAMP as processed_at
        FROM mysql_cdc_source
        WHERE __op IN ('c', 'u', 'r', 'd')  -- 处理所有操作类型
        """
    
    async def monitor_cdc_lag(self, job_id: str) -> Dict[str, Any]:
        """监控CDC延迟"""
        try:
            # 获取作业指标
            metrics = await self.flink_client.get_job_metrics(job_id)
            
            # 计算延迟指标
            lag_info = {
                "job_id": job_id,
                "timestamp": datetime.now().isoformat(),
                "lag_metrics": {},
                "status": "healthy"
            }
            
            if metrics:
                for metric in metrics:
                    metric_name = metric.get("id", "")
                    metric_value = metric.get("value", 0)
                    
                    if "currentFetchEventTimeLag" in metric_name:
                        lag_info["lag_metrics"]["fetch_lag_ms"] = metric_value
                    elif "currentEmitEventTimeLag" in metric_name:
                        lag_info["lag_metrics"]["emit_lag_ms"] = metric_value
                    elif "sourceIdleTime" in metric_name:
                        lag_info["lag_metrics"]["idle_time_ms"] = metric_value
                
                # 判断健康状态
                fetch_lag = lag_info["lag_metrics"].get("fetch_lag_ms", 0)
                if fetch_lag > 60000:  # 超过1分钟认为不健康
                    lag_info["status"] = "unhealthy"
                elif fetch_lag > 30000:  # 超过30秒认为警告
                    lag_info["status"] = "warning"
            
            return lag_info
            
        except Exception as e:
            self.logger.error(f"监控CDC延迟失败: {str(e)}")
            return {
                "job_id": job_id,
                "timestamp": datetime.now().isoformat(),
                "status": "error",
                "error": str(e)
            } 