"""文档处理服务"""

import asyncio
import hashlib
import mimetypes
import os
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple, BinaryIO
from uuid import uuid4

from ..config import get_settings
from ..config.constants import (
    DocumentType, DocumentStatus, ChunkType, TaskType, TaskStatus,
    SUPPORTED_DOCUMENT_FORMATS, MAX_FILE_SIZE, DEFAULT_CHUNK_SIZE,
    DEFAULT_CHUNK_OVERLAP
)
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from ..connectors import (
    Neo4jClient, RedisClient, MinIOClient
)
from ..models import (
    Document, DocumentChunk, Task, TaskResult,
    APIResponse, PaginatedResponse, ErrorResponse
)
from ..repositories import (
    DocumentRepository, VectorRepository
)
from ..utils import get_logger
from .task_service import TaskService
from .ocr_service import OCRService
from .vector_service import VectorService
from .llm_service import LLMService


class DocumentService:
    """文档处理服务"""
    
    def __init__(
        self,
        neo4j_client: Neo4jClient,
        redis_client: RedisClient,
        db_session: Session,
        minio_client: MinIOClient,
        task_service: TaskService,
        ocr_service: OCRService,
        vector_service: VectorService,
        llm_service: LLMService
    ):
        self.neo4j = neo4j_client
        self.redis = redis_client
        self.db = db_session
        self.minio = minio_client
        self.task_service = task_service
        self.ocr_service = ocr_service
        self.vector_service = vector_service
        self.llm_service = llm_service
        self.settings = get_settings()
        self.logger = get_logger(__name__)
        
        # 初始化仓库
        self.document_repo = DocumentRepository(db_session)
        self.vector_repo = VectorRepository(db_session)
    
    async def upload_document(
        self,
        file_content: bytes,
        filename: str,
        user_id: str,
        metadata: Optional[Dict[str, Any]] = None,
        auto_process: bool = True
    ) -> APIResponse[Document]:
        """上传文档"""
        try:
            # 验证文件
            validation_result = await self._validate_file(file_content, filename)
            if not validation_result["valid"]:
                return ErrorResponse(
                    message=validation_result["error"],
                    error_code="INVALID_FILE"
                )
            
            # 计算文件哈希
            file_hash = self._calculate_file_hash(file_content)
            
            # 检查是否已存在相同文件
            existing_doc = await self._find_document_by_hash(file_hash)
            if existing_doc:
                self.logger.info(f"Document with hash {file_hash} already exists")
                return APIResponse(
                    status="success",
                    message="Document already exists",
                    data=existing_doc
                )
            
            # 生成文档ID和存储路径
            doc_id = str(uuid4())
            file_extension = Path(filename).suffix.lower()
            storage_path = f"documents/{user_id}/{doc_id}{file_extension}"
            
            # 上传到MinIO
            await self.minio.upload_data(
                bucket_name="documents",
                object_name=storage_path,
                data=file_content,
                content_type=mimetypes.guess_type(filename)[0]
            )
            
            # 创建文档记录
            document = Document(
                id=doc_id,
                title=Path(filename).stem,
                filename=filename,
                file_path=storage_path,
                file_size=len(file_content),
                file_hash=file_hash,
                mime_type=mimetypes.guess_type(filename)[0] or "application/octet-stream",
                document_type=self._get_document_type(file_extension),
                status=DocumentStatus.UPLOADED,
                uploaded_by=user_id,
                metadata=metadata or {}
            )
            
            # 保存到数据库
            await self._save_document(document)
            
            # 如果启用自动处理，创建处理任务
            if auto_process:
                task = await self.task_service.create_task(
                    task_type=TaskType.DOCUMENT_PROCESSING,
                    title=f"Process document: {filename}",
                    description=f"Process uploaded document {filename}",
                    created_by=user_id,
                    parameters={
                        "document_id": doc_id,
                        "user_id": user_id,
                        "auto_chunk": True,
                        "auto_extract": True,
                        "auto_vectorize": True
                    }
                )
                
                # 异步执行处理任务
                asyncio.create_task(self._process_document_async(doc_id, task.data.id))
            
            self.logger.info(f"Document uploaded successfully: {doc_id}")
            return APIResponse(
                status="success",
                message="Document uploaded successfully",
                data=document
            )
            
        except Exception as e:
            self.logger.error(f"Error uploading document: {str(e)}")
            return ErrorResponse(
                message=f"Failed to upload document: {str(e)}",
                error_code="UPLOAD_FAILED"
            )
    
    async def get_document(self, doc_id: str, user_id: str) -> APIResponse[Document]:
        """获取文档信息"""
        try:
            document = await self._get_document_by_id(doc_id)
            if not document:
                return ErrorResponse(
                    message="Document not found",
                    error_code="NOT_FOUND"
                )
            
            # 检查权限（简化实现）
            if document.uploaded_by != user_id:
                return ErrorResponse(
                    message="Access denied",
                    error_code="FORBIDDEN"
                )
            
            return APIResponse(
                status="success",
                message="Document retrieved successfully",
                data=document
            )
            
        except Exception as e:
            self.logger.error(f"Error getting document {doc_id}: {str(e)}")
            return ErrorResponse(
                message=f"Failed to get document: {str(e)}",
                error_code="GET_FAILED"
            )
    
    async def list_documents(
        self,
        user_id: str,
        page: int = 1,
        page_size: int = 20,
        status: Optional[DocumentStatus] = None,
        document_type: Optional[DocumentType] = None,
        search_query: Optional[str] = None
    ) -> PaginatedResponse[Document]:
        """列出文档"""
        try:
            # 构建查询条件
            conditions = {"uploaded_by": user_id}
            if status:
                conditions["status"] = status
            if document_type:
                conditions["document_type"] = document_type
            
            # 执行查询
            documents, total_count = await self._list_documents_with_pagination(
                conditions=conditions,
                search_query=search_query,
                page=page,
                page_size=page_size
            )
            
            # 构建分页信息
            total_pages = (total_count + page_size - 1) // page_size
            pagination_meta = {
                "page": page,
                "page_size": page_size,
                "total_items": total_count,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1
            }
            
            return PaginatedResponse(
                status="success",
                message="Documents retrieved successfully",
                data=documents,
                pagination=pagination_meta
            )
            
        except Exception as e:
            self.logger.error(f"Error listing documents: {str(e)}")
            return PaginatedResponse(
                status="error",
                message=f"Failed to list documents: {str(e)}",
                data=[],
                pagination={
                    "page": page,
                    "page_size": page_size,
                    "total_items": 0,
                    "total_pages": 0,
                    "has_next": False,
                    "has_prev": False
                }
            )
    
    async def delete_document(self, doc_id: str, user_id: str) -> APIResponse[None]:
        """删除文档"""
        try:
            document = await self._get_document_by_id(doc_id)
            if not document:
                return ErrorResponse(
                    message="Document not found",
                    error_code="NOT_FOUND"
                )
            
            # 检查权限
            if document.uploaded_by != user_id:
                return ErrorResponse(
                    message="Access denied",
                    error_code="FORBIDDEN"
                )
            
            # 删除文件
            try:
                await self.minio.delete_object("documents", document.file_path)
            except Exception as e:
                self.logger.warning(f"Failed to delete file from MinIO: {str(e)}")
            
            # 删除文档块
            await self._delete_document_chunks(doc_id)
            
            # 删除向量
            try:
                await self.vector_service.delete_document_vectors(doc_id)
            except Exception as e:
                self.logger.warning(f"Failed to delete vectors: {str(e)}")
            
            # 软删除文档记录
            await self._soft_delete_document(doc_id)
            
            self.logger.info(f"Document deleted successfully: {doc_id}")
            return APIResponse(
                status="success",
                message="Document deleted successfully",
                data=None
            )
            
        except Exception as e:
            self.logger.error(f"Error deleting document {doc_id}: {str(e)}")
            return ErrorResponse(
                message=f"Failed to delete document: {str(e)}",
                error_code="DELETE_FAILED"
            )
    
    async def process_document(
        self,
        doc_id: str,
        user_id: str,
        options: Optional[Dict[str, Any]] = None
    ) -> APIResponse[Task]:
        """处理文档"""
        try:
            document = await self._get_document_by_id(doc_id)
            if not document:
                return ErrorResponse(
                    message="Document not found",
                    error_code="NOT_FOUND"
                )
            
            # 检查权限
            if document.uploaded_by != user_id:
                return ErrorResponse(
                    message="Access denied",
                    error_code="FORBIDDEN"
                )
            
            # 检查文档状态
            if document.status == DocumentStatus.PROCESSING:
                return ErrorResponse(
                    message="Document is already being processed",
                    error_code="ALREADY_PROCESSING"
                )
            
            # 创建处理任务
            task = await self.task_service.create_task(
                task_type=TaskType.DOCUMENT_PROCESSING,
                title=f"Process document: {document.filename}",
                description=f"Process document {document.filename}",
                created_by=user_id,
                parameters={
                    "document_id": doc_id,
                    "user_id": user_id,
                    **(options or {})
                }
            )
            
            # 异步执行处理
            asyncio.create_task(self._process_document_async(doc_id, task.data.id))
            
            return task
            
        except Exception as e:
            self.logger.error(f"Error processing document {doc_id}: {str(e)}")
            return ErrorResponse(
                message=f"Failed to process document: {str(e)}",
                error_code="PROCESS_FAILED"
            )
    
    async def get_document_chunks(
        self,
        doc_id: str,
        user_id: str,
        page: int = 1,
        page_size: int = 20
    ) -> PaginatedResponse[DocumentChunk]:
        """获取文档块"""
        try:
            # 检查文档权限
            document = await self._get_document_by_id(doc_id)
            if not document or document.uploaded_by != user_id:
                return PaginatedResponse(
                    status="error",
                    message="Document not found or access denied",
                    data=[],
                    pagination={
                        "page": page,
                        "page_size": page_size,
                        "total_items": 0,
                        "total_pages": 0,
                        "has_next": False,
                        "has_prev": False
                    }
                )
            
            # 获取文档块
            chunks, total_count = await self._get_document_chunks_with_pagination(
                doc_id, page, page_size
            )
            
            # 构建分页信息
            total_pages = (total_count + page_size - 1) // page_size
            pagination_meta = {
                "page": page,
                "page_size": page_size,
                "total_items": total_count,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1
            }
            
            return PaginatedResponse(
                status="success",
                message="Document chunks retrieved successfully",
                data=chunks,
                pagination=pagination_meta
            )
            
        except Exception as e:
            self.logger.error(f"Error getting document chunks: {str(e)}")
            return PaginatedResponse(
                status="error",
                message=f"Failed to get document chunks: {str(e)}",
                data=[],
                pagination={
                    "page": page,
                    "page_size": page_size,
                    "total_items": 0,
                    "total_pages": 0,
                    "has_next": False,
                    "has_prev": False
                }
            )
    
    async def download_document(
        self,
        doc_id: str,
        user_id: str
    ) -> Tuple[Optional[bytes], Optional[str], Optional[str]]:
        """下载文档"""
        try:
            document = await self._get_document_by_id(doc_id)
            if not document:
                return None, None, "Document not found"
            
            # 检查权限
            if document.uploaded_by != user_id:
                return None, None, "Access denied"
            
            # 从MinIO下载文件
            file_data = await self.minio.download_data("documents", document.file_path)
            
            return file_data, document.filename, None
            
        except Exception as e:
            self.logger.error(f"Error downloading document {doc_id}: {str(e)}")
            return None, None, f"Failed to download document: {str(e)}"
    
    # 私有方法
    
    async def _validate_file(self, file_content: bytes, filename: str) -> Dict[str, Any]:
        """验证文件"""
        # 检查文件大小
        if len(file_content) > MAX_FILE_SIZE:
            return {
                "valid": False,
                "error": f"File size exceeds maximum limit of {MAX_FILE_SIZE} bytes"
            }
        
        # 检查文件格式
        file_extension = Path(filename).suffix.lower()
        if file_extension not in SUPPORTED_DOCUMENT_FORMATS:
            return {
                "valid": False,
                "error": f"Unsupported file format: {file_extension}"
            }
        
        # 检查文件内容（简单的魔数检查）
        if not self._validate_file_content(file_content, file_extension):
            return {
                "valid": False,
                "error": "Invalid file content"
            }
        
        return {"valid": True}
    
    def _validate_file_content(self, file_content: bytes, file_extension: str) -> bool:
        """验证文件内容"""
        # 简单的文件头检查
        magic_numbers = {
            ".pdf": b"%PDF",
            ".docx": b"PK",
            ".xlsx": b"PK",
            ".pptx": b"PK",
        }
        
        if file_extension in magic_numbers:
            return file_content.startswith(magic_numbers[file_extension])
        
        return True  # 对于其他格式，暂时返回True
    
    def _calculate_file_hash(self, file_content: bytes) -> str:
        """计算文件哈希"""
        return hashlib.sha256(file_content).hexdigest()
    
    def _get_document_type(self, file_extension: str) -> DocumentType:
        """根据文件扩展名获取文档类型"""
        type_mapping = {
            ".pdf": DocumentType.PDF,
            ".doc": DocumentType.WORD,
            ".docx": DocumentType.WORD,
            ".xls": DocumentType.EXCEL,
            ".xlsx": DocumentType.EXCEL,
            ".ppt": DocumentType.POWERPOINT,
            ".pptx": DocumentType.POWERPOINT,
            ".txt": DocumentType.TEXT,
            ".md": DocumentType.MARKDOWN,
            ".html": DocumentType.HTML,
            ".htm": DocumentType.HTML,
            ".csv": DocumentType.CSV,
            ".json": DocumentType.JSON,
            ".xml": DocumentType.XML,
            ".jpg": DocumentType.IMAGE,
            ".jpeg": DocumentType.IMAGE,
            ".png": DocumentType.IMAGE,
            ".gif": DocumentType.IMAGE,
            ".bmp": DocumentType.IMAGE,
            ".tiff": DocumentType.IMAGE,
        }
        
        return type_mapping.get(file_extension, DocumentType.OTHER)
    
    async def _find_document_by_hash(self, file_hash: str) -> Optional[Document]:
        """根据哈希查找文档"""
        # 使用仓库查询
        return await self.document_repo.get_by_hash(file_hash)
    
    async def _save_document(self, document: Document) -> None:
        """保存文档到数据库"""
        # 使用仓库保存
        await self.document_repo.create(document)
        
        # 保存到Neo4j
        await self.neo4j.create_entity(
            "Document",
            document.id,
            document.dict()
        )
        
        # 缓存到Redis
        await self.redis.set(
            f"document:{document.id}",
            document.json(),
            expire=3600  # 1小时过期
        )
    
    async def _get_document_by_id(self, doc_id: str) -> Optional[Document]:
        """根据ID获取文档"""
        # 先从Redis缓存获取
        cached_doc = await self.redis.get(f"document:{doc_id}")
        if cached_doc:
            return Document.parse_raw(cached_doc)
        
        # 使用仓库查询
        document = await self.document_repo.get_by_id(doc_id)
        
        if document:
            # 缓存到Redis
            await self.redis.set(
                f"document:{doc_id}",
                document.json(),
                expire=3600
            )
            return document
        
        return None
    
    async def _list_documents_with_pagination(
        self,
        conditions: Dict[str, Any],
        search_query: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[Document], int]:
        """分页查询文档"""
        # 使用仓库进行分页查询
        return await self.document_repo.list_with_pagination(
            conditions=conditions,
            search_query=search_query,
            page=page,
            page_size=page_size
        )
    
    async def _delete_document_chunks(self, doc_id: str) -> None:
        """删除文档的所有块"""
        # 使用仓库软删除文档块
        await self.document_repo.soft_delete_chunks_by_document_id(doc_id)
        
        # 删除Neo4j中的文档块节点
        await self.neo4j.delete_entities_by_property("DocumentChunk", "document_id", doc_id)
    
    async def _soft_delete_document(self, doc_id: str) -> None:
        """软删除文档"""
        # 使用仓库软删除文档
        await self.document_repo.soft_delete(doc_id)
        
        # 软删除Neo4j中的文档节点
        await self.neo4j.soft_delete_entity("Document", doc_id)
        
        # 删除Redis缓存
        await self.redis.delete(f"document:{doc_id}")
    
    async def _get_document_chunks_with_pagination(
        self,
        doc_id: str,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[DocumentChunk], int]:
        """分页获取文档块"""
        # 使用仓库进行分页查询
        return await self.document_repo.list_chunks_with_pagination(
            document_id=doc_id,
            page=page,
            page_size=page_size
        )
    
    async def _process_document_async(self, doc_id: str, task_id: str) -> None:
        """异步处理文档"""
        try:
            # 更新任务状态
            await self.task_service.update_task_status(task_id, TaskStatus.RUNNING)
            
            # 更新文档状态
            await self._update_document_status(doc_id, DocumentStatus.PROCESSING)
            
            # 获取文档
            document = await self._get_document_by_id(doc_id)
            if not document:
                raise Exception("Document not found")
            
            # 下载文件内容
            file_content = await self.minio.download_data("documents", document.file_path)
            
            # 根据文档类型进行处理
            if document.document_type == DocumentType.IMAGE:
                # OCR处理
                text_content = await self.ocr_service.extract_text(file_content, document.filename)
            else:
                # 文本提取
                text_content = await self._extract_text_content(file_content, document.document_type)
            
            # 文本分块
            chunks = await self._chunk_text(text_content, doc_id)
            
            # 保存文档块
            for chunk in chunks:
                await self._save_document_chunk(chunk)
            
            # 向量化
            await self.vector_service.vectorize_document_chunks(doc_id, chunks)
            
            # 更新文档状态
            await self._update_document_status(doc_id, DocumentStatus.PROCESSED)
            
            # 更新任务状态
            await self.task_service.complete_task(
                task_id,
                TaskResult(
                    task_id=task_id,
                    status=TaskStatus.COMPLETED,
                    result={
                        "document_id": doc_id,
                        "chunks_count": len(chunks),
                        "processing_time": datetime.now().isoformat()
                    }
                )
            )
            
            self.logger.info(f"Document processed successfully: {doc_id}")
            
        except Exception as e:
            self.logger.error(f"Error processing document {doc_id}: {str(e)}")
            
            # 更新文档状态为失败
            await self._update_document_status(doc_id, DocumentStatus.FAILED)
            
            # 更新任务状态为失败
            await self.task_service.fail_task(
                task_id,
                f"Document processing failed: {str(e)}"
            )
    
    async def _extract_text_content(self, file_content: bytes, document_type: DocumentType) -> str:
        """提取文本内容"""
        # 这里应该根据不同的文档类型使用不同的提取方法
        # 简化实现，实际应该使用专门的库
        
        if document_type == DocumentType.TEXT:
            return file_content.decode('utf-8', errors='ignore')
        elif document_type == DocumentType.PDF:
            # 使用PDF解析库
            return await self._extract_pdf_text(file_content)
        elif document_type in [DocumentType.WORD, DocumentType.EXCEL, DocumentType.POWERPOINT]:
            # 使用Office文档解析库
            return await self._extract_office_text(file_content, document_type)
        else:
            # 其他格式，尝试作为文本处理
            return file_content.decode('utf-8', errors='ignore')
    
    async def _extract_pdf_text(self, file_content: bytes) -> str:
        """提取PDF文本"""
        # 这里应该使用PyPDF2、pdfplumber等库
        # 简化实现
        return "PDF text content extracted"
    
    async def _extract_office_text(self, file_content: bytes, document_type: DocumentType) -> str:
        """提取Office文档文本"""
        # 这里应该使用python-docx、openpyxl、python-pptx等库
        # 简化实现
        return f"{document_type.value} text content extracted"
    
    async def _chunk_text(self, text: str, doc_id: str) -> List[DocumentChunk]:
        """文本分块"""
        chunks = []
        chunk_size = DEFAULT_CHUNK_SIZE
        chunk_overlap = DEFAULT_CHUNK_OVERLAP
        
        # 简单的分块实现
        start = 0
        chunk_index = 0
        
        while start < len(text):
            end = start + chunk_size
            chunk_text = text[start:end]
            
            # 如果不是最后一块，尝试在单词边界分割
            if end < len(text):
                last_space = chunk_text.rfind(' ')
                if last_space > chunk_size * 0.8:  # 如果空格位置合理
                    end = start + last_space
                    chunk_text = text[start:end]
            
            chunk = DocumentChunk(
                id=str(uuid4()),
                document_id=doc_id,
                chunk_index=chunk_index,
                content=chunk_text.strip(),
                chunk_type=ChunkType.TEXT,
                start_position=start,
                end_position=end,
                metadata={
                    "length": len(chunk_text),
                    "word_count": len(chunk_text.split())
                }
            )
            
            chunks.append(chunk)
            
            # 下一块的起始位置（考虑重叠）
            start = end - chunk_overlap
            chunk_index += 1
        
        return chunks
    
    async def _save_document_chunk(self, chunk: DocumentChunk) -> None:
        """保存文档块"""
        # 使用仓库保存文档块
        await self.document_repo.create_chunk(chunk)
        
        # 保存到Neo4j
        await self.neo4j.create_entity(
            "DocumentChunk",
            chunk.id,
            chunk.dict()
        )
        
        # 创建与文档的关系
        await self.neo4j.create_relationship(
            "Document", chunk.document_id,
            "DocumentChunk", chunk.id,
            "HAS_CHUNK",
            {"chunk_index": chunk.chunk_index}
        )
    
    async def _update_document_status(self, doc_id: str, status: DocumentStatus) -> None:
        """更新文档状态"""
        # 使用仓库更新文档状态
        await self.document_repo.update_status(doc_id, status)
        
        # 更新Neo4j
        await self.neo4j.update_entity(
            "Document", doc_id,
            {"status": status.value, "updated_at": datetime.now().isoformat()}
        )
        
        # 删除Redis缓存，强制重新加载
        await self.redis.delete(f"document:{doc_id}")