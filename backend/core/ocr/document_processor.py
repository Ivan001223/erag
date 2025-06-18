from typing import Dict, List, Optional, Any, Union, Tuple
from pathlib import Path
import asyncio
import io
from datetime import datetime
import hashlib
import json

from PIL import Image, ImageEnhance, ImageFilter
import numpy as np
import cv2
from pdf2image import convert_from_bytes
import fitz  # PyMuPDF

from backend.utils.logger import get_logger
from backend.config.settings import get_settings
from pydantic import BaseModel, Field

logger = get_logger(__name__)
settings = get_settings()

class DocumentMetadata(BaseModel):
    """文档元数据"""
    filename: str
    file_size: int
    file_type: str
    page_count: int
    creation_time: datetime
    processing_time: Optional[float] = None
    checksum: str
    language: str = "zh-cn"
    encoding: Optional[str] = None

class PageInfo(BaseModel):
    """页面信息"""
    page_number: int
    width: int
    height: int
    dpi: int = 300
    rotation: int = 0
    has_text: bool = False
    has_images: bool = False
    has_tables: bool = False
    text_regions: List[Dict[str, Any]] = []
    image_regions: List[Dict[str, Any]] = []
    table_regions: List[Dict[str, Any]] = []

class ProcessingOptions(BaseModel):
    """处理选项"""
    dpi: int = 300
    enhance_image: bool = True
    auto_rotate: bool = True
    remove_noise: bool = True
    extract_text_regions: bool = True
    extract_image_regions: bool = True
    extract_table_regions: bool = True
    language: str = "zh-cn"
    output_format: str = "json"

class DocumentProcessor:
    """文档处理器"""
    
    def __init__(self):
        self.supported_formats = {
            '.pdf': self._process_pdf,
            '.png': self._process_image,
            '.jpg': self._process_image,
            '.jpeg': self._process_image,
            '.tiff': self._process_image,
            '.tif': self._process_image,
            '.bmp': self._process_image,
            '.webp': self._process_image
        }
        self.max_file_size = 100 * 1024 * 1024  # 100MB
        self.max_pages = 500
        
    async def process_document(
        self,
        file_data: bytes,
        filename: str,
        options: ProcessingOptions = None
    ) -> Dict[str, Any]:
        """
        处理文档
        
        Args:
            file_data: 文件数据
            filename: 文件名
            options: 处理选项
            
        Returns:
            处理结果
        """
        start_time = datetime.now()
        
        try:
            if options is None:
                options = ProcessingOptions()
            
            # 验证文件
            self._validate_file(file_data, filename)
            
            # 生成文档元数据
            metadata = self._generate_metadata(file_data, filename, options.language)
            
            # 根据文件类型处理
            file_extension = Path(filename).suffix.lower()
            if file_extension not in self.supported_formats:
                raise ValueError(f"不支持的文件格式: {file_extension}")
            
            processor = self.supported_formats[file_extension]
            pages_data = await processor(file_data, options)
            
            # 计算处理时间
            processing_time = (datetime.now() - start_time).total_seconds()
            metadata.processing_time = processing_time
            
            result = {
                "metadata": metadata.model_dump(),
                "pages": pages_data,
                "processing_time": processing_time,
                "status": "success"
            }
            
            logger.info(f"文档 {filename} 处理完成，耗时 {processing_time:.2f}s")
            return result
            
        except Exception as e:
            logger.error(f"文档处理失败: {str(e)}")
            processing_time = (datetime.now() - start_time).total_seconds()
            return {
                "metadata": None,
                "pages": [],
                "processing_time": processing_time,
                "status": "error",
                "error": str(e)
            }
    
    def _validate_file(self, file_data: bytes, filename: str) -> None:
        """验证文件"""
        # 检查文件大小
        if len(file_data) > self.max_file_size:
            raise ValueError(f"文件大小超过限制 ({self.max_file_size / 1024 / 1024:.1f}MB)")
        
        # 检查文件扩展名
        file_extension = Path(filename).suffix.lower()
        if file_extension not in self.supported_formats:
            raise ValueError(f"不支持的文件格式: {file_extension}")
        
        # 检查文件内容
        if len(file_data) < 100:
            raise ValueError("文件内容太小，可能已损坏")
    
    def _generate_metadata(
        self, 
        file_data: bytes, 
        filename: str, 
        language: str
    ) -> DocumentMetadata:
        """生成文档元数据"""
        # 计算文件校验和
        checksum = hashlib.md5(file_data).hexdigest()
        
        # 获取文件类型
        file_extension = Path(filename).suffix.lower()
        
        # 估算页数（对于图像文件为1）
        page_count = 1
        if file_extension == '.pdf':
            try:
                doc = fitz.open(stream=file_data, filetype="pdf")
                page_count = len(doc)
                doc.close()
            except:
                page_count = 1
        
        return DocumentMetadata(
            filename=filename,
            file_size=len(file_data),
            file_type=file_extension,
            page_count=page_count,
            creation_time=datetime.now(),
            checksum=checksum,
            language=language
        )
    
    async def _process_pdf(self, file_data: bytes, options: ProcessingOptions) -> List[Dict[str, Any]]:
        """处理 PDF 文件"""
        pages_data = []
        
        try:
            # 使用 PyMuPDF 处理 PDF
            doc = fitz.open(stream=file_data, filetype="pdf")
            
            if len(doc) > self.max_pages:
                raise ValueError(f"PDF 页数超过限制 ({self.max_pages} 页)")
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                
                # 获取页面信息
                rect = page.rect
                page_info = PageInfo(
                    page_number=page_num + 1,
                    width=int(rect.width),
                    height=int(rect.height),
                    dpi=options.dpi
                )
                
                # 转换为图像
                mat = fitz.Matrix(options.dpi / 72, options.dpi / 72)
                pix = page.get_pixmap(matrix=mat)
                img_data = pix.tobytes("png")
                
                # 处理图像
                processed_image = await self._process_page_image(
                    img_data, page_info, options
                )
                
                # 提取文本区域（如果需要）
                if options.extract_text_regions:
                    text_regions = self._extract_text_regions(page)
                    page_info.text_regions = text_regions
                    page_info.has_text = len(text_regions) > 0
                
                # 提取图像区域（如果需要）
                if options.extract_image_regions:
                    image_regions = self._extract_image_regions(page)
                    page_info.image_regions = image_regions
                    page_info.has_images = len(image_regions) > 0
                
                # 提取表格区域（如果需要）
                if options.extract_table_regions:
                    table_regions = self._extract_table_regions(page)
                    page_info.table_regions = table_regions
                    page_info.has_tables = len(table_regions) > 0
                
                pages_data.append({
                    "page_info": page_info.dict(),
                    "processed_image": processed_image
                })
            
            doc.close()
            
        except Exception as e:
            logger.error(f"PDF 处理失败: {str(e)}")
            # 尝试使用 pdf2image 作为备选方案
            try:
                images = convert_from_bytes(
                    file_data, 
                    dpi=options.dpi,
                    first_page=1,
                    last_page=min(self.max_pages, 50)  # 限制页数
                )
                
                for i, image in enumerate(images):
                    img_bytes = io.BytesIO()
                    image.save(img_bytes, format='PNG')
                    img_data = img_bytes.getvalue()
                    
                    page_info = PageInfo(
                        page_number=i + 1,
                        width=image.width,
                        height=image.height,
                        dpi=options.dpi
                    )
                    
                    processed_image = await self._process_page_image(
                        img_data, page_info, options
                    )
                    
                    pages_data.append({
                        "page_info": page_info.dict(),
                        "processed_image": processed_image
                    })
                    
            except Exception as e2:
                logger.error(f"PDF 备选处理方案也失败: {str(e2)}")
                raise e
        
        return pages_data
    
    async def _process_image(self, file_data: bytes, options: ProcessingOptions) -> List[Dict[str, Any]]:
        """处理图像文件"""
        try:
            # 打开图像
            image = Image.open(io.BytesIO(file_data))
            
            # 获取页面信息
            page_info = PageInfo(
                page_number=1,
                width=image.width,
                height=image.height,
                dpi=getattr(image, 'info', {}).get('dpi', (options.dpi, options.dpi))[0]
            )
            
            # 处理图像
            processed_image = await self._process_page_image(
                file_data, page_info, options
            )
            
            return [{
                "page_info": page_info.dict(),
                "processed_image": processed_image
            }]
            
        except Exception as e:
            logger.error(f"图像处理失败: {str(e)}")
            raise
    
    async def _process_page_image(
        self, 
        img_data: bytes, 
        page_info: PageInfo, 
        options: ProcessingOptions
    ) -> Dict[str, Any]:
        """处理页面图像"""
        try:
            # 打开图像
            image = Image.open(io.BytesIO(img_data))
            
            # 转换为 RGB（如果需要）
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # 自动旋转（如果需要）
            if options.auto_rotate:
                image = self._auto_rotate_image(image)
            
            # 图像增强（如果需要）
            if options.enhance_image:
                image = self._enhance_image(image)
            
            # 去噪（如果需要）
            if options.remove_noise:
                image = self._remove_noise(image)
            
            # 转换为字节
            output_buffer = io.BytesIO()
            image.save(output_buffer, format='PNG', optimize=True)
            processed_data = output_buffer.getvalue()
            
            # 计算图像质量指标
            quality_metrics = self._calculate_image_quality(image)
            
            return {
                "image_data": processed_data,
                "quality_metrics": quality_metrics,
                "processing_applied": {
                    "auto_rotate": options.auto_rotate,
                    "enhance_image": options.enhance_image,
                    "remove_noise": options.remove_noise
                }
            }
            
        except Exception as e:
            logger.error(f"页面图像处理失败: {str(e)}")
            return {
                "image_data": img_data,
                "quality_metrics": {},
                "processing_applied": {},
                "error": str(e)
            }
    
    def _auto_rotate_image(self, image: Image.Image) -> Image.Image:
        """自动旋转图像"""
        try:
            # 转换为 OpenCV 格式
            cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
            
            # 检测文本方向
            gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
            
            # 使用 Hough 线变换检测主要线条方向
            edges = cv2.Canny(gray, 50, 150, apertureSize=3)
            lines = cv2.HoughLines(edges, 1, np.pi/180, threshold=100)
            
            if lines is not None:
                angles = []
                for rho, theta in lines[:20]:  # 只考虑前20条线
                    angle = theta * 180 / np.pi
                    if angle > 90:
                        angle = angle - 180
                    angles.append(angle)
                
                if angles:
                    # 计算主要角度
                    median_angle = np.median(angles)
                    
                    # 如果角度偏差较大，进行旋转
                    if abs(median_angle) > 1:
                        image = image.rotate(-median_angle, expand=True, fillcolor='white')
            
            return image
            
        except Exception as e:
            logger.warning(f"自动旋转失败: {str(e)}")
            return image
    
    def _enhance_image(self, image: Image.Image) -> Image.Image:
        """增强图像"""
        try:
            # 调整对比度
            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(1.2)
            
            # 调整锐度
            enhancer = ImageEnhance.Sharpness(image)
            image = enhancer.enhance(1.1)
            
            # 调整亮度（如果图像太暗）
            gray = image.convert('L')
            avg_brightness = np.array(gray).mean()
            
            if avg_brightness < 100:
                enhancer = ImageEnhance.Brightness(image)
                brightness_factor = min(1.3, 120 / avg_brightness)
                image = enhancer.enhance(brightness_factor)
            
            return image
            
        except Exception as e:
            logger.warning(f"图像增强失败: {str(e)}")
            return image
    
    def _remove_noise(self, image: Image.Image) -> Image.Image:
        """去除图像噪声"""
        try:
            # 应用轻微的高斯模糊来减少噪声
            image = image.filter(ImageFilter.GaussianBlur(radius=0.5))
            
            # 转换为 OpenCV 格式进行更高级的去噪
            cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
            
            # 应用非局部均值去噪
            denoised = cv2.fastNlMeansDenoisingColored(cv_image, None, 10, 10, 7, 21)
            
            # 转换回 PIL 格式
            image = Image.fromarray(cv2.cvtColor(denoised, cv2.COLOR_BGR2RGB))
            
            return image
            
        except Exception as e:
            logger.warning(f"去噪失败: {str(e)}")
            return image
    
    def _calculate_image_quality(self, image: Image.Image) -> Dict[str, float]:
        """计算图像质量指标"""
        try:
            # 转换为灰度图
            gray = image.convert('L')
            gray_array = np.array(gray)
            
            # 计算清晰度（拉普拉斯方差）
            laplacian_var = cv2.Laplacian(gray_array, cv2.CV_64F).var()
            sharpness = min(1.0, laplacian_var / 1000)  # 归一化到 0-1
            
            # 计算对比度
            contrast = gray_array.std() / 255.0
            
            # 计算亮度
            brightness = gray_array.mean() / 255.0
            
            # 计算整体质量分数
            quality_score = (sharpness * 0.4 + contrast * 0.3 + 
                           min(1.0, abs(0.5 - brightness) * 2) * 0.3)
            
            return {
                "sharpness": round(sharpness, 3),
                "contrast": round(contrast, 3),
                "brightness": round(brightness, 3),
                "overall_quality": round(quality_score, 3)
            }
            
        except Exception as e:
            logger.warning(f"质量计算失败: {str(e)}")
            return {}
    
    def _extract_text_regions(self, page) -> List[Dict[str, Any]]:
        """提取文本区域"""
        try:
            text_regions = []
            blocks = page.get_text("dict")["blocks"]
            
            for block in blocks:
                if "lines" in block:
                    bbox = block["bbox"]
                    text_content = ""
                    
                    for line in block["lines"]:
                        for span in line["spans"]:
                            text_content += span["text"]
                    
                    if text_content.strip():
                        text_regions.append({
                            "bbox": {
                                "x": int(bbox[0]),
                                "y": int(bbox[1]),
                                "width": int(bbox[2] - bbox[0]),
                                "height": int(bbox[3] - bbox[1])
                            },
                            "text": text_content.strip(),
                            "confidence": 1.0  # PyMuPDF 提取的文本置信度设为1
                        })
            
            return text_regions
            
        except Exception as e:
            logger.warning(f"文本区域提取失败: {str(e)}")
            return []
    
    def _extract_image_regions(self, page) -> List[Dict[str, Any]]:
        """提取图像区域"""
        try:
            image_regions = []
            image_list = page.get_images()
            
            for img_index, img in enumerate(image_list):
                # 获取图像信息
                xref = img[0]
                bbox = page.get_image_bbox(img)
                
                if bbox:
                    image_regions.append({
                        "bbox": {
                            "x": int(bbox.x0),
                            "y": int(bbox.y0),
                            "width": int(bbox.x1 - bbox.x0),
                            "height": int(bbox.y1 - bbox.y0)
                        },
                        "image_index": img_index,
                        "xref": xref
                    })
            
            return image_regions
            
        except Exception as e:
            logger.warning(f"图像区域提取失败: {str(e)}")
            return []
    
    def _extract_table_regions(self, page) -> List[Dict[str, Any]]:
        """提取表格区域（简单实现）"""
        try:
            # 这是一个简化的表格检测实现
            # 在实际应用中，可能需要更复杂的表格检测算法
            table_regions = []
            
            # 获取页面中的所有线条
            drawings = page.get_drawings()
            
            # 简单的启发式方法：查找矩形网格
            horizontal_lines = []
            vertical_lines = []
            
            for drawing in drawings:
                for item in drawing["items"]:
                    if item[0] == "l":  # 线条
                        p1, p2 = item[1], item[2]
                        if abs(p1.y - p2.y) < 2:  # 水平线
                            horizontal_lines.append((p1.x, p2.x, p1.y))
                        elif abs(p1.x - p2.x) < 2:  # 垂直线
                            vertical_lines.append((p1.y, p2.y, p1.x))
            
            # 如果找到足够的线条，可能存在表格
            if len(horizontal_lines) >= 3 and len(vertical_lines) >= 3:
                # 计算可能的表格边界
                min_x = min(line[2] for line in vertical_lines)
                max_x = max(line[2] for line in vertical_lines)
                min_y = min(line[2] for line in horizontal_lines)
                max_y = max(line[2] for line in horizontal_lines)
                
                table_regions.append({
                    "bbox": {
                        "x": int(min_x),
                        "y": int(min_y),
                        "width": int(max_x - min_x),
                        "height": int(max_y - min_y)
                    },
                    "confidence": 0.7,  # 简单检测的置信度较低
                    "rows": len(horizontal_lines) - 1,
                    "columns": len(vertical_lines) - 1
                })
            
            return table_regions
            
        except Exception as e:
            logger.warning(f"表格区域提取失败: {str(e)}")
            return []

# 全局文档处理器实例
_document_processor = None

def get_document_processor() -> DocumentProcessor:
    """获取文档处理器实例"""
    global _document_processor
    if _document_processor is None:
        _document_processor = DocumentProcessor()
    return _document_processor