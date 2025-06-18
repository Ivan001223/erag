"""ETL API路由

提供ETL相关的REST API端点，包括数据结构化、验证、转换、加载等功能。
"""

import json
import uuid
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union
from pathlib import Path

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, UploadFile, File, Form, Query
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field, validator

from backend.core.etl import (
    DataStructurer, DataValidator, DataTransformer, DataLoader, PipelineManager
)
from backend.core.etl.task_generator import TaskGenerator
from backend.core.etl.flink_manager import FlinkManager, FlinkJobConfig, FlinkClusterConfig
from backend.core.etl.cdc_manager import CDCManager, CDCSourceConfig, CDCFilter, CDCProcessor
from backend.services.etl_service import ETLService
from backend.utils.logger import get_logger
from backend.utils.auth import get_current_user
from backend.models.user_models import User

logger = get_logger(__name__)

# 创建路由器
router = APIRouter(prefix="/api/etl", tags=["ETL"])

# 全局实例
data_structurer = DataStructurer()
data_validator = DataValidator()
data_transformer = DataTransformer()
data_loader = DataLoader()
pipeline_manager = PipelineManager()
task_generator = TaskGenerator()
flink_manager = FlinkManager()
cdc_manager = CDCManager()
etl_service = ETLService()


# ==================== 请求/响应模型 ====================

class DataStructureRequest(BaseModel):
    """数据结构化请求"""
    data: Union[str, Dict[str, Any], List[Any]]
    data_type: str = "auto"  # auto, text, json, csv, html, pdf, docx, xlsx
    options: Dict[str, Any] = Field(default_factory=dict)
    extract_entities: bool = True
    extract_relations: bool = True
    chunk_text: bool = True
    chunk_size: int = 1000
    chunk_overlap: int = 200


class ValidationRuleRequest(BaseModel):
    """验证规则请求"""
    field: str
    rule_type: str  # required, format, range, length, pattern, custom, unique, reference, consistency
    parameters: Dict[str, Any] = Field(default_factory=dict)
    level: str = "strict"  # strict, moderate, lenient
    message: Optional[str] = None


class DataValidationRequest(BaseModel):
    """数据验证请求"""
    data: Union[Dict[str, Any], List[Dict[str, Any]]]
    rules: List[ValidationRuleRequest]
    rule_set_name: Optional[str] = None
    stop_on_first_error: bool = False


class TransformationRuleRequest(BaseModel):
    """转换规则请求"""
    field: str
    transform_type: str  # clean, normalize, enrich, filter, map, extract, custom
    parameters: Dict[str, Any] = Field(default_factory=dict)
    target_field: Optional[str] = None
    condition: Optional[Dict[str, Any]] = None


class DataTransformationRequest(BaseModel):
    """数据转换请求"""
    data: Union[Dict[str, Any], List[Dict[str, Any]]]
    rules: List[TransformationRuleRequest]
    rule_chain_name: Optional[str] = None
    parallel: bool = False


class LoadTargetRequest(BaseModel):
    """加载目标请求"""
    target_type: str  # knowledge_graph, vector_store, database, file_system, api, elasticsearch, redis
    connection_config: Dict[str, Any]
    target_config: Dict[str, Any] = Field(default_factory=dict)
    load_strategy: str = "insert"  # insert, update, upsert, merge, replace


class DataLoadRequest(BaseModel):
    """数据加载请求"""
    data: Union[Dict[str, Any], List[Dict[str, Any]]]
    targets: List[LoadTargetRequest]
    batch_size: int = 100
    parallel: bool = False
    validate_before_load: bool = True


class PipelineConfigRequest(BaseModel):
    """管道配置请求"""
    name: str
    description: Optional[str] = None
    source_config: Dict[str, Any]
    structure_config: Dict[str, Any] = Field(default_factory=dict)
    validation_rules: List[ValidationRuleRequest] = Field(default_factory=list)
    transformation_rules: List[TransformationRuleRequest] = Field(default_factory=list)
    load_targets: List[LoadTargetRequest] = Field(default_factory=list)
    execution_mode: str = "sequential"  # sequential, parallel, batch
    batch_size: int = 100
    error_handling: str = "stop"  # stop, skip, retry
    retry_attempts: int = 3
    schedule: Optional[Dict[str, Any]] = None
    tags: List[str] = Field(default_factory=list)


class TaskGenerationRequest(BaseModel):
    """任务生成请求"""
    data_sources: List[Dict[str, Any]]
    processing_requirements: List[Dict[str, Any]]
    schedule_config: Optional[Dict[str, Any]] = None
    optimization_goals: List[str] = Field(default_factory=list)
    constraints: Dict[str, Any] = Field(default_factory=dict)


class FlinkJobSubmitRequest(BaseModel):
    """Flink作业提交请求"""
    job_config: Dict[str, Any]
    cluster_id: str = "default"
    custom_config: Optional[Dict[str, Any]] = None


class CDCSourceRequest(BaseModel):
    """CDC数据源请求"""
    name: str
    source_type: str  # mysql, postgresql, mongodb, oracle, sql_server, kafka, file_system, api
    connection_config: Dict[str, Any]
    tables: List[str] = Field(default_factory=list)
    databases: List[str] = Field(default_factory=list)
    include_patterns: List[str] = Field(default_factory=list)
    exclude_patterns: List[str] = Field(default_factory=list)
    batch_size: int = 1000
    poll_interval_ms: int = 1000
    max_queue_size: int = 10000
    initial_position: str = "latest"
    tags: List[str] = Field(default_factory=list)


class CDCFilterRequest(BaseModel):
    """CDC过滤器请求"""
    name: str
    filter_type: str  # table_filter, column_filter, condition_filter, event_type_filter, custom_filter
    conditions: Dict[str, Any]
    include: bool = True
    priority: int = 0
    enabled: bool = True


# ==================== 数据结构化端点 ====================

@router.post("/structure", summary="结构化数据")
async def structure_data(
    request: DataStructureRequest,
    current_user: User = Depends(get_current_user)
):
    """将非结构化数据转换为结构化格式"""
    try:
        logger.info(f"用户 {current_user.username} 请求数据结构化")
        
        result = await data_structurer.structure_data(
            data=request.data,
            data_type=request.data_type,
            options=request.options,
            extract_entities=request.extract_entities,
            extract_relations=request.extract_relations,
            chunk_text=request.chunk_text,
            chunk_size=request.chunk_size,
            chunk_overlap=request.chunk_overlap
        )
        
        return {
            "success": True,
            "data": result,
            "message": "数据结构化完成"
        }
        
    except Exception as e:
        logger.error(f"数据结构化失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"数据结构化失败: {str(e)}")


@router.post("/structure/batch", summary="批量结构化数据")
async def structure_data_batch(
    file: UploadFile = File(...),
    data_type: str = Form("auto"),
    extract_entities: bool = Form(True),
    extract_relations: bool = Form(True),
    chunk_text: bool = Form(True),
    chunk_size: int = Form(1000),
    chunk_overlap: int = Form(200),
    current_user: User = Depends(get_current_user)
):
    """批量结构化文件数据"""
    try:
        logger.info(f"用户 {current_user.username} 请求批量数据结构化")
        
        # 读取文件内容
        content = await file.read()
        
        # 根据文件类型处理
        if file.content_type and "text" in file.content_type:
            data = content.decode('utf-8')
        else:
            data = content
        
        results = await data_structurer.structure_batch(
            data_list=[data],
            data_type=data_type,
            extract_entities=extract_entities,
            extract_relations=extract_relations,
            chunk_text=chunk_text,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )
        
        return {
            "success": True,
            "data": results,
            "message": f"批量结构化完成，处理了 {len(results)} 个项目"
        }
        
    except Exception as e:
        logger.error(f"批量数据结构化失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"批量数据结构化失败: {str(e)}")


# ==================== 数据验证端点 ====================

@router.post("/validate", summary="验证数据")
async def validate_data(
    request: DataValidationRequest,
    current_user: User = Depends(get_current_user)
):
    """验证数据质量和完整性"""
    try:
        logger.info(f"用户 {current_user.username} 请求数据验证")
        
        # 添加验证规则
        for rule_req in request.rules:
            data_validator.add_rule(
                field=rule_req.field,
                rule_type=rule_req.rule_type,
                parameters=rule_req.parameters,
                level=rule_req.level,
                message=rule_req.message
            )
        
        # 执行验证
        result = await data_validator.validate_data(
            data=request.data,
            rule_set_name=request.rule_set_name,
            stop_on_first_error=request.stop_on_first_error
        )
        
        return {
            "success": True,
            "data": result,
            "message": "数据验证完成"
        }
        
    except Exception as e:
        logger.error(f"数据验证失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"数据验证失败: {str(e)}")


@router.post("/validate/rules", summary="创建验证规则集")
async def create_validation_rules(
    name: str,
    rules: List[ValidationRuleRequest],
    description: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """创建验证规则集"""
    try:
        logger.info(f"用户 {current_user.username} 创建验证规则集: {name}")
        
        # 创建规则集
        rule_set = data_validator.create_rule_set(name, description)
        
        # 添加规则
        for rule_req in rules:
            data_validator.add_rule(
                field=rule_req.field,
                rule_type=rule_req.rule_type,
                parameters=rule_req.parameters,
                level=rule_req.level,
                message=rule_req.message,
                rule_set_name=name
            )
        
        return {
            "success": True,
            "data": {
                "rule_set_id": rule_set.rule_set_id,
                "name": name,
                "rules_count": len(rules)
            },
            "message": f"验证规则集 '{name}' 创建成功"
        }
        
    except Exception as e:
        logger.error(f"创建验证规则集失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"创建验证规则集失败: {str(e)}")


# ==================== 数据转换端点 ====================

@router.post("/transform", summary="转换数据")
async def transform_data(
    request: DataTransformationRequest,
    current_user: User = Depends(get_current_user)
):
    """转换数据格式和内容"""
    try:
        logger.info(f"用户 {current_user.username} 请求数据转换")
        
        # 添加转换规则
        for rule_req in request.rules:
            data_transformer.add_rule(
                field=rule_req.field,
                transform_type=rule_req.transform_type,
                parameters=rule_req.parameters,
                target_field=rule_req.target_field,
                condition=rule_req.condition
            )
        
        # 执行转换
        result = await data_transformer.transform_data(
            data=request.data,
            rule_chain_name=request.rule_chain_name,
            parallel=request.parallel
        )
        
        return {
            "success": True,
            "data": result,
            "message": "数据转换完成"
        }
        
    except Exception as e:
        logger.error(f"数据转换失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"数据转换失败: {str(e)}")


@router.post("/transform/rules", summary="创建转换规则链")
async def create_transformation_rules(
    name: str,
    rules: List[TransformationRuleRequest],
    description: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """创建转换规则链"""
    try:
        logger.info(f"用户 {current_user.username} 创建转换规则链: {name}")
        
        # 创建规则链
        rule_chain = data_transformer.create_rule_chain(name, description)
        
        # 添加规则
        for rule_req in rules:
            data_transformer.add_rule(
                field=rule_req.field,
                transform_type=rule_req.transform_type,
                parameters=rule_req.parameters,
                target_field=rule_req.target_field,
                condition=rule_req.condition,
                rule_chain_name=name
            )
        
        return {
            "success": True,
            "data": {
                "rule_chain_id": rule_chain.rule_chain_id,
                "name": name,
                "rules_count": len(rules)
            },
            "message": f"转换规则链 '{name}' 创建成功"
        }
        
    except Exception as e:
        logger.error(f"创建转换规则链失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"创建转换规则链失败: {str(e)}")


# ==================== 数据加载端点 ====================

@router.post("/load", summary="加载数据")
async def load_data(
    request: DataLoadRequest,
    current_user: User = Depends(get_current_user)
):
    """将数据加载到目标系统"""
    try:
        logger.info(f"用户 {current_user.username} 请求数据加载")
        
        # 添加加载目标
        for target_req in request.targets:
            data_loader.add_target(
                target_type=target_req.target_type,
                connection_config=target_req.connection_config,
                target_config=target_req.target_config,
                load_strategy=target_req.load_strategy
            )
        
        # 执行加载
        results = await data_loader.load_data(
            data=request.data,
            target_names=[f"target_{i}" for i in range(len(request.targets))],
            batch_size=request.batch_size,
            parallel=request.parallel,
            validate_before_load=request.validate_before_load
        )
        
        return {
            "success": True,
            "data": results,
            "message": "数据加载完成"
        }
        
    except Exception as e:
        logger.error(f"数据加载失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"数据加载失败: {str(e)}")


@router.post("/load/test", summary="测试加载目标")
async def test_load_target(
    target: LoadTargetRequest,
    current_user: User = Depends(get_current_user)
):
    """测试加载目标连接"""
    try:
        logger.info(f"用户 {current_user.username} 测试加载目标")
        
        # 添加目标
        target_name = f"test_target_{uuid.uuid4().hex[:8]}"
        data_loader.add_target(
            target_name=target_name,
            target_type=target.target_type,
            connection_config=target.connection_config,
            target_config=target.target_config,
            load_strategy=target.load_strategy
        )
        
        # 测试连接
        result = await data_loader.test_target_connection(target_name)
        
        # 清理测试目标
        data_loader.remove_target(target_name)
        
        return {
            "success": True,
            "data": result,
            "message": "目标连接测试完成"
        }
        
    except Exception as e:
        logger.error(f"测试加载目标失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"测试加载目标失败: {str(e)}")


# ==================== 管道管理端点 ====================

@router.post("/pipeline", summary="创建ETL管道")
async def create_pipeline(
    request: PipelineConfigRequest,
    current_user: User = Depends(get_current_user)
):
    """创建ETL管道"""
    try:
        logger.info(f"用户 {current_user.username} 创建ETL管道: {request.name}")
        
        # 创建管道配置
        config = {
            "name": request.name,
            "description": request.description,
            "source_config": request.source_config,
            "structure_config": request.structure_config,
            "validation_rules": [rule.dict() for rule in request.validation_rules],
            "transformation_rules": [rule.dict() for rule in request.transformation_rules],
            "load_targets": [target.dict() for target in request.load_targets],
            "execution_mode": request.execution_mode,
            "batch_size": request.batch_size,
            "error_handling": request.error_handling,
            "retry_attempts": request.retry_attempts,
            "schedule": request.schedule,
            "tags": request.tags,
            "created_by": current_user.username
        }
        
        pipeline_id = await pipeline_manager.create_pipeline(config)
        
        return {
            "success": True,
            "data": {
                "pipeline_id": pipeline_id,
                "name": request.name
            },
            "message": f"ETL管道 '{request.name}' 创建成功"
        }
        
    except Exception as e:
        logger.error(f"创建ETL管道失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"创建ETL管道失败: {str(e)}")


@router.post("/pipeline/{pipeline_id}/execute", summary="执行ETL管道")
async def execute_pipeline(
    pipeline_id: str,
    data: Optional[Union[Dict[str, Any], List[Dict[str, Any]]]] = None,
    background_tasks: BackgroundTasks = None,
    current_user: User = Depends(get_current_user)
):
    """执行ETL管道"""
    try:
        logger.info(f"用户 {current_user.username} 执行ETL管道: {pipeline_id}")
        
        # 启动管道执行
        execution_id = await pipeline_manager.execute_pipeline(
            pipeline_id=pipeline_id,
            input_data=data
        )
        
        return {
            "success": True,
            "data": {
                "execution_id": execution_id,
                "pipeline_id": pipeline_id,
                "status": "started"
            },
            "message": "ETL管道执行已启动"
        }
        
    except Exception as e:
        logger.error(f"执行ETL管道失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"执行ETL管道失败: {str(e)}")


@router.get("/pipeline/{pipeline_id}/status", summary="获取管道状态")
async def get_pipeline_status(
    pipeline_id: str,
    current_user: User = Depends(get_current_user)
):
    """获取ETL管道状态"""
    try:
        status = await pipeline_manager.get_pipeline_status(pipeline_id)
        
        if not status:
            raise HTTPException(status_code=404, detail="管道不存在")
        
        return {
            "success": True,
            "data": status,
            "message": "获取管道状态成功"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取管道状态失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取管道状态失败: {str(e)}")


@router.get("/pipeline", summary="获取管道列表")
async def get_pipelines(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    current_user: User = Depends(get_current_user)
):
    """获取ETL管道列表"""
    try:
        pipelines = await pipeline_manager.get_pipelines(skip=skip, limit=limit)
        
        return {
            "success": True,
            "data": pipelines,
            "message": "获取管道列表成功"
        }
        
    except Exception as e:
        logger.error(f"获取管道列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取管道列表失败: {str(e)}")


# ==================== 任务生成端点 ====================

@router.post("/task/generate", summary="生成ETL任务")
async def generate_tasks(
    request: TaskGenerationRequest,
    current_user: User = Depends(get_current_user)
):
    """根据数据源和需求生成ETL任务"""
    try:
        logger.info(f"用户 {current_user.username} 请求生成ETL任务")
        
        tasks = await task_generator.generate_tasks(
            data_sources=request.data_sources,
            processing_requirements=request.processing_requirements,
            schedule_config=request.schedule_config,
            optimization_goals=request.optimization_goals,
            constraints=request.constraints
        )
        
        return {
            "success": True,
            "data": tasks,
            "message": f"生成了 {len(tasks)} 个ETL任务"
        }
        
    except Exception as e:
        logger.error(f"生成ETL任务失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"生成ETL任务失败: {str(e)}")


@router.post("/task/batch", summary="批量生成ETL任务")
async def generate_batch_tasks(
    data_sources: List[Dict[str, Any]],
    processing_requirements: List[Dict[str, Any]],
    batch_size: int = 10,
    current_user: User = Depends(get_current_user)
):
    """批量生成ETL任务"""
    try:
        logger.info(f"用户 {current_user.username} 请求批量生成ETL任务")
        
        tasks = await task_generator.generate_batch_tasks(
            data_sources=data_sources,
            processing_requirements=processing_requirements,
            batch_size=batch_size
        )
        
        return {
            "success": True,
            "data": tasks,
            "message": f"批量生成了 {len(tasks)} 个ETL任务"
        }
        
    except Exception as e:
        logger.error(f"批量生成ETL任务失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"批量生成ETL任务失败: {str(e)}")


@router.get("/task/{task_id}", summary="获取任务详情")
async def get_task(
    task_id: str,
    current_user: User = Depends(get_current_user)
):
    """获取ETL任务详情"""
    try:
        task = await task_generator.get_task(task_id)
        
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")
        
        return {
            "success": True,
            "data": task,
            "message": "获取任务详情成功"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取任务详情失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取任务详情失败: {str(e)}")


# ==================== Flink管理端点 ====================

@router.post("/flink/job", summary="提交Flink作业")
async def submit_flink_job(
    request: FlinkJobSubmitRequest,
    current_user: User = Depends(get_current_user)
):
    """提交Flink流处理作业"""
    try:
        logger.info(f"用户 {current_user.username} 提交Flink作业")
        
        # 创建作业配置
        job_config = FlinkJobConfig(**request.job_config)
        flink_manager.add_job_config(job_config)
        
        # 提交作业
        execution = await flink_manager.submit_job(
            job_id=job_config.job_id,
            cluster_id=request.cluster_id,
            custom_config=request.custom_config
        )
        
        return {
            "success": True,
            "data": {
                "execution_id": execution.execution_id,
                "job_id": execution.job_id,
                "cluster_id": execution.cluster_id,
                "state": execution.state.value
            },
            "message": "Flink作业提交成功"
        }
        
    except Exception as e:
        logger.error(f"提交Flink作业失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"提交Flink作业失败: {str(e)}")


@router.get("/flink/job/{execution_id}/status", summary="获取Flink作业状态")
async def get_flink_job_status(
    execution_id: str,
    current_user: User = Depends(get_current_user)
):
    """获取Flink作业状态"""
    try:
        execution = flink_manager.get_job_status(execution_id)
        
        if not execution:
            raise HTTPException(status_code=404, detail="作业不存在")
        
        return {
            "success": True,
            "data": execution.dict(),
            "message": "获取作业状态成功"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取Flink作业状态失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取Flink作业状态失败: {str(e)}")


@router.post("/flink/job/{execution_id}/cancel", summary="取消Flink作业")
async def cancel_flink_job(
    execution_id: str,
    current_user: User = Depends(get_current_user)
):
    """取消Flink作业"""
    try:
        logger.info(f"用户 {current_user.username} 取消Flink作业: {execution_id}")
        
        success = await flink_manager.cancel_job(execution_id)
        
        if not success:
            raise HTTPException(status_code=400, detail="取消作业失败")
        
        return {
            "success": True,
            "message": "Flink作业取消成功"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"取消Flink作业失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"取消Flink作业失败: {str(e)}")


@router.get("/flink/jobs", summary="获取Flink作业列表")
async def get_flink_jobs(
    current_user: User = Depends(get_current_user)
):
    """获取Flink作业列表"""
    try:
        running_jobs = flink_manager.get_running_jobs()
        
        return {
            "success": True,
            "data": [job.dict() for job in running_jobs],
            "message": "获取作业列表成功"
        }
        
    except Exception as e:
        logger.error(f"获取Flink作业列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取Flink作业列表失败: {str(e)}")


# ==================== CDC管理端点 ====================

@router.post("/cdc/source", summary="添加CDC数据源")
async def add_cdc_source(
    request: CDCSourceRequest,
    current_user: User = Depends(get_current_user)
):
    """添加CDC数据源"""
    try:
        logger.info(f"用户 {current_user.username} 添加CDC数据源: {request.name}")
        
        # 创建数据源配置
        config = CDCSourceConfig(
            source_id=str(uuid.uuid4()),
            name=request.name,
            source_type=request.source_type,
            connection_config=request.connection_config,
            tables=request.tables,
            databases=request.databases,
            include_patterns=request.include_patterns,
            exclude_patterns=request.exclude_patterns,
            batch_size=request.batch_size,
            poll_interval_ms=request.poll_interval_ms,
            max_queue_size=request.max_queue_size,
            initial_position=request.initial_position,
            tags=request.tags
        )
        
        cdc_manager.add_source(config)
        
        return {
            "success": True,
            "data": {
                "source_id": config.source_id,
                "name": config.name
            },
            "message": f"CDC数据源 '{request.name}' 添加成功"
        }
        
    except Exception as e:
        logger.error(f"添加CDC数据源失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"添加CDC数据源失败: {str(e)}")


@router.post("/cdc/source/{source_id}/start", summary="启动CDC数据源")
async def start_cdc_source(
    source_id: str,
    current_user: User = Depends(get_current_user)
):
    """启动CDC数据源监控"""
    try:
        logger.info(f"用户 {current_user.username} 启动CDC数据源: {source_id}")
        
        success = await cdc_manager.start_source(source_id)
        
        if not success:
            raise HTTPException(status_code=400, detail="启动数据源失败")
        
        return {
            "success": True,
            "message": "CDC数据源启动成功"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"启动CDC数据源失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"启动CDC数据源失败: {str(e)}")


@router.post("/cdc/source/{source_id}/stop", summary="停止CDC数据源")
async def stop_cdc_source(
    source_id: str,
    current_user: User = Depends(get_current_user)
):
    """停止CDC数据源监控"""
    try:
        logger.info(f"用户 {current_user.username} 停止CDC数据源: {source_id}")
        
        success = await cdc_manager.stop_source(source_id)
        
        if not success:
            raise HTTPException(status_code=400, detail="停止数据源失败")
        
        return {
            "success": True,
            "message": "CDC数据源停止成功"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"停止CDC数据源失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"停止CDC数据源失败: {str(e)}")


@router.get("/cdc/source/{source_id}/status", summary="获取CDC数据源状态")
async def get_cdc_source_status(
    source_id: str,
    current_user: User = Depends(get_current_user)
):
    """获取CDC数据源状态"""
    try:
        status = cdc_manager.get_source_status(source_id)
        
        if not status:
            raise HTTPException(status_code=404, detail="数据源不存在")
        
        return {
            "success": True,
            "data": status,
            "message": "获取数据源状态成功"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取CDC数据源状态失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取CDC数据源状态失败: {str(e)}")


@router.get("/cdc/sources", summary="获取CDC数据源列表")
async def get_cdc_sources(
    current_user: User = Depends(get_current_user)
):
    """获取CDC数据源列表"""
    try:
        sources = cdc_manager.get_all_sources_status()
        
        return {
            "success": True,
            "data": sources,
            "message": "获取数据源列表成功"
        }
        
    except Exception as e:
        logger.error(f"获取CDC数据源列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取CDC数据源列表失败: {str(e)}")


@router.post("/cdc/filter", summary="添加CDC过滤器")
async def add_cdc_filter(
    request: CDCFilterRequest,
    current_user: User = Depends(get_current_user)
):
    """添加CDC过滤器"""
    try:
        logger.info(f"用户 {current_user.username} 添加CDC过滤器: {request.name}")
        
        # 创建过滤器
        filter_config = CDCFilter(
            name=request.name,
            filter_type=request.filter_type,
            conditions=request.conditions,
            include=request.include,
            priority=request.priority,
            enabled=request.enabled
        )
        
        cdc_manager.add_filter(filter_config)
        
        return {
            "success": True,
            "data": {
                "filter_id": filter_config.filter_id,
                "name": filter_config.name
            },
            "message": f"CDC过滤器 '{request.name}' 添加成功"
        }
        
    except Exception as e:
        logger.error(f"添加CDC过滤器失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"添加CDC过滤器失败: {str(e)}")


# ==================== 统计和监控端点 ====================

@router.get("/statistics", summary="获取ETL统计信息")
async def get_etl_statistics(
    current_user: User = Depends(get_current_user)
):
    """获取ETL整体统计信息"""
    try:
        # 获取各组件统计
        pipeline_stats = await pipeline_manager.get_statistics()
        task_stats = await task_generator.get_statistics()
        flink_stats = flink_manager.get_job_statistics()
        cdc_stats = cdc_manager.get_statistics()
        
        return {
            "success": True,
            "data": {
                "pipeline": pipeline_stats,
                "task_generator": task_stats,
                "flink": flink_stats,
                "cdc": cdc_stats,
                "timestamp": datetime.now().isoformat()
            },
            "message": "获取ETL统计信息成功"
        }
        
    except Exception as e:
        logger.error(f"获取ETL统计信息失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取ETL统计信息失败: {str(e)}")


@router.get("/health", summary="ETL健康检查")
async def etl_health_check(
    current_user: User = Depends(get_current_user)
):
    """ETL系统健康检查"""
    try:
        # 获取各组件健康状态
        pipeline_health = await pipeline_manager.health_check()
        flink_health = await flink_manager.health_check()
        cdc_health = await cdc_manager.health_check()
        
        # 汇总健康状态
        all_healthy = all([
            pipeline_health.get("status") == "healthy",
            flink_health.get("status") == "healthy",
            cdc_health.get("status") == "healthy"
        ])
        
        overall_status = "healthy" if all_healthy else "degraded"
        
        # 收集所有问题
        all_issues = []
        all_issues.extend(pipeline_health.get("issues", []))
        all_issues.extend(flink_health.get("issues", []))
        all_issues.extend(cdc_health.get("issues", []))
        
        if len(all_issues) > 10:  # 问题过多时标记为不健康
            overall_status = "unhealthy"
        
        return {
            "success": True,
            "data": {
                "status": overall_status,
                "timestamp": datetime.now().isoformat(),
                "components": {
                    "pipeline": pipeline_health,
                    "flink": flink_health,
                    "cdc": cdc_health
                },
                "issues": all_issues
            },
            "message": "ETL健康检查完成"
        }
        
    except Exception as e:
        logger.error(f"ETL健康检查失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"ETL健康检查失败: {str(e)}")


# ==================== 清理和维护端点 ====================

@router.post("/cleanup", summary="清理ETL资源")
async def cleanup_etl_resources(
    days: int = Query(7, ge=1, le=30),
    current_user: User = Depends(get_current_user)
):
    """清理ETL旧资源"""
    try:
        logger.info(f"用户 {current_user.username} 请求清理ETL资源，保留 {days} 天")
        
        # 清理各组件的旧资源
        pipeline_cleaned = await pipeline_manager.cleanup_old_executions(days)
        flink_cleaned = await flink_manager.cleanup_finished_jobs(days)
        cdc_cleaned = await cdc_manager.cleanup_old_events(days * 24)  # 转换为小时
        
        total_cleaned = pipeline_cleaned + flink_cleaned + cdc_cleaned
        
        return {
            "success": True,
            "data": {
                "pipeline_executions_cleaned": pipeline_cleaned,
                "flink_jobs_cleaned": flink_cleaned,
                "cdc_events_cleaned": cdc_cleaned,
                "total_cleaned": total_cleaned
            },
            "message": f"清理完成，共清理了 {total_cleaned} 个资源"
        }
        
    except Exception as e:
        logger.error(f"清理ETL资源失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"清理ETL资源失败: {str(e)}")