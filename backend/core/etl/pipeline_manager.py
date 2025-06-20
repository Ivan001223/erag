"""ETL管道管理器

负责协调和管理整个ETL流程，包括数据结构化、验证、转换和加载的完整管道。
"""

import json
import uuid
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union, Tuple, Callable
from enum import Enum
from dataclasses import dataclass, field
from pathlib import Path

from pydantic import BaseModel, Field

from backend.utils.logger import get_logger
from backend.core.knowledge_graph.graph_manager import GraphManager
from .data_structurer import DataStructurer, StructuredData, DataType
from .data_validator import DataValidator, DataValidationReport
from .data_transformer import DataTransformer, TransformationReport
from .data_loader import DataLoader, LoadReport

logger = get_logger(__name__)


class PipelineStage(str, Enum):
    """管道阶段枚举"""
    STRUCTURE = "structure"  # 数据结构化
    VALIDATE = "validate"  # 数据验证
    TRANSFORM = "transform"  # 数据转换
    LOAD = "load"  # 数据加载


class PipelineStatus(str, Enum):
    """管道状态枚举"""
    PENDING = "pending"  # 等待执行
    RUNNING = "running"  # 正在执行
    SUCCESS = "success"  # 执行成功
    FAILED = "failed"  # 执行失败
    PARTIAL = "partial"  # 部分成功
    CANCELLED = "cancelled"  # 已取消
    PAUSED = "paused"  # 已暂停


class PipelineMode(str, Enum):
    """管道模式枚举"""
    SEQUENTIAL = "sequential"  # 顺序执行
    PARALLEL = "parallel"  # 并行执行
    CONDITIONAL = "conditional"  # 条件执行
    BATCH = "batch"  # 批处理


@dataclass
class PipelineConfig:
    """管道配置"""
    id: str
    name: str
    description: str = ""
    mode: PipelineMode = PipelineMode.SEQUENTIAL
    enabled_stages: List[PipelineStage] = field(default_factory=lambda: list(PipelineStage))
    
    # 阶段配置
    structure_config: Dict[str, Any] = field(default_factory=dict)
    validation_config: Dict[str, Any] = field(default_factory=dict)
    transformation_config: Dict[str, Any] = field(default_factory=dict)
    load_config: Dict[str, Any] = field(default_factory=dict)
    
    # 执行配置
    max_concurrent: int = 5
    timeout_seconds: int = 3600  # 1小时
    retry_attempts: int = 3
    retry_delay: int = 5  # 秒
    
    # 错误处理
    stop_on_error: bool = False
    error_threshold: float = 0.1  # 10%错误率阈值
    
    # 监控配置
    enable_monitoring: bool = True
    log_level: str = "INFO"
    
    # 元数据
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


class StageResult(BaseModel):
    """阶段执行结果"""
    stage: PipelineStage
    status: PipelineStatus
    message: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_ms: Optional[int] = None
    data_count: int = 0
    success_count: int = 0
    error_count: int = 0
    details: Optional[Dict[str, Any]] = None
    error_details: Optional[Dict[str, Any]] = None


class PipelineExecution(BaseModel):
    """管道执行记录"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    pipeline_id: str
    pipeline_name: str
    status: PipelineStatus
    mode: PipelineMode
    
    # 时间信息
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_ms: Optional[int] = None
    
    # 数据统计
    total_data_count: int = 0
    processed_data_count: int = 0
    successful_data_count: int = 0
    failed_data_count: int = 0
    
    # 阶段结果
    stage_results: List[StageResult] = Field(default_factory=list)
    
    # 详细报告
    validation_reports: List[DataValidationReport] = Field(default_factory=list)
    transformation_reports: List[TransformationReport] = Field(default_factory=list)
    load_reports: List[LoadReport] = Field(default_factory=list)
    
    # 错误信息
    error_message: Optional[str] = None
    error_details: Optional[Dict[str, Any]] = None
    
    # 元数据
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)


class PipelineManager:
    """ETL管道管理器
    
    协调和管理整个ETL流程的执行，提供灵活的管道配置和监控功能。
    """

    def __init__(self, graph_manager: Optional[GraphManager] = None):
        """初始化管道管理器
        
        Args:
            graph_manager: 知识图谱管理器
        """
        self.graph_manager = graph_manager
        
        # 初始化组件
        self.structurer = DataStructurer()
        self.validator = DataValidator()
        self.transformer = DataTransformer()
        self.loader = DataLoader(graph_manager)
        
        # 管道配置
        self.pipelines: Dict[str, PipelineConfig] = {}
        self.executions: Dict[str, PipelineExecution] = {}
        self.running_executions: Dict[str, asyncio.Task] = {}
        
        # 初始化默认管道
        self._initialize_default_pipelines()
        
        logger.info("ETL管道管理器初始化完成")

    def _initialize_default_pipelines(self) -> None:
        """初始化默认管道配置"""
        # 完整ETL管道
        self.add_pipeline(PipelineConfig(
            id="complete_etl",
            name="完整ETL管道",
            description="包含所有阶段的完整ETL处理管道",
            mode=PipelineMode.SEQUENTIAL,
            enabled_stages=list(PipelineStage),
            structure_config={
                "enable_entity_extraction": True,
                "enable_relationship_extraction": True,
                "chunk_size": 1000,
                "overlap_size": 100
            },
            validation_config={
                "validation_level": "medium",
                "enable_quality_check": True,
                "min_quality_score": 0.6
            },
            transformation_config={
                "rule_chain": "complete",
                "enable_enrichment": True
            },
            load_config={
                "target_ids": ["default_knowledge_graph", "file_backup"]
            },
            tags=["default", "complete"]
        ))
        
        # 快速处理管道
        self.add_pipeline(PipelineConfig(
            id="quick_process",
            name="快速处理管道",
            description="用于快速处理的简化管道",
            mode=PipelineMode.SEQUENTIAL,
            enabled_stages=[PipelineStage.STRUCTURE, PipelineStage.LOAD],
            structure_config={
                "enable_entity_extraction": False,
                "enable_relationship_extraction": False,
                "chunk_size": 2000
            },
            load_config={
                "target_ids": ["memory_cache"]
            },
            max_concurrent=10,
            tags=["quick", "simple"]
        ))
        
        # 批处理管道
        self.add_pipeline(PipelineConfig(
            id="batch_process",
            name="批处理管道",
            description="用于大批量数据处理的管道",
            mode=PipelineMode.BATCH,
            enabled_stages=list(PipelineStage),
            max_concurrent=20,
            timeout_seconds=7200,  # 2小时
            error_threshold=0.05,  # 5%错误率
            tags=["batch", "bulk"]
        ))

    def add_pipeline(self, config: PipelineConfig) -> None:
        """添加管道配置
        
        Args:
            config: 管道配置
        """
        config.updated_at = datetime.now()
        self.pipelines[config.id] = config
        logger.debug(f"添加管道配置: {config.name}")

    def remove_pipeline(self, pipeline_id: str) -> None:
        """移除管道配置
        
        Args:
            pipeline_id: 管道ID
        """
        if pipeline_id in self.pipelines:
            del self.pipelines[pipeline_id]
            logger.debug(f"移除管道配置: {pipeline_id}")

    async def execute_pipeline(
        self,
        pipeline_id: str,
        input_data: List[Dict[str, Any]],
        execution_metadata: Optional[Dict[str, Any]] = None
    ) -> PipelineExecution:
        """执行ETL管道
        
        Args:
            pipeline_id: 管道ID
            input_data: 输入数据列表
            execution_metadata: 执行元数据
            
        Returns:
            管道执行记录
        """
        if pipeline_id not in self.pipelines:
            raise ValueError(f"管道不存在: {pipeline_id}")
        
        config = self.pipelines[pipeline_id]
        start_time = datetime.now()
        
        # 创建执行记录
        execution = PipelineExecution(
            pipeline_id=pipeline_id,
            pipeline_name=config.name,
            status=PipelineStatus.RUNNING,
            mode=config.mode,
            start_time=start_time,
            total_data_count=len(input_data),
            metadata=execution_metadata or {}
        )
        
        self.executions[execution.id] = execution
        
        try:
            logger.info(
                f"开始执行管道: {config.name}, 数据量: {len(input_data)}, "
                f"模式: {config.mode}, 执行ID: {execution.id}"
            )
            
            # 根据模式执行管道
            if config.mode == PipelineMode.SEQUENTIAL:
                await self._execute_sequential(execution, config, input_data)
            elif config.mode == PipelineMode.PARALLEL:
                await self._execute_parallel(execution, config, input_data)
            elif config.mode == PipelineMode.BATCH:
                await self._execute_batch(execution, config, input_data)
            else:
                raise ValueError(f"不支持的管道模式: {config.mode}")
            
            # 计算执行时间
            execution.end_time = datetime.now()
            execution.duration_ms = int((execution.end_time - execution.start_time).total_seconds() * 1000)
            
            # 确定最终状态
            if execution.failed_data_count == 0:
                execution.status = PipelineStatus.SUCCESS
            elif execution.successful_data_count > 0:
                execution.status = PipelineStatus.PARTIAL
            else:
                execution.status = PipelineStatus.FAILED
            
            logger.info(
                f"管道执行完成: {config.name}, 状态: {execution.status}, "
                f"成功: {execution.successful_data_count}, 失败: {execution.failed_data_count}, "
                f"耗时: {execution.duration_ms}ms"
            )
            
            return execution
            
        except Exception as e:
            execution.status = PipelineStatus.FAILED
            execution.error_message = str(e)
            execution.error_details = {"exception": str(e)}
            execution.end_time = datetime.now()
            execution.duration_ms = int((execution.end_time - execution.start_time).total_seconds() * 1000)
            
            logger.error(f"管道执行失败: {config.name}, 错误: {str(e)}")
            raise
        
        finally:
            # 清理运行中的执行记录
            if execution.id in self.running_executions:
                del self.running_executions[execution.id]

    async def _execute_sequential(
        self,
        execution: PipelineExecution,
        config: PipelineConfig,
        input_data: List[Dict[str, Any]]
    ) -> None:
        """顺序执行管道"""
        current_data = input_data.copy()
        
        for stage in config.enabled_stages:
            stage_start = datetime.now()
            
            try:
                logger.debug(f"执行阶段: {stage}, 数据量: {len(current_data)}")
                
                if stage == PipelineStage.STRUCTURE:
                    current_data, stage_result = await self._execute_structure_stage(
                        current_data, config.structure_config
                    )
                elif stage == PipelineStage.VALIDATE:
                    current_data, stage_result = await self._execute_validation_stage(
                        current_data, config.validation_config, execution
                    )
                elif stage == PipelineStage.TRANSFORM:
                    current_data, stage_result = await self._execute_transformation_stage(
                        current_data, config.transformation_config, execution
                    )
                elif stage == PipelineStage.LOAD:
                    stage_result = await self._execute_load_stage(
                        current_data, config.load_config, execution
                    )
                
                # 记录阶段结果
                stage_end = datetime.now()
                stage_result.end_time = stage_end
                stage_result.duration_ms = int((stage_end - stage_start).total_seconds() * 1000)
                execution.stage_results.append(stage_result)
                
                # 检查错误阈值
                if config.stop_on_error and stage_result.status == PipelineStatus.FAILED:
                    raise Exception(f"阶段 {stage} 执行失败: {stage_result.message}")
                
                error_rate = stage_result.error_count / max(stage_result.data_count, 1)
                if error_rate > config.error_threshold:
                    raise Exception(
                        f"阶段 {stage} 错误率过高: {error_rate:.2%} > {config.error_threshold:.2%}"
                    )
                
            except Exception as e:
                stage_result = StageResult(
                    stage=stage,
                    status=PipelineStatus.FAILED,
                    message=f"阶段执行失败: {str(e)}",
                    start_time=stage_start,
                    end_time=datetime.now(),
                    error_details={"error": str(e)}
                )
                execution.stage_results.append(stage_result)
                raise

    async def _execute_parallel(
        self,
        execution: PipelineExecution,
        config: PipelineConfig,
        input_data: List[Dict[str, Any]]
    ) -> None:
        """并行执行管道"""
        # 并行处理每个数据项
        semaphore = asyncio.Semaphore(config.max_concurrent)
        
        async def process_single_item(item: Dict[str, Any]) -> Tuple[bool, Any]:
            async with semaphore:
                try:
                    current_item = [item]  # 包装为列表
                    
                    # 顺序执行各个阶段
                    for stage in config.enabled_stages:
                        if stage == PipelineStage.STRUCTURE:
                            current_item, _ = await self._execute_structure_stage(
                                current_item, config.structure_config
                            )
                        elif stage == PipelineStage.VALIDATE:
                            current_item, _ = await self._execute_validation_stage(
                                current_item, config.validation_config, execution
                            )
                        elif stage == PipelineStage.TRANSFORM:
                            current_item, _ = await self._execute_transformation_stage(
                                current_item, config.transformation_config, execution
                            )
                        elif stage == PipelineStage.LOAD:
                            await self._execute_load_stage(
                                current_item, config.load_config, execution
                            )
                    
                    return True, current_item[0] if current_item else None
                    
                except Exception as e:
                    logger.error(f"并行处理项失败: {str(e)}")
                    return False, str(e)
        
        # 执行并行任务
        tasks = [process_single_item(item) for item in input_data]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 统计结果
        successful_count = 0
        failed_count = 0
        
        for result in results:
            if isinstance(result, Exception):
                failed_count += 1
            else:
                success, _ = result
                if success:
                    successful_count += 1
                else:
                    failed_count += 1
        
        execution.processed_data_count = len(input_data)
        execution.successful_data_count = successful_count
        execution.failed_data_count = failed_count

    async def _execute_batch(
        self,
        execution: PipelineExecution,
        config: PipelineConfig,
        input_data: List[Dict[str, Any]]
    ) -> None:
        """批处理执行管道"""
        batch_size = config.max_concurrent
        total_batches = (len(input_data) + batch_size - 1) // batch_size
        
        logger.info(f"批处理执行: 总数据量 {len(input_data)}, 批次大小 {batch_size}, 总批次 {total_batches}")
        
        for batch_idx in range(total_batches):
            start_idx = batch_idx * batch_size
            end_idx = min(start_idx + batch_size, len(input_data))
            batch_data = input_data[start_idx:end_idx]
            
            logger.debug(f"处理批次 {batch_idx + 1}/{total_batches}, 数据量: {len(batch_data)}")
            
            # 顺序执行当前批次
            await self._execute_sequential(execution, config, batch_data)
            
            # 更新进度
            execution.processed_data_count = end_idx

    async def _execute_structure_stage(
        self,
        input_data: List[Dict[str, Any]],
        stage_config: Dict[str, Any]
    ) -> Tuple[List[StructuredData], StageResult]:
        """执行数据结构化阶段"""
        stage_start = datetime.now()
        structured_data = []
        success_count = 0
        error_count = 0
        
        try:
            for item in input_data:
                try:
                    # 确定数据类型
                    data_type = DataType.TEXT  # 默认类型，实际应根据数据内容判断
                    if "type" in item:
                        data_type = DataType(item["type"])
                    
                    # 结构化数据
                    result = await self.structurer.structure_data(
                        content=item.get("content", ""),
                        data_type=data_type,
                        source_id=item.get("source_id"),
                        metadata=item.get("metadata", {}),
                        **stage_config
                    )
                    
                    structured_data.append(result)
                    success_count += 1
                    
                except Exception as e:
                    logger.error(f"数据结构化失败: {str(e)}")
                    error_count += 1
            
            status = PipelineStatus.SUCCESS if error_count == 0 else (
                PipelineStatus.PARTIAL if success_count > 0 else PipelineStatus.FAILED
            )
            
            return structured_data, StageResult(
                stage=PipelineStage.STRUCTURE,
                status=status,
                message=f"结构化完成，成功: {success_count}, 失败: {error_count}",
                start_time=stage_start,
                data_count=len(input_data),
                success_count=success_count,
                error_count=error_count
            )
            
        except Exception as e:
            return [], StageResult(
                stage=PipelineStage.STRUCTURE,
                status=PipelineStatus.FAILED,
                message=f"结构化阶段失败: {str(e)}",
                start_time=stage_start,
                error_details={"error": str(e)}
            )

    async def _execute_validation_stage(
        self,
        structured_data: List[StructuredData],
        stage_config: Dict[str, Any],
        execution: PipelineExecution
    ) -> Tuple[List[StructuredData], StageResult]:
        """执行数据验证阶段"""
        stage_start = datetime.now()
        validated_data = []
        success_count = 0
        error_count = 0
        
        try:
            validation_level = stage_config.get("validation_level", "medium")
            min_quality_score = stage_config.get("min_quality_score", 0.5)
            
            for data in structured_data:
                try:
                    # 验证数据
                    report = await self.validator.validate_data(data, validation_level)
                    execution.validation_reports.append(report)
                    
                    # 检查验证结果
                    if report.is_valid and data.quality_score >= min_quality_score:
                        validated_data.append(data)
                        success_count += 1
                    else:
                        logger.warning(f"数据验证失败: {data.id}, 质量分数: {data.quality_score}")
                        error_count += 1
                        
                except Exception as e:
                    logger.error(f"数据验证异常: {str(e)}")
                    error_count += 1
            
            status = PipelineStatus.SUCCESS if error_count == 0 else (
                PipelineStatus.PARTIAL if success_count > 0 else PipelineStatus.FAILED
            )
            
            return validated_data, StageResult(
                stage=PipelineStage.VALIDATE,
                status=status,
                message=f"验证完成，通过: {success_count}, 失败: {error_count}",
                start_time=stage_start,
                data_count=len(structured_data),
                success_count=success_count,
                error_count=error_count
            )
            
        except Exception as e:
            return [], StageResult(
                stage=PipelineStage.VALIDATE,
                status=PipelineStatus.FAILED,
                message=f"验证阶段失败: {str(e)}",
                start_time=stage_start,
                error_details={"error": str(e)}
            )

    async def _execute_transformation_stage(
        self,
        validated_data: List[StructuredData],
        stage_config: Dict[str, Any],
        execution: PipelineExecution
    ) -> Tuple[List[StructuredData], StageResult]:
        """执行数据转换阶段"""
        stage_start = datetime.now()
        transformed_data = []
        success_count = 0
        error_count = 0
        
        try:
            rule_chain = stage_config.get("rule_chain", "text_processing")
            
            for data in validated_data:
                try:
                    # 转换数据
                    result, report = await self.transformer.transform(data, rule_chain=rule_chain)
                    execution.transformation_reports.append(report)
                    
                    transformed_data.append(result)
                    success_count += 1
                    
                except Exception as e:
                    logger.error(f"数据转换失败: {str(e)}")
                    error_count += 1
            
            status = PipelineStatus.SUCCESS if error_count == 0 else (
                PipelineStatus.PARTIAL if success_count > 0 else PipelineStatus.FAILED
            )
            
            return transformed_data, StageResult(
                stage=PipelineStage.TRANSFORM,
                status=status,
                message=f"转换完成，成功: {success_count}, 失败: {error_count}",
                start_time=stage_start,
                data_count=len(validated_data),
                success_count=success_count,
                error_count=error_count
            )
            
        except Exception as e:
            return [], StageResult(
                stage=PipelineStage.TRANSFORM,
                status=PipelineStatus.FAILED,
                message=f"转换阶段失败: {str(e)}",
                start_time=stage_start,
                error_details={"error": str(e)}
            )

    async def _execute_load_stage(
        self,
        transformed_data: List[StructuredData],
        stage_config: Dict[str, Any],
        execution: PipelineExecution
    ) -> StageResult:
        """执行数据加载阶段"""
        stage_start = datetime.now()
        success_count = 0
        error_count = 0
        
        try:
            target_ids = stage_config.get("target_ids")
            
            for data in transformed_data:
                try:
                    # 加载数据
                    report = await self.loader.load(data, target_ids=target_ids)
                    execution.load_reports.append(report)
                    
                    if report.successful_targets > 0:
                        success_count += 1
                    else:
                        error_count += 1
                        
                except Exception as e:
                    logger.error(f"数据加载失败: {str(e)}")
                    error_count += 1
            
            status = PipelineStatus.SUCCESS if error_count == 0 else (
                PipelineStatus.PARTIAL if success_count > 0 else PipelineStatus.FAILED
            )
            
            # 更新执行统计
            execution.processed_data_count += len(transformed_data)
            execution.successful_data_count += success_count
            execution.failed_data_count += error_count
            
            return StageResult(
                stage=PipelineStage.LOAD,
                status=status,
                message=f"加载完成，成功: {success_count}, 失败: {error_count}",
                start_time=stage_start,
                data_count=len(transformed_data),
                success_count=success_count,
                error_count=error_count
            )
            
        except Exception as e:
            return StageResult(
                stage=PipelineStage.LOAD,
                status=PipelineStatus.FAILED,
                message=f"加载阶段失败: {str(e)}",
                start_time=stage_start,
                error_details={"error": str(e)}
            )

    async def execute_pipeline_async(
        self,
        pipeline_id: str,
        input_data: List[Dict[str, Any]],
        execution_metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """异步执行ETL管道
        
        Args:
            pipeline_id: 管道ID
            input_data: 输入数据列表
            execution_metadata: 执行元数据
            
        Returns:
            执行ID
        """
        execution_id = str(uuid.uuid4())
        
        # 创建异步任务
        task = asyncio.create_task(
            self.execute_pipeline(pipeline_id, input_data, execution_metadata)
        )
        
        self.running_executions[execution_id] = task
        
        logger.info(f"异步执行管道: {pipeline_id}, 执行ID: {execution_id}")
        
        return execution_id

    async def cancel_execution(self, execution_id: str) -> bool:
        """取消管道执行
        
        Args:
            execution_id: 执行ID
            
        Returns:
            是否成功取消
        """
        if execution_id in self.running_executions:
            task = self.running_executions[execution_id]
            task.cancel()
            
            # 更新执行状态
            if execution_id in self.executions:
                self.executions[execution_id].status = PipelineStatus.CANCELLED
                self.executions[execution_id].end_time = datetime.now()
            
            del self.running_executions[execution_id]
            
            logger.info(f"取消管道执行: {execution_id}")
            return True
        
        return False

    def get_execution_status(self, execution_id: str) -> Optional[PipelineExecution]:
        """获取执行状态
        
        Args:
            execution_id: 执行ID
            
        Returns:
            执行记录
        """
        return self.executions.get(execution_id)

    def get_pipelines(self) -> Dict[str, PipelineConfig]:
        """获取所有管道配置"""
        return self.pipelines.copy()

    def get_executions(
        self,
        pipeline_id: Optional[str] = None,
        status: Optional[PipelineStatus] = None,
        limit: int = 100
    ) -> List[PipelineExecution]:
        """获取执行记录
        
        Args:
            pipeline_id: 管道ID过滤
            status: 状态过滤
            limit: 返回数量限制
            
        Returns:
            执行记录列表
        """
        executions = list(self.executions.values())
        
        # 过滤
        if pipeline_id:
            executions = [e for e in executions if e.pipeline_id == pipeline_id]
        
        if status:
            executions = [e for e in executions if e.status == status]
        
        # 排序并限制数量
        executions.sort(key=lambda x: x.created_at, reverse=True)
        
        return executions[:limit]

    def get_pipeline_statistics(self, pipeline_id: str) -> Dict[str, Any]:
        """获取管道统计信息
        
        Args:
            pipeline_id: 管道ID
            
        Returns:
            统计信息
        """
        executions = self.get_executions(pipeline_id=pipeline_id)
        
        if not executions:
            return {"total_executions": 0}
        
        total_executions = len(executions)
        successful_executions = sum(1 for e in executions if e.status == PipelineStatus.SUCCESS)
        failed_executions = sum(1 for e in executions if e.status == PipelineStatus.FAILED)
        
        # 计算平均执行时间
        durations = [e.duration_ms for e in executions if e.duration_ms is not None]
        avg_duration = sum(durations) / len(durations) if durations else 0
        
        # 计算数据处理统计
        total_data_processed = sum(e.processed_data_count for e in executions)
        total_data_successful = sum(e.successful_data_count for e in executions)
        
        return {
            "total_executions": total_executions,
            "successful_executions": successful_executions,
            "failed_executions": failed_executions,
            "success_rate": successful_executions / total_executions if total_executions > 0 else 0,
            "avg_duration_ms": avg_duration,
            "total_data_processed": total_data_processed,
            "total_data_successful": total_data_successful,
            "data_success_rate": total_data_successful / total_data_processed if total_data_processed > 0 else 0,
            "last_execution": executions[0].created_at.isoformat() if executions else None
        }

    async def cleanup_old_executions(self, days: int = 30) -> int:
        """清理旧的执行记录
        
        Args:
            days: 保留天数
            
        Returns:
            清理的记录数
        """
        cutoff_date = datetime.now() - timedelta(days=days)
        
        old_execution_ids = [
            execution_id for execution_id, execution in self.executions.items()
            if execution.created_at < cutoff_date
        ]
        
        for execution_id in old_execution_ids:
            del self.executions[execution_id]
        
        logger.info(f"清理了 {len(old_execution_ids)} 条旧执行记录")
        
        return len(old_execution_ids)