"""MinIO 对象存储客户端"""

import asyncio
import io
from typing import Dict, List, Any, Optional, Union, AsyncGenerator, BinaryIO
from datetime import datetime, timedelta
from pathlib import Path

from minio import Minio
from minio.error import S3Error, InvalidResponseError
from minio.commonconfig import CopySource
from minio.deleteobjects import DeleteObject
from urllib3.exceptions import MaxRetryError

from backend.utils.logger import get_logger
from backend.config.constants import SUPPORTED_FILE_FORMATS


class MinIOClient:
    """MinIO 异步客户端封装"""
    
    def __init__(
        self,
        endpoint: str,
        access_key: str,
        secret_key: str,
        secure: bool = False,
        region: Optional[str] = None,
        http_client: Optional[Any] = None
    ):
        self.endpoint = endpoint
        self.access_key = access_key
        self.secret_key = secret_key
        self.secure = secure
        self.region = region
        self.client: Optional[Minio] = None
        self.logger = get_logger(__name__)
        
        # 默认存储桶配置
        self.default_buckets = {
            "documents": "knowledge-documents",
            "images": "knowledge-images", 
            "vectors": "knowledge-vectors",
            "models": "knowledge-models",
            "temp": "knowledge-temp",
            "backups": "knowledge-backups"
        }
    
    async def connect(self) -> None:
        """建立MinIO连接"""
        try:
            self.client = Minio(
                endpoint=self.endpoint,
                access_key=self.access_key,
                secret_key=self.secret_key,
                secure=self.secure,
                region=self.region,
                http_client=http_client
            )
            
            # 测试连接
            await self._test_connection()
            self.logger.info(f"MinIO 连接成功: {self.endpoint}")
            
            # 创建默认存储桶
            await self._create_default_buckets()
            
        except Exception as e:
            self.logger.error(f"MinIO 连接失败: {str(e)}")
            raise
    
    async def close(self) -> None:
        """关闭MinIO连接"""
        # MinIO客户端不需要显式关闭连接
        self.logger.info("MinIO 连接已关闭")
    
    async def _test_connection(self) -> None:
        """测试连接"""
        if not self.client:
            raise RuntimeError("MinIO 客户端未初始化")
        
        try:
            # 尝试列出存储桶来测试连接
            await asyncio.get_event_loop().run_in_executor(
                None, list, self.client.list_buckets()
            )
        except Exception as e:
            raise ConnectionError(f"MinIO 连接测试失败: {str(e)}")
    
    async def _create_default_buckets(self) -> None:
        """创建默认存储桶"""
        for bucket_type, bucket_name in self.default_buckets.items():
            try:
                await self.create_bucket(bucket_name)
                self.logger.info(f"存储桶 {bucket_name} ({bucket_type}) 已准备就绪")
            except Exception as e:
                self.logger.error(f"创建存储桶 {bucket_name} 失败: {str(e)}")
    
    async def create_bucket(
        self,
        bucket_name: str,
        location: Optional[str] = None
    ) -> bool:
        """创建存储桶"""
        if not self.client:
            raise RuntimeError("MinIO 客户端未初始化")
        
        try:
            # 检查存储桶是否已存在
            exists = await asyncio.get_event_loop().run_in_executor(
                None, self.client.bucket_exists, bucket_name
            )
            
            if not exists:
                await asyncio.get_event_loop().run_in_executor(
                    None, self.client.make_bucket, bucket_name, location or self.region
                )
                self.logger.info(f"存储桶 {bucket_name} 创建成功")
            
            return True
            
        except Exception as e:
            self.logger.error(f"创建存储桶失败: {str(e)}")
            return False
    
    async def delete_bucket(self, bucket_name: str) -> bool:
        """删除存储桶"""
        if not self.client:
            raise RuntimeError("MinIO 客户端未初始化")
        
        try:
            await asyncio.get_event_loop().run_in_executor(
                None, self.client.remove_bucket, bucket_name
            )
            self.logger.info(f"存储桶 {bucket_name} 删除成功")
            return True
            
        except Exception as e:
            self.logger.error(f"删除存储桶失败: {str(e)}")
            return False
    
    async def list_buckets(self) -> List[Dict[str, Any]]:
        """列出所有存储桶"""
        if not self.client:
            raise RuntimeError("MinIO 客户端未初始化")
        
        try:
            buckets = await asyncio.get_event_loop().run_in_executor(
                None, self.client.list_buckets
            )
            
            return [
                {
                    "name": bucket.name,
                    "creation_date": bucket.creation_date.isoformat() if bucket.creation_date else None
                }
                for bucket in buckets
            ]
            
        except Exception as e:
            self.logger.error(f"列出存储桶失败: {str(e)}")
            return []
    
    async def upload_file(
        self,
        bucket_name: str,
        object_name: str,
        file_path: Union[str, Path],
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None
    ) -> bool:
        """上传文件"""
        if not self.client:
            raise RuntimeError("MinIO 客户端未初始化")
        
        try:
            file_path = Path(file_path)
            if not file_path.exists():
                raise FileNotFoundError(f"文件不存在: {file_path}")
            
            # 自动检测内容类型
            if not content_type:
                content_type = self._get_content_type(file_path.suffix)
            
            await asyncio.get_event_loop().run_in_executor(
                None,
                self.client.fput_object,
                bucket_name,
                object_name,
                str(file_path),
                content_type,
                metadata
            )
            
            self.logger.info(f"文件上传成功: {bucket_name}/{object_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"文件上传失败: {str(e)}")
            return False
    
    async def upload_data(
        self,
        bucket_name: str,
        object_name: str,
        data: Union[bytes, str, BinaryIO],
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None
    ) -> bool:
        """上传数据"""
        if not self.client:
            raise RuntimeError("MinIO 客户端未初始化")
        
        try:
            if isinstance(data, str):
                data = data.encode('utf-8')
                if not content_type:
                    content_type = 'text/plain; charset=utf-8'
            
            if isinstance(data, bytes):
                data = io.BytesIO(data)
                length = len(data.getvalue())
            else:
                # 假设是文件对象
                data.seek(0, 2)  # 移动到文件末尾
                length = data.tell()
                data.seek(0)  # 重置到文件开头
            
            await asyncio.get_event_loop().run_in_executor(
                None,
                self.client.put_object,
                bucket_name,
                object_name,
                data,
                length,
                content_type,
                metadata
            )
            
            self.logger.info(f"数据上传成功: {bucket_name}/{object_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"数据上传失败: {str(e)}")
            return False
    
    async def download_file(
        self,
        bucket_name: str,
        object_name: str,
        file_path: Union[str, Path]
    ) -> bool:
        """下载文件"""
        if not self.client:
            raise RuntimeError("MinIO 客户端未初始化")
        
        try:
            file_path = Path(file_path)
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            await asyncio.get_event_loop().run_in_executor(
                None,
                self.client.fget_object,
                bucket_name,
                object_name,
                str(file_path)
            )
            
            self.logger.info(f"文件下载成功: {bucket_name}/{object_name} -> {file_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"文件下载失败: {str(e)}")
            return False
    
    async def download_data(
        self,
        bucket_name: str,
        object_name: str
    ) -> Optional[bytes]:
        """下载数据"""
        if not self.client:
            raise RuntimeError("MinIO 客户端未初始化")
        
        try:
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                self.client.get_object,
                bucket_name,
                object_name
            )
            
            data = response.read()
            response.close()
            response.release_conn()
            
            self.logger.debug(f"数据下载成功: {bucket_name}/{object_name}")
            return data
            
        except Exception as e:
            self.logger.error(f"数据下载失败: {str(e)}")
            return None
    
    async def delete_object(
        self,
        bucket_name: str,
        object_name: str
    ) -> bool:
        """删除对象"""
        if not self.client:
            raise RuntimeError("MinIO 客户端未初始化")
        
        try:
            await asyncio.get_event_loop().run_in_executor(
                None,
                self.client.remove_object,
                bucket_name,
                object_name
            )
            
            self.logger.info(f"对象删除成功: {bucket_name}/{object_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"对象删除失败: {str(e)}")
            return False
    
    async def delete_objects(
        self,
        bucket_name: str,
        object_names: List[str]
    ) -> List[str]:
        """批量删除对象"""
        if not self.client:
            raise RuntimeError("MinIO 客户端未初始化")
        
        try:
            delete_objects = [DeleteObject(name) for name in object_names]
            
            errors = await asyncio.get_event_loop().run_in_executor(
                None,
                list,
                self.client.remove_objects(bucket_name, delete_objects)
            )
            
            failed_objects = [error.object_name for error in errors]
            successful_count = len(object_names) - len(failed_objects)
            
            self.logger.info(f"批量删除完成: 成功 {successful_count}, 失败 {len(failed_objects)}")
            return failed_objects
            
        except Exception as e:
            self.logger.error(f"批量删除失败: {str(e)}")
            return object_names
    
    async def list_objects(
        self,
        bucket_name: str,
        prefix: Optional[str] = None,
        recursive: bool = True,
        max_keys: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """列出对象"""
        if not self.client:
            raise RuntimeError("MinIO 客户端未初始化")
        
        try:
            objects = await asyncio.get_event_loop().run_in_executor(
                None,
                list,
                self.client.list_objects(
                    bucket_name,
                    prefix=prefix,
                    recursive=recursive
                )
            )
            
            result = []
            for obj in objects:
                if max_keys and len(result) >= max_keys:
                    break
                
                result.append({
                    "name": obj.object_name,
                    "size": obj.size,
                    "etag": obj.etag,
                    "last_modified": obj.last_modified.isoformat() if obj.last_modified else None,
                    "content_type": obj.content_type,
                    "is_dir": obj.is_dir
                })
            
            return result
            
        except Exception as e:
            self.logger.error(f"列出对象失败: {str(e)}")
            return []
    
    async def object_exists(
        self,
        bucket_name: str,
        object_name: str
    ) -> bool:
        """检查对象是否存在"""
        if not self.client:
            raise RuntimeError("MinIO 客户端未初始化")
        
        try:
            await asyncio.get_event_loop().run_in_executor(
                None,
                self.client.stat_object,
                bucket_name,
                object_name
            )
            return True
            
        except S3Error as e:
            if e.code == "NoSuchKey":
                return False
            raise
        except Exception as e:
            self.logger.error(f"检查对象存在性失败: {str(e)}")
            return False
    
    async def get_object_info(
        self,
        bucket_name: str,
        object_name: str
    ) -> Optional[Dict[str, Any]]:
        """获取对象信息"""
        if not self.client:
            raise RuntimeError("MinIO 客户端未初始化")
        
        try:
            stat = await asyncio.get_event_loop().run_in_executor(
                None,
                self.client.stat_object,
                bucket_name,
                object_name
            )
            
            return {
                "name": stat.object_name,
                "size": stat.size,
                "etag": stat.etag,
                "last_modified": stat.last_modified.isoformat() if stat.last_modified else None,
                "content_type": stat.content_type,
                "metadata": stat.metadata
            }
            
        except Exception as e:
            self.logger.error(f"获取对象信息失败: {str(e)}")
            return None
    
    async def copy_object(
        self,
        source_bucket: str,
        source_object: str,
        dest_bucket: str,
        dest_object: str,
        metadata: Optional[Dict[str, str]] = None
    ) -> bool:
        """复制对象"""
        if not self.client:
            raise RuntimeError("MinIO 客户端未初始化")
        
        try:
            copy_source = CopySource(source_bucket, source_object)
            
            await asyncio.get_event_loop().run_in_executor(
                None,
                self.client.copy_object,
                dest_bucket,
                dest_object,
                copy_source,
                metadata
            )
            
            self.logger.info(f"对象复制成功: {source_bucket}/{source_object} -> {dest_bucket}/{dest_object}")
            return True
            
        except Exception as e:
            self.logger.error(f"对象复制失败: {str(e)}")
            return False
    
    async def generate_presigned_url(
        self,
        bucket_name: str,
        object_name: str,
        expires: timedelta = timedelta(hours=1),
        method: str = "GET"
    ) -> Optional[str]:
        """生成预签名URL"""
        if not self.client:
            raise RuntimeError("MinIO 客户端未初始化")
        
        try:
            if method.upper() == "GET":
                url = await asyncio.get_event_loop().run_in_executor(
                    None,
                    self.client.presigned_get_object,
                    bucket_name,
                    object_name,
                    expires
                )
            elif method.upper() == "PUT":
                url = await asyncio.get_event_loop().run_in_executor(
                    None,
                    self.client.presigned_put_object,
                    bucket_name,
                    object_name,
                    expires
                )
            else:
                raise ValueError(f"不支持的方法: {method}")
            
            return url
            
        except Exception as e:
            self.logger.error(f"生成预签名URL失败: {str(e)}")
            return None
    
    def _get_content_type(self, file_extension: str) -> str:
        """根据文件扩展名获取内容类型"""
        content_types = {
            ".pdf": "application/pdf",
            ".doc": "application/msword",
            ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ".xls": "application/vnd.ms-excel",
            ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ".ppt": "application/vnd.ms-powerpoint",
            ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            ".txt": "text/plain; charset=utf-8",
            ".md": "text/markdown; charset=utf-8",
            ".html": "text/html; charset=utf-8",
            ".htm": "text/html; charset=utf-8",
            ".json": "application/json; charset=utf-8",
            ".xml": "application/xml; charset=utf-8",
            ".csv": "text/csv; charset=utf-8",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".gif": "image/gif",
            ".bmp": "image/bmp",
            ".tiff": "image/tiff",
            ".svg": "image/svg+xml",
            ".mp4": "video/mp4",
            ".avi": "video/x-msvideo",
            ".mov": "video/quicktime",
            ".mp3": "audio/mpeg",
            ".wav": "audio/wav",
            ".zip": "application/zip",
            ".rar": "application/x-rar-compressed",
            ".7z": "application/x-7z-compressed"
        }
        
        return content_types.get(file_extension.lower(), "application/octet-stream")
    
    async def get_bucket_stats(self, bucket_name: str) -> Dict[str, Any]:
        """获取存储桶统计信息"""
        try:
            objects = await self.list_objects(bucket_name)
            
            total_size = sum(obj["size"] for obj in objects if obj["size"])
            total_count = len(objects)
            
            # 按文件类型统计
            type_stats = {}
            for obj in objects:
                ext = Path(obj["name"]).suffix.lower()
                if ext:
                    type_stats[ext] = type_stats.get(ext, 0) + 1
            
            return {
                "bucket_name": bucket_name,
                "total_objects": total_count,
                "total_size_bytes": total_size,
                "total_size_mb": round(total_size / (1024 * 1024), 2),
                "file_types": type_stats
            }
            
        except Exception as e:
            self.logger.error(f"获取存储桶统计失败: {str(e)}")
            return {}
    
    async def health_check(self) -> bool:
        """健康检查"""
        try:
            if not self.client:
                return False
            
            # 尝试列出存储桶
            await asyncio.get_event_loop().run_in_executor(
                None, list, self.client.list_buckets()
            )
            return True
            
        except Exception as e:
            self.logger.error(f"MinIO 健康检查失败: {str(e)}")
            return False
    
    def get_bucket_name(self, bucket_type: str) -> str:
        """获取存储桶名称"""
        return self.default_buckets.get(bucket_type, bucket_type)