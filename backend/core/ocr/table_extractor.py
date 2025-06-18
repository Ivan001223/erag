from typing import Dict, List, Optional, Any, Tuple, Union
import numpy as np
import cv2
from PIL import Image
import io
import json
from dataclasses import dataclass
from enum import Enum

from backend.utils.logger import get_logger
from pydantic import BaseModel, Field

logger = get_logger(__name__)

class TableDetectionMethod(Enum):
    """表格检测方法"""
    HOUGH_LINES = "hough_lines"
    CONTOUR_DETECTION = "contour_detection"
    MORPHOLOGICAL = "morphological"
    HYBRID = "hybrid"

class CellType(Enum):
    """单元格类型"""
    HEADER = "header"
    DATA = "data"
    MERGED = "merged"
    EMPTY = "empty"

@dataclass
class BoundingBox:
    """边界框"""
    x: int
    y: int
    width: int
    height: int
    
    @property
    def x2(self) -> int:
        return self.x + self.width
    
    @property
    def y2(self) -> int:
        return self.y + self.height
    
    @property
    def area(self) -> int:
        return self.width * self.height
    
    @property
    def center(self) -> Tuple[int, int]:
        return (self.x + self.width // 2, self.y + self.height // 2)
    
    def intersects(self, other: 'BoundingBox') -> bool:
        """检查是否与另一个边界框相交"""
        return not (self.x2 <= other.x or other.x2 <= self.x or 
                   self.y2 <= other.y or other.y2 <= self.y)
    
    def intersection_area(self, other: 'BoundingBox') -> int:
        """计算与另一个边界框的交集面积"""
        if not self.intersects(other):
            return 0
        
        x_overlap = min(self.x2, other.x2) - max(self.x, other.x)
        y_overlap = min(self.y2, other.y2) - max(self.y, other.y)
        return x_overlap * y_overlap
    
    def iou(self, other: 'BoundingBox') -> float:
        """计算IoU（交并比）"""
        intersection = self.intersection_area(other)
        union = self.area + other.area - intersection
        return intersection / union if union > 0 else 0

class TableCell(BaseModel):
    """表格单元格"""
    row: int
    column: int
    bbox: Dict[str, int]  # {"x": int, "y": int, "width": int, "height": int}
    text: str = ""
    confidence: float = Field(ge=0, le=1)
    cell_type: str = CellType.DATA.value
    rowspan: int = 1
    colspan: int = 1
    is_merged: bool = False
    text_alignment: str = "left"  # left, center, right
    background_color: Optional[str] = None
    border_style: Optional[Dict[str, Any]] = None

class TableStructure(BaseModel):
    """表格结构"""
    rows: int
    columns: int
    cells: List[TableCell]
    bbox: Dict[str, int]
    confidence: float = Field(ge=0, le=1)
    table_type: str = "data_table"  # data_table, form, layout
    has_header: bool = False
    header_rows: int = 0
    detection_method: str = TableDetectionMethod.HYBRID.value
    quality_score: float = Field(ge=0, le=1, default=0.0)

class TableExtractionConfig(BaseModel):
    """表格提取配置"""
    detection_method: str = TableDetectionMethod.HYBRID.value
    min_table_area: int = 10000  # 最小表格面积
    min_rows: int = 2
    min_columns: int = 2
    line_thickness_threshold: int = 3
    cell_padding: int = 5
    merge_threshold: float = 0.8  # 单元格合并阈值
    confidence_threshold: float = 0.5
    enable_header_detection: bool = True
    enable_cell_merging: bool = True
    enable_text_alignment_detection: bool = True

class TableExtractor:
    """表格提取器"""
    
    def __init__(self, config: TableExtractionConfig = None):
        self.config = config or TableExtractionConfig()
        
    async def extract_tables(
        self, 
        image_data: bytes, 
        text_regions: List[Dict[str, Any]] = None
    ) -> List[TableStructure]:
        """
        从图像中提取表格
        
        Args:
            image_data: 图像数据
            text_regions: 文本区域信息
            
        Returns:
            提取的表格列表
        """
        try:
            # 加载图像
            image = Image.open(io.BytesIO(image_data))
            cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
            
            # 根据配置选择检测方法
            if self.config.detection_method == TableDetectionMethod.HOUGH_LINES.value:
                tables = self._detect_tables_hough_lines(cv_image)
            elif self.config.detection_method == TableDetectionMethod.CONTOUR_DETECTION.value:
                tables = self._detect_tables_contours(cv_image)
            elif self.config.detection_method == TableDetectionMethod.MORPHOLOGICAL.value:
                tables = self._detect_tables_morphological(cv_image)
            else:  # HYBRID
                tables = self._detect_tables_hybrid(cv_image)
            
            # 过滤和验证表格
            valid_tables = self._filter_tables(tables)
            
            # 提取表格结构
            table_structures = []
            for table_bbox in valid_tables:
                structure = await self._extract_table_structure(
                    cv_image, table_bbox, text_regions
                )
                if structure:
                    table_structures.append(structure)
            
            logger.info(f"提取到 {len(table_structures)} 个表格")
            return table_structures
            
        except Exception as e:
            logger.error(f"表格提取失败: {str(e)}")
            return []
    
    def _detect_tables_hough_lines(self, image: np.ndarray) -> List[BoundingBox]:
        """使用霍夫线变换检测表格"""
        try:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # 边缘检测
            edges = cv2.Canny(gray, 50, 150, apertureSize=3)
            
            # 霍夫线变换
            lines = cv2.HoughLinesP(
                edges, 1, np.pi/180, threshold=100, 
                minLineLength=50, maxLineGap=10
            )
            
            if lines is None:
                return []
            
            # 分离水平线和垂直线
            horizontal_lines = []
            vertical_lines = []
            
            for line in lines:
                x1, y1, x2, y2 = line[0]
                
                # 计算线的角度
                angle = np.arctan2(y2 - y1, x2 - x1) * 180 / np.pi
                
                if abs(angle) < 10 or abs(angle - 180) < 10:  # 水平线
                    horizontal_lines.append((min(x1, x2), max(x1, x2), (y1 + y2) // 2))
                elif abs(angle - 90) < 10 or abs(angle + 90) < 10:  # 垂直线
                    vertical_lines.append((min(y1, y2), max(y1, y2), (x1 + x2) // 2))
            
            # 查找表格区域
            tables = self._find_table_regions_from_lines(
                horizontal_lines, vertical_lines, image.shape
            )
            
            return tables
            
        except Exception as e:
            logger.error(f"霍夫线表格检测失败: {str(e)}")
            return []
    
    def _detect_tables_contours(self, image: np.ndarray) -> List[BoundingBox]:
        """使用轮廓检测表格"""
        try:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # 二值化
            _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
            
            # 形态学操作
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
            binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
            
            # 查找轮廓
            contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            tables = []
            for contour in contours:
                # 计算轮廓面积
                area = cv2.contourArea(contour)
                if area < self.config.min_table_area:
                    continue
                
                # 获取边界矩形
                x, y, w, h = cv2.boundingRect(contour)
                
                # 检查长宽比
                aspect_ratio = w / h
                if 0.2 < aspect_ratio < 5.0:  # 合理的长宽比
                    tables.append(BoundingBox(x, y, w, h))
            
            return tables
            
        except Exception as e:
            logger.error(f"轮廓表格检测失败: {str(e)}")
            return []
    
    def _detect_tables_morphological(self, image: np.ndarray) -> List[BoundingBox]:
        """使用形态学操作检测表格"""
        try:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # 二值化
            _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
            
            # 检测水平线
            horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (40, 1))
            horizontal_lines = cv2.morphologyEx(binary, cv2.MORPH_OPEN, horizontal_kernel)
            
            # 检测垂直线
            vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 40))
            vertical_lines = cv2.morphologyEx(binary, cv2.MORPH_OPEN, vertical_kernel)
            
            # 合并水平线和垂直线
            table_mask = cv2.addWeighted(horizontal_lines, 0.5, vertical_lines, 0.5, 0.0)
            
            # 膨胀操作连接线条
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
            table_mask = cv2.dilate(table_mask, kernel, iterations=2)
            
            # 查找轮廓
            contours, _ = cv2.findContours(table_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            tables = []
            for contour in contours:
                area = cv2.contourArea(contour)
                if area < self.config.min_table_area:
                    continue
                
                x, y, w, h = cv2.boundingRect(contour)
                tables.append(BoundingBox(x, y, w, h))
            
            return tables
            
        except Exception as e:
            logger.error(f"形态学表格检测失败: {str(e)}")
            return []
    
    def _detect_tables_hybrid(self, image: np.ndarray) -> List[BoundingBox]:
        """混合方法检测表格"""
        try:
            # 使用多种方法检测
            hough_tables = self._detect_tables_hough_lines(image)
            contour_tables = self._detect_tables_contours(image)
            morph_tables = self._detect_tables_morphological(image)
            
            # 合并结果
            all_tables = hough_tables + contour_tables + morph_tables
            
            # 去重和合并重叠的表格
            merged_tables = self._merge_overlapping_tables(all_tables)
            
            return merged_tables
            
        except Exception as e:
            logger.error(f"混合表格检测失败: {str(e)}")
            return []
    
    def _find_table_regions_from_lines(
        self, 
        horizontal_lines: List[Tuple[int, int, int]], 
        vertical_lines: List[Tuple[int, int, int]], 
        image_shape: Tuple[int, int, int]
    ) -> List[BoundingBox]:
        """从线条中查找表格区域"""
        tables = []
        
        if len(horizontal_lines) < 2 or len(vertical_lines) < 2:
            return tables
        
        # 按位置排序
        horizontal_lines.sort(key=lambda x: x[2])  # 按y坐标排序
        vertical_lines.sort(key=lambda x: x[2])    # 按x坐标排序
        
        # 查找网格交点
        for i in range(len(horizontal_lines) - 1):
            for j in range(len(vertical_lines) - 1):
                # 获取当前网格的边界
                top_y = horizontal_lines[i][2]
                bottom_y = horizontal_lines[i + 1][2]
                left_x = vertical_lines[j][2]
                right_x = vertical_lines[j + 1][2]
                
                # 检查是否形成有效的矩形
                width = right_x - left_x
                height = bottom_y - top_y
                
                if (width > 50 and height > 30 and 
                    width * height > self.config.min_table_area):
                    
                    # 检查是否有足够的行和列
                    rows = self._count_lines_in_range(
                        horizontal_lines, left_x, right_x, "horizontal"
                    )
                    cols = self._count_lines_in_range(
                        vertical_lines, top_y, bottom_y, "vertical"
                    )
                    
                    if rows >= self.config.min_rows and cols >= self.config.min_columns:
                        tables.append(BoundingBox(left_x, top_y, width, height))
        
        return tables
    
    def _count_lines_in_range(
        self, 
        lines: List[Tuple[int, int, int]], 
        start: int, 
        end: int, 
        line_type: str
    ) -> int:
        """计算范围内的线条数量"""
        count = 0
        for line in lines:
            if line_type == "horizontal":
                # 检查水平线是否在垂直范围内
                if start <= line[0] <= end or start <= line[1] <= end:
                    count += 1
            else:  # vertical
                # 检查垂直线是否在水平范围内
                if start <= line[0] <= end or start <= line[1] <= end:
                    count += 1
        return count
    
    def _merge_overlapping_tables(self, tables: List[BoundingBox]) -> List[BoundingBox]:
        """合并重叠的表格"""
        if not tables:
            return []
        
        # 按面积排序，优先保留大表格
        tables.sort(key=lambda x: x.area, reverse=True)
        
        merged = []
        for table in tables:
            should_merge = False
            
            for i, existing in enumerate(merged):
                iou = table.iou(existing)
                if iou > self.config.merge_threshold:
                    # 合并表格（保留较大的）
                    if table.area > existing.area:
                        merged[i] = table
                    should_merge = True
                    break
            
            if not should_merge:
                merged.append(table)
        
        return merged
    
    def _filter_tables(self, tables: List[BoundingBox]) -> List[BoundingBox]:
        """过滤无效的表格"""
        valid_tables = []
        
        for table in tables:
            # 检查面积
            if table.area < self.config.min_table_area:
                continue
            
            # 检查长宽比
            aspect_ratio = table.width / table.height
            if aspect_ratio < 0.1 or aspect_ratio > 10:
                continue
            
            # 检查最小尺寸
            if table.width < 100 or table.height < 50:
                continue
            
            valid_tables.append(table)
        
        return valid_tables
    
    async def _extract_table_structure(
        self, 
        image: np.ndarray, 
        table_bbox: BoundingBox, 
        text_regions: List[Dict[str, Any]] = None
    ) -> Optional[TableStructure]:
        """提取表格结构"""
        try:
            # 裁剪表格区域
            table_image = image[
                table_bbox.y:table_bbox.y2,
                table_bbox.x:table_bbox.x2
            ]
            
            # 检测网格线
            grid_lines = self._detect_grid_lines(table_image)
            
            if not grid_lines:
                return None
            
            # 计算行列数
            rows, columns = self._calculate_grid_dimensions(grid_lines, table_image.shape)
            
            if rows < self.config.min_rows or columns < self.config.min_columns:
                return None
            
            # 提取单元格
            cells = self._extract_cells(
                table_image, table_bbox, grid_lines, rows, columns, text_regions
            )
            
            # 检测表头
            has_header = False
            header_rows = 0
            if self.config.enable_header_detection:
                has_header, header_rows = self._detect_header(cells)
            
            # 计算质量分数
            quality_score = self._calculate_table_quality(cells, grid_lines)
            
            # 创建表格结构
            structure = TableStructure(
                rows=rows,
                columns=columns,
                cells=cells,
                bbox={
                    "x": table_bbox.x,
                    "y": table_bbox.y,
                    "width": table_bbox.width,
                    "height": table_bbox.height
                },
                confidence=min(1.0, quality_score),
                has_header=has_header,
                header_rows=header_rows,
                detection_method=self.config.detection_method,
                quality_score=quality_score
            )
            
            return structure
            
        except Exception as e:
            logger.error(f"表格结构提取失败: {str(e)}")
            return None
    
    def _detect_grid_lines(self, table_image: np.ndarray) -> Dict[str, List[int]]:
        """检测网格线"""
        try:
            gray = cv2.cvtColor(table_image, cv2.COLOR_BGR2GRAY)
            
            # 检测水平线
            horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (25, 1))
            horizontal_lines = cv2.morphologyEx(gray, cv2.MORPH_OPEN, horizontal_kernel)
            
            # 检测垂直线
            vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 25))
            vertical_lines = cv2.morphologyEx(gray, cv2.MORPH_OPEN, vertical_kernel)
            
            # 提取线条位置
            h_positions = []
            v_positions = []
            
            # 水平线位置
            for y in range(horizontal_lines.shape[0]):
                if np.sum(horizontal_lines[y, :]) > horizontal_lines.shape[1] * 50:
                    h_positions.append(y)
            
            # 垂直线位置
            for x in range(vertical_lines.shape[1]):
                if np.sum(vertical_lines[:, x]) > vertical_lines.shape[0] * 50:
                    v_positions.append(x)
            
            # 去重和排序
            h_positions = sorted(list(set(h_positions)))
            v_positions = sorted(list(set(v_positions)))
            
            return {
                "horizontal": h_positions,
                "vertical": v_positions
            }
            
        except Exception as e:
            logger.error(f"网格线检测失败: {str(e)}")
            return {"horizontal": [], "vertical": []}
    
    def _calculate_grid_dimensions(
        self, 
        grid_lines: Dict[str, List[int]], 
        image_shape: Tuple[int, int, int]
    ) -> Tuple[int, int]:
        """计算网格维度"""
        h_lines = grid_lines["horizontal"]
        v_lines = grid_lines["vertical"]
        
        # 添加边界线（如果不存在）
        if not h_lines or h_lines[0] > 10:
            h_lines.insert(0, 0)
        if not h_lines or h_lines[-1] < image_shape[0] - 10:
            h_lines.append(image_shape[0])
        
        if not v_lines or v_lines[0] > 10:
            v_lines.insert(0, 0)
        if not v_lines or v_lines[-1] < image_shape[1] - 10:
            v_lines.append(image_shape[1])
        
        rows = len(h_lines) - 1
        columns = len(v_lines) - 1
        
        return rows, columns
    
    def _extract_cells(
        self,
        table_image: np.ndarray,
        table_bbox: BoundingBox,
        grid_lines: Dict[str, List[int]],
        rows: int,
        columns: int,
        text_regions: List[Dict[str, Any]] = None
    ) -> List[TableCell]:
        """提取单元格"""
        cells = []
        h_lines = grid_lines["horizontal"]
        v_lines = grid_lines["vertical"]
        
        for row in range(rows):
            for col in range(columns):
                # 计算单元格边界
                y1 = h_lines[row]
                y2 = h_lines[row + 1]
                x1 = v_lines[col]
                x2 = v_lines[col + 1]
                
                # 转换为全局坐标
                global_x = table_bbox.x + x1
                global_y = table_bbox.y + y1
                width = x2 - x1
                height = y2 - y1
                
                # 提取单元格文本
                cell_text = self._extract_cell_text(
                    global_x, global_y, width, height, text_regions
                )
                
                # 计算置信度
                confidence = self._calculate_cell_confidence(
                    table_image[y1:y2, x1:x2], cell_text
                )
                
                # 检测单元格类型
                cell_type = self._detect_cell_type(row, cell_text)
                
                cell = TableCell(
                    row=row,
                    column=col,
                    bbox={
                        "x": global_x,
                        "y": global_y,
                        "width": width,
                        "height": height
                    },
                    text=cell_text,
                    confidence=confidence,
                    cell_type=cell_type
                )
                
                cells.append(cell)
        
        # 处理合并单元格
        if self.config.enable_cell_merging:
            cells = self._detect_merged_cells(cells)
        
        return cells
    
    def _extract_cell_text(
        self,
        x: int,
        y: int,
        width: int,
        height: int,
        text_regions: List[Dict[str, Any]] = None
    ) -> str:
        """提取单元格文本"""
        if not text_regions:
            return ""
        
        cell_bbox = BoundingBox(x, y, width, height)
        cell_text = ""
        
        for region in text_regions:
            region_bbox = BoundingBox(
                region["bbox"]["x"],
                region["bbox"]["y"],
                region["bbox"]["width"],
                region["bbox"]["height"]
            )
            
            # 检查文本区域是否在单元格内
            if cell_bbox.intersects(region_bbox):
                overlap_ratio = (
                    cell_bbox.intersection_area(region_bbox) / region_bbox.area
                )
                
                # 如果重叠比例足够大，认为文本属于该单元格
                if overlap_ratio > 0.5:
                    if cell_text:
                        cell_text += " "
                    cell_text += region["text"]
        
        return cell_text.strip()
    
    def _calculate_cell_confidence(
        self, 
        cell_image: np.ndarray, 
        cell_text: str
    ) -> float:
        """计算单元格置信度"""
        try:
            # 基础置信度
            confidence = 0.5
            
            # 如果有文本，增加置信度
            if cell_text.strip():
                confidence += 0.3
            
            # 检查单元格图像质量
            if cell_image.size > 0:
                gray = cv2.cvtColor(cell_image, cv2.COLOR_BGR2GRAY)
                
                # 计算对比度
                contrast = gray.std()
                if contrast > 20:
                    confidence += 0.1
                
                # 检查边界清晰度
                edges = cv2.Canny(gray, 50, 150)
                edge_density = np.sum(edges > 0) / edges.size
                if edge_density > 0.01:
                    confidence += 0.1
            
            return min(1.0, confidence)
            
        except Exception:
            return 0.5
    
    def _detect_cell_type(self, row: int, text: str) -> str:
        """检测单元格类型"""
        # 简单的表头检测
        if row == 0 and text.strip():
            return CellType.HEADER.value
        
        if not text.strip():
            return CellType.EMPTY.value
        
        return CellType.DATA.value
    
    def _detect_merged_cells(self, cells: List[TableCell]) -> List[TableCell]:
        """检测合并单元格"""
        # 这是一个简化的实现
        # 在实际应用中，需要更复杂的算法来检测合并单元格
        return cells
    
    def _detect_header(self, cells: List[TableCell]) -> Tuple[bool, int]:
        """检测表头"""
        if not cells:
            return False, 0
        
        # 检查第一行是否为表头
        first_row_cells = [cell for cell in cells if cell.row == 0]
        
        if not first_row_cells:
            return False, 0
        
        # 简单的表头检测逻辑
        header_indicators = 0
        total_cells = len(first_row_cells)
        
        for cell in first_row_cells:
            # 检查是否包含典型的表头文本
            text = cell.text.lower()
            if any(keyword in text for keyword in ["名称", "编号", "日期", "类型", "状态"]):
                header_indicators += 1
            
            # 检查文本长度（表头通常较短）
            if len(cell.text) < 20 and cell.text.strip():
                header_indicators += 0.5
        
        # 如果超过一半的单元格符合表头特征，认为是表头
        has_header = header_indicators / total_cells > 0.5
        header_rows = 1 if has_header else 0
        
        return has_header, header_rows
    
    def _calculate_table_quality(self, cells: List[TableCell], grid_lines: Dict[str, List[int]]) -> float:
        """计算表格质量分数"""
        try:
            quality_score = 0.0
            
            # 网格线质量（30%）
            h_lines = len(grid_lines["horizontal"])
            v_lines = len(grid_lines["vertical"])
            if h_lines >= 2 and v_lines >= 2:
                quality_score += 0.3
            
            # 单元格填充率（40%）
            if cells:
                filled_cells = sum(1 for cell in cells if cell.text.strip())
                fill_rate = filled_cells / len(cells)
                quality_score += 0.4 * fill_rate
            
            # 结构一致性（30%）
            if self._check_structure_consistency(cells):
                quality_score += 0.3
            
            return min(1.0, quality_score)
            
        except Exception:
            return 0.5
    
    def _check_structure_consistency(self, cells: List[TableCell]) -> bool:
        """检查结构一致性"""
        if not cells:
            return False
        
        # 检查是否有规律的行列结构
        rows = set(cell.row for cell in cells)
        columns = set(cell.column for cell in cells)
        
        expected_cells = len(rows) * len(columns)
        actual_cells = len(cells)
        
        # 如果实际单元格数量接近期望数量，认为结构一致
        return actual_cells / expected_cells > 0.8

# 全局表格提取器实例
_table_extractor = None

def get_table_extractor(config: TableExtractionConfig = None) -> TableExtractor:
    """获取表格提取器实例"""
    global _table_extractor
    if _table_extractor is None:
        _table_extractor = TableExtractor(config)
    return _table_extractor