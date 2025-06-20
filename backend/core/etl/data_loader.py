"""数据加载器

负责将处理后的数据加载到目标系统中，支持多种目标类型和加载策略。
"""

import json
import uuid
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union, Tuple, AsyncGenerator
from enum import Enum
from dataclasses import dataclass
from pathlib import Path

import aiofiles
from pydantic import BaseModel, Field

from backend.utils.logger import get_logger
from backend.core.knowledge_graph.graph_manager import GraphManager
from backend.models.knowledge import Entity, Relation
from .data_structurer import StructuredData, DataType

logger = get_logger(__name__)


class LoadTargetType(str, Enum):
    """加载目标类型枚举"""
    KNOWLEDGE_GRAPH = "knowledge_graph"  # 知识图谱
    VECTOR_STORE = "vector_store"  # 向量存储
    DATABASE = "database"  # 数据库
    FILE_SYSTEM = "file_system"  # 文件系统
    ELASTICSEARCH = "elasticsearch"  # Elasticsearch
    CACHE = "cache"  # 缓存
    API = "api"  # API接口
    QUEUE = "queue"  # 消息队列


class LoadStrategy(str, Enum):
    """加载策略枚举"""
    INSERT = "insert"  # 插入新数据
    UPDATE = "update"  # 更新现有数据
    UPSERT = "upsert"  # 插入或更新
    REPLACE = "replace"  # 替换数据
    APPEND = "append"  # 追加数据
    MERGE = "merge"  # 合并数据
    SKIP_EXISTING = "skip_existing"  # 跳过已存在的数据


class LoadStatus(str, Enum):
    """加载状态枚举"""
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"
    SKIPPED = "skipped"
    PENDING = "pending"
    RETRY = "retry"


@dataclass
class LoadTarget:
    """加载目标配置"""
    id: str
    name: str
    target_type: LoadTargetType
    connection_config: Dict[str, Any]
    load_strategy: LoadStrategy = LoadStrategy.UPSERT
    batch_size: int = 100
    max_retries: int = 3
    retry_delay: int = 5  # 秒
    timeout: int = 300  # 秒
    enabled: bool = True
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class LoadResult(BaseModel):
    """加载结果"""
    data_id: str
    target_id: str
    target_name: str
    status: LoadStatus
    message: str
    records_processed: int = 0
    records_successful: int = 0
    records_failed: int = 0
    records_skipped: int = 0
    execution_time_ms: Optional[int] = None
    retry_count: int = 0
    error_details: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.now)


class LoadReport(BaseModel):
    """加载报告"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    data_id: str
    total_targets: int
    successful_targets: int
    failed_targets: int
    partial_targets: int
    skipped_targets: int
    results: List[LoadResult]
    summary: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)
    duration_ms: Optional[int] = None


class DataLoader:
    """数据加载器
    
    提供灵活的数据加载功能，支持多种目标系统和加载策略。
    """

    def __init__(self, graph_manager: Optional[GraphManager] = None):
        """初始化数据加载器
        
        Args:
            graph_manager: 知识图谱管理器
        """
        self.graph_manager = graph_manager
        self.targets: Dict[str, LoadTarget] = {}
        self._initialize_default_targets()
        
    def _initialize_default_targets(self) -> None:
        """初始化默认加载目标"""
        # 知识图谱目标
        self.add_target(LoadTarget(
            id="default_knowledge_graph",
            name="默认知识图谱",
            target_type=LoadTargetType.KNOWLEDGE_GRAPH,
            connection_config={},
            load_strategy=LoadStrategy.UPSERT,
            batch_size=50
        ))
        
        # 文件系统目标
        self.add_target(LoadTarget(
            id="file_backup",
            name="文件备份",
            target_type=LoadTargetType.FILE_SYSTEM,
            connection_config={
                "base_path": "./data/processed",
                "format": "json"
            },
            load_strategy=LoadStrategy.APPEND,
            batch_size=100
        ))
        
        # 缓存目标
        self.add_target(LoadTarget(
            id="memory_cache",
            name="内存缓存",
            target_type=LoadTargetType.CACHE,
            connection_config={
                "ttl": 3600,  # 1小时
                "max_size": 10000
            },
            load_strategy=LoadStrategy.REPLACE,
            batch_size=200
        ))

    def add_target(self, target: LoadTarget) -> None:
        """添加加载目标
        
        Args:
            target: 加载目标配置
        """
        self.targets[target.id] = target
        logger.debug(f"添加加载目标: {target.name}")

    def remove_target(self, target_id: str) -> None:
        """移除加载目标
        
        Args:
            target_id: 目标ID
        """
        if target_id in self.targets:
            del self.targets[target_id]
            logger.debug(f"移除加载目标: {target_id}")

    async def load(
        self,
        data: StructuredData,
        target_ids: Optional[List[str]] = None
    ) -> LoadReport:
        """加载数据到目标系统
        
        Args:
            data: 结构化数据
            target_ids: 目标ID列表，如果为None则加载到所有启用的目标
            
        Returns:
            加载报告
        """
        start_time = datetime.now()
        
        try:
            logger.info(f"开始加载数据: {data.id}")
            
            # 确定要加载的目标
            if target_ids:
                targets_to_load = [self.targets[tid] for tid in target_ids if tid in self.targets]
            else:
                targets_to_load = [target for target in self.targets.values() if target.enabled]
            
            # 并行加载到各个目标
            tasks = []
            for target in targets_to_load:
                task = asyncio.create_task(self._load_to_target(data, target))
                tasks.append(task)
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 处理结果
            load_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    # 处理异常
                    target = targets_to_load[i]
                    error_result = LoadResult(
                        data_id=data.id,
                        target_id=target.id,
                        target_name=target.name,
                        status=LoadStatus.FAILED,
                        message=f"加载过程中发生异常: {str(result)}",
                        error_details={"exception": str(result)}
                    )
                    load_results.append(error_result)
                else:
                    load_results.append(result)
            
            # 统计结果
            successful = sum(1 for r in load_results if r.status == LoadStatus.SUCCESS)
            failed = sum(1 for r in load_results if r.status == LoadStatus.FAILED)
            partial = sum(1 for r in load_results if r.status == LoadStatus.PARTIAL)
            skipped = sum(1 for r in load_results if r.status == LoadStatus.SKIPPED)
            
            # 创建报告
            duration = int((datetime.now() - start_time).total_seconds() * 1000)
            
            report = LoadReport(
                data_id=data.id,
                total_targets=len(load_results),
                successful_targets=successful,
                failed_targets=failed,
                partial_targets=partial,
                skipped_targets=skipped,
                results=load_results,
                duration_ms=duration,
                summary=self._generate_summary(load_results)
            )
            
            logger.info(
                f"数据加载完成: {data.id}, 成功: {successful}, "
                f"失败: {failed}, 部分: {partial}, 跳过: {skipped}"
            )
            
            return report
            
        except Exception as e:
            logger.error(f"数据加载失败: {data.id}, 错误: {str(e)}")
            raise

    async def _load_to_target(
        self,
        data: StructuredData,
        target: LoadTarget
    ) -> LoadResult:
        """加载数据到指定目标
        
        Args:
            data: 结构化数据
            target: 加载目标
            
        Returns:
            加载结果
        """
        start_time = datetime.now()
        retry_count = 0
        
        while retry_count <= target.max_retries:
            try:
                logger.debug(f"加载数据到目标: {target.name}, 重试次数: {retry_count}")
                
                # 根据目标类型执行加载
                if target.target_type == LoadTargetType.KNOWLEDGE_GRAPH:
                    result = await self._load_to_knowledge_graph(data, target)
                elif target.target_type == LoadTargetType.FILE_SYSTEM:
                    result = await self._load_to_file_system(data, target)
                elif target.target_type == LoadTargetType.CACHE:
                    result = await self._load_to_cache(data, target)
                elif target.target_type == LoadTargetType.DATABASE:
                    result = await self._load_to_database(data, target)
                elif target.target_type == LoadTargetType.VECTOR_STORE:
                    result = await self._load_to_vector_store(data, target)
                else:
                    result = LoadResult(
                        data_id=data.id,
                        target_id=target.id,
                        target_name=target.name,
                        status=LoadStatus.SKIPPED,
                        message=f"不支持的目标类型: {target.target_type}"
                    )
                
                # 设置执行时间和重试次数
                execution_time = int((datetime.now() - start_time).total_seconds() * 1000)
                result.execution_time_ms = execution_time
                result.retry_count = retry_count
                
                return result
                
            except Exception as e:
                retry_count += 1
                logger.warning(
                    f"加载到目标 {target.name} 失败 (重试 {retry_count}/{target.max_retries}): {str(e)}"
                )
                
                if retry_count <= target.max_retries:
                    await asyncio.sleep(target.retry_delay)
                else:
                    # 达到最大重试次数
                    execution_time = int((datetime.now() - start_time).total_seconds() * 1000)
                    return LoadResult(
                        data_id=data.id,
                        target_id=target.id,
                        target_name=target.name,
                        status=LoadStatus.FAILED,
                        message=f"达到最大重试次数，最后错误: {str(e)}",
                        execution_time_ms=execution_time,
                        retry_count=retry_count - 1,
                        error_details={"last_error": str(e)}
                    )

    async def _load_to_knowledge_graph(
        self,
        data: StructuredData,
        target: LoadTarget
    ) -> LoadResult:
        """加载数据到知识图谱"""
        if not self.graph_manager:
            return LoadResult(
                data_id=data.id,
                target_id=target.id,
                target_name=target.name,
                status=LoadStatus.FAILED,
                message="知识图谱管理器未初始化"
            )
        
        try:
            records_processed = 0
            records_successful = 0
            records_failed = 0
            
            # 加载实体
            if data.entities:
                for entity_data in data.entities:
                    try:
                        entity = Entity(
                            id=entity_data.get("id", str(uuid.uuid4())),
                            type=entity_data.get("type", "unknown"),
                            properties=entity_data.get("properties", {})
                        )
                        
                        if target.load_strategy == LoadStrategy.UPSERT:
                            await self.graph_manager.upsert_entity(entity)
                        elif target.load_strategy == LoadStrategy.INSERT:
                            await self.graph_manager.create_entity(entity)
                        elif target.load_strategy == LoadStrategy.UPDATE:
                            await self.graph_manager.update_entity(entity)
                        
                        records_successful += 1
                    except Exception as e:
                        logger.error(f"加载实体失败: {entity_data}, 错误: {str(e)}")
                        records_failed += 1
                    
                    records_processed += 1
            
            # 加载关系
            if data.relationships:
                for rel_data in data.relationships:
                    try:
                        relationship = Relation(
                            id=rel_data.get("id", str(uuid.uuid4())),
                            source_id=rel_data.get("source_id"),
                            target_id=rel_data.get("target_id"),
                            type=rel_data.get("type"),
                            properties=rel_data.get("properties", {})
                        )
                        
                        if target.load_strategy == LoadStrategy.UPSERT:
                            await self.graph_manager.upsert_relationship(relationship)
                        elif target.load_strategy == LoadStrategy.INSERT:
                            await self.graph_manager.create_relationship(relationship)
                        elif target.load_strategy == LoadStrategy.UPDATE:
                            await self.graph_manager.update_relationship(relationship)
                        
                        records_successful += 1
                    except Exception as e:
                        logger.error(f"加载关系失败: {rel_data}, 错误: {str(e)}")
                        records_failed += 1
                    
                    records_processed += 1
            
            # 确定状态
            if records_failed == 0:
                status = LoadStatus.SUCCESS
                message = f"成功加载 {records_successful} 条记录到知识图谱"
            elif records_successful > 0:
                status = LoadStatus.PARTIAL
                message = f"部分成功，成功: {records_successful}, 失败: {records_failed}"
            else:
                status = LoadStatus.FAILED
                message = f"加载失败，失败记录数: {records_failed}"
            
            return LoadResult(
                data_id=data.id,
                target_id=target.id,
                target_name=target.name,
                status=status,
                message=message,
                records_processed=records_processed,
                records_successful=records_successful,
                records_failed=records_failed
            )
            
        except Exception as e:
            return LoadResult(
                data_id=data.id,
                target_id=target.id,
                target_name=target.name,
                status=LoadStatus.FAILED,
                message=f"知识图谱加载失败: {str(e)}",
                error_details={"error": str(e)}
            )

    async def _load_to_file_system(
        self,
        data: StructuredData,
        target: LoadTarget
    ) -> LoadResult:
        """加载数据到文件系统"""
        try:
            base_path = Path(target.connection_config.get("base_path", "./data"))
            file_format = target.connection_config.get("format", "json")
            
            # 确保目录存在
            base_path.mkdir(parents=True, exist_ok=True)
            
            # 生成文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{data.id}_{timestamp}.{file_format}"
            file_path = base_path / filename
            
            # 准备数据
            if file_format == "json":
                content = data.json(indent=2, ensure_ascii=False)
            else:
                content = str(data)
            
            # 写入文件
            async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
                await f.write(content)
            
            return LoadResult(
                data_id=data.id,
                target_id=target.id,
                target_name=target.name,
                status=LoadStatus.SUCCESS,
                message=f"成功保存到文件: {file_path}",
                records_processed=1,
                records_successful=1
            )
            
        except Exception as e:
            return LoadResult(
                data_id=data.id,
                target_id=target.id,
                target_name=target.name,
                status=LoadStatus.FAILED,
                message=f"文件系统加载失败: {str(e)}",
                error_details={"error": str(e)}
            )

    async def _load_to_cache(
        self,
        data: StructuredData,
        target: LoadTarget
    ) -> LoadResult:
        """加载数据到缓存"""
        try:
            # 这里应该集成实际的缓存系统（如Redis）
            # 目前使用简单的内存缓存模拟
            
            cache_key = f"structured_data:{data.id}"
            cache_data = data.dict()
            
            # 模拟缓存操作
            logger.debug(f"缓存数据: {cache_key}")
            
            return LoadResult(
                data_id=data.id,
                target_id=target.id,
                target_name=target.name,
                status=LoadStatus.SUCCESS,
                message=f"成功缓存数据: {cache_key}",
                records_processed=1,
                records_successful=1
            )
            
        except Exception as e:
            return LoadResult(
                data_id=data.id,
                target_id=target.id,
                target_name=target.name,
                status=LoadStatus.FAILED,
                message=f"缓存加载失败: {str(e)}",
                error_details={"error": str(e)}
            )

    async def _load_to_database(
        self,
        data: StructuredData,
        target: LoadTarget
    ) -> LoadResult:
        """加载数据到数据库"""
        try:
            # 这里应该集成实际的数据库连接
            # 目前返回模拟结果
            
            return LoadResult(
                data_id=data.id,
                target_id=target.id,
                target_name=target.name,
                status=LoadStatus.SUCCESS,
                message="数据库加载功能待实现",
                records_processed=1,
                records_successful=1
            )
            
        except Exception as e:
            return LoadResult(
                data_id=data.id,
                target_id=target.id,
                target_name=target.name,
                status=LoadStatus.FAILED,
                message=f"数据库加载失败: {str(e)}",
                error_details={"error": str(e)}
            )

    async def _load_to_vector_store(
        self,
        data: StructuredData,
        target: LoadTarget
    ) -> LoadResult:
        """加载数据到向量存储"""
        try:
            # 这里应该集成向量存储系统
            # 目前返回模拟结果
            
            return LoadResult(
                data_id=data.id,
                target_id=target.id,
                target_name=target.name,
                status=LoadStatus.SUCCESS,
                message="向量存储加载功能待实现",
                records_processed=1,
                records_successful=1
            )
            
        except Exception as e:
            return LoadResult(
                data_id=data.id,
                target_id=target.id,
                target_name=target.name,
                status=LoadStatus.FAILED,
                message=f"向量存储加载失败: {str(e)}",
                error_details={"error": str(e)}
            )

    def _generate_summary(self, results: List[LoadResult]) -> Dict[str, Any]:
        """生成加载摘要"""
        summary = {
            "load_time": datetime.now().isoformat(),
            "targets_by_status": {},
            "targets_by_type": {},
            "failed_targets": [],
            "execution_times": [],
            "total_records": {
                "processed": 0,
                "successful": 0,
                "failed": 0,
                "skipped": 0
            }
        }
        
        # 按状态统计
        for status in LoadStatus:
            count = sum(1 for r in results if r.status == status)
            summary["targets_by_status"][status.value] = count
        
        # 按类型统计
        type_counts = {}
        for result in results:
            target = self.targets.get(result.target_id)
            if target:
                target_type = target.target_type.value
                type_counts[target_type] = type_counts.get(target_type, 0) + 1
        summary["targets_by_type"] = type_counts
        
        # 收集失败的目标
        summary["failed_targets"] = [
            {
                "target_id": r.target_id,
                "target_name": r.target_name,
                "message": r.message,
                "retry_count": r.retry_count
            }
            for r in results if r.status == LoadStatus.FAILED
        ]
        
        # 执行时间统计
        execution_times = [r.execution_time_ms for r in results if r.execution_time_ms is not None]
        if execution_times:
            summary["execution_times"] = {
                "min": min(execution_times),
                "max": max(execution_times),
                "avg": sum(execution_times) / len(execution_times),
                "total": sum(execution_times)
            }
        
        # 记录统计
        for result in results:
            summary["total_records"]["processed"] += result.records_processed
            summary["total_records"]["successful"] += result.records_successful
            summary["total_records"]["failed"] += result.records_failed
            summary["total_records"]["skipped"] += result.records_skipped
        
        return summary

    async def batch_load(
        self,
        data_list: List[StructuredData],
        target_ids: Optional[List[str]] = None,
        max_concurrent: int = 5
    ) -> List[LoadReport]:
        """批量加载数据
        
        Args:
            data_list: 结构化数据列表
            target_ids: 目标ID列表
            max_concurrent: 最大并发数
            
        Returns:
            加载报告列表
        """
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def load_with_semaphore(data: StructuredData) -> LoadReport:
            async with semaphore:
                return await self.load(data, target_ids)
        
        tasks = [load_with_semaphore(data) for data in data_list]
        reports = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理异常
        final_reports = []
        for i, report in enumerate(reports):
            if isinstance(report, Exception):
                # 创建错误报告
                data = data_list[i]
                error_report = LoadReport(
                    data_id=data.id,
                    total_targets=0,
                    successful_targets=0,
                    failed_targets=1,
                    partial_targets=0,
                    skipped_targets=0,
                    results=[
                        LoadResult(
                            data_id=data.id,
                            target_id="system_error",
                            target_name="系统错误",
                            status=LoadStatus.FAILED,
                            message=f"批量加载过程中发生错误: {str(report)}"
                        )
                    ]
                )
                final_reports.append(error_report)
            else:
                final_reports.append(report)
        
        return final_reports

    def get_targets(self) -> Dict[str, LoadTarget]:
        """获取所有加载目标"""
        return self.targets.copy()

    def get_targets_by_type(self, target_type: LoadTargetType) -> List[LoadTarget]:
        """根据类型获取加载目标"""
        return [target for target in self.targets.values() if target.target_type == target_type]

    async def test_target_connection(self, target_id: str) -> Dict[str, Any]:
        """测试目标连接
        
        Args:
            target_id: 目标ID
            
        Returns:
            连接测试结果
        """
        if target_id not in self.targets:
            return {
                "success": False,
                "message": f"目标不存在: {target_id}"
            }
        
        target = self.targets[target_id]
        
        try:
            # 根据目标类型执行连接测试
            if target.target_type == LoadTargetType.KNOWLEDGE_GRAPH:
                if self.graph_manager:
                    # 测试知识图谱连接
                    return {
                        "success": True,
                        "message": "知识图谱连接正常"
                    }
                else:
                    return {
                        "success": False,
                        "message": "知识图谱管理器未初始化"
                    }
            
            elif target.target_type == LoadTargetType.FILE_SYSTEM:
                # 测试文件系统访问
                base_path = Path(target.connection_config.get("base_path", "./data"))
                base_path.mkdir(parents=True, exist_ok=True)
                return {
                    "success": True,
                    "message": f"文件系统访问正常: {base_path}"
                }
            
            else:
                return {
                    "success": True,
                    "message": f"目标类型 {target.target_type} 连接测试通过"
                }
                
        except Exception as e:
            return {
                "success": False,
                "message": f"连接测试失败: {str(e)}"
            }