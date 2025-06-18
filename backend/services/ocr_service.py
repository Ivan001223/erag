from typing import List, Dict, Any, Optional, Tuple, Union
from datetime import datetime
import asyncio
import json
import base64
import io
from enum import Enum
from pathlib import Path

from PIL import Image
import numpy as np

from backend.connectors.redis_client import RedisClient
from backend.connectors.minio_client import MinIOClient
from backend.models.base import BaseModel
from backend.utils.logger import get_logger

logger = get_logger(__name__)


class OCREngine(str, Enum):
    """OCR引擎枚举"""
    PADDLE_OCR = "paddle_ocr"
    TESSERACT = "tesseract"
    EASYOCR = "easyocr"
    ONNX_OCR = "onnx_ocr"
    AZURE_VISION = "azure_vision"
    GOOGLE_VISION = "google_vision"
    AWS_TEXTRACT = "aws_textract"


class DocumentType(str, Enum):
    """文档类型枚举"""
    IMAGE = "image"
    PDF = "pdf"
    WORD = "word"
    EXCEL = "excel"
    POWERPOINT = "powerpoint"
    TEXT = "text"


class OCRQuality(str, Enum):
    """OCR质量等级"""
    LOW = "low"        # 快速处理，准确率较低
    MEDIUM = "medium"  # 平衡速度和准确率
    HIGH = "high"      # 高准确率，处理较慢
    ULTRA = "ultra"    # 最高准确率，最慢


class TextBlock(BaseModel):
    """文本块模型"""
    text: str
    confidence: float
    bbox: List[int]  # [x1, y1, x2, y2]
    page_num: int = 0
    block_type: str = "text"  # text, table, image, header, footer
    font_size: Optional[float] = None
    font_family: Optional[str] = None
    is_bold: bool = False
    is_italic: bool = False
    text_color: Optional[str] = None
    background_color: Optional[str] = None
    rotation_angle: float = 0.0
    language: Optional[str] = None


class TableCell(BaseModel):
    """表格单元格模型"""
    text: str
    confidence: float
    row: int
    col: int
    rowspan: int = 1
    colspan: int = 1
    bbox: List[int]
    is_header: bool = False


class Table(BaseModel):
    """表格模型"""
    cells: List[TableCell]
    rows: int
    cols: int
    bbox: List[int]
    page_num: int = 0
    confidence: float
    table_type: str = "standard"  # standard, form, invoice


class OCRResult(BaseModel):
    """OCR结果模型"""
    id: str
    document_id: str
    engine: OCREngine
    quality: OCRQuality
    text_blocks: List[TextBlock]
    tables: List[Table] = []
    full_text: str
    page_count: int
    confidence: float
    processing_time_ms: int
    language: Optional[str] = None
    metadata: Dict[str, Any] = {}
    created_at: datetime
    file_path: Optional[str] = None
    file_size: int = 0
    image_dimensions: Optional[Tuple[int, int]] = None


class OCRConfig(BaseModel):
    """OCR配置模型"""
    engine: OCREngine
    quality: OCRQuality = OCRQuality.MEDIUM
    languages: List[str] = ["zh", "en"]  # 支持的语言
    detect_tables: bool = True
    detect_layout: bool = True
    enhance_image: bool = True
    remove_noise: bool = True
    correct_skew: bool = True
    merge_lines: bool = True
    min_confidence: float = 0.5
    max_image_size: int = 4096  # 最大图像尺寸
    dpi: int = 300  # 图像DPI
    timeout_seconds: int = 300
    parallel_pages: int = 4  # 并行处理页数


class OCRService:
    """OCR服务"""
    
    def __init__(self, redis_client: RedisClient, minio_client: MinIOClient):
        self.redis = redis_client
        self.minio = minio_client
        self.engines: Dict[OCREngine, Any] = {}
        self.default_config = OCRConfig(engine=OCREngine.PADDLE_OCR)
        
    async def initialize(self):
        """初始化OCR引擎"""
        try:
            # 初始化各种OCR引擎
            await self._initialize_paddle_ocr()
            await self._initialize_tesseract()
            await self._initialize_easyocr()
            await self._initialize_onnx_ocr()
            
            logger.info("OCR engines initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize OCR engines: {str(e)}")
            raise
    
    async def process_document(
        self,
        document_id: str,
        file_path: str,
        config: Optional[OCRConfig] = None
    ) -> OCRResult:
        """处理文档OCR"""
        start_time = datetime.now()
        config = config or self.default_config
        
        try:
            # 检查缓存
            cache_key = f"ocr:{document_id}:{config.engine.value}:{config.quality.value}"
            cached_result = await self.redis.get(cache_key)
            
            if cached_result:
                logger.info(f"OCR result found in cache for document {document_id}")
                return OCRResult(**json.loads(cached_result))
            
            # 下载文件
            file_data = await self._download_file(file_path)
            
            # 检测文档类型
            doc_type = self._detect_document_type(file_path, file_data)
            
            # 预处理文档
            images = await self._preprocess_document(file_data, doc_type, config)
            
            # 执行OCR
            result = await self._perform_ocr(images, config, document_id)
            
            # 后处理
            result = await self._post_process_result(result, config)
            
            # 计算处理时间
            end_time = datetime.now()
            result.processing_time_ms = int((end_time - start_time).total_seconds() * 1000)
            result.created_at = end_time
            
            # 缓存结果
            await self.redis.setex(
                cache_key,
                3600,  # 1小时缓存
                result.json()
            )
            
            logger.info(f"OCR completed for document {document_id} in {result.processing_time_ms}ms")
            return result
            
        except Exception as e:
            logger.error(f"OCR processing failed for document {document_id}: {str(e)}")
            raise
    
    async def process_image(
        self,
        image_data: bytes,
        config: Optional[OCRConfig] = None
    ) -> OCRResult:
        """处理单张图像OCR"""
        start_time = datetime.now()
        config = config or self.default_config
        
        try:
            # 生成临时ID
            temp_id = f"temp_{int(datetime.now().timestamp() * 1000)}"
            
            # 预处理图像
            image = Image.open(io.BytesIO(image_data))
            processed_image = await self._preprocess_image(image, config)
            
            # 执行OCR
            result = await self._perform_ocr([processed_image], config, temp_id)
            
            # 后处理
            result = await self._post_process_result(result, config)
            
            # 计算处理时间
            end_time = datetime.now()
            result.processing_time_ms = int((end_time - start_time).total_seconds() * 1000)
            result.created_at = end_time
            result.image_dimensions = image.size
            
            return result
            
        except Exception as e:
            logger.error(f"Image OCR processing failed: {str(e)}")
            raise
    
    async def extract_tables(
        self,
        document_id: str,
        file_path: str,
        config: Optional[OCRConfig] = None
    ) -> List[Table]:
        """专门提取表格"""
        try:
            config = config or self.default_config
            config.detect_tables = True
            
            result = await self.process_document(document_id, file_path, config)
            return result.tables
            
        except Exception as e:
            logger.error(f"Table extraction failed: {str(e)}")
            raise
    
    async def get_supported_languages(self, engine: OCREngine) -> List[str]:
        """获取支持的语言列表"""
        language_map = {
            OCREngine.PADDLE_OCR: ["zh", "en", "fr", "de", "ja", "ko"],
            OCREngine.TESSERACT: ["zh", "en", "fr", "de", "ja", "ko", "ar", "hi"],
            OCREngine.EASYOCR: ["zh", "en", "fr", "de", "ja", "ko", "th", "vi"],
            OCREngine.ONNX_OCR: ["zh", "en"],
            OCREngine.AZURE_VISION: ["zh", "en", "fr", "de", "ja", "ko", "ar", "hi"],
            OCREngine.GOOGLE_VISION: ["zh", "en", "fr", "de", "ja", "ko", "ar", "hi"],
            OCREngine.AWS_TEXTRACT: ["zh", "en", "fr", "de", "ja", "ko"]
        }
        
        return language_map.get(engine, ["en"])
    
    async def get_engine_status(self) -> Dict[str, Dict[str, Any]]:
        """获取引擎状态"""
        status = {}
        
        for engine in OCREngine:
            try:
                is_available = engine in self.engines
                health_check = await self._health_check_engine(engine) if is_available else False
                
                status[engine.value] = {
                    "available": is_available,
                    "healthy": health_check,
                    "supported_languages": await self.get_supported_languages(engine),
                    "last_check": datetime.now().isoformat()
                }
                
            except Exception as e:
                status[engine.value] = {
                    "available": False,
                    "healthy": False,
                    "error": str(e),
                    "last_check": datetime.now().isoformat()
                }
                
        return status
    
    async def _download_file(self, file_path: str) -> bytes:
        """从MinIO下载文件"""
        try:
            bucket_name = "documents"
            response = await self.minio.get_object(bucket_name, file_path)
            return await response.read()
            
        except Exception as e:
            logger.error(f"Failed to download file {file_path}: {str(e)}")
            raise
    
    def _detect_document_type(self, file_path: str, file_data: bytes) -> DocumentType:
        """检测文档类型"""
        file_extension = Path(file_path).suffix.lower()
        
        if file_extension in [".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".webp"]:
            return DocumentType.IMAGE
        elif file_extension == ".pdf":
            return DocumentType.PDF
        elif file_extension in [".doc", ".docx"]:
            return DocumentType.WORD
        elif file_extension in [".xls", ".xlsx"]:
            return DocumentType.EXCEL
        elif file_extension in [".ppt", ".pptx"]:
            return DocumentType.POWERPOINT
        elif file_extension == ".txt":
            return DocumentType.TEXT
        else:
            # 尝试通过文件头检测
            if file_data.startswith(b'%PDF'):
                return DocumentType.PDF
            elif file_data.startswith(b'\x89PNG'):
                return DocumentType.IMAGE
            elif file_data.startswith(b'\xff\xd8\xff'):
                return DocumentType.IMAGE
            else:
                return DocumentType.IMAGE  # 默认作为图像处理
    
    async def _preprocess_document(
        self,
        file_data: bytes,
        doc_type: DocumentType,
        config: OCRConfig
    ) -> List[Image.Image]:
        """预处理文档"""
        try:
            if doc_type == DocumentType.IMAGE:
                image = Image.open(io.BytesIO(file_data))
                processed_image = await self._preprocess_image(image, config)
                return [processed_image]
                
            elif doc_type == DocumentType.PDF:
                return await self._convert_pdf_to_images(file_data, config)
                
            elif doc_type in [DocumentType.WORD, DocumentType.EXCEL, DocumentType.POWERPOINT]:
                return await self._convert_office_to_images(file_data, doc_type, config)
                
            elif doc_type == DocumentType.TEXT:
                # 文本文件直接返回空图像列表，后续特殊处理
                return []
                
            else:
                raise ValueError(f"Unsupported document type: {doc_type}")
                
        except Exception as e:
            logger.error(f"Document preprocessing failed: {str(e)}")
            raise
    
    async def _preprocess_image(self, image: Image.Image, config: OCRConfig) -> Image.Image:
        """预处理图像"""
        try:
            # 转换为RGB模式
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # 调整图像大小
            if max(image.size) > config.max_image_size:
                ratio = config.max_image_size / max(image.size)
                new_size = (int(image.width * ratio), int(image.height * ratio))
                image = image.resize(new_size, Image.Resampling.LANCZOS)
            
            if config.enhance_image:
                image = await self._enhance_image(image)
                
            if config.remove_noise:
                image = await self._remove_noise(image)
                
            if config.correct_skew:
                image = await self._correct_skew(image)
                
            return image
            
        except Exception as e:
            logger.error(f"Image preprocessing failed: {str(e)}")
            return image
    
    async def _convert_pdf_to_images(
        self,
        pdf_data: bytes,
        config: OCRConfig
    ) -> List[Image.Image]:
        """将PDF转换为图像"""
        try:
            # TODO: 使用pdf2image或类似库转换PDF
            # 这里是示例实现
            images = []
            
            # 模拟PDF转换
            # import fitz  # PyMuPDF
            # doc = fitz.open(stream=pdf_data, filetype="pdf")
            # for page_num in range(len(doc)):
            #     page = doc.load_page(page_num)
            #     pix = page.get_pixmap(matrix=fitz.Matrix(config.dpi/72, config.dpi/72))
            #     img_data = pix.tobytes("ppm")
            #     image = Image.open(io.BytesIO(img_data))
            #     processed_image = await self._preprocess_image(image, config)
            #     images.append(processed_image)
            
            logger.warning("PDF conversion not implemented, returning empty list")
            return images
            
        except Exception as e:
            logger.error(f"PDF conversion failed: {str(e)}")
            raise
    
    async def _convert_office_to_images(
        self,
        file_data: bytes,
        doc_type: DocumentType,
        config: OCRConfig
    ) -> List[Image.Image]:
        """将Office文档转换为图像"""
        try:
            # TODO: 使用python-docx, openpyxl, python-pptx等库转换
            # 这里是示例实现
            images = []
            
            logger.warning(f"{doc_type} conversion not implemented, returning empty list")
            return images
            
        except Exception as e:
            logger.error(f"Office document conversion failed: {str(e)}")
            raise
    
    async def _perform_ocr(
        self,
        images: List[Image.Image],
        config: OCRConfig,
        document_id: str
    ) -> OCRResult:
        """执行OCR识别"""
        try:
            engine = self.engines.get(config.engine)
            if not engine:
                raise ValueError(f"OCR engine {config.engine} not available")
            
            all_text_blocks = []
            all_tables = []
            full_text_parts = []
            total_confidence = 0.0
            
            # 并行处理多页
            if len(images) > 1 and config.parallel_pages > 1:
                tasks = []
                for i in range(0, len(images), config.parallel_pages):
                    batch = images[i:i + config.parallel_pages]
                    task = self._process_image_batch(batch, i, config, engine)
                    tasks.append(task)
                    
                batch_results = await asyncio.gather(*tasks)
                
                for batch_result in batch_results:
                    all_text_blocks.extend(batch_result["text_blocks"])
                    all_tables.extend(batch_result["tables"])
                    full_text_parts.extend(batch_result["text_parts"])
                    total_confidence += batch_result["confidence"]
            else:
                # 顺序处理
                for page_num, image in enumerate(images):
                    page_result = await self._process_single_image(
                        image, page_num, config, engine
                    )
                    all_text_blocks.extend(page_result["text_blocks"])
                    all_tables.extend(page_result["tables"])
                    full_text_parts.append(page_result["text"])
                    total_confidence += page_result["confidence"]
            
            # 计算平均置信度
            avg_confidence = total_confidence / len(images) if images else 0.0
            
            # 合并文本
            full_text = "\n\n".join(full_text_parts)
            
            result = OCRResult(
                id=f"ocr_{int(datetime.now().timestamp() * 1000)}",
                document_id=document_id,
                engine=config.engine,
                quality=config.quality,
                text_blocks=all_text_blocks,
                tables=all_tables,
                full_text=full_text,
                page_count=len(images),
                confidence=avg_confidence,
                processing_time_ms=0,  # 将在调用方设置
                language=config.languages[0] if config.languages else "en",
                created_at=datetime.now()
            )
            
            return result
            
        except Exception as e:
            logger.error(f"OCR processing failed: {str(e)}")
            raise
    
    async def _process_image_batch(
        self,
        images: List[Image.Image],
        start_page: int,
        config: OCRConfig,
        engine: Any
    ) -> Dict[str, Any]:
        """处理图像批次"""
        text_blocks = []
        tables = []
        text_parts = []
        total_confidence = 0.0
        
        for i, image in enumerate(images):
            page_num = start_page + i
            result = await self._process_single_image(image, page_num, config, engine)
            text_blocks.extend(result["text_blocks"])
            tables.extend(result["tables"])
            text_parts.append(result["text"])
            total_confidence += result["confidence"]
            
        return {
            "text_blocks": text_blocks,
            "tables": tables,
            "text_parts": text_parts,
            "confidence": total_confidence
        }
    
    async def _process_single_image(
        self,
        image: Image.Image,
        page_num: int,
        config: OCRConfig,
        engine: Any
    ) -> Dict[str, Any]:
        """处理单张图像"""
        try:
            if config.engine == OCREngine.PADDLE_OCR:
                return await self._paddle_ocr_process(image, page_num, config)
            elif config.engine == OCREngine.TESSERACT:
                return await self._tesseract_process(image, page_num, config)
            elif config.engine == OCREngine.EASYOCR:
                return await self._easyocr_process(image, page_num, config)
            elif config.engine == OCREngine.ONNX_OCR:
                return await self._onnx_ocr_process(image, page_num, config)
            else:
                raise ValueError(f"Unsupported OCR engine: {config.engine}")
                
        except Exception as e:
            logger.error(f"Single image processing failed: {str(e)}")
            # 返回空结果
            return {
                "text_blocks": [],
                "tables": [],
                "text": "",
                "confidence": 0.0
            }
    
    async def _paddle_ocr_process(
        self,
        image: Image.Image,
        page_num: int,
        config: OCRConfig
    ) -> Dict[str, Any]:
        """PaddleOCR处理"""
        try:
            # TODO: 实现PaddleOCR调用
            # 这里是示例实现
            text_blocks = [
                TextBlock(
                    text="示例文本",
                    confidence=0.95,
                    bbox=[100, 100, 200, 120],
                    page_num=page_num
                )
            ]
            
            tables = []
            if config.detect_tables:
                # TODO: 实现表格检测
                pass
                
            return {
                "text_blocks": text_blocks,
                "tables": tables,
                "text": "示例文本",
                "confidence": 0.95
            }
            
        except Exception as e:
            logger.error(f"PaddleOCR processing failed: {str(e)}")
            raise
    
    async def _tesseract_process(
        self,
        image: Image.Image,
        page_num: int,
        config: OCRConfig
    ) -> Dict[str, Any]:
        """Tesseract处理"""
        try:
            # TODO: 实现Tesseract调用
            # import pytesseract
            # text = pytesseract.image_to_string(image, lang='+'.join(config.languages))
            
            text_blocks = [
                TextBlock(
                    text="示例文本",
                    confidence=0.90,
                    bbox=[100, 100, 200, 120],
                    page_num=page_num
                )
            ]
            
            return {
                "text_blocks": text_blocks,
                "tables": [],
                "text": "示例文本",
                "confidence": 0.90
            }
            
        except Exception as e:
            logger.error(f"Tesseract processing failed: {str(e)}")
            raise
    
    async def _easyocr_process(
        self,
        image: Image.Image,
        page_num: int,
        config: OCRConfig
    ) -> Dict[str, Any]:
        """EasyOCR处理"""
        try:
            # TODO: 实现EasyOCR调用
            text_blocks = [
                TextBlock(
                    text="示例文本",
                    confidence=0.92,
                    bbox=[100, 100, 200, 120],
                    page_num=page_num
                )
            ]
            
            return {
                "text_blocks": text_blocks,
                "tables": [],
                "text": "示例文本",
                "confidence": 0.92
            }
            
        except Exception as e:
            logger.error(f"EasyOCR processing failed: {str(e)}")
            raise
    
    async def _onnx_ocr_process(
        self,
        image: Image.Image,
        page_num: int,
        config: OCRConfig
    ) -> Dict[str, Any]:
        """ONNX OCR处理"""
        try:
            # TODO: 实现ONNX OCR调用
            text_blocks = [
                TextBlock(
                    text="示例文本",
                    confidence=0.88,
                    bbox=[100, 100, 200, 120],
                    page_num=page_num
                )
            ]
            
            return {
                "text_blocks": text_blocks,
                "tables": [],
                "text": "示例文本",
                "confidence": 0.88
            }
            
        except Exception as e:
            logger.error(f"ONNX OCR processing failed: {str(e)}")
            raise
    
    async def _post_process_result(
        self,
        result: OCRResult,
        config: OCRConfig
    ) -> OCRResult:
        """后处理OCR结果"""
        try:
            # 过滤低置信度文本块
            filtered_blocks = [
                block for block in result.text_blocks
                if block.confidence >= config.min_confidence
            ]
            result.text_blocks = filtered_blocks
            
            # 合并行
            if config.merge_lines:
                result.text_blocks = await self._merge_text_lines(result.text_blocks)
            
            # 重新生成全文
            text_parts = []
            for page_num in range(result.page_count):
                page_blocks = [
                    block for block in result.text_blocks
                    if block.page_num == page_num
                ]
                # 按位置排序
                page_blocks.sort(key=lambda b: (b.bbox[1], b.bbox[0]))
                page_text = " ".join([block.text for block in page_blocks])
                text_parts.append(page_text)
                
            result.full_text = "\n\n".join(text_parts)
            
            # 重新计算置信度
            if result.text_blocks:
                result.confidence = sum(block.confidence for block in result.text_blocks) / len(result.text_blocks)
            
            return result
            
        except Exception as e:
            logger.error(f"Post-processing failed: {str(e)}")
            return result
    
    async def _merge_text_lines(self, text_blocks: List[TextBlock]) -> List[TextBlock]:
        """合并文本行"""
        try:
            # TODO: 实现智能文本行合并逻辑
            # 基于位置、字体大小等信息合并相邻的文本块
            return text_blocks
            
        except Exception as e:
            logger.error(f"Text line merging failed: {str(e)}")
            return text_blocks
    
    async def _enhance_image(self, image: Image.Image) -> Image.Image:
        """增强图像质量"""
        try:
            # TODO: 实现图像增强算法
            # 如对比度增强、锐化、去模糊等
            return image
            
        except Exception as e:
            logger.error(f"Image enhancement failed: {str(e)}")
            return image
    
    async def _remove_noise(self, image: Image.Image) -> Image.Image:
        """去除图像噪声"""
        try:
            # TODO: 实现噪声去除算法
            return image
            
        except Exception as e:
            logger.error(f"Noise removal failed: {str(e)}")
            return image
    
    async def _correct_skew(self, image: Image.Image) -> Image.Image:
        """纠正图像倾斜"""
        try:
            # TODO: 实现倾斜纠正算法
            return image
            
        except Exception as e:
            logger.error(f"Skew correction failed: {str(e)}")
            return image
    
    async def _initialize_paddle_ocr(self):
        """初始化PaddleOCR"""
        try:
            # TODO: 初始化PaddleOCR
            # from paddleocr import PaddleOCR
            # self.engines[OCREngine.PADDLE_OCR] = PaddleOCR(use_angle_cls=True, lang='ch')
            logger.info("PaddleOCR initialized (mock)")
            self.engines[OCREngine.PADDLE_OCR] = "mock_paddle_ocr"
            
        except Exception as e:
            logger.warning(f"Failed to initialize PaddleOCR: {str(e)}")
    
    async def _initialize_tesseract(self):
        """初始化Tesseract"""
        try:
            # TODO: 检查Tesseract安装
            logger.info("Tesseract initialized (mock)")
            self.engines[OCREngine.TESSERACT] = "mock_tesseract"
            
        except Exception as e:
            logger.warning(f"Failed to initialize Tesseract: {str(e)}")
    
    async def _initialize_easyocr(self):
        """初始化EasyOCR"""
        try:
            # TODO: 初始化EasyOCR
            # import easyocr
            # self.engines[OCREngine.EASYOCR] = easyocr.Reader(['ch_sim', 'en'])
            logger.info("EasyOCR initialized (mock)")
            self.engines[OCREngine.EASYOCR] = "mock_easyocr"
            
        except Exception as e:
            logger.warning(f"Failed to initialize EasyOCR: {str(e)}")
    
    async def _initialize_onnx_ocr(self):
        """初始化ONNX OCR"""
        try:
            # TODO: 初始化ONNX OCR模型
            logger.info("ONNX OCR initialized (mock)")
            self.engines[OCREngine.ONNX_OCR] = "mock_onnx_ocr"
            
        except Exception as e:
            logger.warning(f"Failed to initialize ONNX OCR: {str(e)}")
    
    async def _health_check_engine(self, engine: OCREngine) -> bool:
        """检查引擎健康状态"""
        try:
            # TODO: 实现各引擎的健康检查
            return True
            
        except Exception as e:
            logger.error(f"Health check failed for {engine}: {str(e)}")
            return False