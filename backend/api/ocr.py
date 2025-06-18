from typing import List, Optional, Dict, Any
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, BackgroundTasks, Query
from fastapi.responses import JSONResponse
import asyncio
import uuid
from datetime import datetime
import io

from backend.core.ocr.ocr_service import OCRService, OCRRequest, OCRResponse
from backend.core.ocr.quality_assurance import get_quality_assurance, QualityAssessmentConfig
from backend.utils.logger import get_logger
from backend.utils.auth import get_current_user
from backend.models.user import User
from backend.models.knowledge import Document
from backend.services.document_service import DocumentService
from backend.services.task_service import TaskService
from pydantic import BaseModel, Field

logger = get_logger(__name__)

router = APIRouter(prefix="/api/ocr", tags=["OCR"])

# 依赖注入
def get_ocr_service() -> OCRService:
    return OCRService()

def get_document_service() -> DocumentService:
    return DocumentService()

def get_task_service() -> TaskService:
    return TaskService()

# 请求/响应模型
class OCRUploadRequest(BaseModel):
    """OCR上传请求"""
    extract_tables: bool = Field(default=True, description="是否提取表格")
    extract_images: bool = Field(default=False, description="是否提取图像")
    quality_check: bool = Field(default=True, description="是否进行质量检查")
    language: str = Field(default="auto", description="文档语言")
    ocr_model: str = Field(default="default", description="OCR模型")
    preprocessing: bool = Field(default=True, description="是否预处理")

class BatchOCRRequest(BaseModel):
    """批量OCR请求"""
    extract_tables: bool = Field(default=True, description="是否提取表格")
    extract_images: bool = Field(default=False, description="是否提取图像")
    quality_check: bool = Field(default=True, description="是否进行质量检查")
    language: str = Field(default="auto", description="文档语言")
    ocr_model: str = Field(default="default", description="OCR模型")
    preprocessing: bool = Field(default=True, description="是否预处理")
    max_concurrent: int = Field(default=3, ge=1, le=10, description="最大并发数")

class OCRTaskResponse(BaseModel):
    """OCR任务响应"""
    task_id: str
    status: str
    message: str
    created_at: datetime
    estimated_completion: Optional[datetime] = None

class OCRResultResponse(BaseModel):
    """OCR结果响应"""
    task_id: str
    document_id: str
    filename: str
    status: str
    result: Optional[Dict[str, Any]] = None
    quality_report: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    processing_time: Optional[float] = None
    created_at: datetime
    completed_at: Optional[datetime] = None

class BatchOCRStatusResponse(BaseModel):
    """批量OCR状态响应"""
    batch_id: str
    total_documents: int
    completed_documents: int
    failed_documents: int
    status: str
    results: List[OCRResultResponse]
    created_at: datetime
    estimated_completion: Optional[datetime] = None

@router.post("/upload", response_model=OCRTaskResponse)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    request_data: OCRUploadRequest = Depends(),
    current_user: User = Depends(get_current_user),
    ocr_service: OCRService = Depends(get_ocr_service),
    document_service: DocumentService = Depends(get_document_service),
    task_service: TaskService = Depends(get_task_service)
):
    """
    上传单个文档进行OCR处理
    
    Args:
        file: 上传的文件
        request_data: OCR请求参数
        current_user: 当前用户
        
    Returns:
        OCR任务响应
    """
    try:
        # 验证文件
        if not file.filename:
            raise HTTPException(status_code=400, detail="文件名不能为空")
        
        # 检查文件类型
        allowed_types = [
            "image/jpeg", "image/png", "image/tiff", "image/bmp",
            "application/pdf"
        ]
        
        if file.content_type not in allowed_types:
            raise HTTPException(
                status_code=400, 
                detail=f"不支持的文件类型: {file.content_type}"
            )
        
        # 检查文件大小（50MB限制）
        max_size = 50 * 1024 * 1024
        file_content = await file.read()
        if len(file_content) > max_size:
            raise HTTPException(
                status_code=400,
                detail="文件大小超过50MB限制"
            )
        
        # 重置文件指针
        await file.seek(0)
        
        # 生成任务ID
        task_id = str(uuid.uuid4())
        
        # 创建文档记录
        document = await document_service.create_document(
            filename=file.filename,
            content_type=file.content_type,
            file_size=len(file_content),
            user_id=current_user.id,
            metadata={
                "ocr_request": request_data.dict(),
                "task_id": task_id
            }
        )
        
        # 创建任务记录
        task = await task_service.create_task(
            task_id=task_id,
            task_type="ocr_single",
            user_id=current_user.id,
            metadata={
                "document_id": document.id,
                "filename": file.filename,
                "ocr_params": request_data.dict()
            }
        )
        
        # 添加后台任务
        background_tasks.add_task(
            process_single_document,
            task_id=task_id,
            document_id=document.id,
            file_content=file_content,
            filename=file.filename,
            request_data=request_data,
            ocr_service=ocr_service,
            document_service=document_service,
            task_service=task_service
        )
        
        logger.info(f"OCR任务已创建: {task_id}, 文档: {file.filename}")
        
        return OCRTaskResponse(
            task_id=task_id,
            status="processing",
            message="文档已上传，正在处理中",
            created_at=datetime.now(),
            estimated_completion=None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"上传文档失败: {str(e)}")
        raise HTTPException(status_code=500, detail="文档上传失败")

@router.post("/batch", response_model=OCRTaskResponse)
async def upload_batch_documents(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    request_data: BatchOCRRequest = Depends(),
    current_user: User = Depends(get_current_user),
    ocr_service: OCRService = Depends(get_ocr_service),
    document_service: DocumentService = Depends(get_document_service),
    task_service: TaskService = Depends(get_task_service)
):
    """
    批量上传文档进行OCR处理
    
    Args:
        files: 上传的文件列表
        request_data: 批量OCR请求参数
        current_user: 当前用户
        
    Returns:
        批量OCR任务响应
    """
    try:
        # 验证文件数量
        if len(files) > 20:
            raise HTTPException(status_code=400, detail="批量上传文件数量不能超过20个")
        
        if not files:
            raise HTTPException(status_code=400, detail="请至少上传一个文件")
        
        # 生成批次ID
        batch_id = str(uuid.uuid4())
        
        # 验证所有文件
        validated_files = []
        for file in files:
            if not file.filename:
                continue
                
            # 检查文件类型
            allowed_types = [
                "image/jpeg", "image/png", "image/tiff", "image/bmp",
                "application/pdf"
            ]
            
            if file.content_type not in allowed_types:
                logger.warning(f"跳过不支持的文件类型: {file.filename} ({file.content_type})")
                continue
            
            # 检查文件大小
            file_content = await file.read()
            if len(file_content) > 50 * 1024 * 1024:
                logger.warning(f"跳过过大的文件: {file.filename}")
                continue
            
            validated_files.append((file, file_content))
            await file.seek(0)
        
        if not validated_files:
            raise HTTPException(status_code=400, detail="没有有效的文件可以处理")
        
        # 创建批次任务记录
        batch_task = await task_service.create_task(
            task_id=batch_id,
            task_type="ocr_batch",
            user_id=current_user.id,
            metadata={
                "total_files": len(validated_files),
                "ocr_params": request_data.dict(),
                "file_list": [file.filename for file, _ in validated_files]
            }
        )
        
        # 添加后台任务
        background_tasks.add_task(
            process_batch_documents,
            batch_id=batch_id,
            files_data=validated_files,
            request_data=request_data,
            current_user=current_user,
            ocr_service=ocr_service,
            document_service=document_service,
            task_service=task_service
        )
        
        logger.info(f"批量OCR任务已创建: {batch_id}, 文件数量: {len(validated_files)}")
        
        return OCRTaskResponse(
            task_id=batch_id,
            status="processing",
            message=f"批量任务已创建，共{len(validated_files)}个文件正在处理中",
            created_at=datetime.now()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"批量上传失败: {str(e)}")
        raise HTTPException(status_code=500, detail="批量上传失败")

@router.get("/task/{task_id}", response_model=OCRResultResponse)
async def get_task_status(
    task_id: str,
    current_user: User = Depends(get_current_user),
    task_service: TaskService = Depends(get_task_service)
):
    """
    获取OCR任务状态
    
    Args:
        task_id: 任务ID
        current_user: 当前用户
        
    Returns:
        OCR结果响应
    """
    try:
        # 获取任务信息
        task = await task_service.get_task(task_id)
        
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")
        
        # 检查权限
        if task.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="无权访问此任务")
        
        # 构建响应
        response = OCRResultResponse(
            task_id=task_id,
            document_id=task.metadata.get("document_id", ""),
            filename=task.metadata.get("filename", ""),
            status=task.status,
            created_at=task.created_at,
            completed_at=task.completed_at
        )
        
        # 如果任务完成，添加结果
        if task.status == "completed" and task.result:
            response.result = task.result
            response.processing_time = task.metadata.get("processing_time")
            
            # 添加质量报告
            if "quality_report" in task.result:
                response.quality_report = task.result["quality_report"]
        
        # 如果任务失败，添加错误信息
        elif task.status == "failed":
            response.error_message = task.metadata.get("error_message", "处理失败")
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取任务状态失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取任务状态失败")

@router.get("/batch/{batch_id}", response_model=BatchOCRStatusResponse)
async def get_batch_status(
    batch_id: str,
    current_user: User = Depends(get_current_user),
    task_service: TaskService = Depends(get_task_service)
):
    """
    获取批量OCR任务状态
    
    Args:
        batch_id: 批次ID
        current_user: 当前用户
        
    Returns:
        批量OCR状态响应
    """
    try:
        # 获取批次任务
        batch_task = await task_service.get_task(batch_id)
        
        if not batch_task:
            raise HTTPException(status_code=404, detail="批次任务不存在")
        
        # 检查权限
        if batch_task.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="无权访问此批次任务")
        
        # 获取子任务
        sub_tasks = await task_service.get_tasks_by_parent(batch_id)
        
        # 统计状态
        total_documents = len(sub_tasks)
        completed_documents = sum(1 for task in sub_tasks if task.status == "completed")
        failed_documents = sum(1 for task in sub_tasks if task.status == "failed")
        
        # 确定批次状态
        if completed_documents + failed_documents == total_documents:
            batch_status = "completed"
        elif failed_documents > 0 and completed_documents + failed_documents == total_documents:
            batch_status = "partially_failed"
        else:
            batch_status = "processing"
        
        # 构建子任务结果
        results = []
        for task in sub_tasks:
            result = OCRResultResponse(
                task_id=task.id,
                document_id=task.metadata.get("document_id", ""),
                filename=task.metadata.get("filename", ""),
                status=task.status,
                created_at=task.created_at,
                completed_at=task.completed_at
            )
            
            if task.status == "completed" and task.result:
                result.result = task.result
                result.processing_time = task.metadata.get("processing_time")
                if "quality_report" in task.result:
                    result.quality_report = task.result["quality_report"]
            elif task.status == "failed":
                result.error_message = task.metadata.get("error_message", "处理失败")
            
            results.append(result)
        
        return BatchOCRStatusResponse(
            batch_id=batch_id,
            total_documents=total_documents,
            completed_documents=completed_documents,
            failed_documents=failed_documents,
            status=batch_status,
            results=results,
            created_at=batch_task.created_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取批次状态失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取批次状态失败")

@router.get("/models")
async def list_ocr_models(
    current_user: User = Depends(get_current_user),
    ocr_service: OCRService = Depends(get_ocr_service)
):
    """
    获取可用的OCR模型列表
    
    Returns:
        可用模型列表
    """
    try:
        models = await ocr_service.get_available_models()
        return {"models": models}
        
    except Exception as e:
        logger.error(f"获取OCR模型列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取模型列表失败")

@router.delete("/task/{task_id}")
async def delete_task_result(
    task_id: str,
    current_user: User = Depends(get_current_user),
    task_service: TaskService = Depends(get_task_service),
    document_service: DocumentService = Depends(get_document_service)
):
    """
    删除OCR任务结果
    
    Args:
        task_id: 任务ID
        current_user: 当前用户
    """
    try:
        # 获取任务
        task = await task_service.get_task(task_id)
        
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")
        
        # 检查权限
        if task.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="无权删除此任务")
        
        # 删除任务
        await task_service.delete_task(task_id)
        
        # 删除相关文档（如果存在）
        document_id = task.metadata.get("document_id")
        if document_id:
            await document_service.delete_document(document_id)
        
        logger.info(f"已删除OCR任务: {task_id}")
        
        return {"message": "任务已删除"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除任务失败: {str(e)}")
        raise HTTPException(status_code=500, detail="删除任务失败")

@router.get("/tasks")
async def list_user_tasks(
    current_user: User = Depends(get_current_user),
    task_service: TaskService = Depends(get_task_service),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    status: Optional[str] = Query(None, description="任务状态过滤")
):
    """
    获取用户的OCR任务列表
    
    Args:
        current_user: 当前用户
        page: 页码
        page_size: 每页数量
        status: 状态过滤
        
    Returns:
        任务列表
    """
    try:
        # 构建过滤条件
        filters = {
            "user_id": current_user.id,
            "task_type": ["ocr_single", "ocr_batch"]
        }
        
        if status:
            filters["status"] = status
        
        # 获取任务列表
        tasks, total = await task_service.get_tasks(
            filters=filters,
            page=page,
            page_size=page_size,
            order_by="created_at",
            order_desc=True
        )
        
        # 构建响应
        task_list = []
        for task in tasks:
            task_info = {
                "task_id": task.id,
                "task_type": task.task_type,
                "status": task.status,
                "filename": task.metadata.get("filename", ""),
                "created_at": task.created_at,
                "completed_at": task.completed_at,
                "processing_time": task.metadata.get("processing_time")
            }
            
            # 添加批次信息
            if task.task_type == "ocr_batch":
                task_info["total_files"] = task.metadata.get("total_files", 0)
            
            task_list.append(task_info)
        
        return {
            "tasks": task_list,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size
        }
        
    except Exception as e:
        logger.error(f"获取任务列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取任务列表失败")

# 后台处理函数
async def process_single_document(
    task_id: str,
    document_id: str,
    file_content: bytes,
    filename: str,
    request_data: OCRUploadRequest,
    ocr_service: OCRService,
    document_service: DocumentService,
    task_service: TaskService
):
    """
    处理单个文档的OCR任务
    """
    start_time = datetime.now()
    
    try:
        # 更新任务状态
        await task_service.update_task_status(task_id, "processing")
        
        # 质量检查
        quality_report = None
        if request_data.quality_check:
            qa = get_quality_assurance()
            quality_report = await qa.assess_quality(
                image_data=file_content,
                filename=filename,
                document_id=document_id
            )
            
            # 如果质量不合格，提前结束
            if not quality_report.is_suitable_for_ocr:
                await task_service.update_task_status(
                    task_id, 
                    "failed",
                    metadata={
                        "error_message": "文档质量不符合OCR要求",
                        "quality_report": quality_report.dict()
                    }
                )
                return
        
        # 创建OCR请求
        ocr_request = OCRRequest(
            image_data=file_content,
            filename=filename,
            extract_tables=request_data.extract_tables,
            extract_images=request_data.extract_images,
            language=request_data.language,
            model_name=request_data.ocr_model,
            preprocessing=request_data.preprocessing
        )
        
        # 执行OCR
        ocr_result = await ocr_service.process_document(ocr_request)
        
        # 计算处理时间
        processing_time = (datetime.now() - start_time).total_seconds()
        
        # 构建结果
        result = {
            "ocr_result": ocr_result.dict(),
            "processing_time": processing_time
        }
        
        if quality_report:
            result["quality_report"] = quality_report.dict()
        
        # 更新任务状态为完成
        await task_service.update_task_status(
            task_id,
            "completed",
            result=result,
            metadata={"processing_time": processing_time}
        )
        
        # 更新文档状态
        await document_service.update_document_status(
            document_id,
            "processed",
            metadata={"ocr_completed": True, "processing_time": processing_time}
        )
        
        logger.info(f"OCR任务完成: {task_id}, 处理时间: {processing_time:.2f}秒")
        
    except Exception as e:
        logger.error(f"OCR任务失败: {task_id}, 错误: {str(e)}")
        
        # 更新任务状态为失败
        await task_service.update_task_status(
            task_id,
            "failed",
            metadata={"error_message": str(e)}
        )
        
        # 更新文档状态
        await document_service.update_document_status(
            document_id,
            "failed",
            metadata={"error_message": str(e)}
        )

async def process_batch_documents(
    batch_id: str,
    files_data: List[tuple],
    request_data: BatchOCRRequest,
    current_user: User,
    ocr_service: OCRService,
    document_service: DocumentService,
    task_service: TaskService
):
    """
    处理批量文档的OCR任务
    """
    try:
        # 更新批次任务状态
        await task_service.update_task_status(batch_id, "processing")
        
        # 创建信号量控制并发
        semaphore = asyncio.Semaphore(request_data.max_concurrent)
        
        # 创建子任务
        sub_tasks = []
        for file, file_content in files_data:
            # 生成子任务ID
            sub_task_id = str(uuid.uuid4())
            
            # 创建文档记录
            document = await document_service.create_document(
                filename=file.filename,
                content_type=file.content_type,
                file_size=len(file_content),
                user_id=current_user.id,
                metadata={
                    "batch_id": batch_id,
                    "sub_task_id": sub_task_id
                }
            )
            
            # 创建子任务记录
            await task_service.create_task(
                task_id=sub_task_id,
                task_type="ocr_single",
                user_id=current_user.id,
                parent_task_id=batch_id,
                metadata={
                    "document_id": document.id,
                    "filename": file.filename,
                    "batch_id": batch_id
                }
            )
            
            # 创建处理任务
            task = asyncio.create_task(
                process_single_document_with_semaphore(
                    semaphore=semaphore,
                    task_id=sub_task_id,
                    document_id=document.id,
                    file_content=file_content,
                    filename=file.filename,
                    request_data=OCRUploadRequest(**request_data.dict()),
                    ocr_service=ocr_service,
                    document_service=document_service,
                    task_service=task_service
                )
            )
            
            sub_tasks.append(task)
        
        # 等待所有子任务完成
        await asyncio.gather(*sub_tasks, return_exceptions=True)
        
        # 更新批次任务状态为完成
        await task_service.update_task_status(batch_id, "completed")
        
        logger.info(f"批量OCR任务完成: {batch_id}")
        
    except Exception as e:
        logger.error(f"批量OCR任务失败: {batch_id}, 错误: {str(e)}")
        
        # 更新批次任务状态为失败
        await task_service.update_task_status(
            batch_id,
            "failed",
            metadata={"error_message": str(e)}
        )

async def process_single_document_with_semaphore(
    semaphore: asyncio.Semaphore,
    task_id: str,
    document_id: str,
    file_content: bytes,
    filename: str,
    request_data: OCRUploadRequest,
    ocr_service: OCRService,
    document_service: DocumentService,
    task_service: TaskService
):
    """
    使用信号量控制并发的单文档处理
    """
    async with semaphore:
        await process_single_document(
            task_id=task_id,
            document_id=document_id,
            file_content=file_content,
            filename=filename,
            request_data=request_data,
            ocr_service=ocr_service,
            document_service=document_service,
            task_service=task_service
        )