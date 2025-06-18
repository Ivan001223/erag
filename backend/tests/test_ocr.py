import pytest
import asyncio
import io
from unittest.mock import Mock, AsyncMock, patch
from fastapi.testclient import TestClient
from fastapi import UploadFile
from PIL import Image
import numpy as np

from backend.core.ocr.ocr_service import OCRService, OCRRequest, OCRResponse
from backend.core.ocr.document_processor import DocumentProcessor
from backend.core.ocr.table_extractor import TableExtractor
from backend.core.ocr.quality_assurance import QualityAssurance, QualityAssessmentConfig
from backend.api.ocr import router
from backend.models.user import User
from backend.models.knowledge import Document

class TestOCRService:
    """OCR服务测试"""
    
    @pytest.fixture
    def ocr_service(self):
        return OCRService()
    
    @pytest.fixture
    def sample_image_data(self):
        """创建示例图像数据"""
        # 创建一个简单的测试图像
        image = Image.new('RGB', (800, 600), color='white')
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format='PNG')
        return img_byte_arr.getvalue()
    
    @pytest.fixture
    def sample_ocr_request(self, sample_image_data):
        return OCRRequest(
            image_data=sample_image_data,
            filename="test.png",
            extract_tables=True,
            extract_images=False,
            language="auto",
            model_name="default",
            preprocessing=True
        )
    
    @pytest.mark.asyncio
    async def test_process_document_success(self, ocr_service, sample_ocr_request):
        """测试文档处理成功"""
        with patch.object(ocr_service, '_call_ocr_service') as mock_ocr:
            # 模拟OCR服务响应
            mock_ocr.return_value = {
                "text_content": "Sample text content",
                "confidence_score": 0.95,
                "processing_time": 1.5,
                "tables": [],
                "images": []
            }
            
            result = await ocr_service.process_document(sample_ocr_request)
            
            assert isinstance(result, OCRResponse)
            assert result.text_content == "Sample text content"
            assert result.confidence_score == 0.95
            assert result.processing_time == 1.5
            mock_ocr.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_process_document_with_tables(self, ocr_service, sample_ocr_request):
        """测试包含表格的文档处理"""
        with patch.object(ocr_service, '_call_ocr_service') as mock_ocr:
            mock_ocr.return_value = {
                "text_content": "Document with table",
                "confidence_score": 0.90,
                "processing_time": 2.0,
                "tables": [
                    {
                        "rows": 3,
                        "columns": 2,
                        "cells": [
                            {"row": 0, "col": 0, "text": "Header 1"},
                            {"row": 0, "col": 1, "text": "Header 2"},
                            {"row": 1, "col": 0, "text": "Data 1"},
                            {"row": 1, "col": 1, "text": "Data 2"}
                        ],
                        "confidence": 0.85
                    }
                ],
                "images": []
            }
            
            result = await ocr_service.process_document(sample_ocr_request)
            
            assert len(result.tables) == 1
            assert result.tables[0]["rows"] == 3
            assert result.tables[0]["columns"] == 2
            assert len(result.tables[0]["cells"]) == 4
    
    @pytest.mark.asyncio
    async def test_process_document_failure(self, ocr_service, sample_ocr_request):
        """测试文档处理失败"""
        with patch.object(ocr_service, '_call_ocr_service') as mock_ocr:
            mock_ocr.side_effect = Exception("OCR service error")
            
            with pytest.raises(Exception) as exc_info:
                await ocr_service.process_document(sample_ocr_request)
            
            assert "OCR service error" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_batch_process_documents(self, ocr_service, sample_image_data):
        """测试批量文档处理"""
        requests = [
            OCRRequest(
                image_data=sample_image_data,
                filename=f"test_{i}.png",
                extract_tables=True,
                extract_images=False
            )
            for i in range(3)
        ]
        
        with patch.object(ocr_service, '_call_batch_ocr_service') as mock_batch_ocr:
            mock_batch_ocr.return_value = {
                "batch_id": "test_batch_123",
                "status": "processing",
                "total_documents": 3,
                "estimated_completion_time": 30
            }
            
            result = await ocr_service.batch_process_documents(requests)
            
            assert result["batch_id"] == "test_batch_123"
            assert result["status"] == "processing"
            assert result["total_documents"] == 3
            mock_batch_ocr.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_available_models(self, ocr_service):
        """测试获取可用模型"""
        with patch.object(ocr_service, '_call_ocr_service') as mock_ocr:
            mock_ocr.return_value = {
                "models": [
                    {"name": "default", "description": "Default OCR model"},
                    {"name": "chinese", "description": "Chinese OCR model"},
                    {"name": "english", "description": "English OCR model"}
                ]
            }
            
            models = await ocr_service.get_available_models()
            
            assert len(models) == 3
            assert any(model["name"] == "default" for model in models)
            assert any(model["name"] == "chinese" for model in models)

class TestDocumentProcessor:
    """文档处理器测试"""
    
    @pytest.fixture
    def document_processor(self):
        return DocumentProcessor()
    
    @pytest.fixture
    def sample_image(self):
        """创建示例图像"""
        return Image.new('RGB', (800, 600), color='white')
    
    def test_validate_file_valid_image(self, document_processor):
        """测试有效图像文件验证"""
        image = Image.new('RGB', (100, 100), color='white')
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format='PNG')
        image_data = img_byte_arr.getvalue()
        
        is_valid, message = document_processor.validate_file(
            image_data, "test.png", "image/png"
        )
        
        assert is_valid
        assert message == "文件验证通过"
    
    def test_validate_file_invalid_format(self, document_processor):
        """测试无效文件格式验证"""
        is_valid, message = document_processor.validate_file(
            b"invalid data", "test.txt", "text/plain"
        )
        
        assert not is_valid
        assert "不支持的文件类型" in message
    
    def test_validate_file_too_large(self, document_processor):
        """测试文件过大验证"""
        large_data = b"x" * (51 * 1024 * 1024)  # 51MB
        
        is_valid, message = document_processor.validate_file(
            large_data, "large.png", "image/png"
        )
        
        assert not is_valid
        assert "文件大小超过限制" in message
    
    def test_generate_metadata(self, document_processor, sample_image):
        """测试元数据生成"""
        img_byte_arr = io.BytesIO()
        sample_image.save(img_byte_arr, format='PNG')
        image_data = img_byte_arr.getvalue()
        
        metadata = document_processor.generate_metadata(
            image_data, "test.png", "image/png"
        )
        
        assert metadata["filename"] == "test.png"
        assert metadata["content_type"] == "image/png"
        assert metadata["file_size"] == len(image_data)
        assert "width" in metadata
        assert "height" in metadata
        assert "format" in metadata
    
    def test_enhance_image(self, document_processor, sample_image):
        """测试图像增强"""
        enhanced = document_processor.enhance_image(sample_image)
        
        assert isinstance(enhanced, Image.Image)
        assert enhanced.size == sample_image.size
    
    def test_calculate_quality_score(self, document_processor, sample_image):
        """测试质量分数计算"""
        score = document_processor.calculate_quality_score(sample_image)
        
        assert 0 <= score <= 1
        assert isinstance(score, float)

class TestTableExtractor:
    """表格提取器测试"""
    
    @pytest.fixture
    def table_extractor(self):
        return TableExtractor()
    
    @pytest.fixture
    def sample_table_image(self):
        """创建包含表格的示例图像"""
        # 创建一个简单的表格图像
        image = Image.new('RGB', (400, 300), color='white')
        # 这里可以添加绘制表格线的代码
        return np.array(image)
    
    def test_detect_tables_empty_image(self, table_extractor):
        """测试空图像的表格检测"""
        empty_image = np.ones((100, 100, 3), dtype=np.uint8) * 255
        
        tables = table_extractor.detect_tables(empty_image)
        
        assert isinstance(tables, list)
        # 空图像应该检测不到表格
        assert len(tables) == 0
    
    def test_extract_table_structure_empty_region(self, table_extractor):
        """测试空区域的表格结构提取"""
        empty_region = np.ones((50, 50), dtype=np.uint8) * 255
        
        structure = table_extractor.extract_table_structure(empty_region)
        
        assert structure["rows"] >= 0
        assert structure["columns"] >= 0
        assert isinstance(structure["cells"], list)
    
    def test_calculate_table_confidence(self, table_extractor):
        """测试表格置信度计算"""
        # 创建一个简单的表格结构
        table_structure = {
            "rows": 3,
            "columns": 2,
            "cells": [
                {"row": 0, "col": 0, "text": "Header 1", "confidence": 0.9},
                {"row": 0, "col": 1, "text": "Header 2", "confidence": 0.8},
                {"row": 1, "col": 0, "text": "Data 1", "confidence": 0.85},
                {"row": 1, "col": 1, "text": "Data 2", "confidence": 0.75}
            ]
        }
        
        confidence = table_extractor.calculate_table_confidence(table_structure)
        
        assert 0 <= confidence <= 1
        assert isinstance(confidence, float)

class TestQualityAssurance:
    """质量保证测试"""
    
    @pytest.fixture
    def quality_assurance(self):
        config = QualityAssessmentConfig(
            min_resolution=150,
            min_contrast=0.3,
            min_sharpness=0.4,
            strictness_level="normal"
        )
        return QualityAssurance(config)
    
    @pytest.fixture
    def sample_image_data(self):
        """创建示例图像数据"""
        image = Image.new('RGB', (800, 600), color='white')
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format='PNG')
        return img_byte_arr.getvalue()
    
    @pytest.mark.asyncio
    async def test_assess_quality_basic(self, quality_assurance, sample_image_data):
        """测试基本质量评估"""
        report = await quality_assurance.assess_quality(
            image_data=sample_image_data,
            filename="test.png"
        )
        
        assert report.filename == "test.png"
        assert hasattr(report, 'metrics')
        assert hasattr(report, 'issues')
        assert hasattr(report, 'recommendations')
        assert isinstance(report.is_suitable_for_ocr, bool)
        assert 0 <= report.estimated_accuracy <= 1
    
    @pytest.mark.asyncio
    async def test_assess_quality_with_ocr_results(self, quality_assurance, sample_image_data):
        """测试包含OCR结果的质量评估"""
        ocr_results = {
            "text_content": "Sample text content for testing",
            "confidence_score": 0.85,
            "tables": [
                {
                    "rows": 2,
                    "columns": 2,
                    "cells": [
                        {"row": 0, "col": 0, "text": "A1"},
                        {"row": 0, "col": 1, "text": "B1"}
                    ],
                    "confidence": 0.8
                }
            ]
        }
        
        report = await quality_assurance.assess_quality(
            image_data=sample_image_data,
            filename="test_with_ocr.png",
            ocr_results=ocr_results
        )
        
        assert report.metrics.character_confidence == 0.85
        assert report.metrics.text_clarity_score > 0
        assert report.metrics.table_structure_score > 0
    
    def test_quality_level_determination(self, quality_assurance):
        """测试质量等级判定"""
        # 测试不同分数对应的质量等级
        test_cases = [
            (0.95, "excellent"),
            (0.80, "good"),
            (0.65, "fair"),
            (0.50, "poor"),
            (0.30, "unacceptable")
        ]
        
        for score, expected_level in test_cases:
            level = quality_assurance._determine_quality_level(score)
            assert level == expected_level
    
    def test_preprocessing_suggestions(self, quality_assurance):
        """测试预处理建议生成"""
        from backend.core.ocr.quality_assurance import QualityMetrics, QualityIssue, IssueType
        
        # 创建低质量指标
        metrics = QualityMetrics(
            resolution_score=0.3,
            contrast_score=0.4,
            sharpness_score=0.3,
            noise_score=0.6,
            brightness_score=0.5,
            text_clarity_score=0.0,
            text_completeness_score=0.0,
            character_confidence=0.0,
            layout_score=0.0,
            table_structure_score=0.0,
            overall_score=0.4,
            quality_level="poor"
        )
        
        issues = [
            QualityIssue(
                issue_type=IssueType.SKEW.value,
                severity=0.6,
                description="Document is skewed",
                confidence=0.8
            )
        ]
        
        suggestions = quality_assurance._generate_preprocessing_suggestions(metrics, issues)
        
        assert suggestions["enhance_contrast"] == True
        assert suggestions["sharpen"] == True
        assert suggestions["resize"] == True
        assert suggestions["deskew"] == True

class TestOCRAPI:
    """OCR API测试"""
    
    @pytest.fixture
    def client(self):
        from fastapi import FastAPI
        app = FastAPI()
        app.include_router(router)
        return TestClient(app)
    
    @pytest.fixture
    def mock_user(self):
        return User(
            id="test_user_123",
            username="testuser",
            email="test@example.com",
            is_active=True
        )
    
    @pytest.fixture
    def sample_file_data(self):
        """创建示例文件数据"""
        image = Image.new('RGB', (100, 100), color='white')
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format='PNG')
        return img_byte_arr.getvalue()
    
    def test_upload_document_invalid_file_type(self, client):
        """测试上传无效文件类型"""
        with patch('backend.api.ocr.get_current_user') as mock_auth:
            mock_auth.return_value = Mock(id="test_user")
            
            response = client.post(
                "/api/ocr/upload",
                files={"file": ("test.txt", b"text content", "text/plain")}
            )
            
            assert response.status_code == 400
            assert "不支持的文件类型" in response.json()["detail"]
    
    def test_upload_document_no_filename(self, client):
        """测试上传无文件名的文件"""
        with patch('backend.api.ocr.get_current_user') as mock_auth:
            mock_auth.return_value = Mock(id="test_user")
            
            response = client.post(
                "/api/ocr/upload",
                files={"file": ("", b"image data", "image/png")}
            )
            
            assert response.status_code == 400
            assert "文件名不能为空" in response.json()["detail"]
    
    @patch('backend.api.ocr.get_current_user')
    @patch('backend.api.ocr.get_ocr_service')
    @patch('backend.api.ocr.get_document_service')
    @patch('backend.api.ocr.get_task_service')
    def test_upload_document_success(
        self, 
        mock_task_service, 
        mock_doc_service, 
        mock_ocr_service, 
        mock_auth, 
        client, 
        sample_file_data
    ):
        """测试成功上传文档"""
        # 设置模拟
        mock_auth.return_value = Mock(id="test_user")
        mock_doc_service.return_value.create_document = AsyncMock(
            return_value=Mock(id="doc_123")
        )
        mock_task_service.return_value.create_task = AsyncMock(
            return_value=Mock(id="task_123")
        )
        
        response = client.post(
            "/api/ocr/upload",
            files={"file": ("test.png", sample_file_data, "image/png")},
            data={
                "extract_tables": "true",
                "quality_check": "true"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "task_id" in data
        assert data["status"] == "processing"
        assert "正在处理中" in data["message"]
    
    def test_get_task_status_not_found(self, client):
        """测试获取不存在的任务状态"""
        with patch('backend.api.ocr.get_current_user') as mock_auth, \
             patch('backend.api.ocr.get_task_service') as mock_task_service:
            
            mock_auth.return_value = Mock(id="test_user")
            mock_task_service.return_value.get_task = AsyncMock(return_value=None)
            
            response = client.get("/api/ocr/task/nonexistent_task")
            
            assert response.status_code == 404
            assert "任务不存在" in response.json()["detail"]
    
    def test_get_task_status_unauthorized(self, client):
        """测试获取无权限任务状态"""
        with patch('backend.api.ocr.get_current_user') as mock_auth, \
             patch('backend.api.ocr.get_task_service') as mock_task_service:
            
            mock_auth.return_value = Mock(id="test_user")
            mock_task_service.return_value.get_task = AsyncMock(
                return_value=Mock(
                    user_id="other_user",
                    status="completed",
                    metadata={}
                )
            )
            
            response = client.get("/api/ocr/task/unauthorized_task")
            
            assert response.status_code == 403
            assert "无权访问" in response.json()["detail"]
    
    @patch('backend.api.ocr.get_current_user')
    @patch('backend.api.ocr.get_ocr_service')
    def test_list_ocr_models(
        self, 
        mock_ocr_service, 
        mock_auth, 
        client
    ):
        """测试获取OCR模型列表"""
        mock_auth.return_value = Mock(id="test_user")
        mock_ocr_service.return_value.get_available_models = AsyncMock(
            return_value=[
                {"name": "default", "description": "Default model"},
                {"name": "chinese", "description": "Chinese model"}
            ]
        )
        
        response = client.get("/api/ocr/models")
        
        assert response.status_code == 200
        data = response.json()
        assert "models" in data
        assert len(data["models"]) == 2
        assert data["models"][0]["name"] == "default"

# 性能测试
class TestOCRPerformance:
    """OCR性能测试"""
    
    @pytest.mark.asyncio
    async def test_concurrent_ocr_requests(self):
        """测试并发OCR请求"""
        ocr_service = OCRService()
        
        # 创建多个并发请求
        async def make_request(i):
            image = Image.new('RGB', (100, 100), color='white')
            img_byte_arr = io.BytesIO()
            image.save(img_byte_arr, format='PNG')
            
            request = OCRRequest(
                image_data=img_byte_arr.getvalue(),
                filename=f"test_{i}.png",
                extract_tables=False,
                extract_images=False
            )
            
            with patch.object(ocr_service, '_call_ocr_service') as mock_ocr:
                mock_ocr.return_value = {
                    "text_content": f"Text {i}",
                    "confidence_score": 0.9,
                    "processing_time": 0.1,
                    "tables": [],
                    "images": []
                }
                
                return await ocr_service.process_document(request)
        
        # 并发执行多个请求
        tasks = [make_request(i) for i in range(5)]
        results = await asyncio.gather(*tasks)
        
        assert len(results) == 5
        for i, result in enumerate(results):
            assert result.text_content == f"Text {i}"
    
    @pytest.mark.asyncio
    async def test_large_batch_processing(self):
        """测试大批量处理"""
        ocr_service = OCRService()
        
        # 创建大量请求
        requests = []
        for i in range(10):
            image = Image.new('RGB', (100, 100), color='white')
            img_byte_arr = io.BytesIO()
            image.save(img_byte_arr, format='PNG')
            
            request = OCRRequest(
                image_data=img_byte_arr.getvalue(),
                filename=f"batch_test_{i}.png",
                extract_tables=False,
                extract_images=False
            )
            requests.append(request)
        
        with patch.object(ocr_service, '_call_batch_ocr_service') as mock_batch:
            mock_batch.return_value = {
                "batch_id": "large_batch_test",
                "status": "processing",
                "total_documents": 10,
                "estimated_completion_time": 60
            }
            
            result = await ocr_service.batch_process_documents(requests)
            
            assert result["total_documents"] == 10
            assert result["status"] == "processing"

if __name__ == "__main__":
    pytest.main([__file__, "-v"])