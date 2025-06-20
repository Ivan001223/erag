"""变更数据捕获(CDC)管理器

负责监控数据源的变更，实时捕获数据变化并触发相应的ETL处理。
"""

import json
import uuid
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union, Tuple, Callable, Set
from enum import Enum
from dataclasses import dataclass, field
from pathlib import Path
import hashlib

from pydantic import BaseModel, Field

from backend.utils.logger import get_logger
from backend.services.etl_service import ETLJobStatus

logger = get_logger(__name__)


class CDCEventType(str, Enum):
    """CDC事件类型枚举"""
    INSERT = "insert"  # 插入
    UPDATE = "update"  # 更新
    DELETE = "delete"  # 删除
    TRUNCATE = "truncate"  # 截断
    SCHEMA_CHANGE = "schema_change"  # 模式变更
    HEARTBEAT = "heartbeat"  # 心跳


class CDCSourceType(str, Enum):
    """CDC数据源类型枚举"""
    MYSQL = "mysql"
    POSTGRESQL = "postgresql"
    MONGODB = "mongodb"
    ORACLE = "oracle"
    SQL_SERVER = "sql_server"
    KAFKA = "kafka"
    FILE_SYSTEM = "file_system"
    API = "api"
    CUSTOM = "custom"


class CDCStatus(str, Enum):
    """CDC状态枚举"""
    STOPPED = "stopped"  # 已停止
    STARTING = "starting"  # 启动中
    RUNNING = "running"  # 运行中
    PAUSED = "paused"  # 暂停
    ERROR = "error"  # 错误
    STOPPING = "stopping"  # 停止中


class CDCFilterType(str, Enum):
    """CDC过滤器类型枚举"""
    TABLE_FILTER = "table_filter"  # 表过滤
    COLUMN_FILTER = "column_filter"  # 列过滤
    CONDITION_FILTER = "condition_filter"  # 条件过滤
    EVENT_TYPE_FILTER = "event_type_filter"  # 事件类型过滤
    CUSTOM_FILTER = "custom_filter"  # 自定义过滤


@dataclass
class CDCSourceConfig:
    """CDC数据源配置"""
    # TODO: 从配置文件读取
    source_id: str
    name: str
    source_type: CDCSourceType
    
    # 连接配置
    connection_config: Dict[str, Any] = field(default_factory=dict)
    
    # 监控配置
    tables: List[str] = field(default_factory=list)  # 监控的表
    databases: List[str] = field(default_factory=list)  # 监控的数据库
    
    # 过滤配置
    include_patterns: List[str] = field(default_factory=list)
    exclude_patterns: List[str] = field(default_factory=list)
    
    # 性能配置
    batch_size: int = 1000
    poll_interval_ms: int = 1000
    max_queue_size: int = 10000
    
    # 容错配置
    retry_attempts: int = 3
    retry_delay_ms: int = 5000
    error_tolerance: str = "none"  # none, all, data
    
    # 位置跟踪
    initial_position: str = "latest"  # latest, earliest, timestamp
    checkpoint_interval_ms: int = 30000
    
    # 元数据
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class CDCEvent(BaseModel):
    """CDC事件"""
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source_id: str
    event_type: CDCEventType
    timestamp: datetime = Field(default_factory=datetime.now)
    
    # 数据信息
    database: Optional[str] = None
    table: Optional[str] = None
    
    # 变更数据
    before_data: Optional[Dict[str, Any]] = None  # 变更前数据
    after_data: Optional[Dict[str, Any]] = None   # 变更后数据
    
    # 位置信息
    position: Optional[Dict[str, Any]] = None  # 事件位置（如binlog位置）
    
    # 模式信息
    schema: Optional[Dict[str, Any]] = None
    
    # 元数据
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    def get_key(self) -> str:
        """获取事件唯一键"""
        key_parts = [self.source_id, self.database or "", self.table or ""]
        if self.after_data and "id" in self.after_data:
            key_parts.append(str(self.after_data["id"]))
        elif self.before_data and "id" in self.before_data:
            key_parts.append(str(self.before_data["id"]))
        
        return "|".join(key_parts)
    
    def get_hash(self) -> str:
        """获取事件哈希值"""
        content = {
            "source_id": self.source_id,
            "event_type": self.event_type.value,
            "database": self.database,
            "table": self.table,
            "before_data": self.before_data,
            "after_data": self.after_data
        }
        
        content_str = json.dumps(content, sort_keys=True, default=str)
        return hashlib.md5(content_str.encode()).hexdigest()


class CDCFilter(BaseModel):
    """CDC过滤器"""
    filter_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    filter_type: CDCFilterType
    
    # 过滤条件
    conditions: Dict[str, Any] = Field(default_factory=dict)
    
    # 过滤逻辑
    include: bool = True  # True表示包含，False表示排除
    
    # 优先级
    priority: int = 0  # 数字越大优先级越高
    
    # 状态
    enabled: bool = True
    
    # 元数据
    created_at: datetime = Field(default_factory=datetime.now)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    def matches(self, event: CDCEvent) -> bool:
        """检查事件是否匹配过滤器"""
        if not self.enabled:
            return True
        
        try:
            if self.filter_type == CDCFilterType.TABLE_FILTER:
                return self._match_table_filter(event)
            elif self.filter_type == CDCFilterType.COLUMN_FILTER:
                return self._match_column_filter(event)
            elif self.filter_type == CDCFilterType.CONDITION_FILTER:
                return self._match_condition_filter(event)
            elif self.filter_type == CDCFilterType.EVENT_TYPE_FILTER:
                return self._match_event_type_filter(event)
            elif self.filter_type == CDCFilterType.CUSTOM_FILTER:
                return self._match_custom_filter(event)
            
            return True
            
        except Exception as e:
            logger.error(f"过滤器匹配失败 {self.filter_id}: {str(e)}")
            return True  # 出错时默认通过
    
    def _match_table_filter(self, event: CDCEvent) -> bool:
        """匹配表过滤器"""
        tables = self.conditions.get("tables", [])
        if not tables:
            return True
        
        table_name = f"{event.database}.{event.table}" if event.database else event.table
        return table_name in tables
    
    def _match_column_filter(self, event: CDCEvent) -> bool:
        """匹配列过滤器"""
        columns = self.conditions.get("columns", [])
        if not columns:
            return True
        
        # 检查变更数据中是否包含指定列
        data = event.after_data or event.before_data or {}
        return any(col in data for col in columns)
    
    def _match_condition_filter(self, event: CDCEvent) -> bool:
        """匹配条件过滤器"""
        conditions = self.conditions.get("conditions", {})
        if not conditions:
            return True
        
        data = event.after_data or event.before_data or {}
        
        for field, condition in conditions.items():
            if field not in data:
                continue
            
            value = data[field]
            
            if isinstance(condition, dict):
                # 复杂条件
                if "eq" in condition and value != condition["eq"]:
                    return False
                if "ne" in condition and value == condition["ne"]:
                    return False
                if "gt" in condition and value <= condition["gt"]:
                    return False
                if "lt" in condition and value >= condition["lt"]:
                    return False
                if "in" in condition and value not in condition["in"]:
                    return False
                if "not_in" in condition and value in condition["not_in"]:
                    return False
            else:
                # 简单相等条件
                if value != condition:
                    return False
        
        return True
    
    def _match_event_type_filter(self, event: CDCEvent) -> bool:
        """匹配事件类型过滤器"""
        event_types = self.conditions.get("event_types", [])
        if not event_types:
            return True
        
        return event.event_type.value in event_types
    
    def _match_custom_filter(self, event: CDCEvent) -> bool:
        """匹配自定义过滤器"""
        # 自定义过滤逻辑可以通过脚本或函数实现
        custom_logic = self.conditions.get("custom_logic")
        if not custom_logic:
            return True
        # TODO: 实现自定义过滤逻辑
        # 这里可以实现脚本执行或函数调用
        # 为了安全起见，暂时返回True
        return True


class CDCProcessor(BaseModel):
    """CDC处理器"""
    processor_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    
    # 处理配置
    batch_size: int = 100
    batch_timeout_ms: int = 5000
    
    # 处理函数
    processor_function: Optional[Callable[[List[CDCEvent]], None]] = None
    
    # 状态
    enabled: bool = True
    
    # 统计
    processed_count: int = 0
    error_count: int = 0
    last_processed_at: Optional[datetime] = None
    
    # 元数据
    created_at: datetime = Field(default_factory=datetime.now)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        arbitrary_types_allowed = True
    
    async def process_events(self, events: List[CDCEvent]) -> None:
        """处理事件列表"""
        if not self.enabled or not events:
            return
        
        try:
            if self.processor_function:
                # 如果是异步函数
                if asyncio.iscoroutinefunction(self.processor_function):
                    await self.processor_function(events)
                else:
                    # 同步函数在线程池中执行
                    loop = asyncio.get_event_loop()
                    await loop.run_in_executor(None, self.processor_function, events)
            
            self.processed_count += len(events)
            self.last_processed_at = datetime.now()
            
        except Exception as e:
            self.error_count += 1
            logger.error(f"处理器 {self.processor_id} 处理事件失败: {str(e)}")
            raise


class CDCPosition(BaseModel):
    """CDC位置信息"""
    source_id: str
    position_data: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)
    
    def to_string(self) -> str:
        """转换为字符串表示"""
        return json.dumps(self.position_data, sort_keys=True, default=str)
    
    @classmethod
    def from_string(cls, source_id: str, position_str: str) -> "CDCPosition":
        """从字符串创建位置对象"""
        position_data = json.loads(position_str)
        return cls(source_id=source_id, position_data=position_data)


class CDCManager:
    """变更数据捕获管理器
    
    负责管理CDC数据源、监控数据变更、过滤事件和触发处理。
    """

    def __init__(self):
        """初始化CDC管理器"""
        # 数据源配置
        self.sources: Dict[str, CDCSourceConfig] = {}
        
        # 过滤器
        self.filters: Dict[str, CDCFilter] = {}
        
        # 处理器
        self.processors: Dict[str, CDCProcessor] = {}
        
        # 运行状态
        self.source_status: Dict[str, CDCStatus] = {}
        
        # 位置跟踪
        self.positions: Dict[str, CDCPosition] = {}
        
        # 事件队列
        self.event_queues: Dict[str, asyncio.Queue] = {}
        
        # 监控任务
        self.monitoring_tasks: Dict[str, asyncio.Task] = {}
        
        # 处理任务
        self.processing_tasks: Dict[str, asyncio.Task] = {}
        
        # 统计信息
        self.statistics: Dict[str, Dict[str, Any]] = {}
        
        # 去重缓存
        self.dedup_cache: Dict[str, Set[str]] = {}
        self.dedup_cache_size = 10000
        
        logger.info("CDC管理器初始化完成")

    def add_source(self, config: CDCSourceConfig) -> None:
        """添加CDC数据源
        
        Args:
            config: 数据源配置
        """
        config.updated_at = datetime.now()
        self.sources[config.source_id] = config
        self.source_status[config.source_id] = CDCStatus.STOPPED
        self.event_queues[config.source_id] = asyncio.Queue(maxsize=config.max_queue_size)
        self.statistics[config.source_id] = {
            "events_captured": 0,
            "events_processed": 0,
            "events_filtered": 0,
            "errors": 0,
            "last_event_time": None,
            "start_time": None
        }
        self.dedup_cache[config.source_id] = set()
        
        logger.info(f"添加CDC数据源: {config.name}")

    def remove_source(self, source_id: str) -> None:
        """移除CDC数据源
        
        Args:
            source_id: 数据源ID
        """
        if source_id in self.sources:
            # 停止监控
            asyncio.create_task(self.stop_source(source_id))
            
            # 清理资源
            del self.sources[source_id]
            del self.source_status[source_id]
            del self.event_queues[source_id]
            del self.statistics[source_id]
            del self.dedup_cache[source_id]
            
            if source_id in self.positions:
                del self.positions[source_id]
            
            logger.info(f"移除CDC数据源: {source_id}")

    def add_filter(self, filter_config: CDCFilter) -> None:
        """添加过滤器
        
        Args:
            filter_config: 过滤器配置
        """
        self.filters[filter_config.filter_id] = filter_config
        logger.debug(f"添加CDC过滤器: {filter_config.name}")

    def remove_filter(self, filter_id: str) -> None:
        """移除过滤器
        
        Args:
            filter_id: 过滤器ID
        """
        if filter_id in self.filters:
            del self.filters[filter_id]
            logger.debug(f"移除CDC过滤器: {filter_id}")

    def add_processor(self, processor: CDCProcessor) -> None:
        """添加处理器
        
        Args:
            processor: 处理器
        """
        self.processors[processor.processor_id] = processor
        logger.debug(f"添加CDC处理器: {processor.name}")

    def remove_processor(self, processor_id: str) -> None:
        """移除处理器
        
        Args:
            processor_id: 处理器ID
        """
        if processor_id in self.processors:
            del self.processors[processor_id]
            logger.debug(f"移除CDC处理器: {processor_id}")

    async def start_source(self, source_id: str) -> bool:
        """启动CDC数据源监控
        
        Args:
            source_id: 数据源ID
            
        Returns:
            是否成功启动
        """
        if source_id not in self.sources:
            logger.error(f"数据源不存在: {source_id}")
            return False
        
        if self.source_status[source_id] == CDCStatus.RUNNING:
            logger.warning(f"数据源已在运行: {source_id}")
            return True
        
        config = self.sources[source_id]
        
        logger.info(f"启动CDC数据源监控: {config.name}")
        
        try:
            self.source_status[source_id] = CDCStatus.STARTING
            
            # 初始化位置
            await self._initialize_position(source_id)
            
            # 启动监控任务
            monitoring_task = asyncio.create_task(
                self._monitor_source(source_id)
            )
            self.monitoring_tasks[source_id] = monitoring_task
            
            # 启动处理任务
            processing_task = asyncio.create_task(
                self._process_events(source_id)
            )
            self.processing_tasks[source_id] = processing_task
            
            self.source_status[source_id] = CDCStatus.RUNNING
            self.statistics[source_id]["start_time"] = datetime.now()
            
            logger.info(f"CDC数据源启动成功: {config.name}")
            return True
            
        except Exception as e:
            self.source_status[source_id] = CDCStatus.ERROR
            logger.error(f"启动CDC数据源失败 {config.name}: {str(e)}")
            return False

    async def stop_source(self, source_id: str) -> bool:
        """停止CDC数据源监控
        
        Args:
            source_id: 数据源ID
            
        Returns:
            是否成功停止
        """
        if source_id not in self.sources:
            return False
        
        if self.source_status[source_id] == CDCStatus.STOPPED:
            return True
        
        config = self.sources[source_id]
        
        logger.info(f"停止CDC数据源监控: {config.name}")
        
        try:
            self.source_status[source_id] = CDCStatus.STOPPING
            
            # 停止监控任务
            if source_id in self.monitoring_tasks:
                self.monitoring_tasks[source_id].cancel()
                try:
                    await self.monitoring_tasks[source_id]
                except asyncio.CancelledError:
                    pass
                del self.monitoring_tasks[source_id]
            
            # 停止处理任务
            if source_id in self.processing_tasks:
                self.processing_tasks[source_id].cancel()
                try:
                    await self.processing_tasks[source_id]
                except asyncio.CancelledError:
                    pass
                del self.processing_tasks[source_id]
            
            # 保存位置
            await self._save_position(source_id)
            
            self.source_status[source_id] = CDCStatus.STOPPED
            
            logger.info(f"CDC数据源停止成功: {config.name}")
            return True
            
        except Exception as e:
            logger.error(f"停止CDC数据源失败 {config.name}: {str(e)}")
            return False

    async def _initialize_position(self, source_id: str) -> None:
        """初始化位置信息"""
        config = self.sources[source_id]
        
        # 尝试从存储中加载位置
        saved_position = await self._load_position(source_id)
        
        if saved_position:
            self.positions[source_id] = saved_position
            logger.debug(f"加载保存的位置: {source_id}")
        else:
            # 根据初始位置配置创建新位置
            if config.initial_position == "earliest":
                position_data = {"type": "earliest"}
            elif config.initial_position == "latest":
                position_data = {"type": "latest"}
            else:
                # 时间戳位置
                position_data = {
                    "type": "timestamp",
                    "timestamp": config.initial_position
                }
            
            self.positions[source_id] = CDCPosition(
                source_id=source_id,
                position_data=position_data
            )
            
            logger.debug(f"创建新位置: {source_id}, {position_data}")

    async def _load_position(self, source_id: str) -> Optional[CDCPosition]:
        """从存储中加载位置信息"""
        # TODO: 从数据库加载位置
        # 这里应该从持久化存储（如数据库、文件）中加载位置
        # 暂时返回None，表示没有保存的位置
        return None

    async def _save_position(self, source_id: str) -> None:
        """保存位置信息到存储"""
        if source_id in self.positions:
            position = self.positions[source_id]
            # 这里应该将位置信息保存到持久化存储
            # TODO: 实现数据库保存
            logger.debug(f"保存位置: {source_id}, {position.to_string()}")

    async def _monitor_source(self, source_id: str) -> None:
        """监控数据源变更"""
        config = self.sources[source_id]
        
        logger.debug(f"开始监控数据源: {config.name}")
        
        try:
            while self.source_status[source_id] == CDCStatus.RUNNING:
                try:
                    # 根据数据源类型获取变更事件
                    events = await self._capture_events(source_id)
                    
                    for event in events:
                        # 去重检查
                        if self._is_duplicate_event(source_id, event):
                            continue
                        
                        # 应用过滤器
                        if self._should_filter_event(event):
                            self.statistics[source_id]["events_filtered"] += 1
                            continue
                        
                        # 添加到事件队列
                        try:
                            await self.event_queues[source_id].put(event)
                            self.statistics[source_id]["events_captured"] += 1
                            self.statistics[source_id]["last_event_time"] = datetime.now()
                        except asyncio.QueueFull:
                            logger.warning(f"事件队列已满: {source_id}")
                            # 可以选择丢弃事件或等待
                            # TODO: 实现队列满后的处理策略
                            break
                    
                    # 更新位置
                    if events:
                        await self._update_position(source_id, events[-1])
                    
                    # 等待下一次轮询
                    await asyncio.sleep(config.poll_interval_ms / 1000.0)
                    
                except Exception as e:
                    self.statistics[source_id]["errors"] += 1
                    logger.error(f"监控数据源出错 {source_id}: {str(e)}")
                    
                    # 根据容错配置决定是否继续
                    if config.error_tolerance == "none":
                        raise
                    
                    # 等待重试
                    await asyncio.sleep(config.retry_delay_ms / 1000.0)
                    
        except asyncio.CancelledError:
            logger.debug(f"监控任务被取消: {source_id}")
            raise
        except Exception as e:
            self.source_status[source_id] = CDCStatus.ERROR
            logger.error(f"监控任务失败 {source_id}: {str(e)}")

    async def _capture_events(self, source_id: str) -> List[CDCEvent]:
        """捕获变更事件"""
        config = self.sources[source_id]
        
        # 根据数据源类型实现不同的捕获逻辑
        if config.source_type == CDCSourceType.MYSQL:
            return await self._capture_mysql_events(source_id)
        elif config.source_type == CDCSourceType.POSTGRESQL:
            return await self._capture_postgresql_events(source_id)
        elif config.source_type == CDCSourceType.MONGODB:
            return await self._capture_mongodb_events(source_id)
        elif config.source_type == CDCSourceType.FILE_SYSTEM:
            return await self._capture_file_events(source_id)
        else:
            # 模拟事件生成
            # TODO: 实现其他类型事件捕获
            return await self._generate_mock_events(source_id)

    async def _capture_mysql_events(self, source_id: str) -> List[CDCEvent]:
        """捕获MySQL变更事件"""
        # 实际实现需要连接MySQL并读取binlog
        # 这里返回模拟事件
        # TODO: 实现MySQL事件捕获
        return await self._generate_mock_events(source_id)

    async def _capture_postgresql_events(self, source_id: str) -> List[CDCEvent]:
        """捕获PostgreSQL变更事件"""
        # 实际实现需要使用逻辑复制或触发器
        # 这里返回模拟事件
        # TODO: 实现PostgreSQL事件捕获
        return await self._generate_mock_events(source_id)

    async def _capture_mongodb_events(self, source_id: str) -> List[CDCEvent]:
        """捕获MongoDB变更事件"""
        # 实际实现需要使用Change Streams
        # 这里返回模拟事件
        # TODO: 实现MongoDB事件捕获
        return await self._generate_mock_events(source_id)

    async def _capture_file_events(self, source_id: str) -> List[CDCEvent]:
        """捕获文件系统变更事件"""
        # 实际实现需要使用文件系统监控
        # 这里返回模拟事件
        # TODO: 实现文件系统事件捕获
        return await self._generate_mock_events(source_id)

    async def _generate_mock_events(self, source_id: str) -> List[CDCEvent]:
        """生成模拟事件（用于测试）"""
        import random
        
        config = self.sources[source_id]
        events = []
        
        # 随机生成0-5个事件
        event_count = random.randint(0, 5)
        
        for i in range(event_count):
            event_type = random.choice(list(CDCEventType))
            
            if event_type == CDCEventType.HEARTBEAT:
                event = CDCEvent(
                    source_id=source_id,
                    event_type=event_type,
                    metadata={"heartbeat": True}
                )
            else:
                # 模拟数据变更事件
                table = random.choice(config.tables) if config.tables else "test_table"
                database = random.choice(config.databases) if config.databases else "test_db"
                
                record_id = random.randint(1, 1000)
                
                before_data = None
                after_data = None
                
                if event_type == CDCEventType.INSERT:
                    after_data = {
                        "id": record_id,
                        "name": f"record_{record_id}",
                        "value": random.randint(1, 100),
                        "created_at": datetime.now().isoformat()
                    }
                elif event_type == CDCEventType.UPDATE:
                    before_data = {
                        "id": record_id,
                        "name": f"record_{record_id}",
                        "value": random.randint(1, 100),
                        "updated_at": (datetime.now() - timedelta(minutes=1)).isoformat()
                    }
                    after_data = {
                        "id": record_id,
                        "name": f"record_{record_id}_updated",
                        "value": random.randint(1, 100),
                        "updated_at": datetime.now().isoformat()
                    }
                elif event_type == CDCEventType.DELETE:
                    before_data = {
                        "id": record_id,
                        "name": f"record_{record_id}",
                        "value": random.randint(1, 100)
                    }
                
                event = CDCEvent(
                    source_id=source_id,
                    event_type=event_type,
                    database=database,
                    table=table,
                    before_data=before_data,
                    after_data=after_data,
                    position={
                        "binlog_file": "mysql-bin.000001",
                        "binlog_position": random.randint(1000, 10000)
                    }
                )
            
            events.append(event)
        
        return events

    def _is_duplicate_event(self, source_id: str, event: CDCEvent) -> bool:
        """检查是否为重复事件"""
        event_hash = event.get_hash()
        
        if event_hash in self.dedup_cache[source_id]:
            return True
        
        # 添加到去重缓存
        self.dedup_cache[source_id].add(event_hash)
        
        # 限制缓存大小
        if len(self.dedup_cache[source_id]) > self.dedup_cache_size:
            # 移除最旧的一半
            cache_list = list(self.dedup_cache[source_id])
            self.dedup_cache[source_id] = set(cache_list[len(cache_list)//2:])
        
        return False

    def _should_filter_event(self, event: CDCEvent) -> bool:
        """检查事件是否应该被过滤"""
        # 按优先级排序过滤器
        sorted_filters = sorted(
            self.filters.values(),
            key=lambda f: f.priority,
            reverse=True
        )
        
        for filter_config in sorted_filters:
            if filter_config.matches(event):
                # 如果是排除过滤器且匹配，则过滤掉
                if not filter_config.include:
                    return True
            else:
                # 如果是包含过滤器且不匹配，则过滤掉
                if filter_config.include:
                    return True
        
        return False

    async def _update_position(self, source_id: str, event: CDCEvent) -> None:
        """更新位置信息"""
        if source_id in self.positions and event.position:
            position = self.positions[source_id]
            position.position_data.update(event.position)
            position.timestamp = datetime.now()

    async def _process_events(self, source_id: str) -> None:
        """处理事件队列"""
        config = self.sources[source_id]
        event_queue = self.event_queues[source_id]
        
        logger.debug(f"开始处理事件: {source_id}")
        
        try:
            event_batch = []
            last_batch_time = datetime.now()
            
            while self.source_status[source_id] == CDCStatus.RUNNING:
                try:
                    # 等待事件或超时
                    timeout = config.poll_interval_ms / 1000.0
                    
                    try:
                        event = await asyncio.wait_for(event_queue.get(), timeout=timeout)
                        event_batch.append(event)
                    except asyncio.TimeoutError:
                        # 超时，检查是否需要处理当前批次
                        pass
                    
                    current_time = datetime.now()
                    batch_timeout = (current_time - last_batch_time).total_seconds() * 1000
                    
                    # 检查是否需要处理批次
                    should_process = (
                        len(event_batch) >= config.batch_size or
                        (event_batch and batch_timeout >= config.poll_interval_ms)
                    )
                    
                    if should_process and event_batch:
                        # 处理事件批次
                        await self._process_event_batch(source_id, event_batch)
                        
                        # 更新统计
                        self.statistics[source_id]["events_processed"] += len(event_batch)
                        
                        # 重置批次
                        event_batch = []
                        last_batch_time = current_time
                        
                        # 定期保存位置
                        if batch_timeout >= config.checkpoint_interval_ms:
                            await self._save_position(source_id)
                    
                except Exception as e:
                    self.statistics[source_id]["errors"] += 1
                    logger.error(f"处理事件出错 {source_id}: {str(e)}")
                    
                    # 根据容错配置决定是否继续
                    if config.error_tolerance == "none":
                        raise
                    
                    # 清空当前批次，避免重复处理错误事件
                    event_batch = []
                    last_batch_time = datetime.now()
                    
                    await asyncio.sleep(1)
            
            # 处理剩余事件
            if event_batch:
                await self._process_event_batch(source_id, event_batch)
                self.statistics[source_id]["events_processed"] += len(event_batch)
                
        except asyncio.CancelledError:
            logger.debug(f"事件处理任务被取消: {source_id}")
            raise
        except Exception as e:
            self.source_status[source_id] = CDCStatus.ERROR
            logger.error(f"事件处理任务失败 {source_id}: {str(e)}")

    async def _process_event_batch(self, source_id: str, events: List[CDCEvent]) -> None:
        """处理事件批次"""
        if not events:
            return
        
        logger.debug(f"处理事件批次: {source_id}, 事件数: {len(events)}")
        
        # 调用所有启用的处理器
        for processor in self.processors.values():
            if processor.enabled:
                try:
                    await processor.process_events(events)
                except Exception as e:
                    logger.error(f"处理器 {processor.processor_id} 处理失败: {str(e)}")
                    # 继续处理其他处理器

    def get_source_status(self, source_id: str) -> Dict[str, Any]:
        """获取数据源状态
        
        Args:
            source_id: 数据源ID
            
        Returns:
            状态信息
        """
        if source_id not in self.sources:
            return {}
        
        config = self.sources[source_id]
        status = self.source_status[source_id]
        stats = self.statistics[source_id]
        
        result = {
            "source_id": source_id,
            "name": config.name,
            "source_type": config.source_type.value,
            "status": status.value,
            "statistics": stats.copy()
        }
        
        # 添加位置信息
        if source_id in self.positions:
            result["position"] = self.positions[source_id].position_data
        
        # 添加队列信息
        if source_id in self.event_queues:
            result["queue_size"] = self.event_queues[source_id].qsize()
            result["queue_max_size"] = config.max_queue_size
        
        return result

    def get_all_sources_status(self) -> List[Dict[str, Any]]:
        """获取所有数据源状态
        
        Returns:
            所有数据源状态列表
        """
        return [self.get_source_status(source_id) for source_id in self.sources.keys()]

    def get_statistics(self) -> Dict[str, Any]:
        """获取整体统计信息
        
        Returns:
            统计信息
        """
        total_stats = {
            "total_sources": len(self.sources),
            "running_sources": sum(1 for status in self.source_status.values() if status == CDCStatus.RUNNING),
            "total_events_captured": sum(stats["events_captured"] for stats in self.statistics.values()),
            "total_events_processed": sum(stats["events_processed"] for stats in self.statistics.values()),
            "total_events_filtered": sum(stats["events_filtered"] for stats in self.statistics.values()),
            "total_errors": sum(stats["errors"] for stats in self.statistics.values()),
            "total_filters": len(self.filters),
            "active_filters": sum(1 for f in self.filters.values() if f.enabled),
            "total_processors": len(self.processors),
            "active_processors": sum(1 for p in self.processors.values() if p.enabled)
        }
        
        # 按数据源类型统计
        source_type_stats = {}
        for config in self.sources.values():
            source_type = config.source_type.value
            if source_type not in source_type_stats:
                source_type_stats[source_type] = 0
            source_type_stats[source_type] += 1
        
        total_stats["source_type_distribution"] = source_type_stats
        
        return total_stats

    async def pause_source(self, source_id: str) -> bool:
        """暂停数据源监控
        
        Args:
            source_id: 数据源ID
            
        Returns:
            是否成功暂停
        """
        if source_id not in self.sources or self.source_status[source_id] != CDCStatus.RUNNING:
            return False
        
        self.source_status[source_id] = CDCStatus.PAUSED
        logger.info(f"暂停CDC数据源: {source_id}")
        return True

    async def resume_source(self, source_id: str) -> bool:
        """恢复数据源监控
        
        Args:
            source_id: 数据源ID
            
        Returns:
            是否成功恢复
        """
        if source_id not in self.sources or self.source_status[source_id] != CDCStatus.PAUSED:
            return False
        
        self.source_status[source_id] = CDCStatus.RUNNING
        logger.info(f"恢复CDC数据源: {source_id}")
        return True

    async def reset_source_position(self, source_id: str, new_position: Optional[Dict[str, Any]] = None) -> bool:
        """重置数据源位置
        
        Args:
            source_id: 数据源ID
            new_position: 新位置，如果为None则重置为初始位置
            
        Returns:
            是否成功重置
        """
        if source_id not in self.sources:
            return False
        
        config = self.sources[source_id]
        
        if new_position:
            position_data = new_position
        else:
            # 重置为初始位置
            if config.initial_position == "earliest":
                position_data = {"type": "earliest"}
            elif config.initial_position == "latest":
                position_data = {"type": "latest"}
            else:
                position_data = {
                    "type": "timestamp",
                    "timestamp": config.initial_position
                }
        
        self.positions[source_id] = CDCPosition(
            source_id=source_id,
            position_data=position_data
        )
        
        await self._save_position(source_id)
        
        logger.info(f"重置CDC数据源位置: {source_id}")
        return True

    async def cleanup_old_events(self, hours: int = 24) -> int:
        """清理旧事件
        
        Args:
            hours: 保留小时数
            
        Returns:
            清理的事件数
        """
        cutoff_time = datetime.now() - timedelta(hours=hours)
        cleaned_count = 0
        
        # 清理去重缓存
        for source_id in self.dedup_cache:
            cache_size_before = len(self.dedup_cache[source_id])
            # 简单清理：清空一半缓存
            cache_list = list(self.dedup_cache[source_id])
            self.dedup_cache[source_id] = set(cache_list[len(cache_list)//2:])
            cleaned_count += cache_size_before - len(self.dedup_cache[source_id])
        
        logger.info(f"清理了 {cleaned_count} 个旧事件记录")
        return cleaned_count

    async def health_check(self) -> Dict[str, Any]:
        """健康检查
        
        Returns:
            健康状态信息
        """
        health_status = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "sources": {},
            "overall": {
                "total_sources": len(self.sources),
                "running_sources": 0,
                "error_sources": 0
            },
            "issues": []
        }
        
        # 检查各数据源状态
        for source_id, status in self.source_status.items():
            config = self.sources[source_id]
            
            source_health = {
                "name": config.name,
                "status": status.value,
                "last_event_time": self.statistics[source_id].get("last_event_time")
            }
            
            if status == CDCStatus.RUNNING:
                health_status["overall"]["running_sources"] += 1
                
                # 检查是否长时间没有事件
                last_event_time = self.statistics[source_id].get("last_event_time")
                if last_event_time:
                    time_since_last_event = datetime.now() - last_event_time
                    if time_since_last_event > timedelta(minutes=30):
                        health_status["issues"].append(
                            f"数据源 {config.name} 长时间没有事件: {time_since_last_event}"
                        )
                        source_health["warning"] = "长时间没有事件"
            
            elif status == CDCStatus.ERROR:
                health_status["overall"]["error_sources"] += 1
                health_status["issues"].append(f"数据源 {config.name} 处于错误状态")
            
            # 检查队列积压
            if source_id in self.event_queues:
                queue_size = self.event_queues[source_id].qsize()
                max_size = config.max_queue_size
                
                if queue_size > max_size * 0.8:  # 80%阈值
                    health_status["issues"].append(
                        f"数据源 {config.name} 事件队列积压: {queue_size}/{max_size}"
                    )
                    source_health["warning"] = "队列积压"
                
                source_health["queue_usage"] = f"{queue_size}/{max_size}"
            
            health_status["sources"][source_id] = source_health
        
        # 确定整体健康状态
        if health_status["issues"]:
            if health_status["overall"]["error_sources"] > 0:
                health_status["status"] = "unhealthy"
            else:
                health_status["status"] = "degraded"
        
        return health_status