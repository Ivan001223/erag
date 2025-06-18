from typing import Dict, List, Optional, Any, Tuple, Union
import numpy as np
import cv2
from PIL import Image, ImageStat
import io
import re
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

from backend.utils.logger import get_logger
from pydantic import BaseModel, Field

logger = get_logger(__name__)

class QualityLevel(Enum):
    """质量等级"""
    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"
    UNACCEPTABLE = "unacceptable"

class IssueType(Enum):
    """问题类型"""
    LOW_RESOLUTION = "low_resolution"
    POOR_CONTRAST = "poor_contrast"
    BLUR = "blur"
    NOISE = "noise"
    SKEW = "skew"
    LIGHTING = "lighting"
    COMPRESSION_ARTIFACTS = "compression_artifacts"
    TEXT_CLARITY = "text_clarity"
    INCOMPLETE_TEXT = "incomplete_text"
    MIXED_LANGUAGES = "mixed_languages"
    SPECIAL_CHARACTERS = "special_characters"

class QualityMetrics(BaseModel):
    """质量指标"""
    # 图像质量指标
    resolution_score: float = Field(ge=0, le=1, description="分辨率分数")
    contrast_score: float = Field(ge=0, le=1, description="对比度分数")
    sharpness_score: float = Field(ge=0, le=1, description="清晰度分数")
    noise_score: float = Field(ge=0, le=1, description="噪声分数（越高越好）")
    brightness_score: float = Field(ge=0, le=1, description="亮度分数")
    
    # 文本质量指标
    text_clarity_score: float = Field(ge=0, le=1, description="文本清晰度分数")
    text_completeness_score: float = Field(ge=0, le=1, description="文本完整性分数")
    character_confidence: float = Field(ge=0, le=1, description="字符识别置信度")
    
    # 结构质量指标
    layout_score: float = Field(ge=0, le=1, description="布局分数")
    table_structure_score: float = Field(ge=0, le=1, description="表格结构分数")
    
    # 综合分数
    overall_score: float = Field(ge=0, le=1, description="综合质量分数")
    quality_level: str = Field(description="质量等级")

class QualityIssue(BaseModel):
    """质量问题"""
    issue_type: str
    severity: float = Field(ge=0, le=1, description="严重程度")
    description: str
    affected_regions: List[Dict[str, int]] = []  # 受影响的区域
    confidence: float = Field(ge=0, le=1, description="检测置信度")
    recommendation: str = ""

class QualityReport(BaseModel):
    """质量报告"""
    document_id: str
    filename: str
    assessment_time: datetime
    metrics: QualityMetrics
    issues: List[QualityIssue]
    recommendations: List[str]
    processing_suggestions: Dict[str, Any]
    is_suitable_for_ocr: bool
    estimated_accuracy: float = Field(ge=0, le=1)

class QualityAssessmentConfig(BaseModel):
    """质量评估配置"""
    # 阈值设置
    min_resolution: int = 150  # 最小DPI
    min_contrast: float = 0.3
    min_sharpness: float = 0.4
    max_noise_level: float = 0.3
    min_brightness: float = 0.2
    max_brightness: float = 0.8
    
    # 文本质量阈值
    min_text_confidence: float = 0.7
    min_character_size: int = 8  # 最小字符像素大小
    
    # 评估选项
    enable_image_analysis: bool = True
    enable_text_analysis: bool = True
    enable_structure_analysis: bool = True
    enable_preprocessing_suggestions: bool = True
    
    # 严格程度
    strictness_level: str = "normal"  # strict, normal, lenient

class QualityAssurance:
    """质量保证系统"""
    
    def __init__(self, config: QualityAssessmentConfig = None):
        self.config = config or QualityAssessmentConfig()
        self._setup_thresholds()
    
    def _setup_thresholds(self):
        """根据严格程度设置阈值"""
        if self.config.strictness_level == "strict":
            self.config.min_resolution = 200
            self.config.min_contrast = 0.4
            self.config.min_sharpness = 0.5
            self.config.min_text_confidence = 0.8
        elif self.config.strictness_level == "lenient":
            self.config.min_resolution = 100
            self.config.min_contrast = 0.2
            self.config.min_sharpness = 0.3
            self.config.min_text_confidence = 0.6
    
    async def assess_quality(
        self,
        image_data: bytes,
        filename: str,
        ocr_results: Dict[str, Any] = None,
        document_id: str = None
    ) -> QualityReport:
        """
        评估文档质量
        
        Args:
            image_data: 图像数据
            filename: 文件名
            ocr_results: OCR结果（可选）
            document_id: 文档ID
            
        Returns:
            质量报告
        """
        try:
            # 加载图像
            image = Image.open(io.BytesIO(image_data))
            cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
            
            # 初始化质量指标
            metrics = QualityMetrics(
                resolution_score=0.0,
                contrast_score=0.0,
                sharpness_score=0.0,
                noise_score=0.0,
                brightness_score=0.0,
                text_clarity_score=0.0,
                text_completeness_score=0.0,
                character_confidence=0.0,
                layout_score=0.0,
                table_structure_score=0.0,
                overall_score=0.0,
                quality_level=QualityLevel.POOR.value
            )
            
            issues = []
            recommendations = []
            
            # 图像质量分析
            if self.config.enable_image_analysis:
                image_metrics, image_issues = await self._analyze_image_quality(
                    image, cv_image
                )
                metrics.resolution_score = image_metrics["resolution_score"]
                metrics.contrast_score = image_metrics["contrast_score"]
                metrics.sharpness_score = image_metrics["sharpness_score"]
                metrics.noise_score = image_metrics["noise_score"]
                metrics.brightness_score = image_metrics["brightness_score"]
                issues.extend(image_issues)
            
            # 文本质量分析
            if self.config.enable_text_analysis and ocr_results:
                text_metrics, text_issues = await self._analyze_text_quality(
                    ocr_results, cv_image
                )
                metrics.text_clarity_score = text_metrics["text_clarity_score"]
                metrics.text_completeness_score = text_metrics["text_completeness_score"]
                metrics.character_confidence = text_metrics["character_confidence"]
                issues.extend(text_issues)
            
            # 结构质量分析
            if self.config.enable_structure_analysis:
                structure_metrics, structure_issues = await self._analyze_structure_quality(
                    cv_image, ocr_results
                )
                metrics.layout_score = structure_metrics["layout_score"]
                metrics.table_structure_score = structure_metrics["table_structure_score"]
                issues.extend(structure_issues)
            
            # 计算综合分数
            metrics.overall_score = self._calculate_overall_score(metrics)
            metrics.quality_level = self._determine_quality_level(metrics.overall_score)
            
            # 生成建议
            recommendations = self._generate_recommendations(metrics, issues)
            
            # 生成预处理建议
            processing_suggestions = {}
            if self.config.enable_preprocessing_suggestions:
                processing_suggestions = self._generate_preprocessing_suggestions(
                    metrics, issues
                )
            
            # 判断是否适合OCR
            is_suitable_for_ocr = self._is_suitable_for_ocr(metrics, issues)
            
            # 估算准确率
            estimated_accuracy = self._estimate_ocr_accuracy(metrics, issues)
            
            # 创建质量报告
            report = QualityReport(
                document_id=document_id or f"doc_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                filename=filename,
                assessment_time=datetime.now(),
                metrics=metrics,
                issues=issues,
                recommendations=recommendations,
                processing_suggestions=processing_suggestions,
                is_suitable_for_ocr=is_suitable_for_ocr,
                estimated_accuracy=estimated_accuracy
            )
            
            logger.info(f"质量评估完成: {filename}, 综合分数: {metrics.overall_score:.3f}")
            return report
            
        except Exception as e:
            logger.error(f"质量评估失败: {str(e)}")
            # 返回默认的低质量报告
            return self._create_error_report(filename, str(e))
    
    async def _analyze_image_quality(
        self, 
        image: Image.Image, 
        cv_image: np.ndarray
    ) -> Tuple[Dict[str, float], List[QualityIssue]]:
        """分析图像质量"""
        metrics = {}
        issues = []
        
        try:
            # 分辨率分析
            width, height = image.size
            dpi = getattr(image, 'info', {}).get('dpi', (72, 72))
            if isinstance(dpi, tuple):
                dpi = dpi[0]
            
            resolution_score = min(1.0, dpi / 300.0)
            metrics["resolution_score"] = resolution_score
            
            if dpi < self.config.min_resolution:
                issues.append(QualityIssue(
                    issue_type=IssueType.LOW_RESOLUTION.value,
                    severity=1.0 - resolution_score,
                    description=f"分辨率过低: {dpi} DPI (建议 >= {self.config.min_resolution} DPI)",
                    confidence=0.9,
                    recommendation="提高扫描分辨率或使用更高质量的图像源"
                ))
            
            # 对比度分析
            gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
            contrast = gray.std() / 255.0
            contrast_score = min(1.0, contrast / 0.5)
            metrics["contrast_score"] = contrast_score
            
            if contrast < self.config.min_contrast:
                issues.append(QualityIssue(
                    issue_type=IssueType.POOR_CONTRAST.value,
                    severity=1.0 - contrast_score,
                    description=f"对比度不足: {contrast:.3f} (建议 >= {self.config.min_contrast})",
                    confidence=0.8,
                    recommendation="调整图像对比度或改善扫描条件"
                ))
            
            # 清晰度分析（拉普拉斯方差）
            laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
            sharpness_score = min(1.0, laplacian_var / 1000.0)
            metrics["sharpness_score"] = sharpness_score
            
            if sharpness_score < self.config.min_sharpness:
                issues.append(QualityIssue(
                    issue_type=IssueType.BLUR.value,
                    severity=1.0 - sharpness_score,
                    description=f"图像模糊: 清晰度分数 {sharpness_score:.3f}",
                    confidence=0.7,
                    recommendation="使用更稳定的扫描设备或提高图像质量"
                ))
            
            # 噪声分析
            noise_level = self._calculate_noise_level(gray)
            noise_score = max(0.0, 1.0 - noise_level)
            metrics["noise_score"] = noise_score
            
            if noise_level > self.config.max_noise_level:
                issues.append(QualityIssue(
                    issue_type=IssueType.NOISE.value,
                    severity=noise_level,
                    description=f"噪声过多: 噪声水平 {noise_level:.3f}",
                    confidence=0.6,
                    recommendation="应用降噪滤波器或改善扫描环境"
                ))
            
            # 亮度分析
            brightness = gray.mean() / 255.0
            if self.config.min_brightness <= brightness <= self.config.max_brightness:
                brightness_score = 1.0
            else:
                brightness_score = max(0.0, 1.0 - abs(brightness - 0.5) * 2)
            
            metrics["brightness_score"] = brightness_score
            
            if brightness < self.config.min_brightness:
                issues.append(QualityIssue(
                    issue_type=IssueType.LIGHTING.value,
                    severity=1.0 - brightness_score,
                    description=f"图像过暗: 亮度 {brightness:.3f}",
                    confidence=0.8,
                    recommendation="增加亮度或改善照明条件"
                ))
            elif brightness > self.config.max_brightness:
                issues.append(QualityIssue(
                    issue_type=IssueType.LIGHTING.value,
                    severity=1.0 - brightness_score,
                    description=f"图像过亮: 亮度 {brightness:.3f}",
                    confidence=0.8,
                    recommendation="降低亮度或减少过度曝光"
                ))
            
            # 倾斜检测
            skew_angle = self._detect_skew(gray)
            if abs(skew_angle) > 2.0:  # 倾斜角度超过2度
                issues.append(QualityIssue(
                    issue_type=IssueType.SKEW.value,
                    severity=min(1.0, abs(skew_angle) / 10.0),
                    description=f"文档倾斜: {skew_angle:.1f}度",
                    confidence=0.7,
                    recommendation="校正文档倾斜角度"
                ))
            
        except Exception as e:
            logger.error(f"图像质量分析失败: {str(e)}")
            # 设置默认值
            for key in ["resolution_score", "contrast_score", "sharpness_score", 
                       "noise_score", "brightness_score"]:
                if key not in metrics:
                    metrics[key] = 0.5
        
        return metrics, issues
    
    async def _analyze_text_quality(
        self, 
        ocr_results: Dict[str, Any], 
        cv_image: np.ndarray
    ) -> Tuple[Dict[str, float], List[QualityIssue]]:
        """分析文本质量"""
        metrics = {
            "text_clarity_score": 0.0,
            "text_completeness_score": 0.0,
            "character_confidence": 0.0
        }
        issues = []
        
        try:
            if not ocr_results or "text_content" not in ocr_results:
                return metrics, issues
            
            text_content = ocr_results.get("text_content", "")
            confidence_score = ocr_results.get("confidence_score", 0.0)
            
            # 字符置信度分析
            metrics["character_confidence"] = confidence_score
            
            if confidence_score < self.config.min_text_confidence:
                issues.append(QualityIssue(
                    issue_type=IssueType.TEXT_CLARITY.value,
                    severity=1.0 - confidence_score,
                    description=f"文本识别置信度低: {confidence_score:.3f}",
                    confidence=0.9,
                    recommendation="提高图像质量或使用更适合的OCR模型"
                ))
            
            # 文本完整性分析
            completeness_score = self._analyze_text_completeness(text_content)
            metrics["text_completeness_score"] = completeness_score
            
            if completeness_score < 0.7:
                issues.append(QualityIssue(
                    issue_type=IssueType.INCOMPLETE_TEXT.value,
                    severity=1.0 - completeness_score,
                    description=f"文本可能不完整: 完整性分数 {completeness_score:.3f}",
                    confidence=0.6,
                    recommendation="检查原始文档是否完整或调整OCR参数"
                ))
            
            # 文本清晰度分析
            clarity_score = self._analyze_text_clarity(text_content, cv_image)
            metrics["text_clarity_score"] = clarity_score
            
            # 特殊字符检测
            special_char_ratio = self._detect_special_characters(text_content)
            if special_char_ratio > 0.1:
                issues.append(QualityIssue(
                    issue_type=IssueType.SPECIAL_CHARACTERS.value,
                    severity=special_char_ratio,
                    description=f"包含大量特殊字符: {special_char_ratio:.1%}",
                    confidence=0.8,
                    recommendation="检查OCR模型是否适合当前文档类型"
                ))
            
            # 混合语言检测
            if self._detect_mixed_languages(text_content):
                issues.append(QualityIssue(
                    issue_type=IssueType.MIXED_LANGUAGES.value,
                    severity=0.3,
                    description="检测到混合语言文本",
                    confidence=0.6,
                    recommendation="使用支持多语言的OCR模型"
                ))
            
        except Exception as e:
            logger.error(f"文本质量分析失败: {str(e)}")
        
        return metrics, issues
    
    async def _analyze_structure_quality(
        self, 
        cv_image: np.ndarray, 
        ocr_results: Dict[str, Any] = None
    ) -> Tuple[Dict[str, float], List[QualityIssue]]:
        """分析结构质量"""
        metrics = {
            "layout_score": 0.0,
            "table_structure_score": 0.0
        }
        issues = []
        
        try:
            # 布局分析
            layout_score = self._analyze_layout_quality(cv_image)
            metrics["layout_score"] = layout_score
            
            # 表格结构分析
            if ocr_results and "tables" in ocr_results:
                table_score = self._analyze_table_structure(ocr_results["tables"])
                metrics["table_structure_score"] = table_score
            else:
                metrics["table_structure_score"] = 0.5  # 默认分数
            
        except Exception as e:
            logger.error(f"结构质量分析失败: {str(e)}")
        
        return metrics, issues
    
    def _calculate_noise_level(self, gray_image: np.ndarray) -> float:
        """计算噪声水平"""
        try:
            # 使用高斯模糊后的差异来估算噪声
            blurred = cv2.GaussianBlur(gray_image, (5, 5), 0)
            noise = cv2.absdiff(gray_image, blurred)
            noise_level = noise.mean() / 255.0
            return noise_level
        except:
            return 0.1  # 默认噪声水平
    
    def _detect_skew(self, gray_image: np.ndarray) -> float:
        """检测文档倾斜角度"""
        try:
            # 边缘检测
            edges = cv2.Canny(gray_image, 50, 150, apertureSize=3)
            
            # 霍夫线变换
            lines = cv2.HoughLines(edges, 1, np.pi/180, threshold=100)
            
            if lines is None:
                return 0.0
            
            # 计算主要角度
            angles = []
            for rho, theta in lines[:20]:  # 只考虑前20条线
                angle = theta * 180 / np.pi
                if angle > 90:
                    angle = angle - 180
                angles.append(angle)
            
            if angles:
                return np.median(angles)
            
            return 0.0
            
        except:
            return 0.0
    
    def _analyze_text_completeness(self, text: str) -> float:
        """分析文本完整性"""
        if not text:
            return 0.0
        
        # 检查文本特征
        features = {
            "has_sentences": bool(re.search(r'[.!?。！？]', text)),
            "has_words": len(text.split()) > 5,
            "reasonable_length": 10 < len(text) < 10000,
            "no_excessive_spaces": text.count('  ') / len(text) < 0.1,
            "balanced_punctuation": abs(text.count('(') - text.count(')')) <= 2
        }
        
        score = sum(features.values()) / len(features)
        return score
    
    def _analyze_text_clarity(self, text: str, image: np.ndarray) -> float:
        """分析文本清晰度"""
        if not text:
            return 0.0
        
        # 基于文本内容的清晰度指标
        clarity_indicators = {
            "no_garbled_chars": len(re.findall(r'[\x00-\x1f\x7f-\x9f]', text)) == 0,
            "reasonable_char_ratio": 0.8 < len(re.findall(r'[\w\s]', text)) / len(text) < 1.0,
            "no_excessive_repetition": not re.search(r'(.)\1{5,}', text),
            "proper_spacing": 0.1 < text.count(' ') / len(text) < 0.3
        }
        
        score = sum(clarity_indicators.values()) / len(clarity_indicators)
        return score
    
    def _detect_special_characters(self, text: str) -> float:
        """检测特殊字符比例"""
        if not text:
            return 0.0
        
        special_chars = re.findall(r'[^\w\s\u4e00-\u9fff.,!?;:()\[\]{}"\'-]', text)
        return len(special_chars) / len(text)
    
    def _detect_mixed_languages(self, text: str) -> bool:
        """检测混合语言"""
        if not text:
            return False
        
        # 简单的混合语言检测
        has_chinese = bool(re.search(r'[\u4e00-\u9fff]', text))
        has_english = bool(re.search(r'[a-zA-Z]', text))
        has_numbers = bool(re.search(r'\d', text))
        
        # 如果同时包含中文和英文，且比例相对均衡
        if has_chinese and has_english:
            chinese_count = len(re.findall(r'[\u4e00-\u9fff]', text))
            english_count = len(re.findall(r'[a-zA-Z]', text))
            total_chars = chinese_count + english_count
            
            if total_chars > 0:
                min_ratio = min(chinese_count, english_count) / total_chars
                return min_ratio > 0.2  # 如果少数语言占比超过20%
        
        return False
    
    def _analyze_layout_quality(self, image: np.ndarray) -> float:
        """分析布局质量"""
        try:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # 检测文本区域的分布
            _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
            
            # 查找连通组件
            num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(binary)
            
            if num_labels < 2:
                return 0.3  # 很少的文本区域
            
            # 分析文本区域的分布
            areas = stats[1:, cv2.CC_STAT_AREA]  # 排除背景
            
            # 检查区域大小的一致性
            if len(areas) > 0:
                area_std = np.std(areas) / np.mean(areas) if np.mean(areas) > 0 else 1
                consistency_score = max(0, 1 - area_std)
            else:
                consistency_score = 0
            
            # 检查区域分布的均匀性
            if len(centroids) > 1:
                y_coords = centroids[1:, 1]  # 排除背景
                y_distribution = np.std(y_coords) / image.shape[0]
                distribution_score = min(1, y_distribution * 2)
            else:
                distribution_score = 0
            
            layout_score = (consistency_score + distribution_score) / 2
            return min(1.0, layout_score)
            
        except:
            return 0.5
    
    def _analyze_table_structure(self, tables: List[Dict[str, Any]]) -> float:
        """分析表格结构质量"""
        if not tables:
            return 0.5  # 没有表格时返回中性分数
        
        total_score = 0
        for table in tables:
            table_score = 0
            
            # 检查表格完整性
            if "rows" in table and "columns" in table:
                rows = table["rows"]
                columns = table["columns"]
                
                if rows >= 2 and columns >= 2:
                    table_score += 0.4
                
                # 检查单元格填充率
                if "cells" in table:
                    cells = table["cells"]
                    filled_cells = sum(1 for cell in cells if cell.get("text", "").strip())
                    fill_rate = filled_cells / len(cells) if cells else 0
                    table_score += 0.3 * fill_rate
                
                # 检查置信度
                confidence = table.get("confidence", 0)
                table_score += 0.3 * confidence
            
            total_score += table_score
        
        return total_score / len(tables)
    
    def _calculate_overall_score(self, metrics: QualityMetrics) -> float:
        """计算综合质量分数"""
        # 权重设置
        weights = {
            "image_quality": 0.4,
            "text_quality": 0.4,
            "structure_quality": 0.2
        }
        
        # 图像质量分数
        image_score = (
            metrics.resolution_score * 0.2 +
            metrics.contrast_score * 0.25 +
            metrics.sharpness_score * 0.25 +
            metrics.noise_score * 0.15 +
            metrics.brightness_score * 0.15
        )
        
        # 文本质量分数
        text_score = (
            metrics.text_clarity_score * 0.4 +
            metrics.text_completeness_score * 0.3 +
            metrics.character_confidence * 0.3
        )
        
        # 结构质量分数
        structure_score = (
            metrics.layout_score * 0.6 +
            metrics.table_structure_score * 0.4
        )
        
        # 综合分数
        overall_score = (
            image_score * weights["image_quality"] +
            text_score * weights["text_quality"] +
            structure_score * weights["structure_quality"]
        )
        
        return min(1.0, max(0.0, overall_score))
    
    def _determine_quality_level(self, overall_score: float) -> str:
        """确定质量等级"""
        if overall_score >= 0.9:
            return QualityLevel.EXCELLENT.value
        elif overall_score >= 0.75:
            return QualityLevel.GOOD.value
        elif overall_score >= 0.6:
            return QualityLevel.FAIR.value
        elif overall_score >= 0.4:
            return QualityLevel.POOR.value
        else:
            return QualityLevel.UNACCEPTABLE.value
    
    def _generate_recommendations(self, metrics: QualityMetrics, issues: List[QualityIssue]) -> List[str]:
        """生成改进建议"""
        recommendations = []
        
        # 基于问题生成建议
        for issue in issues:
            if issue.recommendation and issue.recommendation not in recommendations:
                recommendations.append(issue.recommendation)
        
        # 基于指标生成通用建议
        if metrics.resolution_score < 0.6:
            recommendations.append("建议使用更高分辨率进行扫描（至少300 DPI）")
        
        if metrics.contrast_score < 0.5:
            recommendations.append("调整图像对比度以提高文字清晰度")
        
        if metrics.sharpness_score < 0.5:
            recommendations.append("确保扫描时文档平整，避免模糊")
        
        if metrics.character_confidence < 0.7:
            recommendations.append("考虑使用更适合的OCR模型或预处理图像")
        
        return recommendations[:5]  # 限制建议数量
    
    def _generate_preprocessing_suggestions(self, metrics: QualityMetrics, issues: List[QualityIssue]) -> Dict[str, Any]:
        """生成预处理建议"""
        suggestions = {
            "enhance_contrast": metrics.contrast_score < 0.5,
            "denoise": metrics.noise_score < 0.7,
            "sharpen": metrics.sharpness_score < 0.5,
            "adjust_brightness": metrics.brightness_score < 0.6,
            "deskew": any(issue.issue_type == IssueType.SKEW.value for issue in issues),
            "resize": metrics.resolution_score < 0.4
        }
        
        # 添加具体参数建议
        if suggestions["enhance_contrast"]:
            suggestions["contrast_factor"] = min(2.0, 1.0 + (0.5 - metrics.contrast_score))
        
        if suggestions["adjust_brightness"]:
            if metrics.brightness_score < 0.3:
                suggestions["brightness_factor"] = 1.3
            else:
                suggestions["brightness_factor"] = 0.8
        
        return suggestions
    
    def _is_suitable_for_ocr(self, metrics: QualityMetrics, issues: List[QualityIssue]) -> bool:
        """判断是否适合OCR处理"""
        # 检查关键指标
        critical_issues = [
            IssueType.LOW_RESOLUTION.value,
            IssueType.POOR_CONTRAST.value,
            IssueType.BLUR.value
        ]
        
        # 如果有严重的关键问题，不适合OCR
        for issue in issues:
            if issue.issue_type in critical_issues and issue.severity > 0.7:
                return False
        
        # 检查综合分数
        return metrics.overall_score >= 0.4
    
    def _estimate_ocr_accuracy(self, metrics: QualityMetrics, issues: List[QualityIssue]) -> float:
        """估算OCR准确率"""
        base_accuracy = metrics.overall_score
        
        # 根据问题调整准确率估算
        for issue in issues:
            if issue.issue_type in [IssueType.TEXT_CLARITY.value, IssueType.INCOMPLETE_TEXT.value]:
                base_accuracy *= (1 - issue.severity * 0.3)
        
        return max(0.1, min(0.95, base_accuracy))
    
    def _create_error_report(self, filename: str, error_message: str) -> QualityReport:
        """创建错误报告"""
        return QualityReport(
            document_id=f"error_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            filename=filename,
            assessment_time=datetime.now(),
            metrics=QualityMetrics(
                resolution_score=0.0,
                contrast_score=0.0,
                sharpness_score=0.0,
                noise_score=0.0,
                brightness_score=0.0,
                text_clarity_score=0.0,
                text_completeness_score=0.0,
                character_confidence=0.0,
                layout_score=0.0,
                table_structure_score=0.0,
                overall_score=0.0,
                quality_level=QualityLevel.UNACCEPTABLE.value
            ),
            issues=[QualityIssue(
                issue_type="processing_error",
                severity=1.0,
                description=f"质量评估失败: {error_message}",
                confidence=1.0,
                recommendation="检查文件格式和完整性"
            )],
            recommendations=["检查文件格式和完整性", "重新上传文档"],
            processing_suggestions={},
            is_suitable_for_ocr=False,
            estimated_accuracy=0.0
        )

# 全局质量保证实例
_quality_assurance = None

def get_quality_assurance(config: QualityAssessmentConfig = None) -> QualityAssurance:
    """获取质量保证实例"""
    global _quality_assurance
    if _quality_assurance is None:
        _quality_assurance = QualityAssurance(config)
    return _quality_assurance