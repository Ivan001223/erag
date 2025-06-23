"""应用设置配置"""

from functools import lru_cache
from typing import Optional
from pydantic import Field, validator
from pydantic_settings import BaseSettings
import os
import secrets


class Settings(BaseSettings):
    """应用设置类"""
    
    # 应用基础配置
    app_name: str = Field(default="Enterprise Knowledge Base", env="APP_NAME")
    app_version: str = Field(default="1.0.0", env="APP_VERSION")
    app_debug: bool = Field(default=False, env="APP_DEBUG")
    app_host: str = Field(default="0.0.0.0", env="APP_HOST")
    app_port: int = Field(default=8000, env="APP_PORT")
    
    # 安全配置 - 强制从环境变量读取
    secret_key: str = Field(env="SECRET_KEY")
    access_token_expire_minutes: int = Field(default=30, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    refresh_token_expire_days: int = Field(default=7, env="REFRESH_TOKEN_EXPIRE_DAYS")
    
    # Neo4j 配置 - 移除默认密码
    neo4j_url: str = Field(env="NEO4J_URL")
    neo4j_user: str = Field(env="NEO4J_USER")
    neo4j_password: str = Field(env="NEO4J_PASSWORD")
    
    # MySQL 数据库配置 - 移除默认密码
    mysql_host: str = Field(env="MYSQL_HOST")
    mysql_port: int = Field(default=3306, env="MYSQL_PORT")
    mysql_user: str = Field(env="MYSQL_USER")
    mysql_password: str = Field(env="MYSQL_PASSWORD")
    mysql_database: str = Field(env="MYSQL_DATABASE")
    
    # StarRocks 配置
    starrocks_host: str = Field(default="192.168.0.101", env="STARROCKS_HOST")
    starrocks_port: int = Field(default=9030, env="STARROCKS_PORT")
    starrocks_user: str = Field(default="root", env="STARROCKS_USER")
    starrocks_password: str = Field(default="", env="STARROCKS_PASSWORD")
    starrocks_database: str = Field(default="knowledge_base", env="STARROCKS_DATABASE")
    
    # Redis 配置 - 移除默认密码
    redis_url: str = Field(env="REDIS_URL")
    redis_password: Optional[str] = Field(env="REDIS_PASSWORD")
    redis_db: int = Field(default=0, env="REDIS_DB")
    
    # MinIO 配置
    minio_endpoint: str = Field(default="192.168.0.101:9000", env="MINIO_ENDPOINT")
    minio_access_key: str = Field(default="minioadmin", env="MINIO_ACCESS_KEY")
    minio_secret_key: str = Field(default="minioadmin123", env="MINIO_SECRET_KEY")
    minio_bucket_name: str = Field(default="knowledge-base", env="MINIO_BUCKET_NAME")
    minio_secure: bool = Field(default=False, env="MINIO_SECURE")
    
    # LLM 配置
    llm_api_key: Optional[str] = Field(default=None, env="LLM_API_KEY")
    llm_model: str = Field(default="qwen-max", env="LLM_MODEL")
    llm_base_url: str = Field(
        default="https://dashscope.aliyuncs.com/compatible-mode/v1",
        env="LLM_BASE_URL"
    )
    llm_temperature: float = Field(default=0.7, env="LLM_TEMPERATURE")
    llm_max_tokens: int = Field(default=2048, env="LLM_MAX_TOKENS")
    
    # OCR 服务配置
    ocr_service_url: str = Field(default="http://localhost:8002", env="OCR_SERVICE_URL")
    ocr_max_file_size: int = Field(default=10485760, env="OCR_MAX_FILE_SIZE")  # 10MB
    ocr_supported_formats: str = Field(
        default="pdf,png,jpg,jpeg,tiff,bmp",
        env="OCR_SUPPORTED_FORMATS"
    )
    
    # Flink 配置
    flink_jobmanager_url: str = Field(
        default="http://192.168.0.101:8081",
        env="FLINK_JOBMANAGER_URL"
    )
    flink_parallelism: int = Field(default=2, env="FLINK_PARALLELISM")
    flink_checkpoint_interval: int = Field(default=60000, env="FLINK_CHECKPOINT_INTERVAL")
    
    # 日志配置
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_format: str = Field(default="json", env="LOG_FORMAT")
    log_file_path: str = Field(default="logs/app.log", env="LOG_FILE_PATH")
    log_max_size: int = Field(default=10485760, env="LOG_MAX_SIZE")  # 10MB
    log_backup_count: int = Field(default=5, env="LOG_BACKUP_COUNT")
    
    # 向量配置
    vector_dimension: int = Field(default=1536, env="VECTOR_DIMENSION")
    vector_similarity_threshold: float = Field(
        default=0.7,
        env="VECTOR_SIMILARITY_THRESHOLD"
    )
    vector_top_k: int = Field(default=10, env="VECTOR_TOP_K")
    
    # 知识图谱配置
    kg_confidence_threshold: float = Field(
        default=0.8,
        env="KG_CONFIDENCE_THRESHOLD"
    )
    kg_max_entities_per_document: int = Field(
        default=100,
        env="KG_MAX_ENTITIES_PER_DOCUMENT"
    )
    kg_max_relations_per_document: int = Field(
        default=200,
        env="KG_MAX_RELATIONS_PER_DOCUMENT"
    )
    
    # ETL 配置
    etl_batch_size: int = Field(default=100, env="ETL_BATCH_SIZE")
    etl_retry_attempts: int = Field(default=3, env="ETL_RETRY_ATTEMPTS")
    etl_retry_delay: int = Field(default=5, env="ETL_RETRY_DELAY")
    
    # 缓存配置
    cache_ttl: int = Field(default=3600, env="CACHE_TTL")  # 1小时
    cache_max_size: int = Field(default=1000, env="CACHE_MAX_SIZE")
    
    # 监控配置
    metrics_enabled: bool = Field(default=True, env="METRICS_ENABLED")
    metrics_port: int = Field(default=9090, env="METRICS_PORT")
    health_check_interval: int = Field(default=30, env="HEALTH_CHECK_INTERVAL")
    
    # Dify 集成配置
    dify_api_url: str = Field(default="http://localhost:5001", env="DIFY_API_URL")
    dify_api_key: Optional[str] = Field(default=None, env="DIFY_API_KEY")
    dify_workspace_id: Optional[str] = Field(default=None, env="DIFY_WORKSPACE_ID")
    
    # MySQL URL (用于元数据存储)
    mysql_url: Optional[str] = Field(default=None, env="MYSQL_URL")
    
    @validator('secret_key')
    def validate_secret_key(cls, v):
        """验证密钥强度"""
        if not v:
            raise ValueError("SECRET_KEY必须设置")
        if len(v) < 32:
            raise ValueError("SECRET_KEY长度至少32个字符")
        return v
    
    @validator('neo4j_password', 'mysql_password')
    def validate_passwords(cls, v):
        """验证数据库密码强度"""
        if not v:
            raise ValueError("数据库密码不能为空")
        if len(v) < 12:
            raise ValueError("数据库密码长度至少12个字符")
        return v
    
    def generate_secure_secret_key(self) -> str:
        """生成安全的密钥"""
        return secrets.token_urlsafe(32)
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
    
    def get_mysql_url(self) -> str:
        """获取 MySQL 连接 URL"""
        if self.mysql_url:
            return self.mysql_url
        
        return (
            f"mysql+pymysql://{self.mysql_user}:{self.mysql_password}"
            f"@{self.mysql_host}:{self.mysql_port}/{self.mysql_database}"
        )
    
    def get_ocr_supported_formats(self) -> list[str]:
        """获取支持的 OCR 格式列表"""
        return [fmt.strip().lower() for fmt in self.ocr_supported_formats.split(",")]
    
    def is_production(self) -> bool:
        """判断是否为生产环境"""
        return not self.app_debug
    
    def get_log_config(self) -> dict:
        """获取日志配置"""
        return {
            "level": self.log_level,
            "format": self.log_format,
            "file_path": self.log_file_path,
            "max_size": self.log_max_size,
            "backup_count": self.log_backup_count
        }


@lru_cache()
def get_settings() -> Settings:
    """获取设置实例（单例模式）"""
    return Settings()