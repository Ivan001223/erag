import pytest
import asyncio
import io
import json
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient
from PIL import Image
import numpy as np

from ocr_service.main import app, OCRProcessor, OCRRequest, OCRResponse, BatchOCRRequest

class TestOCRServiceMain:
    """OCR服务主应用测试"""
    
    @pytest.fixture
    def client(self):
        return TestClient(app)
    
    @pytest.fixture
    def sample_image_data(self):
        """创建示例图像数据"""
        image = Image.new('RGB', (800, 600), color='white')
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format='PNG')
        return img_byte_arr.getvalue()
    
    def test_health_check(self, client):
        """测试健康检查端点"""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "version" in data
        assert "uptime" in data
    
    def test_process_document_missing_file(self, client):
        """测试处理文档时缺少文件"""
        response = client.post("/process")
        
        assert response.status_code == 422  # Validation error
    
    def test_process_document_invalid_file_type(self, client):
        """测试处理无效文件类型"""
        response = client.post(
            "/process",
            files={"file": ("test.txt", b"text content", "text/plain")}
        )
        
        assert response.status_code == 400
        assert "不支持的文件类型" in response.json()["detail"]
    
    def test_process_document_success(self, client, sample_image_data):
        """测试成功处理文档"""
        with patch('ocr_service.main.ocr_processor') as mock_processor:
            # 模拟OCR处理器响应
            mock_processor.process_image.return_value = {
                "text_content": "Sample extracted text",
                "confidence_score": 0.95,
                "processing_time": 1.2,
                "tables": [],
                "images": [],
                "quality_metrics": {
                    "resolution_score": 0.9,
                    "contrast_score": 0.8,
                    "sharpness_score": 0.85
                }
            }
            
            response = client.post(
                "/process",
                files={"file": ("test.png", sample_image_data, "image/png")},
                data={
                    "extract_tables": "true",
                    "extract_images": "false",
                    "language": "auto",
                    "model_name": "default"
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["text_content"] == "Sample extracted text"
            assert data["confidence_score"] == 0.95
            assert data["processing_time"] == 1.2
            assert "quality_metrics" in data
    
    def test_process_document_with_tables(self, client, sample_image_data):
        """测试处理包含表格的文档"""
        with patch('ocr_service.main.ocr_processor') as mock_processor:
            mock_processor.process_image.return_value = {
                "text_content": "Document with table",
                "confidence_score": 0.90,
                "processing_time": 2.5,
                "tables": [
                    {
                        "rows": 3,
                        "columns": 2,
                        "cells": [
                            {"row": 0, "col": 0, "text": "Header 1", "confidence": 0.9},
                            {"row": 0, "col": 1, "text": "Header 2", "confidence": 0.85},
                            {"row": 1, "col": 0, "text": "Data 1", "confidence": 0.8},
                            {"row": 1, "col": 1, "text": "Data 2", "confidence": 0.75}
                        ],
                        "confidence": 0.82
                    }
                ],
                "images": [],
                "quality_metrics": {
                    "resolution_score": 0.85,
                    "contrast_score": 0.75,
                    "sharpness_score": 0.8
                }
            }
            
            response = client.post(
                "/process",
                files={"file": ("table_doc.png", sample_image_data, "image/png")},
                data={"extract_tables": "true"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert len(data["tables"]) == 1
            assert data["tables"][0]["rows"] == 3
            assert data["tables"][0]["columns"] == 2
            assert len(data["tables"][0]["cells"]) == 4
    
    def test_batch_process_documents(self, client, sample_image_data):
        """测试批量处理文档"""
        files = [
            ("files", (f"test_{i}.png", sample_image_data, "image/png"))
            for i in range(3)
        ]
        
        with patch('ocr_service.main.ocr_processor') as mock_processor:
            mock_processor.process_image.return_value = {
                "text_content": "Batch processed text",
                "confidence_score": 0.88,
                "processing_time": 1.0,
                "tables": [],
                "images": [],
                "quality_metrics": {}
            }
            
            response = client.post(
                "/batch_process",
                files=files,
                data={"extract_tables": "false"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "batch_id" in data
            assert data["status"] == "processing"
            assert data["total_documents"] == 3
    
    def test_get_task_status_not_found(self, client):
        """测试获取不存在的任务状态"""
        response = client.get("/task/nonexistent_task_id")
        
        assert response.status_code == 404
        assert "任务不存在" in response.json()["detail"]
    
    def test_get_task_status_success(self, client):
        """测试成功获取任务状态"""
        # 首先创建一个任务
        task_id = "test_task_123"
        from ocr_service.main import task_results
        task_results[task_id] = {
            "status": "completed",
            "result": {
                "text_content": "Completed task text",
                "confidence_score": 0.92,
                "processing_time": 1.8
            },
            "created_at": "2024-01-01T00:00:00",
            "completed_at": "2024-01-01T00:01:00"
        }
        
        response = client.get(f"/task/{task_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert "result" in data
        assert data["result"]["text_content"] == "Completed task text"
    
    def test_get_batch_task_status_not_found(self, client):
        """测试获取不存在的批量任务状态"""
        response = client.get("/batch_task/nonexistent_batch_id")
        
        assert response.status_code == 404
        assert "批量任务不存在" in response.json()["detail"]
    
    def test_get_batch_task_status_success(self, client):
        """测试成功获取批量任务状态"""
        # 首先创建一个批量任务
        batch_id = "test_batch_456"
        from ocr_service.main import batch_task_results
        batch_task_results[batch_id] = {
            "status": "completed",
            "total_documents": 3,
            "completed_documents": 3,
            "failed_documents": 0,
            "results": [
                {"filename": "test_1.png", "status": "completed"},
                {"filename": "test_2.png", "status": "completed"},
                {"filename": "test_3.png", "status": "completed"}
            ],
            "created_at": "2024-01-01T00:00:00",
            "completed_at": "2024-01-01T00:03:00"
        }
        
        response = client.get(f"/batch_task/{batch_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert data["total_documents"] == 3
        assert data["completed_documents"] == 3
        assert len(data["results"]) == 3
    
    def test_list_models(self, client):
        """测试获取模型列表"""
        response = client.get("/models")
        
        assert response.status_code == 200
        data = response.json()
        assert "models" in data
        assert len(data["models"]) > 0
        
        # 检查默认模型是否存在
        model_names = [model["name"] for model in data["models"]]
        assert "default" in model_names
    
    def test_delete_task_result_not_found(self, client):
        """测试删除不存在的任务结果"""
        response = client.delete("/task/nonexistent_task")
        
        assert response.status_code == 404
        assert "任务不存在" in response.json()["detail"]
    
    def test_delete_task_result_success(self, client):
        """测试成功删除任务结果"""
        # 首先创建一个任务
        task_id = "test_delete_task"
        from ocr_service.main import task_results
        task_results[task_id] = {
            "status": "completed",
            "result": {"text_content": "To be deleted"}
        }
        
        response = client.delete(f"/task/{task_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "任务结果已删除"
        
        # 验证任务已被删除
        assert task_id not in task_results
    
    def test_get_metrics(self, client):
        """测试获取服务指标"""
        response = client.get("/metrics")
        
        assert response.status_code == 200
        data = response.json()
        assert "total_requests" in data
        assert "successful_requests" in data
        assert "failed_requests" in data
        assert "average_processing_time" in data
        assert "uptime_seconds" in data
        assert "memory_usage_mb" in data
        assert "cpu_usage_percent" in data

class TestOCRProcessor:
    """OCR处理器测试"""
    
    @pytest.fixture
    def ocr_processor(self):
        return OCRProcessor()
    
    @pytest.fixture
    def sample_image(self):
        """创建示例图像"""
        return Image.new('RGB', (800, 600), color='white')
    
    def test_validate_image_valid(self, ocr_processor, sample_image):
        """测试有效图像验证"""
        is_valid, message = ocr_processor.validate_image(sample_image)
        
        assert is_valid
        assert message == "图像验证通过"
    
    def test_validate_image_too_small(self, ocr_processor):
        """测试图像过小验证"""
        small_image = Image.new('RGB', (50, 50), color='white')
        
        is_valid, message = ocr_processor.validate_image(small_image)
        
        assert not is_valid
        assert "图像尺寸过小" in message
    
    def test_validate_image_too_large(self, ocr_processor):
        """测试图像过大验证"""
        large_image = Image.new('RGB', (10000, 10000), color='white')
        
        is_valid, message = ocr_processor.validate_image(large_image)
        
        assert not is_valid
        assert "图像尺寸过大" in message
    
    def test_preprocess_image(self, ocr_processor, sample_image):
        """测试图像预处理"""
        processed = ocr_processor.preprocess_image(sample_image)
        
        assert isinstance(processed, Image.Image)
        # 预处理后的图像应该保持合理的尺寸
        assert processed.width <= 2000
        assert processed.height <= 2000
    
    def test_extract_text_basic(self, ocr_processor, sample_image):
        """测试基本文本提取"""
        with patch('ocr_service.main.pytesseract') as mock_tesseract:
            mock_tesseract.image_to_string.return_value = "Sample extracted text"
            mock_tesseract.image_to_data.return_value = {
                'conf': [90, 85, 80],
                'text': ['Sample', 'extracted', 'text']
            }
            
            text, confidence = ocr_processor.extract_text(sample_image, "eng")
            
            assert text == "Sample extracted text"
            assert 0 <= confidence <= 1
    
    def test_extract_tables_no_tables(self, ocr_processor, sample_image):
        """测试无表格图像的表格提取"""
        tables = ocr_processor.extract_tables(sample_image)
        
        assert isinstance(tables, list)
        # 空白图像应该检测不到表格
        assert len(tables) == 0
    
    def test_extract_images_no_images(self, ocr_processor, sample_image):
        """测试无嵌入图像的图像提取"""
        images = ocr_processor.extract_images(sample_image)
        
        assert isinstance(images, list)
        # 简单的白色图像应该检测不到嵌入图像
        assert len(images) == 0
    
    def test_assess_quality(self, ocr_processor, sample_image):
        """测试质量评估"""
        quality_metrics = ocr_processor.assess_quality(sample_image)
        
        assert "resolution_score" in quality_metrics
        assert "contrast_score" in quality_metrics
        assert "sharpness_score" in quality_metrics
        assert "noise_score" in quality_metrics
        assert "brightness_score" in quality_metrics
        
        # 所有分数应该在0-1之间
        for score in quality_metrics.values():
            assert 0 <= score <= 1
    
    def test_process_image_complete(self, ocr_processor, sample_image):
        """测试完整的图像处理流程"""
        with patch.object(ocr_processor, 'extract_text') as mock_extract_text, \
             patch.object(ocr_processor, 'extract_tables') as mock_extract_tables, \
             patch.object(ocr_processor, 'extract_images') as mock_extract_images:
            
            # 设置模拟返回值
            mock_extract_text.return_value = ("Sample text", 0.9)
            mock_extract_tables.return_value = []
            mock_extract_images.return_value = []
            
            result = ocr_processor.process_image(
                sample_image,
                extract_tables=True,
                extract_images=True,
                language="eng",
                model_name="default"
            )
            
            assert result["text_content"] == "Sample text"
            assert result["confidence_score"] == 0.9
            assert "processing_time" in result
            assert "tables" in result
            assert "images" in result
            assert "quality_metrics" in result
    
    def test_calculate_sharpness(self, ocr_processor, sample_image):
        """测试清晰度计算"""
        # 转换为numpy数组
        image_array = np.array(sample_image.convert('L'))
        
        sharpness = ocr_processor._calculate_sharpness(image_array)
        
        assert isinstance(sharpness, float)
        assert 0 <= sharpness <= 1
    
    def test_calculate_contrast(self, ocr_processor, sample_image):
        """测试对比度计算"""
        # 转换为numpy数组
        image_array = np.array(sample_image.convert('L'))
        
        contrast = ocr_processor._calculate_contrast(image_array)
        
        assert isinstance(contrast, float)
        assert 0 <= contrast <= 1
    
    def test_calculate_noise_level(self, ocr_processor, sample_image):
        """测试噪声水平计算"""
        # 转换为numpy数组
        image_array = np.array(sample_image.convert('L'))
        
        noise_level = ocr_processor._calculate_noise_level(image_array)
        
        assert isinstance(noise_level, float)
        assert 0 <= noise_level <= 1
    
    def test_calculate_brightness(self, ocr_processor, sample_image):
        """测试亮度计算"""
        # 转换为numpy数组
        image_array = np.array(sample_image.convert('L'))
        
        brightness = ocr_processor._calculate_brightness(image_array)
        
        assert isinstance(brightness, float)
        assert 0 <= brightness <= 1

class TestDataModels:
    """数据模型测试"""
    
    def test_ocr_request_model(self):
        """测试OCR请求模型"""
        request_data = {
            "extract_tables": True,
            "extract_images": False,
            "language": "eng",
            "model_name": "default",
            "preprocessing": True
        }
        
        request = OCRRequest(**request_data)
        
        assert request.extract_tables == True
        assert request.extract_images == False
        assert request.language == "eng"
        assert request.model_name == "default"
        assert request.preprocessing == True
    
    def test_ocr_request_defaults(self):
        """测试OCR请求模型默认值"""
        request = OCRRequest()
        
        assert request.extract_tables == False
        assert request.extract_images == False
        assert request.language == "auto"
        assert request.model_name == "default"
        assert request.preprocessing == True
    
    def test_ocr_response_model(self):
        """测试OCR响应模型"""
        response_data = {
            "text_content": "Sample text",
            "confidence_score": 0.95,
            "processing_time": 1.5,
            "tables": [],
            "images": [],
            "quality_metrics": {
                "resolution_score": 0.9,
                "contrast_score": 0.8
            }
        }
        
        response = OCRResponse(**response_data)
        
        assert response.text_content == "Sample text"
        assert response.confidence_score == 0.95
        assert response.processing_time == 1.5
        assert response.tables == []
        assert response.images == []
        assert response.quality_metrics["resolution_score"] == 0.9
    
    def test_batch_ocr_request_model(self):
        """测试批量OCR请求模型"""
        request_data = {
            "extract_tables": True,
            "extract_images": True,
            "language": "chi_sim",
            "model_name": "chinese",
            "preprocessing": False
        }
        
        request = BatchOCRRequest(**request_data)
        
        assert request.extract_tables == True
        assert request.extract_images == True
        assert request.language == "chi_sim"
        assert request.model_name == "chinese"
        assert request.preprocessing == False

# 集成测试
class TestOCRServiceIntegration:
    """OCR服务集成测试"""
    
    @pytest.fixture
    def client(self):
        return TestClient(app)
    
    def test_full_ocr_workflow(self, client):
        """测试完整的OCR工作流程"""
        # 创建测试图像
        image = Image.new('RGB', (400, 300), color='white')
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format='PNG')
        image_data = img_byte_arr.getvalue()
        
        with patch('ocr_service.main.ocr_processor') as mock_processor:
            # 模拟OCR处理
            mock_processor.process_image.return_value = {
                "text_content": "Integration test text",
                "confidence_score": 0.88,
                "processing_time": 2.1,
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
                ],
                "images": [],
                "quality_metrics": {
                    "resolution_score": 0.85,
                    "contrast_score": 0.75,
                    "sharpness_score": 0.8,
                    "noise_score": 0.9,
                    "brightness_score": 0.7
                }
            }
            
            # 1. 处理文档
            response = client.post(
                "/process",
                files={"file": ("integration_test.png", image_data, "image/png")},
                data={
                    "extract_tables": "true",
                    "extract_images": "false",
                    "language": "eng"
                }
            )
            
            assert response.status_code == 200
            result = response.json()
            
            # 验证处理结果
            assert result["text_content"] == "Integration test text"
            assert result["confidence_score"] == 0.88
            assert len(result["tables"]) == 1
            assert "quality_metrics" in result
            
            # 2. 检查服务指标
            metrics_response = client.get("/metrics")
            assert metrics_response.status_code == 200
            
            # 3. 检查模型列表
            models_response = client.get("/models")
            assert models_response.status_code == 200
            models_data = models_response.json()
            assert len(models_data["models"]) > 0
    
    def test_error_handling_workflow(self, client):
        """测试错误处理工作流程"""
        # 1. 测试无效文件类型
        response = client.post(
            "/process",
            files={"file": ("test.txt", b"not an image", "text/plain")}
        )
        assert response.status_code == 400
        
        # 2. 测试不存在的任务
        response = client.get("/task/nonexistent")
        assert response.status_code == 404
        
        # 3. 测试不存在的批量任务
        response = client.get("/batch_task/nonexistent")
        assert response.status_code == 404
        
        # 4. 测试删除不存在的任务
        response = client.delete("/task/nonexistent")
        assert response.status_code == 404

if __name__ == "__main__":
    pytest.main([__file__, "-v"])