from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import asyncio
import aiofiles
import os
import uuid
from datetime import datetime
import json
from loguru import logger
import cv2
import numpy as np
from PIL import Image
import io

# 配置日志
logger.add("logs/ocr_service.log", rotation="500 MB", level="INFO")

app = FastAPI(
    title="OCR Service",
    description="企业知识库 OCR 文档处理服务",
    version="1.0.0"
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 数据模型
class OCRRequest(BaseModel):
    """OCR 请求模型"""
    task_id: Optional[str] = None
    language: str = "zh-cn"
    extract_tables: bool = True
    quality_check: bool = True
    output_format: str = "json"  # json, markdown, text

class OCRResult(BaseModel):
    """OCR 结果模型"""
    task_id: str
    status: str  # processing, completed, failed
    text_content: Optional[str] = None
    tables: Optional[List[Dict[str, Any]]] = None
    confidence_score: Optional[float] = None
    processing_time: Optional[float] = None
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class BatchOCRRequest(BaseModel):
    """批量 OCR 请求模型"""
    batch_id: Optional[str] = None
    language: str = "zh-cn"
    extract_tables: bool = True
    quality_check: bool = True
    output_format: str = "json"

# 全局变量
task_results: Dict[str, OCRResult] = {}
batch_results: Dict[str, Dict[str, Any]] = {}

# OCR 处理类
class OCRProcessor:
    """OCR 处理器"""
    
    def __init__(self):
        self.model_path = "onnx_models/"
        self.supported_formats = [".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".bmp"]
        
    async def process_image(self, image_data: bytes, language: str = "zh-cn") -> Dict[str, Any]:
        """处理单个图像"""
        try:
            # 将字节数据转换为图像
            image = Image.open(io.BytesIO(image_data))
            
            # 转换为 OpenCV 格式
            opencv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
            
            # 模拟 OCR 处理（实际应该使用 OnnxOCR）
            # TODO：调用OnnxOCR模型进行文本识别
            # 这里返回模拟结果
            text_content = "这是模拟的OCR文本识别结果。在实际实现中，这里会调用OnnxOCR模型进行文本识别。"
            
            confidence_score = 0.95
            
            return {
                "text_content": text_content,
                "confidence_score": confidence_score,
                "image_size": image.size,
                "format": image.format
            }
            
        except Exception as e:
            logger.error(f"图像处理失败: {str(e)}")
            raise HTTPException(status_code=500, detail=f"图像处理失败: {str(e)}")
    
    async def extract_tables(self, image_data: bytes) -> List[Dict[str, Any]]:
        """提取表格"""
        try:
            # 模拟表格提取
            tables = [
                {
                    "table_id": 1,
                    "rows": 3,
                    "columns": 4,
                    "data": [
                        ["姓名", "年龄", "部门", "职位"],
                        ["张三", "28", "技术部", "工程师"],
                        ["李四", "32", "产品部", "产品经理"]
                    ],
                    "confidence": 0.92
                }
            ]
            return tables
        except Exception as e:
            logger.error(f"表格提取失败: {str(e)}")
            return []
    
    def quality_assessment(self, image_data: bytes, text_content: str) -> Dict[str, Any]:
        """质量评估"""
        try:
            # 模拟质量评估
            quality_metrics = {
                "text_clarity": 0.9,
                "image_quality": 0.85,
                "text_completeness": 0.95,
                "overall_score": 0.9
            }
            return quality_metrics
        except Exception as e:
            logger.error(f"质量评估失败: {str(e)}")
            return {}

# 初始化 OCR 处理器
ocr_processor = OCRProcessor()

# API 端点
@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.post("/ocr/process", response_model=OCRResult)
async def process_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    language: str = "zh-cn",
    extract_tables: bool = True,
    quality_check: bool = True,
    output_format: str = "json"
):
    """处理单个文档"""
    task_id = str(uuid.uuid4())
    
    # 验证文件格式
    file_extension = os.path.splitext(file.filename)[1].lower()
    if file_extension not in ocr_processor.supported_formats:
        raise HTTPException(
            status_code=400, 
            detail=f"不支持的文件格式: {file_extension}"
        )
    
    # 创建初始任务结果
    task_results[task_id] = OCRResult(
        task_id=task_id,
        status="processing"
    )
    
    # 后台处理
    background_tasks.add_task(
        process_document_background,
        task_id,
        file,
        language,
        extract_tables,
        quality_check,
        output_format
    )
    
    return task_results[task_id]

async def process_document_background(
    task_id: str,
    file: UploadFile,
    language: str,
    extract_tables: bool,
    quality_check: bool,
    output_format: str
):
    """后台处理文档"""
    start_time = datetime.now()
    
    try:
        # 读取文件内容
        file_content = await file.read()
        
        # OCR 处理
        ocr_result = await ocr_processor.process_image(file_content, language)
        
        # 表格提取
        tables = []
        if extract_tables:
            tables = await ocr_processor.extract_tables(file_content)
        
        # 质量评估
        quality_metrics = {}
        if quality_check:
            quality_metrics = ocr_processor.quality_assessment(
                file_content, 
                ocr_result["text_content"]
            )
        
        # 计算处理时间
        processing_time = (datetime.now() - start_time).total_seconds()
        
        # 更新任务结果
        task_results[task_id] = OCRResult(
            task_id=task_id,
            status="completed",
            text_content=ocr_result["text_content"],
            tables=tables,
            confidence_score=ocr_result["confidence_score"],
            processing_time=processing_time,
            metadata={
                "filename": file.filename,
                "file_size": len(file_content),
                "image_info": {
                    "size": ocr_result.get("image_size"),
                    "format": ocr_result.get("format")
                },
                "quality_metrics": quality_metrics,
                "language": language,
                "output_format": output_format
            }
        )
        
        logger.info(f"任务 {task_id} 处理完成，耗时 {processing_time:.2f} 秒")
        
    except Exception as e:
        logger.error(f"任务 {task_id} 处理失败: {str(e)}")
        task_results[task_id] = OCRResult(
            task_id=task_id,
            status="failed",
            error_message=str(e),
            processing_time=(datetime.now() - start_time).total_seconds()
        )

@app.post("/ocr/batch")
async def process_batch(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    language: str = "zh-cn",
    extract_tables: bool = True,
    quality_check: bool = True,
    output_format: str = "json"
):
    """批量处理文档"""
    batch_id = str(uuid.uuid4())
    
    # 验证文件数量
    if len(files) > 50:  # 限制批量处理文件数量
        raise HTTPException(status_code=400, detail="批量处理文件数量不能超过50个")
    
    # 创建批量任务
    task_ids = []
    for file in files:
        task_id = str(uuid.uuid4())
        task_ids.append(task_id)
        
        # 验证文件格式
        file_extension = os.path.splitext(file.filename)[1].lower()
        if file_extension not in ocr_processor.supported_formats:
            task_results[task_id] = OCRResult(
                task_id=task_id,
                status="failed",
                error_message=f"不支持的文件格式: {file_extension}"
            )
            continue
        
        # 创建初始任务结果
        task_results[task_id] = OCRResult(
            task_id=task_id,
            status="processing"
        )
        
        # 后台处理
        background_tasks.add_task(
            process_document_background,
            task_id,
            file,
            language,
            extract_tables,
            quality_check,
            output_format
        )
    
    # 保存批量任务信息
    batch_results[batch_id] = {
        "batch_id": batch_id,
        "task_ids": task_ids,
        "total_files": len(files),
        "created_at": datetime.now().isoformat(),
        "status": "processing"
    }
    
    return {
        "batch_id": batch_id,
        "task_ids": task_ids,
        "total_files": len(files),
        "message": "批量处理已开始"
    }

@app.get("/ocr/status/{task_id}", response_model=OCRResult)
async def get_task_status(task_id: str):
    """获取任务状态"""
    if task_id not in task_results:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    return task_results[task_id]

@app.get("/ocr/batch/{batch_id}")
async def get_batch_status(batch_id: str):
    """获取批量任务状态"""
    if batch_id not in batch_results:
        raise HTTPException(status_code=404, detail="批量任务不存在")
    
    batch_info = batch_results[batch_id]
    task_ids = batch_info["task_ids"]
    
    # 统计任务状态
    completed = sum(1 for tid in task_ids if task_results.get(tid, {}).status == "completed")
    failed = sum(1 for tid in task_ids if task_results.get(tid, {}).status == "failed")
    processing = len(task_ids) - completed - failed
    
    # 更新批量任务状态
    if processing == 0:
        batch_results[batch_id]["status"] = "completed" if failed == 0 else "partial_completed"
    
    return {
        "batch_id": batch_id,
        "total_files": batch_info["total_files"],
        "completed": completed,
        "failed": failed,
        "processing": processing,
        "status": batch_results[batch_id]["status"],
        "task_results": [task_results.get(tid) for tid in task_ids]
    }

@app.get("/ocr/models")
async def list_models():
    """列出可用的 OCR 模型"""
    return {
        "models": [
            {
                "name": "onnx-ocr-zh",
                "language": "zh-cn",
                "description": "中文 OCR 模型",
                "version": "1.0.0"
            },
            {
                "name": "onnx-ocr-en",
                "language": "en",
                "description": "英文 OCR 模型",
                "version": "1.0.0"
            }
        ]
    }

@app.delete("/ocr/tasks/{task_id}")
async def delete_task(task_id: str):
    """删除任务结果"""
    if task_id not in task_results:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    del task_results[task_id]
    return {"message": "任务已删除"}

@app.get("/metrics")
async def get_metrics():
    """获取服务指标"""
    total_tasks = len(task_results)
    completed_tasks = sum(1 for result in task_results.values() if result.status == "completed")
    failed_tasks = sum(1 for result in task_results.values() if result.status == "failed")
    processing_tasks = total_tasks - completed_tasks - failed_tasks
    
    return {
        "total_tasks": total_tasks,
        "completed_tasks": completed_tasks,
        "failed_tasks": failed_tasks,
        "processing_tasks": processing_tasks,
        "success_rate": completed_tasks / total_tasks if total_tasks > 0 else 0
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)