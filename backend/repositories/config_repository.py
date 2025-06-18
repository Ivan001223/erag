"""配置数据仓库"""

from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc, text
from sqlalchemy.exc import SQLAlchemyError
import json
import uuid
from datetime import datetime

from backend.utils.logger import get_logger
from backend.config.database import get_db
from backend.models.config import SystemConfig

logger = get_logger(__name__)


class ConfigRepository:
    """配置数据仓库"""
    
    def __init__(self, db: Session):
        self.db = db
    
    async def get_config(self, key: str) -> Optional[Any]:
        """
        获取配置值
        """
        try:
            config = self.db.query(SystemConfig).filter(
                SystemConfig.config_key == key,
                SystemConfig.is_deleted == False
            ).first()
            
            if config:
                return config.get_parsed_value()
            return None
        except Exception as e:
            logger.error(f"获取配置失败: {str(e)}")
            return None
    
    async def set_config(self, key: str, value: Any, description: Optional[str] = None) -> bool:
        """设置配置值"""
        try:
            # 检查配置是否已存在
            existing_config = self.db.query(SystemConfig).filter(
                SystemConfig.config_key == key,
                SystemConfig.is_deleted == False
            ).first()
            
            if existing_config:
                # 更新现有配置
                existing_config.set_value(value)
                if description is not None:
                    existing_config.description = description
                existing_config.updated_at = datetime.utcnow()
            else:
                # 创建新配置
                new_config = SystemConfig(
                    id=str(uuid.uuid4()),
                    config_key=key,
                    description=description,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                    is_deleted=False
                )
                new_config.set_value(value)
                self.db.add(new_config)
            
            self.db.commit()
            logger.info(f"Set config: {key} = {value}")
            return True
            
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Failed to set config {key}: {str(e)}")
            return False
    
    async def delete_config(self, key: str) -> bool:
        """删除配置（软删除）"""
        try:
            config = self.db.query(SystemConfig).filter(
                SystemConfig.config_key == key,
                SystemConfig.is_deleted == False
            ).first()
            
            if config:
                config.is_deleted = True
                config.updated_at = datetime.utcnow()
                self.db.commit()
                logger.info(f"Deleted config: {key}")
                return True
            
            return False
            
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Failed to delete config {key}: {str(e)}")
            return False
    
    async def get_all_configs(self, prefix: Optional[str] = None) -> Dict[str, Any]:
        """获取所有配置"""
        try:
            query = self.db.query(SystemConfig).filter(
                SystemConfig.is_deleted == False
            )
            
            if prefix:
                query = query.filter(SystemConfig.config_key.like(f"{prefix}%"))
            
            configs = {}
            for config in query.all():
                configs[config.config_key] = config.get_parsed_value()
            
            return configs
            
        except Exception as e:
            logger.error(f"获取所有配置失败: {str(e)}")
            return {}
    
    async def get_config_list(
        self, 
        prefix: Optional[str] = None, 
        limit: int = 100, 
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        获取配置列表（分页）
        """
        try:
            query = self.db.query(SystemConfig).filter(
                SystemConfig.is_deleted == False
            ).order_by(SystemConfig.config_key)
            
            if prefix:
                query = query.filter(SystemConfig.config_key.like(f"{prefix}%"))
            
            query = query.limit(limit).offset(offset)
            
            configs = []
            for config in query.all():
                configs.append({
                    "key": config.config_key,
                    "value": config.get_parsed_value(),
                    "description": config.description,
                    "created_at": config.created_at,
                    "updated_at": config.updated_at
                })
            
            return configs
            
        except Exception as e:
            logger.error(f"获取配置列表失败: {str(e)}")
            return []
    
    async def batch_set_configs(self, configs: Dict[str, Any]) -> int:
        """批量设置配置"""
        try:
            success_count = 0
            
            for key, value in configs.items():
                if await self.set_config(key, value):
                    success_count += 1
            
            logger.info(f"Batch set {success_count}/{len(configs)} configs")
            return success_count
            
        except Exception as e:
            logger.error(f"Failed to batch set configs: {str(e)}")
            return 0
    
    async def get_config_by_category(self, category: str) -> Dict[str, Any]:
        """根据分类获取配置"""
        return await self.get_all_configs(prefix=f"{category}.")
    
    async def init_default_configs(self) -> bool:
        """初始化默认配置"""
        try:
            default_configs = {
                'system.name': 'ERAG System',
                'system.version': '1.0.0',
                'system.description': 'Enterprise RAG System',
                'embedding.model': 'text-embedding-ada-002',
                'embedding.dimension': 1536,
                'embedding.batch_size': 100,
                'llm.model': 'gpt-3.5-turbo',
                'llm.temperature': 0.7,
                'llm.max_tokens': 2048,
                'search.default_limit': 20,
                'search.similarity_threshold': 0.7,
                'chunk.max_size': 1000,
                'chunk.overlap_size': 200,
                'upload.max_file_size': 50 * 1024 * 1024,  # 50MB
                'upload.allowed_extensions': ['.txt', '.pdf', '.docx', '.md'],
                'cache.ttl': 3600,  # 1 hour
                'rate_limit.requests_per_minute': 60
            }
            
            success_count = 0
            for key, value in default_configs.items():
                # 只设置不存在的配置
                existing_value = await self.get_config(key)
                if existing_value is None:
                    if await self.set_config(key, value, f"Default {key} configuration"):
                        success_count += 1
            
            logger.info(f"Initialized {success_count} default configs")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize default configs: {str(e)}")
            return False
    
    async def backup_configs(self) -> Dict[str, Any]:
        """备份所有配置"""
        try:
            configs = await self.get_all_configs()
            backup_data = {
                'timestamp': datetime.utcnow().isoformat(),
                'configs': configs
            }
            
            logger.info(f"Backed up {len(configs)} configs")
            return backup_data
            
        except Exception as e:
            logger.error(f"Failed to backup configs: {str(e)}")
            return {}
    
    async def restore_configs(self, backup_data: Dict[str, Any]) -> bool:
        """从备份恢复配置"""
        try:
            if 'configs' not in backup_data:
                logger.error("Invalid backup data format")
                return False
            
            configs = backup_data['configs']
            success_count = await self.batch_set_configs(configs)
            
            logger.info(f"Restored {success_count}/{len(configs)} configs")
            return success_count == len(configs)
            
        except Exception as e:
            logger.error(f"Failed to restore configs: {str(e)}")
            return False
    
    async def get_config_statistics(self) -> Dict[str, Any]:
        """获取配置统计信息"""
        try:
            # 总配置数
            total_count = self.db.query(SystemConfig).filter(
                SystemConfig.is_deleted == False
            ).count()
            
            # 按前缀分组统计
            configs = self.db.query(SystemConfig).filter(
                SystemConfig.is_deleted == False
            ).all()
            
            categories = {}
            for config in configs:
                category = config.config_key.split('.')[0] if '.' in config.config_key else config.config_key
                categories[category] = categories.get(category, 0) + 1
            
            # 最近更新的配置
            recent_configs_query = self.db.query(SystemConfig).filter(
                SystemConfig.is_deleted == False
            ).order_by(SystemConfig.updated_at.desc()).limit(5)
            
            recent_configs = [
                {"key": config.config_key, "updated_at": config.updated_at} 
                for config in recent_configs_query.all()
            ]
            
            return {
                "total_count": total_count,
                "categories": categories,
                "recent_configs": recent_configs
            }
            
        except Exception as e:
            logger.error(f"获取配置统计失败: {str(e)}")
            return {
                "total_count": 0,
                "categories": {},
                "recent_configs": []
            }