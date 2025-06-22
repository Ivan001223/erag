"""数据备份和恢复策略

提供知识图谱数据的备份、恢复和数据同步功能。
"""

import asyncio
import json
import gzip
import shutil
import tarfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from enum import Enum
import hashlib
import boto3
from botocore.exceptions import ClientError

from backend.config.settings import get_settings
from backend.utils.logger import get_logger
from backend.connectors.neo4j_client import Neo4jClient
from backend.connectors.redis_client import RedisClient
from backend.connectors.minio_client import MinIOClient
from backend.core.base_service import BaseService, ServiceError

settings = get_settings()
logger = get_logger(__name__)


class BackupType(Enum):
    """备份类型"""
    FULL = "full"
    INCREMENTAL = "incremental"
    DIFFERENTIAL = "differential"


class BackupStatus(Enum):
    """备份状态"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class BackupMetadata:
    """备份元数据"""
    backup_id: str
    backup_type: BackupType
    status: BackupStatus
    start_time: datetime
    end_time: Optional[datetime] = None
    file_path: str = ""
    file_size: int = 0
    checksum: str = ""
    error_message: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BackupConfig:
    """备份配置"""
    enabled: bool = True
    schedule_cron: str = "0 2 * * *"  # 每天凌晨2点
    retention_days: int = 30
    max_backups: int = 100
    compression: bool = True
    encryption: bool = False
    storage_backend: str = "local"  # local, s3, minio
    storage_config: Dict[str, Any] = field(default_factory=dict)


class BackupManager(BaseService):
    """备份管理器"""
    
    def __init__(
        self,
        neo4j_client: Neo4jClient,
        redis_client: RedisClient,
        minio_client: Optional[MinIOClient] = None,
        config: Optional[BackupConfig] = None
    ):
        super().__init__("BackupManager")
        
        self.neo4j = neo4j_client
        self.redis = redis_client
        self.minio = minio_client
        self.config = config or BackupConfig()
        
        # 备份存储路径
        self.backup_dir = Path(getattr(settings, 'backup_dir', "/tmp/backups"))
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        # 备份记录
        self.backup_history: List[BackupMetadata] = []
        
        # S3客户端（如果使用S3存储）
        self.s3_client = None
        if self.config.storage_backend == "s3":
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=self.config.storage_config.get('access_key'),
                aws_secret_access_key=self.config.storage_config.get('secret_key'),
                region_name=self.config.storage_config.get('region', 'us-east-1')
            )
    
    async def initialize(self) -> None:
        """初始化备份管理器"""
        await self._load_backup_history()
        await self._cleanup_old_backups()
        self.logger.info("备份管理器初始化完成")
    
    async def cleanup(self) -> None:
        """清理资源"""
        await self._save_backup_history()
        self.logger.info("备份管理器清理完成")
    
    async def create_backup(
        self,
        backup_type: BackupType = BackupType.FULL,
        description: Optional[str] = None
    ) -> BackupMetadata:
        """创建备份"""
        backup_id = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        metadata = BackupMetadata(
            backup_id=backup_id,
            backup_type=backup_type,
            status=BackupStatus.PENDING,
            start_time=datetime.now(),
            metadata={
                "description": description or f"{backup_type.value} backup",
                "version": settings.app_version,
                "node_count": 0,
                "relationship_count": 0
            }
        )
        
        try:
            self.logger.info(f"开始创建备份: {backup_id}")
            metadata.status = BackupStatus.IN_PROGRESS
            
            # 创建备份文件
            backup_file = await self._create_backup_file(metadata)
            metadata.file_path = str(backup_file)
            metadata.file_size = backup_file.stat().st_size
            metadata.checksum = await self._calculate_checksum(backup_file)
            
            # 上传到远程存储
            if self.config.storage_backend != "local":
                await self._upload_backup(backup_file, metadata)
            
            metadata.status = BackupStatus.COMPLETED
            metadata.end_time = datetime.now()
            
            # 记录备份历史
            self.backup_history.append(metadata)
            await self._save_backup_history()
            
            self.logger.info(f"备份创建成功: {backup_id}, 大小: {metadata.file_size} bytes")
            return metadata
            
        except Exception as e:
            metadata.status = BackupStatus.FAILED
            metadata.error_message = str(e)
            metadata.end_time = datetime.now()
            
            self.logger.error(f"备份创建失败: {backup_id}, 错误: {str(e)}")
            raise ServiceError(f"备份创建失败: {str(e)}", "BACKUP_FAILED")
    
    async def restore_backup(
        self,
        backup_id: str,
        target_database: Optional[str] = None,
        dry_run: bool = False
    ) -> bool:
        """恢复备份"""
        try:
            # 查找备份元数据
            backup_metadata = None
            for backup in self.backup_history:
                if backup.backup_id == backup_id:
                    backup_metadata = backup
                    break
            
            if not backup_metadata:
                raise ServiceError(f"未找到备份: {backup_id}", "BACKUP_NOT_FOUND")
            
            self.logger.info(f"开始恢复备份: {backup_id}")
            
            # 下载备份文件（如果需要）
            backup_file = Path(backup_metadata.file_path)
            if not backup_file.exists() and self.config.storage_backend != "local":
                backup_file = await self._download_backup(backup_metadata)
            
            if not backup_file.exists():
                raise ServiceError(f"备份文件不存在: {backup_file}", "BACKUP_FILE_NOT_FOUND")
            
            # 验证备份文件
            if not await self._verify_backup(backup_file, backup_metadata):
                raise ServiceError("备份文件验证失败", "BACKUP_VERIFICATION_FAILED")
            
            if dry_run:
                self.logger.info(f"干运行模式：备份 {backup_id} 验证通过")
                return True
            
            # 执行恢复
            await self._restore_from_file(backup_file, target_database)
            
            self.logger.info(f"备份恢复成功: {backup_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"备份恢复失败: {backup_id}, 错误: {str(e)}")
            raise ServiceError(f"备份恢复失败: {str(e)}", "RESTORE_FAILED")
    
    async def list_backups(
        self,
        backup_type: Optional[BackupType] = None,
        status: Optional[BackupStatus] = None,
        limit: int = 50
    ) -> List[BackupMetadata]:
        """列出备份"""
        backups = self.backup_history.copy()
        
        # 过滤条件
        if backup_type:
            backups = [b for b in backups if b.backup_type == backup_type]
        
        if status:
            backups = [b for b in backups if b.status == status]
        
        # 按时间倒序排列
        backups.sort(key=lambda x: x.start_time, reverse=True)
        
        return backups[:limit]
    
    async def delete_backup(self, backup_id: str) -> bool:
        """删除备份"""
        try:
            # 查找备份
            backup_metadata = None
            for i, backup in enumerate(self.backup_history):
                if backup.backup_id == backup_id:
                    backup_metadata = backup
                    self.backup_history.pop(i)
                    break
            
            if not backup_metadata:
                raise ServiceError(f"未找到备份: {backup_id}", "BACKUP_NOT_FOUND")
            
            # 删除本地文件
            backup_file = Path(backup_metadata.file_path)
            if backup_file.exists():
                backup_file.unlink()
            
            # 删除远程文件
            if self.config.storage_backend != "local":
                await self._delete_remote_backup(backup_metadata)
            
            # 更新历史记录
            await self._save_backup_history()
            
            self.logger.info(f"备份删除成功: {backup_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"删除备份失败: {backup_id}, 错误: {str(e)}")
            raise ServiceError(f"删除备份失败: {str(e)}", "DELETE_BACKUP_FAILED")
    
    async def _create_backup_file(self, metadata: BackupMetadata) -> Path:
        """创建备份文件"""
        backup_file = self.backup_dir / f"{metadata.backup_id}.json"
        
        if self.config.compression:
            backup_file = backup_file.with_suffix('.json.gz')
        
        # 导出Neo4j数据
        neo4j_data = await self._export_neo4j_data()
        
        # 导出Redis数据
        redis_data = await self._export_redis_data()
        
        # 组装备份数据
        backup_data = {
            "metadata": {
                "backup_id": metadata.backup_id,
                "backup_type": metadata.backup_type.value,
                "timestamp": metadata.start_time.isoformat(),
                "version": settings.app_version
            },
            "neo4j": neo4j_data,
            "redis": redis_data
        }
        
        # 更新统计信息
        metadata.metadata["node_count"] = neo4j_data.get("node_count", 0)
        metadata.metadata["relationship_count"] = neo4j_data.get("relationship_count", 0)
        
        # 写入文件
        if self.config.compression:
            with gzip.open(backup_file, 'wt', encoding='utf-8') as f:
                json.dump(backup_data, f, indent=2, ensure_ascii=False)
        else:
            with open(backup_file, 'w', encoding='utf-8') as f:
                json.dump(backup_data, f, indent=2, ensure_ascii=False)
        
        return backup_file
    
    async def _export_neo4j_data(self) -> Dict[str, Any]:
        """导出Neo4j数据"""
        try:
            # 导出所有节点
            nodes_query = """
            MATCH (n)
            RETURN n, labels(n) as labels, id(n) as internal_id
            """
            nodes_result = await self.neo4j.run(nodes_query)
            
            # 导出所有关系
            relationships_query = """
            MATCH (a)-[r]->(b)
            RETURN r, type(r) as rel_type, 
                   id(startNode(r)) as start_id, 
                   id(endNode(r)) as end_id,
                   id(r) as internal_id
            """
            relationships_result = await self.neo4j.run(relationships_query)
            
            # 获取统计信息
            stats_query = """
            MATCH (n) WITH count(n) as node_count
            MATCH ()-[r]->() WITH node_count, count(r) as rel_count
            RETURN node_count, rel_count
            """
            stats_result = await self.neo4j.run(stats_query)
            stats = stats_result[0] if stats_result else {"node_count": 0, "rel_count": 0}
            
            return {
                "nodes": nodes_result,
                "relationships": relationships_result,
                "node_count": stats["node_count"],
                "relationship_count": stats["rel_count"],
                "export_time": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Neo4j数据导出失败: {str(e)}")
            raise
    
    async def _export_redis_data(self) -> Dict[str, Any]:
        """导出Redis数据"""
        try:
            # 获取所有键
            keys = await self.redis.keys("*")
            
            redis_data = {}
            for key in keys:
                key_type = await self.redis.type(key)
                
                if key_type == "string":
                    redis_data[key] = await self.redis.get(key)
                elif key_type == "hash":
                    redis_data[key] = await self.redis.hgetall(key)
                elif key_type == "list":
                    redis_data[key] = await self.redis.lrange(key, 0, -1)
                elif key_type == "set":
                    redis_data[key] = list(await self.redis.smembers(key))
                elif key_type == "zset":
                    redis_data[key] = await self.redis.zrange(key, 0, -1, withscores=True)
            
            return {
                "data": redis_data,
                "key_count": len(keys),
                "export_time": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Redis数据导出失败: {str(e)}")
            return {"data": {}, "key_count": 0, "export_time": datetime.now().isoformat()}
    
    async def _restore_from_file(self, backup_file: Path, target_database: Optional[str] = None):
        """从备份文件恢复数据"""
        try:
            # 读取备份文件
            if backup_file.suffix == '.gz':
                with gzip.open(backup_file, 'rt', encoding='utf-8') as f:
                    backup_data = json.load(f)
            else:
                with open(backup_file, 'r', encoding='utf-8') as f:
                    backup_data = json.load(f)
            
            # 清空现有数据（谨慎操作）
            if not target_database:
                await self._clear_databases()
            
            # 恢复Neo4j数据
            await self._restore_neo4j_data(backup_data["neo4j"])
            
            # 恢复Redis数据
            await self._restore_redis_data(backup_data["redis"])
            
        except Exception as e:
            self.logger.error(f"数据恢复失败: {str(e)}")
            raise
    
    async def _restore_neo4j_data(self, neo4j_data: Dict[str, Any]):
        """恢复Neo4j数据"""
        try:
            # 恢复节点
            for node_data in neo4j_data["nodes"]:
                node = node_data["n"]
                labels = node_data["labels"]
                
                # 创建节点
                create_query = f"""
                CREATE (n:{':'.join(labels)})
                SET n = $properties
                RETURN id(n) as new_id
                """
                await self.neo4j.run(create_query, {"properties": dict(node)})
            
            # 恢复关系
            for rel_data in neo4j_data["relationships"]:
                rel = rel_data["r"]
                rel_type = rel_data["rel_type"]
                
                # 这里需要根据节点的原始ID映射到新ID
                # 简化实现，实际应用中需要维护ID映射表
                create_rel_query = f"""
                MATCH (a), (b)
                WHERE id(a) = $start_id AND id(b) = $end_id
                CREATE (a)-[r:{rel_type}]->(b)
                SET r = $properties
                """
                await self.neo4j.run(create_rel_query, {
                    "start_id": rel_data["start_id"],
                    "end_id": rel_data["end_id"],
                    "properties": dict(rel)
                })
            
        except Exception as e:
            self.logger.error(f"Neo4j数据恢复失败: {str(e)}")
            raise
    
    async def _restore_redis_data(self, redis_data: Dict[str, Any]):
        """恢复Redis数据"""
        try:
            for key, value in redis_data["data"].items():
                if isinstance(value, str):
                    await self.redis.set(key, value)
                elif isinstance(value, dict):
                    await self.redis.hset(key, mapping=value)
                elif isinstance(value, list):
                    if value:  # 避免空列表
                        await self.redis.lpush(key, *value)
                # 其他类型的处理...
                
        except Exception as e:
            self.logger.error(f"Redis数据恢复失败: {str(e)}")
            raise
    
    async def _calculate_checksum(self, file_path: Path) -> str:
        """计算文件校验和"""
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    
    async def _verify_backup(self, backup_file: Path, metadata: BackupMetadata) -> bool:
        """验证备份文件"""
        try:
            # 验证文件存在
            if not backup_file.exists():
                return False
            
            # 验证文件大小
            if backup_file.stat().st_size != metadata.file_size:
                return False
            
            # 验证校验和
            current_checksum = await self._calculate_checksum(backup_file)
            if current_checksum != metadata.checksum:
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"备份验证失败: {str(e)}")
            return False
    
    async def _cleanup_old_backups(self):
        """清理过期备份"""
        if not self.config.enabled:
            return
        
        cutoff_date = datetime.now() - timedelta(days=self.config.retention_days)
        
        # 找出过期备份
        expired_backups = [
            backup for backup in self.backup_history
            if backup.start_time < cutoff_date
        ]
        
        # 删除过期备份
        for backup in expired_backups:
            try:
                await self.delete_backup(backup.backup_id)
            except Exception as e:
                self.logger.error(f"清理过期备份失败: {backup.backup_id}, 错误: {str(e)}")
    
    async def _load_backup_history(self):
        """加载备份历史"""
        history_file = self.backup_dir / "backup_history.json"
        if history_file.exists():
            try:
                with open(history_file, 'r') as f:
                    history_data = json.load(f)
                
                self.backup_history = []
                for item in history_data:
                    metadata = BackupMetadata(
                        backup_id=item["backup_id"],
                        backup_type=BackupType(item["backup_type"]),
                        status=BackupStatus(item["status"]),
                        start_time=datetime.fromisoformat(item["start_time"]),
                        end_time=datetime.fromisoformat(item["end_time"]) if item.get("end_time") else None,
                        file_path=item.get("file_path", ""),
                        file_size=item.get("file_size", 0),
                        checksum=item.get("checksum", ""),
                        error_message=item.get("error_message", ""),
                        metadata=item.get("metadata", {})
                    )
                    self.backup_history.append(metadata)
                    
            except Exception as e:
                self.logger.error(f"加载备份历史失败: {str(e)}")
    
    async def _save_backup_history(self):
        """保存备份历史"""
        history_file = self.backup_dir / "backup_history.json"
        try:
            history_data = []
            for backup in self.backup_history:
                history_data.append({
                    "backup_id": backup.backup_id,
                    "backup_type": backup.backup_type.value,
                    "status": backup.status.value,
                    "start_time": backup.start_time.isoformat(),
                    "end_time": backup.end_time.isoformat() if backup.end_time else None,
                    "file_path": backup.file_path,
                    "file_size": backup.file_size,
                    "checksum": backup.checksum,
                    "error_message": backup.error_message,
                    "metadata": backup.metadata
                })
            
            with open(history_file, 'w') as f:
                json.dump(history_data, f, indent=2)
                
        except Exception as e:
            self.logger.error(f"保存备份历史失败: {str(e)}")
    
    async def _clear_databases(self):
        """清空数据库（谨慎操作）"""
        # 清空Neo4j
        await self.neo4j.run("MATCH (n) DETACH DELETE n")
        
        # 清空Redis
        await self.redis.flushdb()
    
    async def _upload_backup(self, backup_file: Path, metadata: BackupMetadata):
        """上传备份到远程存储"""
        if self.config.storage_backend == "s3" and self.s3_client:
            bucket = self.config.storage_config.get('bucket')
            key = f"backups/{metadata.backup_id}/{backup_file.name}"
            
            self.s3_client.upload_file(str(backup_file), bucket, key)
            
        elif self.config.storage_backend == "minio" and self.minio:
            bucket = self.config.storage_config.get('bucket', 'backups')
            object_name = f"{metadata.backup_id}/{backup_file.name}"
            
            await self.minio.upload_file(bucket, object_name, str(backup_file))
    
    async def _download_backup(self, metadata: BackupMetadata) -> Path:
        """从远程存储下载备份"""
        backup_file = self.backup_dir / f"{metadata.backup_id}.json"
        
        if self.config.storage_backend == "s3" and self.s3_client:
            bucket = self.config.storage_config.get('bucket')
            key = f"backups/{metadata.backup_id}/{backup_file.name}"
            
            self.s3_client.download_file(bucket, key, str(backup_file))
            
        elif self.config.storage_backend == "minio" and self.minio:
            bucket = self.config.storage_config.get('bucket', 'backups')
            object_name = f"{metadata.backup_id}/{backup_file.name}"
            
            await self.minio.download_file(bucket, object_name, str(backup_file))
        
        return backup_file
    
    async def _delete_remote_backup(self, metadata: BackupMetadata):
        """删除远程备份"""
        if self.config.storage_backend == "s3" and self.s3_client:
            bucket = self.config.storage_config.get('bucket')
            key = f"backups/{metadata.backup_id}/"
            
            # 删除S3对象
            response = self.s3_client.list_objects_v2(Bucket=bucket, Prefix=key)
            if 'Contents' in response:
                objects = [{'Key': obj['Key']} for obj in response['Contents']]
                self.s3_client.delete_objects(Bucket=bucket, Delete={'Objects': objects})
                
        elif self.config.storage_backend == "minio" and self.minio:
            bucket = self.config.storage_config.get('bucket', 'backups')
            object_name = f"{metadata.backup_id}/"
            
            # 删除MinIO对象
            await self.minio.remove_objects(bucket, [object_name]) 