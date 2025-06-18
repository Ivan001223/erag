from typing import Dict, List, Optional, Any, Union
from datetime import datetime
import asyncio
import aiohttp
import json
from pathlib import Path
import io
from PIL import Image
import base64

from backend.utils.logger import get_logger
from backend.config.settings import get_settings
from backend.models.base import BaseModel
from pydantic import BaseModel as PydanticBaseModel, Field

logger = get_logger(__name__)
settings = get_settings()

class OCRRequest(PydanticBaseModel):
    """OCR 请求模型"""
    file_data: Union[str, bytes]  # base64 编码的文件数据或字节数据
    filename: str
    language: str = "zh-cn"
    extract_tables: bool = True
    quality_check: bool = True
    output_format: str = "json"
    task_id: Optional[str] = None

class OCRResponse(PydanticBaseModel):
    """OCR 响应模型"""
    task_id: str
    status: str  # processing, completed, failed
    text_content: Optional[str] = None
    tables: Optional[List[Dict[str, Any]]] = None
    confidence_score: Optional[float] = None
    processing_time: Optional[float] = None
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class TableData(PydanticBaseModel):
    """表格数据模型"""
    table_id: int
    rows: int
    columns: int
    data: List[List[str]]
    confidence: float
    position: Optional[Dict[str, int]] = None  # x, y, width, height

class QualityMetrics(PydanticBaseModel):
    """质量评估指标"""
    text_clarity: float = Field(ge=0, le=1)
    image_quality: float = Field(ge=0, le=1)
    text_completeness: float = Field(ge=0, le=1)
    overall_score: float = Field(ge=0, le=1)
    issues: List[str] = []
    recommendations: List[str] = []

class OCRService:
    """OCR 服务类"""
    
    def __init__(self):
        self.ocr_service_url = getattr(settings, 'OCR_SERVICE_URL', 'http://localhost:8002')
        self.timeout = 300  # 5分钟超时
        self.max_retries = 3
        self.supported_formats = [".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".webp"]
        
    async def process_document(
        self, 
        file_data: Union[str, bytes], 
        filename: str,
        language: str = "zh-cn",
        extract_tables: bool = True,
        quality_check: bool = True,
        output_format: str = "json"
    ) -> OCRResponse:
        """
        处理单个文档的 OCR
        
        Args:
            file_data: 文件数据（base64 字符串或字节数据）
            filename: 文件名
            language: 识别语言
            extract_tables: 是否提取表格
            quality_check: 是否进行质量检查
            output_format: 输出格式
            
        Returns:
            OCR 处理结果
        """
        try:
            # 验证文件格式
            file_extension = Path(filename).suffix.lower()
            if file_extension not in self.supported_formats:
                raise ValueError(f"不支持的文件格式: {file_extension}")
            
            # 准备请求数据
            if isinstance(file_data, str):
                # 如果是 base64 字符串，解码为字节
                file_bytes = base64.b64decode(file_data)
            else:
                file_bytes = file_data
            
            # 调用 OCR 服务
            result = await self._call_ocr_service(
                file_bytes=file_bytes,
                filename=filename,
                language=language,
                extract_tables=extract_tables,
                quality_check=quality_check,
                output_format=output_format
            )
            
            logger.info(f"文档 {filename} OCR 处理完成")
            return result
            
        except Exception as e:
            logger.error(f"OCR 处理失败: {str(e)}")
            raise
    
    async def process_batch(
        self,
        files: List[Dict[str, Any]],
        language: str = "zh-cn",
        extract_tables: bool = True,
        quality_check: bool = True,
        output_format: str = "json"
    ) -> Dict[str, Any]:
        """
        批量处理文档
        
        Args:
            files: 文件列表，每个文件包含 file_data 和 filename
            language: 识别语言
            extract_tables: 是否提取表格
            quality_check: 是否进行质量检查
            output_format: 输出格式
            
        Returns:
            批量处理结果
        """
        try:
            # 验证文件数量
            if len(files) > 50:
                raise ValueError("批量处理文件数量不能超过50个")
            
            # 准备文件数据
            file_data_list = []
            for file_info in files:
                file_data = file_info["file_data"]
                filename = file_info["filename"]
                
                # 验证文件格式
                file_extension = Path(filename).suffix.lower()
                if file_extension not in self.supported_formats:
                    logger.warning(f"跳过不支持的文件格式: {filename}")
                    continue
                
                if isinstance(file_data, str):
                    file_bytes = base64.b64decode(file_data)
                else:
                    file_bytes = file_data
                
                file_data_list.append({
                    "file_bytes": file_bytes,
                    "filename": filename
                })
            
            # 调用批量 OCR 服务
            result = await self._call_batch_ocr_service(
                files=file_data_list,
                language=language,
                extract_tables=extract_tables,
                quality_check=quality_check,
                output_format=output_format
            )
            
            logger.info(f"批量处理 {len(files)} 个文件完成")
            return result
            
        except Exception as e:
            logger.error(f"批量 OCR 处理失败: {str(e)}")
            raise
    
    async def get_task_status(self, task_id: str) -> OCRResponse:
        """
        获取任务状态
        
        Args:
            task_id: 任务ID
            
        Returns:
            任务状态
        """
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.ocr_service_url}/ocr/status/{task_id}"
                
                async with session.get(url, timeout=self.timeout) as response:
                    if response.status == 200:
                        data = await response.json()
                        return OCRResponse(**data)
                    elif response.status == 404:
                        raise ValueError(f"任务 {task_id} 不存在")
                    else:
                        raise Exception(f"获取任务状态失败: {response.status}")
                        
        except Exception as e:
            logger.error(f"获取任务状态失败: {str(e)}")
            raise
    
    async def _call_ocr_service(
        self,
        file_bytes: bytes,
        filename: str,
        language: str,
        extract_tables: bool,
        quality_check: bool,
        output_format: str
    ) -> OCRResponse:
        """调用 OCR 服务"""
        for attempt in range(self.max_retries):
            try:
                async with aiohttp.ClientSession() as session:
                    # 准备表单数据
                    data = aiohttp.FormData()
                    data.add_field('file', file_bytes, filename=filename)
                    data.add_field('language', language)
                    data.add_field('extract_tables', str(extract_tables).lower())
                    data.add_field('quality_check', str(quality_check).lower())
                    data.add_field('output_format', output_format)
                    
                    url = f"{self.ocr_service_url}/ocr/process"
                    
                    async with session.post(
                        url, 
                        data=data, 
                        timeout=self.timeout
                    ) as response:
                        if response.status == 200:
                            result_data = await response.json()
                            return OCRResponse(**result_data)
                        else:
                            error_text = await response.text()
                            raise Exception(f"OCR 服务错误: {response.status} - {error_text}")
                            
            except asyncio.TimeoutError:
                logger.warning(f"OCR 服务超时，重试 {attempt + 1}/{self.max_retries}")
                if attempt == self.max_retries - 1:
                    raise Exception("OCR 服务超时")
                await asyncio.sleep(2 ** attempt)  # 指数退避
                
            except Exception as e:
                if attempt == self.max_retries - 1:
                    raise
                logger.warning(f"OCR 服务调用失败，重试 {attempt + 1}/{self.max_retries}: {str(e)}")
                await asyncio.sleep(2 ** attempt)
    
    async def _call_batch_ocr_service(
        self,
        files: List[Dict[str, Any]],
        language: str,
        extract_tables: bool,
        quality_check: bool,
        output_format: str
    ) -> Dict[str, Any]:
        """调用批量 OCR 服务"""
        for attempt in range(self.max_retries):
            try:
                async with aiohttp.ClientSession() as session:
                    # 准备表单数据
                    data = aiohttp.FormData()
                    
                    for file_info in files:
                        data.add_field(
                            'files', 
                            file_info["file_bytes"], 
                            filename=file_info["filename"]
                        )
                    
                    data.add_field('language', language)
                    data.add_field('extract_tables', str(extract_tables).lower())
                    data.add_field('quality_check', str(quality_check).lower())
                    data.add_field('output_format', output_format)
                    
                    url = f"{self.ocr_service_url}/ocr/batch"
                    
                    async with session.post(
                        url, 
                        data=data, 
                        timeout=self.timeout
                    ) as response:
                        if response.status == 200:
                            return await response.json()
                        else:
                            error_text = await response.text()
                            raise Exception(f"批量 OCR 服务错误: {response.status} - {error_text}")
                            
            except asyncio.TimeoutError:
                logger.warning(f"批量 OCR 服务超时，重试 {attempt + 1}/{self.max_retries}")
                if attempt == self.max_retries - 1:
                    raise Exception("批量 OCR 服务超时")
                await asyncio.sleep(2 ** attempt)
                
            except Exception as e:
                if attempt == self.max_retries - 1:
                    raise
                logger.warning(f"批量 OCR 服务调用失败，重试 {attempt + 1}/{self.max_retries}: {str(e)}")
                await asyncio.sleep(2 ** attempt)
    
    def validate_image(self, file_data: bytes) -> Dict[str, Any]:
        """
        验证图像文件
        
        Args:
            file_data: 图像文件数据
            
        Returns:
            验证结果和图像信息
        """
        try:
            image = Image.open(io.BytesIO(file_data))
            
            # 检查图像尺寸
            width, height = image.size
            if width < 100 or height < 100:
                return {
                    "valid": False,
                    "error": "图像尺寸太小，最小尺寸为 100x100 像素"
                }
            
            # 检查图像格式
            if image.format not in ['JPEG', 'PNG', 'TIFF', 'BMP', 'WEBP']:
                return {
                    "valid": False,
                    "error": f"不支持的图像格式: {image.format}"
                }
            
            # 检查文件大小（最大 50MB）
            if len(file_data) > 50 * 1024 * 1024:
                return {
                    "valid": False,
                    "error": "文件大小超过 50MB 限制"
                }
            
            return {
                "valid": True,
                "image_info": {
                    "width": width,
                    "height": height,
                    "format": image.format,
                    "mode": image.mode,
                    "size_bytes": len(file_data)
                }
            }
            
        except Exception as e:
            return {
                "valid": False,
                "error": f"图像验证失败: {str(e)}"
            }
    
    async def get_service_health(self) -> Dict[str, Any]:
        """
        检查 OCR 服务健康状态
        
        Returns:
            服务健康状态
        """
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.ocr_service_url}/health"
                
                async with session.get(url, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        return {
                            "healthy": True,
                            "service_info": data
                        }
                    else:
                        return {
                            "healthy": False,
                            "error": f"服务返回状态码: {response.status}"
                        }
                        
        except Exception as e:
            return {
                "healthy": False,
                "error": f"无法连接到 OCR 服务: {str(e)}"
            }
    
    async def get_service_metrics(self) -> Dict[str, Any]:
        """
        获取 OCR 服务指标
        
        Returns:
            服务指标
        """
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.ocr_service_url}/metrics"
                
                async with session.get(url, timeout=10) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        raise Exception(f"获取指标失败: {response.status}")
                        
        except Exception as e:
            logger.error(f"获取 OCR 服务指标失败: {str(e)}")
            return {}

# 全局 OCR 服务实例
_ocr_service = None

def get_ocr_service() -> OCRService:
    """获取 OCR 服务实例"""
    global _ocr_service
    if _ocr_service is None:
        _ocr_service = OCRService()
    return _ocr_service