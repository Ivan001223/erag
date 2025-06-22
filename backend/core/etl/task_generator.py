"""ETL任务生成器

负责根据数据源和处理需求自动生成ETL任务配置和执行计划。
"""

import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union, Tuple
from enum import Enum
from dataclasses import dataclass, field
from pathlib import Path

from pydantic import BaseModel, Field

from backend.utils.logger import get_logger
from backend.models.task import (
    TaskPriority, TaskStatus, TaskDependency
)
from .pipeline_manager import PipelineConfig, PipelineMode, PipelineStage

# 为了兼容测试，添加别名
ETLJobStatus = TaskStatus

logger = get_logger(__name__)


class TaskType(str, Enum):
    """ETL任务类型枚举"""
    DOCUMENT_PROCESSING = "document_processing"  # 文档处理
    DATA_INGESTION = "data_ingestion"  # 数据摄取
    KNOWLEDGE_EXTRACTION = "knowledge_extraction"  # 知识提取
    GRAPH_BUILDING = "graph_building"  # 图构建
    VECTOR_INDEXING = "vector_indexing"  # 向量索引
    DATA_VALIDATION = "data_validation"  # 数据验证
    DATA_TRANSFORMATION = "data_transformation"  # 数据转换
    BATCH_PROCESSING = "batch_processing"  # 批处理
    REAL_TIME_PROCESSING = "real_time_processing"  # 实时处理
    INCREMENTAL_UPDATE = "incremental_update"  # 增量更新


class ScheduleType(str, Enum):
    """调度类型枚举"""
    IMMEDIATE = "immediate"  # 立即执行
    SCHEDULED = "scheduled"  # 定时执行
    RECURRING = "recurring"  # 周期执行
    TRIGGERED = "triggered"  # 触发执行
    CONDITIONAL = "conditional"  # 条件执行


@dataclass
class DataSourceInfo:
    """数据源信息"""
    id: str
    name: str
    type: str  # file, database, api, stream等
    location: str  # 文件路径、数据库连接字符串、API端点等
    format: str  # json, csv, pdf, docx等
    size_bytes: Optional[int] = None
    last_modified: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    credentials: Optional[Dict[str, str]] = None
    
    # 处理配置
    chunk_size: Optional[int] = None
    batch_size: Optional[int] = None
    parallel_workers: Optional[int] = None


@dataclass
class ProcessingRequirements:
    """处理需求"""
    task_type: TaskType
    priority: TaskPriority = TaskPriority.NORMAL
    
    # 质量要求
    quality_threshold: float = 0.7
    accuracy_requirement: float = 0.8
    completeness_requirement: float = 0.9
    
    # 性能要求
    max_processing_time: Optional[int] = None  # 秒
    max_memory_usage: Optional[int] = None  # MB
    max_cpu_usage: Optional[float] = None  # 百分比
    
    # 输出要求
    output_formats: List[str] = field(default_factory=list)
    output_targets: List[str] = field(default_factory=list)
    
    # 特殊要求
    enable_entity_extraction: bool = True
    enable_relationship_extraction: bool = True
    enable_vector_embedding: bool = True
    enable_knowledge_graph: bool = True
    
    # 验证要求
    validation_rules: List[str] = field(default_factory=list)
    custom_validators: List[str] = field(default_factory=list)
    
    # 转换要求
    transformation_rules: List[str] = field(default_factory=list)
    custom_transformers: List[str] = field(default_factory=list)


# 为了向后兼容，提供单数形式的别名
ProcessingRequirement = ProcessingRequirements


@dataclass
class ScheduleConfig:
    """调度配置"""
    type: ScheduleType
    
    # 立即执行
    execute_immediately: bool = False
    
    # 定时执行
    scheduled_time: Optional[datetime] = None
    
    # 周期执行
    cron_expression: Optional[str] = None
    interval_seconds: Optional[int] = None
    
    # 触发执行
    trigger_events: List[str] = field(default_factory=list)
    trigger_conditions: List[str] = field(default_factory=list)
    
    # 条件执行
    condition_expression: Optional[str] = None
    dependency_tasks: List[str] = field(default_factory=list)
    
    # 重试配置
    max_retries: int = 3
    retry_delay: int = 60  # 秒
    exponential_backoff: bool = True
    
    # 超时配置
    timeout_seconds: int = 3600  # 1小时
    
    # 并发控制
    max_concurrent_instances: int = 1
    allow_overlap: bool = False


class ETLTask(BaseModel):
    """ETL任务"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str = ""
    
    # 任务分类
    task_type: TaskType
    priority: TaskPriority
    
    # 数据源
    data_sources: List[DataSourceInfo]
    
    # 处理需求
    requirements: ProcessingRequirements
    
    # 调度配置
    schedule: ScheduleConfig
    
    # 管道配置
    pipeline_id: str
    pipeline_config: Optional[Dict[str, Any]] = None
    
    # 执行配置
    execution_config: Dict[str, Any] = Field(default_factory=dict)
    
    # 状态信息
    status: ETLJobStatus = ETLJobStatus.PENDING
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    created_by: Optional[str] = None
    
    # 依赖关系
    dependencies: List[str] = Field(default_factory=list)
    dependents: List[str] = Field(default_factory=list)
    
    # 标签和元数据
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    # 估算信息
    estimated_duration: Optional[int] = None  # 秒
    estimated_cost: Optional[float] = None
    estimated_resources: Optional[Dict[str, Any]] = None


@dataclass
class TaskExecution:
    """任务执行信息"""
    task_id: str
    execution_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    status: TaskStatus = TaskStatus.PENDING
    progress: float = 0.0
    logs: List[str] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None


class TaskGenerator:
    """ETL任务生成器
    
    根据数据源和处理需求自动生成优化的ETL任务配置。
    """

    def __init__(self):
        """初始化任务生成器"""
        # 任务模板
        self.task_templates: Dict[TaskType, Dict[str, Any]] = {}
        
        # 管道模板
        self.pipeline_templates: Dict[str, PipelineConfig] = {}
        
        # 生成的任务
        self.generated_tasks: Dict[str, ETLTask] = {}
        
        # 初始化默认模板
        self._initialize_templates()
        
        logger.info("ETL任务生成器初始化完成")

    def _initialize_templates(self) -> None:
        """初始化默认任务模板"""
        # 文档处理模板
        self.task_templates[TaskType.DOCUMENT_PROCESSING] = {
            "pipeline_stages": [PipelineStage.STRUCTURE, PipelineStage.VALIDATE, PipelineStage.TRANSFORM, PipelineStage.LOAD],
            "default_priority": TaskPriority.NORMAL,
            "estimated_duration_per_mb": 30,  # 秒/MB
            "resource_requirements": {
                "cpu_cores": 2,
                "memory_mb": 1024,
                "disk_mb": 500
            },
            "quality_thresholds": {
                "min_quality_score": 0.7,
                "min_confidence": 0.6
            }
        }
        
        # 数据摄取模板
        self.task_templates[TaskType.DATA_INGESTION] = {
            "pipeline_stages": [PipelineStage.STRUCTURE, PipelineStage.LOAD],
            "default_priority": TaskPriority.HIGH,
            "estimated_duration_per_mb": 10,
            "resource_requirements": {
                "cpu_cores": 1,
                "memory_mb": 512,
                "disk_mb": 200
            }
        }
        
        # 知识提取模板
        self.task_templates[TaskType.KNOWLEDGE_EXTRACTION] = {
            "pipeline_stages": [PipelineStage.STRUCTURE, PipelineStage.VALIDATE, PipelineStage.TRANSFORM],
            "default_priority": TaskPriority.HIGH,
            "estimated_duration_per_mb": 60,
            "resource_requirements": {
                "cpu_cores": 4,
                "memory_mb": 2048,
                "disk_mb": 1000
            },
            "quality_thresholds": {
                "min_quality_score": 0.8,
                "min_confidence": 0.7
            }
        }
        
        # 批处理模板
        self.task_templates[TaskType.BATCH_PROCESSING] = {
            "pipeline_stages": list(PipelineStage),
            "default_priority": TaskPriority.LOW,
            "estimated_duration_per_mb": 20,
            "resource_requirements": {
                "cpu_cores": 8,
                "memory_mb": 4096,
                "disk_mb": 2000
            },
            "execution_config": {
                "mode": PipelineMode.BATCH,
                "max_concurrent": 20,
                "batch_size": 100
            }
        }
        
        # 实时处理模板
        self.task_templates[TaskType.REAL_TIME_PROCESSING] = {
            "pipeline_stages": [PipelineStage.STRUCTURE, PipelineStage.LOAD],
            "default_priority": TaskPriority.URGENT,
            "estimated_duration_per_mb": 5,
            "resource_requirements": {
                "cpu_cores": 2,
                "memory_mb": 1024,
                "disk_mb": 100
            },
            "execution_config": {
                "mode": PipelineMode.PARALLEL,
                "max_concurrent": 10,
                "timeout_seconds": 300
            }
        }

    def generate_task(
        self,
        name: str,
        data_sources: List[DataSourceInfo],
        requirements: ProcessingRequirements,
        schedule: Optional[ScheduleConfig] = None,
        custom_config: Optional[Dict[str, Any]] = None
    ) -> ETLTask:
        """生成ETL任务
        
        Args:
            name: 任务名称
            data_sources: 数据源列表
            requirements: 处理需求
            schedule: 调度配置
            custom_config: 自定义配置
            
        Returns:
            生成的ETL任务
        """
        logger.info(f"开始生成ETL任务: {name}")
        
        # 获取任务模板
        template = self.task_templates.get(requirements.task_type, {})
        
        # 生成管道配置
        pipeline_config = self._generate_pipeline_config(
            requirements.task_type,
            data_sources,
            requirements,
            template
        )
        
        # 生成调度配置
        if schedule is None:
            schedule = self._generate_default_schedule(requirements.task_type)
        
        # 估算资源和时间
        estimates = self._estimate_task_resources(data_sources, requirements, template)
        
        # 创建任务
        task = ETLTask(
            name=name,
            description=f"自动生成的{requirements.task_type.value}任务",
            task_type=requirements.task_type,
            priority=requirements.priority,
            data_sources=data_sources,
            requirements=requirements,
            schedule=schedule,
            pipeline_id=pipeline_config.id,
            pipeline_config=pipeline_config.dict() if hasattr(pipeline_config, 'dict') else pipeline_config.__dict__,
            execution_config=template.get("execution_config", {}),
            estimated_duration=estimates.get("duration"),
            estimated_cost=estimates.get("cost"),
            estimated_resources=estimates.get("resources"),
            tags=self._generate_tags(requirements.task_type, data_sources),
            metadata={
                "generated_at": datetime.now().isoformat(),
                "template_used": requirements.task_type.value,
                "data_source_count": len(data_sources),
                "custom_config": custom_config or {}
            }
        )
        
        # 应用自定义配置
        if custom_config:
            self._apply_custom_config(task, custom_config)
        
        # 保存任务
        self.generated_tasks[task.id] = task
        
        logger.info(f"ETL任务生成完成: {task.id}, 估算时长: {task.estimated_duration}秒")
        
        return task

    def _generate_pipeline_config(
        self,
        task_type: TaskType,
        data_sources: List[DataSourceInfo],
        requirements: ProcessingRequirements,
        template: Dict[str, Any]
    ) -> PipelineConfig:
        """生成管道配置"""
        pipeline_id = f"pipeline_{task_type.value}_{uuid.uuid4().hex[:8]}"
        
        # 确定启用的阶段
        enabled_stages = template.get("pipeline_stages", list(PipelineStage))
        
        # 生成阶段配置
        structure_config = {
            "enable_entity_extraction": requirements.enable_entity_extraction,
            "enable_relationship_extraction": requirements.enable_relationship_extraction,
            "chunk_size": self._calculate_chunk_size(data_sources),
            "overlap_size": 100,
            "quality_threshold": requirements.quality_threshold
        }
        
        validation_config = {
            "validation_level": "strict" if requirements.priority in [TaskPriority.URGENT, TaskPriority.CRITICAL] else "medium",
            "min_quality_score": requirements.quality_threshold,
            "min_accuracy": requirements.accuracy_requirement,
            "min_completeness": requirements.completeness_requirement,
            "custom_rules": requirements.validation_rules
        }
        
        transformation_config = {
            "rule_chain": "complete" if task_type == TaskType.KNOWLEDGE_EXTRACTION else "basic",
            "enable_enrichment": requirements.enable_knowledge_graph,
            "custom_rules": requirements.transformation_rules,
            "quality_threshold": requirements.quality_threshold
        }
        
        load_config = {
            "target_ids": requirements.output_targets or ["default_knowledge_graph"],
            "output_formats": requirements.output_formats or ["json"],
            "enable_vector_storage": requirements.enable_vector_embedding,
            "enable_graph_storage": requirements.enable_knowledge_graph
        }
        
        # 确定执行模式
        mode = PipelineMode.SEQUENTIAL
        if task_type == TaskType.BATCH_PROCESSING:
            mode = PipelineMode.BATCH
        elif task_type == TaskType.REAL_TIME_PROCESSING:
            mode = PipelineMode.PARALLEL
        
        # 计算并发数
        max_concurrent = self._calculate_max_concurrent(data_sources, requirements)
        
        return PipelineConfig(
            id=pipeline_id,
            name=f"Pipeline for {task_type.value}",
            description=f"自动生成的{task_type.value}管道",
            mode=mode,
            enabled_stages=enabled_stages,
            structure_config=structure_config,
            validation_config=validation_config,
            transformation_config=transformation_config,
            load_config=load_config,
            max_concurrent=max_concurrent,
            timeout_seconds=requirements.max_processing_time or 3600,
            retry_attempts=3,
            stop_on_error=requirements.priority in [TaskPriority.URGENT, TaskPriority.CRITICAL],
            error_threshold=0.05 if requirements.priority == TaskPriority.CRITICAL else 0.1,
            tags=[task_type.value, "auto_generated"]
        )

    def _generate_default_schedule(self, task_type: TaskType) -> ScheduleConfig:
        """生成默认调度配置"""
        if task_type == TaskType.REAL_TIME_PROCESSING:
            return ScheduleConfig(
                type=ScheduleType.IMMEDIATE,
                execute_immediately=True,
                max_retries=1,
                timeout_seconds=300
            )
        elif task_type == TaskType.BATCH_PROCESSING:
            return ScheduleConfig(
                type=ScheduleType.SCHEDULED,
                scheduled_time=datetime.now() + timedelta(minutes=5),
                max_retries=3,
                timeout_seconds=7200
            )
        else:
            return ScheduleConfig(
                type=ScheduleType.IMMEDIATE,
                execute_immediately=True,
                max_retries=3,
                timeout_seconds=3600
            )

    def _estimate_task_resources(
        self,
        data_sources: List[DataSourceInfo],
        requirements: ProcessingRequirements,
        template: Dict[str, Any]
    ) -> Dict[str, Any]:
        """估算任务资源需求"""
        # 计算总数据大小
        total_size_mb = sum(
            (source.size_bytes or 1024 * 1024) / (1024 * 1024)
            for source in data_sources
        )
        
        # 估算处理时间
        duration_per_mb = template.get("estimated_duration_per_mb", 30)
        base_duration = total_size_mb * duration_per_mb
        
        # 根据复杂度调整
        complexity_factor = 1.0
        if requirements.enable_entity_extraction:
            complexity_factor += 0.5
        if requirements.enable_relationship_extraction:
            complexity_factor += 0.3
        if requirements.enable_vector_embedding:
            complexity_factor += 0.2
        
        estimated_duration = int(base_duration * complexity_factor)
        
        # 估算资源需求
        base_resources = template.get("resource_requirements", {})
        estimated_resources = {
            "cpu_cores": base_resources.get("cpu_cores", 2),
            "memory_mb": int(base_resources.get("memory_mb", 1024) * complexity_factor),
            "disk_mb": int(base_resources.get("disk_mb", 500) + total_size_mb * 2),
            "network_mb": int(total_size_mb * 0.1)  # 网络传输
        }
        
        # 估算成本（简化模型）
        estimated_cost = (
            estimated_duration / 3600 * 0.1 +  # 计算成本
            total_size_mb / 1024 * 0.01  # 存储成本
        )
        
        return {
            "duration": estimated_duration,
            "resources": estimated_resources,
            "cost": estimated_cost
        }

    def _calculate_chunk_size(self, data_sources: List[DataSourceInfo]) -> int:
        """计算合适的分块大小"""
        # 根据数据源大小和类型确定分块大小
        total_size = sum(source.size_bytes or 0 for source in data_sources)
        
        if total_size < 1024 * 1024:  # < 1MB
            return 500
        elif total_size < 10 * 1024 * 1024:  # < 10MB
            return 1000
        elif total_size < 100 * 1024 * 1024:  # < 100MB
            return 2000
        else:
            return 4000

    def _calculate_max_concurrent(self, data_sources: List[DataSourceInfo], requirements: ProcessingRequirements) -> int:
        """计算最大并发数"""
        # 基础并发数
        base_concurrent = 5
        
        # 根据优先级调整
        if requirements.priority == TaskPriority.URGENT:
            base_concurrent *= 2
        elif requirements.priority == TaskPriority.CRITICAL:
            base_concurrent *= 3
        elif requirements.priority == TaskPriority.LOW:
            base_concurrent = max(1, base_concurrent // 2)
        
        # 根据数据源数量调整
        source_count = len(data_sources)
        if source_count > 10:
            base_concurrent = min(base_concurrent, source_count // 2)
        
        return max(1, min(base_concurrent, 20))  # 限制在1-20之间

    def _generate_tags(self, task_type: TaskType, data_sources: List[DataSourceInfo]) -> List[str]:
        """生成任务标签"""
        tags = [task_type.value, "auto_generated"]
        
        # 添加数据源类型标签
        source_types = set(source.type for source in data_sources)
        tags.extend(f"source_{source_type}" for source_type in source_types)
        
        # 添加数据格式标签
        formats = set(source.format for source in data_sources)
        tags.extend(f"format_{format_type}" for format_type in formats)
        
        return tags

    def _apply_custom_config(self, task: ETLTask, custom_config: Dict[str, Any]) -> None:
        """应用自定义配置"""
        # 更新任务属性
        for key, value in custom_config.items():
            if hasattr(task, key):
                setattr(task, key, value)
        
        # 更新管道配置
        if "pipeline_config" in custom_config:
            pipeline_updates = custom_config["pipeline_config"]
            if task.pipeline_config:
                task.pipeline_config.update(pipeline_updates)
            else:
                task.pipeline_config = pipeline_updates
        
        # 更新执行配置
        if "execution_config" in custom_config:
            task.execution_config.update(custom_config["execution_config"])
        
        # 更新元数据
        if "metadata" in custom_config:
            task.metadata.update(custom_config["metadata"])

    def generate_batch_tasks(
        self,
        base_name: str,
        data_sources_groups: List[List[DataSourceInfo]],
        requirements: ProcessingRequirements,
        schedule: Optional[ScheduleConfig] = None
    ) -> List[ETLTask]:
        """批量生成ETL任务
        
        Args:
            base_name: 基础任务名称
            data_sources_groups: 数据源分组列表
            requirements: 处理需求
            schedule: 调度配置
            
        Returns:
            生成的任务列表
        """
        tasks = []
        
        for i, data_sources in enumerate(data_sources_groups):
            task_name = f"{base_name}_batch_{i+1}"
            
            # 为批处理调整需求
            batch_requirements = ProcessingRequirements(
                task_type=TaskType.BATCH_PROCESSING,
                priority=requirements.priority,
                quality_threshold=requirements.quality_threshold,
                accuracy_requirement=requirements.accuracy_requirement,
                completeness_requirement=requirements.completeness_requirement,
                output_formats=requirements.output_formats,
                output_targets=requirements.output_targets,
                enable_entity_extraction=requirements.enable_entity_extraction,
                enable_relationship_extraction=requirements.enable_relationship_extraction,
                enable_vector_embedding=requirements.enable_vector_embedding,
                enable_knowledge_graph=requirements.enable_knowledge_graph
            )
            
            task = self.generate_task(
                name=task_name,
                data_sources=data_sources,
                requirements=batch_requirements,
                schedule=schedule
            )
            
            # 设置依赖关系
            if i > 0:
                task.dependencies = [tasks[i-1].id]
                tasks[i-1].dependents = [task.id]
            
            tasks.append(task)
        
        logger.info(f"批量生成了 {len(tasks)} 个ETL任务")
        
        return tasks

    def generate_dependency_chain(
        self,
        task_configs: List[Dict[str, Any]]
    ) -> List[ETLTask]:
        """生成依赖链任务
        
        Args:
            task_configs: 任务配置列表，每个配置包含name, data_sources, requirements等
            
        Returns:
            按依赖顺序排列的任务列表
        """
        tasks = []
        
        for i, config in enumerate(task_configs):
            task = self.generate_task(
                name=config["name"],
                data_sources=config["data_sources"],
                requirements=config["requirements"],
                schedule=config.get("schedule"),
                custom_config=config.get("custom_config")
            )
            
            # 设置依赖关系
            if i > 0:
                task.dependencies = [tasks[i-1].id]
                tasks[i-1].dependents = [task.id]
            
            tasks.append(task)
        
        logger.info(f"生成了 {len(tasks)} 个依赖链任务")
        
        return tasks

    def optimize_task_schedule(
        self,
        tasks: List[ETLTask],
        optimization_criteria: str = "time"  # time, cost, resource
    ) -> List[ETLTask]:
        """优化任务调度
        
        Args:
            tasks: 任务列表
            optimization_criteria: 优化标准
            
        Returns:
            优化后的任务列表
        """
        logger.info(f"开始优化任务调度，标准: {optimization_criteria}")
        
        if optimization_criteria == "time":
            # 按优先级和估算时间排序
            priority_order = {p: i for i, p in enumerate(TaskPriority)}
            tasks.sort(key=lambda t: (priority_order[t.priority], t.estimated_duration or 0))
        
        elif optimization_criteria == "cost":
            # 按成本排序
            tasks.sort(key=lambda t: t.estimated_cost or 0)
        
        elif optimization_criteria == "resource":
            # 按资源需求排序
            tasks.sort(key=lambda t: (
                t.estimated_resources.get("memory_mb", 0) if t.estimated_resources else 0
            ))
        
        # 调整调度时间
        current_time = datetime.now()
        for i, task in enumerate(tasks):
            if task.schedule.type == ScheduleType.SCHEDULED:
                # 错开调度时间避免资源冲突
                task.schedule.scheduled_time = current_time + timedelta(minutes=i * 5)
        
        logger.info(f"任务调度优化完成，共 {len(tasks)} 个任务")
        
        return tasks

    def get_task(self, task_id: str) -> Optional[ETLTask]:
        """获取任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            任务对象
        """
        return self.generated_tasks.get(task_id)

    def get_tasks(
        self,
        task_type: Optional[TaskType] = None,
        priority: Optional[TaskPriority] = None,
        status: Optional[ETLJobStatus] = None
    ) -> List[ETLTask]:
        """获取任务列表
        
        Args:
            task_type: 任务类型过滤
            priority: 优先级过滤
            status: 状态过滤
            
        Returns:
            任务列表
        """
        tasks = list(self.generated_tasks.values())
        
        if task_type:
            tasks = [t for t in tasks if t.task_type == task_type]
        
        if priority:
            tasks = [t for t in tasks if t.priority == priority]
        
        if status:
            tasks = [t for t in tasks if t.status == status]
        
        return tasks

    def update_task_status(self, task_id: str, status: ETLJobStatus) -> bool:
        """更新任务状态
        
        Args:
            task_id: 任务ID
            status: 新状态
            
        Returns:
            是否更新成功
        """
        if task_id in self.generated_tasks:
            self.generated_tasks[task_id].status = status
            self.generated_tasks[task_id].updated_at = datetime.now()
            return True
        return False

    def delete_task(self, task_id: str) -> bool:
        """删除任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            是否删除成功
        """
        if task_id in self.generated_tasks:
            del self.generated_tasks[task_id]
            logger.info(f"删除任务: {task_id}")
            return True
        return False

    def export_tasks(self, file_path: str, task_ids: Optional[List[str]] = None) -> None:
        """导出任务配置
        
        Args:
            file_path: 导出文件路径
            task_ids: 要导出的任务ID列表，None表示导出所有
        """
        if task_ids:
            tasks_to_export = {tid: task for tid, task in self.generated_tasks.items() if tid in task_ids}
        else:
            tasks_to_export = self.generated_tasks
        
        # 转换为可序列化格式
        export_data = {
            "tasks": {
                task_id: task.dict() if hasattr(task, 'dict') else task.__dict__
                for task_id, task in tasks_to_export.items()
            },
            "exported_at": datetime.now().isoformat(),
            "total_tasks": len(tasks_to_export)
        }
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False, default=str)
        
        logger.info(f"导出了 {len(tasks_to_export)} 个任务到 {file_path}")

    def import_tasks(self, file_path: str) -> int:
        """导入任务配置
        
        Args:
            file_path: 导入文件路径
            
        Returns:
            导入的任务数量
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            import_data = json.load(f)
        
        imported_count = 0
        
        for task_id, task_data in import_data.get("tasks", {}).items():
            try:
                # 重新创建任务对象
                task = ETLTask(**task_data)
                self.generated_tasks[task_id] = task
                imported_count += 1
            except Exception as e:
                logger.error(f"导入任务失败 {task_id}: {str(e)}")
        
        logger.info(f"从 {file_path} 导入了 {imported_count} 个任务")
        
        return imported_count

    def get_task_statistics(self) -> Dict[str, Any]:
        """获取任务统计信息
        
        Returns:
            统计信息字典
        """
        tasks = list(self.generated_tasks.values())
        
        if not tasks:
            return {"total_tasks": 0}
        
        # 按类型统计
        type_counts = {}
        for task_type in TaskType:
            type_counts[task_type.value] = sum(1 for t in tasks if t.task_type == task_type)
        
        # 按优先级统计
        priority_counts = {}
        for priority in TaskPriority:
            priority_counts[priority.value] = sum(1 for t in tasks if t.priority == priority)
        
        # 按状态统计
        status_counts = {}
        for status in ETLJobStatus:
            status_counts[status.value] = sum(1 for t in tasks if t.status == status)
        
        # 资源统计
        total_estimated_duration = sum(t.estimated_duration or 0 for t in tasks)
        total_estimated_cost = sum(t.estimated_cost or 0 for t in tasks)
        
        return {
            "total_tasks": len(tasks),
            "type_distribution": type_counts,
            "priority_distribution": priority_counts,
            "status_distribution": status_counts,
            "total_estimated_duration": total_estimated_duration,
            "total_estimated_cost": total_estimated_cost,
            "avg_estimated_duration": total_estimated_duration / len(tasks) if tasks else 0,
            "avg_estimated_cost": total_estimated_cost / len(tasks) if tasks else 0
        }