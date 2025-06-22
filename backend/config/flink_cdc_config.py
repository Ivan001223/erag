"""Flink CDC 配置

包含MySQL CDC到StarRocks的配置信息
"""

from typing import Dict, List, Any
from dataclasses import dataclass, field
from backend.config.settings import get_settings

settings = get_settings()


@dataclass
class MySQLCDCSourceConfig:
    """MySQL CDC源配置"""
    hostname: str = "mysql"
    port: int = 3306
    username: str = "cdc_user"
    password: str = "cdc_password123"
    database_name: str = "erag"
    table_name: str = "documents"  # 可以是具体表名或正则表达式
    server_id: str = "5400-5404"
    server_time_zone: str = "Asia/Shanghai"
    
    # 扫描配置
    scan_incremental_snapshot_enabled: bool = True
    scan_incremental_snapshot_chunk_size: int = 8096
    scan_startup_mode: str = "initial"  # initial, earliest-offset, latest-offset, specific-offset
    
    # 连接配置
    connect_timeout: str = "30s"
    connect_max_retries: int = 3
    connection_pool_size: int = 20
    heartbeat_interval: str = "30s"
    
    # 性能优化
    chunk_meta_group_size: int = 1000
    chunk_key_even_distribution_factor_upper_bound: float = 1000.0
    chunk_key_even_distribution_factor_lower_bound: float = 0.05


@dataclass
class StarRocksSinkConfig:
    """StarRocks目标配置"""
    jdbc_url: str = "jdbc:mysql://starrocks:9030"
    load_url: str = "starrocks:8030"
    database_name: str = "erag"
    table_name: str = "cdc_documents"
    username: str = "root"
    password: str = ""
    
    # Sink属性
    sink_properties_format: str = "json"
    sink_properties_strip_outer_array: bool = True
    sink_properties_ignore_json_size: bool = True
    
    # 缓冲配置
    sink_buffer_flush_max_rows: int = 1000
    sink_buffer_flush_max_bytes: int = 1048576  # 1MB
    sink_buffer_flush_interval: str = "5s"
    sink_max_retries: int = 3


@dataclass
class FlinkJobConfig:
    """Flink作业配置"""
    job_name: str = "mysql-cdc-to-starrocks"
    parallelism: int = 2
    checkpoint_interval: str = "30s"
    checkpoint_timeout: str = "10min"
    min_pause_between_checkpoints: str = "5s"
    max_concurrent_checkpoints: int = 1
    
    # 重启策略
    restart_strategy: str = "fixed-delay"
    restart_attempts: int = 3
    restart_delay: str = "10s"
    
    # 状态后端
    state_backend: str = "filesystem"
    state_backend_checkpoint_dir: str = "file:///tmp/flink-checkpoints"
    state_backend_savepoint_dir: str = "file:///tmp/flink-savepoints"


# 默认配置实例
DEFAULT_MYSQL_CDC_CONFIG = MySQLCDCSourceConfig()
DEFAULT_STARROCKS_CONFIG = StarRocksSinkConfig()
DEFAULT_FLINK_JOB_CONFIG = FlinkJobConfig()

# 预定义的表映射配置
TABLE_MAPPINGS = {
    "documents": {
        "source_table": "documents",
        "target_table": "cdc_documents", 
        "columns": [
            "id", "title", "content", "doc_type", 
            "file_path", "file_size", "created_at", 
            "updated_at", "deleted_at"
        ],
        "primary_key": ["id"]
    },
    "entities": {
        "source_table": "entities",
        "target_table": "cdc_entities",
        "columns": [
            "id", "name", "entity_type", "description",
            "properties", "source_doc_id", "confidence",
            "created_at", "updated_at", "deleted_at"
        ],
        "primary_key": ["id"]
    },
    "relations": {
        "source_table": "relations", 
        "target_table": "cdc_relations",
        "columns": [
            "id", "source_entity_id", "target_entity_id",
            "relation_type", "properties", "source_doc_id",
            "confidence", "created_at", "updated_at", "deleted_at"
        ],
        "primary_key": ["id"]
    }
}

# Flink SQL模板
FLINK_SQL_TEMPLATES = {
    "mysql_cdc_source": """
    CREATE TABLE {table_name}_source (
        {columns},
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
        'hostname' = '{hostname}',
        'port' = '{port}',
        'username' = '{username}',
        'password' = '{password}',
        'database-name' = '{database_name}',
        'table-name' = '{source_table_name}',
        'server-id' = '{server_id}',
        'server-time-zone' = '{server_time_zone}',
        'scan.incremental.snapshot.enabled' = '{scan_incremental_snapshot_enabled}',
        'scan.incremental.snapshot.chunk.size' = '{scan_incremental_snapshot_chunk_size}',
        'scan.startup.mode' = '{scan_startup_mode}',
        'connect.timeout' = '{connect_timeout}',
        'connect.max-retries' = '{connect_max_retries}',
        'connection.pool.size' = '{connection_pool_size}',
        'heartbeat.interval' = '{heartbeat_interval}',
        'chunk-meta.group.size' = '{chunk_meta_group_size}',
        'chunk-key.even-distribution.factor.upper-bound' = '{chunk_key_even_distribution_factor_upper_bound}d',
        'chunk-key.even-distribution.factor.lower-bound' = '{chunk_key_even_distribution_factor_lower_bound}d'
    )
    """,
    
    "starrocks_sink": """
    CREATE TABLE {table_name}_sink (
        {columns},
        op_type STRING,
        source_timestamp TIMESTAMP(3),
        source_file STRING,
        source_position BIGINT,
        processed_at TIMESTAMP(3)
    ) WITH (
        'connector' = 'starrocks',
        'jdbc-url' = '{jdbc_url}',
        'load-url' = '{load_url}',
        'database-name' = '{database_name}',
        'table-name' = '{target_table_name}',
        'username' = '{username}',
        'password' = '{password}',
        'sink.properties.format' = '{sink_properties_format}',
        'sink.properties.strip_outer_array' = '{sink_properties_strip_outer_array}',
        'sink.properties.ignore_json_size' = '{sink_properties_ignore_json_size}',
        'sink.buffer-flush.max-rows' = '{sink_buffer_flush_max_rows}',
        'sink.buffer-flush.max-bytes' = '{sink_buffer_flush_max_bytes}',
        'sink.buffer-flush.interval' = '{sink_buffer_flush_interval}',
        'sink.max-retries' = '{sink_max_retries}'
    )
    """,
    
    "transform_insert": """
    INSERT INTO {table_name}_sink
    SELECT 
        {select_columns},
        __op as op_type,
        __source_ts as source_timestamp,
        __source_file as source_file,
        __source_pos as source_position,
        CURRENT_TIMESTAMP as processed_at
    FROM {table_name}_source
    WHERE __op IN ('c', 'u', 'r', 'd')  -- 处理所有操作类型
    """
}

def get_mysql_cdc_config() -> MySQLCDCSourceConfig:
    """获取MySQL CDC配置"""
    config = MySQLCDCSourceConfig()
    
    # 从环境变量或设置中读取配置
    if hasattr(settings, 'MYSQL_CDC_HOST'):
        config.hostname = settings.MYSQL_CDC_HOST
    if hasattr(settings, 'MYSQL_CDC_PORT'):
        config.port = settings.MYSQL_CDC_PORT
    if hasattr(settings, 'MYSQL_CDC_USERNAME'):
        config.username = settings.MYSQL_CDC_USERNAME
    if hasattr(settings, 'MYSQL_CDC_PASSWORD'):
        config.password = settings.MYSQL_CDC_PASSWORD
    if hasattr(settings, 'MYSQL_CDC_DATABASE'):
        config.database_name = settings.MYSQL_CDC_DATABASE
        
    return config

def get_starrocks_config() -> StarRocksSinkConfig:
    """获取StarRocks配置"""
    config = StarRocksSinkConfig()
    
    # 从环境变量或设置中读取配置
    if hasattr(settings, 'STARROCKS_JDBC_URL'):
        config.jdbc_url = settings.STARROCKS_JDBC_URL
    if hasattr(settings, 'STARROCKS_LOAD_URL'):
        config.load_url = settings.STARROCKS_LOAD_URL
    if hasattr(settings, 'STARROCKS_USERNAME'):
        config.username = settings.STARROCKS_USERNAME
    if hasattr(settings, 'STARROCKS_PASSWORD'):
        config.password = settings.STARROCKS_PASSWORD
    if hasattr(settings, 'STARROCKS_DATABASE'):
        config.database_name = settings.STARROCKS_DATABASE
        
    return config

def get_flink_job_config() -> FlinkJobConfig:
    """获取Flink作业配置"""
    config = FlinkJobConfig()
    
    # 从环境变量或设置中读取配置
    if hasattr(settings, 'FLINK_JOB_PARALLELISM'):
        config.parallelism = settings.FLINK_JOB_PARALLELISM
    if hasattr(settings, 'FLINK_CHECKPOINT_INTERVAL'):
        config.checkpoint_interval = settings.FLINK_CHECKPOINT_INTERVAL
        
    return config

def build_flink_sql_for_table(table_name: str) -> List[str]:
    """为指定表构建Flink SQL语句"""
    if table_name not in TABLE_MAPPINGS:
        raise ValueError(f"未找到表 {table_name} 的映射配置")
    
    table_mapping = TABLE_MAPPINGS[table_name]
    mysql_config = get_mysql_cdc_config()
    starrocks_config = get_starrocks_config()
    
    # 构建列定义
    columns_def = []
    select_columns = []
    
    for column in table_mapping["columns"]:
        if column in ["created_at", "updated_at"]:
            columns_def.append(f"{column} TIMESTAMP(3)")
        elif column in ["id", "source_doc_id", "source_entity_id", "target_entity_id", "file_size"]:
            columns_def.append(f"{column} BIGINT")
        elif column in ["confidence"]:
            columns_def.append(f"{column} DECIMAL(3,2)")
        elif column in ["properties"]:
            columns_def.append(f"{column} STRING")  # JSON存储为STRING
        else:
            columns_def.append(f"{column} STRING")
        
        select_columns.append(column)
    
    columns_sql = ",\n        ".join(columns_def)
    select_columns_sql = ",\n        ".join(select_columns)
    
    # 构建SQL语句
    sql_statements = []
    
    # 源表SQL
    source_sql = FLINK_SQL_TEMPLATES["mysql_cdc_source"].format(
        table_name=table_name,
        columns=columns_sql,
        hostname=mysql_config.hostname,
        port=mysql_config.port,
        username=mysql_config.username,
        password=mysql_config.password,
        database_name=mysql_config.database_name,
        source_table_name=table_mapping["source_table"],
        server_id=mysql_config.server_id,
        server_time_zone=mysql_config.server_time_zone,
        scan_incremental_snapshot_enabled=str(mysql_config.scan_incremental_snapshot_enabled).lower(),
        scan_incremental_snapshot_chunk_size=mysql_config.scan_incremental_snapshot_chunk_size,
        scan_startup_mode=mysql_config.scan_startup_mode,
        connect_timeout=mysql_config.connect_timeout,
        connect_max_retries=mysql_config.connect_max_retries,
        connection_pool_size=mysql_config.connection_pool_size,
        heartbeat_interval=mysql_config.heartbeat_interval,
        chunk_meta_group_size=mysql_config.chunk_meta_group_size,
        chunk_key_even_distribution_factor_upper_bound=mysql_config.chunk_key_even_distribution_factor_upper_bound,
        chunk_key_even_distribution_factor_lower_bound=mysql_config.chunk_key_even_distribution_factor_lower_bound
    )
    sql_statements.append(source_sql)
    
    # 目标表SQL
    sink_sql = FLINK_SQL_TEMPLATES["starrocks_sink"].format(
        table_name=table_name,
        columns=columns_sql,
        jdbc_url=starrocks_config.jdbc_url,
        load_url=starrocks_config.load_url,
        database_name=starrocks_config.database_name,
        target_table_name=table_mapping["target_table"],
        username=starrocks_config.username,
        password=starrocks_config.password,
        sink_properties_format=starrocks_config.sink_properties_format,
        sink_properties_strip_outer_array=str(starrocks_config.sink_properties_strip_outer_array).lower(),
        sink_properties_ignore_json_size=str(starrocks_config.sink_properties_ignore_json_size).lower(),
        sink_buffer_flush_max_rows=starrocks_config.sink_buffer_flush_max_rows,
        sink_buffer_flush_max_bytes=starrocks_config.sink_buffer_flush_max_bytes,
        sink_buffer_flush_interval=starrocks_config.sink_buffer_flush_interval,
        sink_max_retries=starrocks_config.sink_max_retries
    )
    sql_statements.append(sink_sql)
    
    # 转换插入SQL
    transform_sql = FLINK_SQL_TEMPLATES["transform_insert"].format(
        table_name=table_name,
        select_columns=select_columns_sql
    )
    sql_statements.append(transform_sql)
    
    return sql_statements

def get_all_table_flink_sql() -> Dict[str, List[str]]:
    """获取所有表的Flink SQL语句"""
    all_sql = {}
    for table_name in TABLE_MAPPINGS.keys():
        all_sql[table_name] = build_flink_sql_for_table(table_name)
    return all_sql 