"""系统常量定义"""

from enum import Enum
from typing import Dict, List


# 实体类型常量
class EntityType(str, Enum):
    """实体类型枚举"""
    PERSON = "PERSON"  # 人员
    ORGANIZATION = "ORGANIZATION"  # 组织机构
    LOCATION = "LOCATION"  # 地点
    PRODUCT = "PRODUCT"  # 产品
    CONCEPT = "CONCEPT"  # 概念
    EVENT = "EVENT"  # 事件
    TIME = "TIME"  # 时间
    MONEY = "MONEY"  # 金额
    PERCENT = "PERCENT"  # 百分比
    DOCUMENT = "DOCUMENT"  # 文档
    TECHNOLOGY = "TECHNOLOGY"  # 技术
    PROCESS = "PROCESS"  # 流程
    REGULATION = "REGULATION"  # 法规
    STANDARD = "STANDARD"  # 标准
    METRIC = "METRIC"  # 指标


# 关系类型常量
class RelationType(str, Enum):
    """关系类型枚举"""
    BELONGS_TO = "BELONGS_TO"  # 属于
    WORKS_FOR = "WORKS_FOR"  # 工作于
    LOCATED_IN = "LOCATED_IN"  # 位于
    MANAGES = "MANAGES"  # 管理
    REPORTS_TO = "REPORTS_TO"  # 汇报给
    COLLABORATES_WITH = "COLLABORATES_WITH"  # 协作
    DEPENDS_ON = "DEPENDS_ON"  # 依赖于
    IMPLEMENTS = "IMPLEMENTS"  # 实现
    USES = "USES"  # 使用
    PRODUCES = "PRODUCES"  # 生产
    CONTAINS = "CONTAINS"  # 包含
    PART_OF = "PART_OF"  # 是...的一部分
    SIMILAR_TO = "SIMILAR_TO"  # 类似于
    RELATED_TO = "RELATED_TO"  # 相关于
    CAUSES = "CAUSES"  # 导致
    AFFECTS = "AFFECTS"  # 影响
    FOLLOWS = "FOLLOWS"  # 跟随
    PRECEDES = "PRECEDES"  # 先于
    MENTIONS = "MENTIONS"  # 提及
    REFERENCES = "REFERENCES"  # 引用


# 文档类型常量
class DocumentType(str, Enum):
    """文档类型枚举"""
    PDF = "pdf"
    WORD = "docx"
    EXCEL = "xlsx"
    POWERPOINT = "pptx"
    TEXT = "txt"
    MARKDOWN = "md"
    HTML = "html"
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"


# 文档状态常量
class DocumentStatus(str, Enum):
    """文档状态枚举"""
    PENDING = "pending"  # 待处理
    PROCESSING = "processing"  # 处理中
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"  # 失败
    ARCHIVED = "archived"  # 已归档
    DELETED = "deleted"  # 已删除


# 文档块类型常量
class ChunkType(str, Enum):
    """文档块类型枚举"""
    TEXT = "text"  # 文本块
    IMAGE = "image"  # 图像块
    TABLE = "table"  # 表格块
    HEADER = "header"  # 标题块
    FOOTER = "footer"  # 页脚块
    PARAGRAPH = "paragraph"  # 段落块
    LIST = "list"  # 列表块
    CODE = "code"  # 代码块


class TaskPriority(str, Enum):
    """任务优先级"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    NORMAL = "normal"
    URGENT = "urgent"
    CRITICAL = "critical"

class TaskCategory(str, Enum):
    """任务分类"""
    SYSTEM = "system"
    USER = "user"
    SCHEDULED = "scheduled"
    WEBHOOK = "webhook"
    BATCH = "batch"
    MAINTENANCE = "maintenance"
    OTHER = "other"

class ExecutionMode(str, Enum):
    """执行模式"""
    SYNC = "sync"
    ASYNC = "async"


# 任务相关常量
TASK_MAX_RETRIES = 3
TASK_RETRY_DELAY = 60  # 秒
TASK_TIMEOUT = 3600  # 秒

# 任务状态常量
class TaskStatus(str, Enum):
    """任务状态枚举"""
    PENDING = "pending"  # 待处理
    RUNNING = "running"  # 运行中
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"  # 失败
    CANCELLED = "cancelled"  # 已取消
    PAUSED = "paused"  # 已暂停


# 任务类型常量
class TaskType(str, Enum):
    """任务类型枚举"""
    OCR_PROCESSING = "ocr_processing"  # OCR处理
    ENTITY_EXTRACTION = "entity_extraction"  # 实体提取
    RELATION_EXTRACTION = "relation_extraction"  # 关系提取
    VECTOR_EMBEDDING = "vector_embedding"  # 向量嵌入
    KNOWLEDGE_GRAPH_BUILD = "knowledge_graph_build"  # 知识图谱构建
    DATA_SYNC = "data_sync"  # 数据同步
    INDEX_BUILD = "index_build"  # 索引构建
    QUALITY_CHECK = "quality_check"  # 质量检查


# 数据源类型常量
class DataSourceType(str, Enum):
    """数据源类型枚举"""
    FILE_UPLOAD = "file_upload"  # 文件上传
    DATABASE = "database"  # 数据库
    API = "api"  # API接口
    WEB_CRAWL = "web_crawl"  # 网页爬取
    EMAIL = "email"  # 邮件
    CHAT = "chat"  # 聊天记录
    SENSOR = "sensor"  # 传感器数据


# 置信度等级常量
class ConfidenceLevel(str, Enum):
    """置信度等级枚举"""
    VERY_LOW = "very_low"  # 0.0 - 0.2
    LOW = "low"  # 0.2 - 0.4
    MEDIUM = "medium"  # 0.4 - 0.6
    HIGH = "high"  # 0.6 - 0.8
    VERY_HIGH = "very_high"  # 0.8 - 1.0


# 查询类型常量
class QueryType(str, Enum):
    """查询类型枚举"""
    VECTOR_SEARCH = "vector_search"  # 向量搜索
    GRAPH_QUERY = "graph_query"  # 图查询
    HYBRID_SEARCH = "hybrid_search"  # 混合搜索
    SEMANTIC_SEARCH = "semantic_search"  # 语义搜索
    KEYWORD_SEARCH = "keyword_search"  # 关键词搜索


# 日志级别常量
class LogLevel(str, Enum):
    """日志级别枚举"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


# 缓存键前缀枚举
class CacheKeyPrefix(str, Enum):
    """缓存键前缀枚举"""
    DEFAULT = "default:"
    ENTITY = "entity:"
    RELATION = "relation:"
    DOCUMENT = "document:"
    VECTOR = "vector:"
    QUERY = "query:"
    USER = "user:"
    SESSION = "session:"
    TASK = "task:"
    METRICS = "metrics:"
    EMBEDDING = "embedding:"
    GRAPH = "graph:"
    OCR = "ocr:"
    LLM = "llm:"
    CONFIG = "config:"


# 缓存键前缀字典（向后兼容）
CACHE_PREFIXES = {
    "entity": "entity:",
    "relation": "relation:",
    "document": "document:",
    "vector": "vector:",
    "query": "query:",
    "user": "user:",
    "session": "session:",
    "task": "task:",
    "metrics": "metrics:"
}

# 默认分页参数
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100
DEFAULT_PAGE = 1

# 文件大小限制（字节）
FILE_SIZE_LIMITS = {
    "image": 10 * 1024 * 1024,  # 10MB
    "document": 50 * 1024 * 1024,  # 50MB
    "video": 500 * 1024 * 1024,  # 500MB
    "audio": 100 * 1024 * 1024,  # 100MB
}

# 支持的文件格式
SUPPORTED_FORMATS = {
    "image": ["jpg", "jpeg", "png", "bmp", "tiff", "gif"],
    "document": ["pdf", "docx", "doc", "xlsx", "xls", "pptx", "ppt", "txt", "md"],
    "video": ["mp4", "avi", "mov", "wmv", "flv", "mkv"],
    "audio": ["mp3", "wav", "flac", "aac", "ogg"]
}

# 支持的文件格式（扁平化列表）
SUPPORTED_FILE_FORMATS = [
    "jpg", "jpeg", "png", "bmp", "tiff", "gif",  # 图像
    "pdf", "docx", "doc", "xlsx", "xls", "pptx", "ppt", "txt", "md",  # 文档
    "mp4", "avi", "mov", "wmv", "flv", "mkv",  # 视频
    "mp3", "wav", "flac", "aac", "ogg"  # 音频
]

# OCR 相关常量
OCR_CONSTANTS = {
    "max_image_size": (4096, 4096),  # 最大图像尺寸
    "min_confidence": 0.5,  # 最小置信度
    "supported_languages": ["zh", "en", "ja", "ko"],  # 支持的语言
    "batch_size": 10,  # 批处理大小
}

# 向量相关常量
VECTOR_CONSTANTS = {
    "default_dimension": 1536,  # 默认向量维度
    "similarity_threshold": 0.7,  # 相似度阈值
    "max_results": 100,  # 最大返回结果数
    "index_type": "HNSW",  # 索引类型
}

# 知识图谱相关常量
KG_CONSTANTS = {
    "max_depth": 5,  # 最大查询深度
    "max_nodes": 1000,  # 最大节点数
    "max_edges": 5000,  # 最大边数
    "community_algorithm": "louvain",  # 社区发现算法
}

# 知识图谱配置
KG_CONFIDENCE_THRESHOLD = 0.7
KG_MAX_ENTITIES_PER_DOCUMENT = 100
KG_MAX_RELATIONS_PER_DOCUMENT = 200

# 知识图谱常量
KNOWLEDGE_GRAPH_MAX_DEPTH = 5
KNOWLEDGE_GRAPH_MAX_NODES = 1000

# 用户相关枚举
class UserRole(str, Enum):
    """用户角色"""
    ADMIN = "admin"
    USER = "user"
    GUEST = "guest"
    VIEWER = "viewer"
    EDITOR = "editor"
    MANAGER = "manager"


class UserStatus(str, Enum):
    """用户状态"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING = "pending"
    BANNED = "banned"


class AuthProvider(str, Enum):
    """认证提供商"""
    LOCAL = "local"
    OAUTH2 = "oauth2"
    LDAP = "ldap"
    SSO = "sso"
    GOOGLE = "google"
    GITHUB = "github"
    MICROSOFT = "microsoft"


# JWT 相关常量
JWT_ALGORITHM = "HS256"
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = 30
JWT_REFRESH_TOKEN_EXPIRE_DAYS = 7

# API 相关常量
API_CONSTANTS = {
    "rate_limit": 1000,  # 每分钟请求限制
    "timeout": 30,  # 请求超时时间（秒）
    "max_retries": 3,  # 最大重试次数
    "retry_delay": 1,  # 重试延迟（秒）
}

# 错误代码常量
ERROR_CODES = {
    "VALIDATION_ERROR": "E001",
    "AUTHENTICATION_ERROR": "E002",
    "AUTHORIZATION_ERROR": "E003",
    "RESOURCE_NOT_FOUND": "E004",
    "RESOURCE_CONFLICT": "E005",
    "INTERNAL_SERVER_ERROR": "E006",
    "SERVICE_UNAVAILABLE": "E007",
    "RATE_LIMIT_EXCEEDED": "E008",
    "INVALID_FILE_FORMAT": "E009",
    "FILE_TOO_LARGE": "E010",
    "OCR_PROCESSING_ERROR": "E011",
    "VECTOR_PROCESSING_ERROR": "E012",
    "GRAPH_PROCESSING_ERROR": "E013",
    "LLM_PROCESSING_ERROR": "E014",
    "DATABASE_ERROR": "E015",
    "CACHE_ERROR": "E016",
    "EXTERNAL_API_ERROR": "E017",
}

# 成功消息常量
SUCCESS_MESSAGES = {
    "ENTITY_CREATED": "实体创建成功",
    "ENTITY_UPDATED": "实体更新成功",
    "ENTITY_DELETED": "实体删除成功",
    "RELATION_CREATED": "关系创建成功",
    "RELATION_UPDATED": "关系更新成功",
    "RELATION_DELETED": "关系删除成功",
    "DOCUMENT_UPLOADED": "文档上传成功",
    "DOCUMENT_PROCESSED": "文档处理成功",
    "TASK_CREATED": "任务创建成功",
    "TASK_COMPLETED": "任务完成",
    "SEARCH_COMPLETED": "搜索完成",
    "SYNC_COMPLETED": "同步完成",
}

# 正则表达式模式
REGEX_PATTERNS = {
    "email": r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",
    "phone": r"^1[3-9]\d{9}$",
    "id_card": r"^[1-9]\d{5}(18|19|20)\d{2}((0[1-9])|(1[0-2]))(([0-2][1-9])|10|20|30|31)\d{3}[0-9Xx]$",
    "url": r"^https?://[\w\.-]+\.[a-zA-Z]{2,}(/.*)?$",
    "ip": r"^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$",
}

# 时间格式常量
TIME_FORMATS = {
    "datetime": "%Y-%m-%d %H:%M:%S",
    "date": "%Y-%m-%d",
    "time": "%H:%M:%S",
    "iso": "%Y-%m-%dT%H:%M:%S.%fZ",
    "timestamp": "%Y%m%d_%H%M%S",
}

# 系统配置常量
SYSTEM_CONFIG = {
    "version": "1.0.0",
    "name": "Enterprise Knowledge Base",
    "description": "企业级智能知识库系统",
    "author": "ERAG Team",
    "license": "MIT",
    "repository": "https://github.com/your-org/erag",
    "documentation": "https://docs.erag.com",
}

# 支持的文档格式
SUPPORTED_DOCUMENT_FORMATS = [
    "pdf", "docx", "doc", "xlsx", "xls", "pptx", "ppt", "txt", "md", "html"
]

# 最大文件大小（字节）
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

# 默认文档块大小
DEFAULT_CHUNK_SIZE = 1000

# 默认文档块重叠大小
DEFAULT_CHUNK_OVERLAP = 200