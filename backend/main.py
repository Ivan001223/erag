"""FastAPI 主应用程序"""

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import time

from backend.config.settings import get_settings
from backend.utils.logger import get_logger
from backend.api.v1 import (
    knowledge_routes,
)
from backend.connectors.neo4j_client import Neo4jClient
from backend.connectors.redis_client import RedisClient
from backend.connectors.minio_client import MinIOClient

# 获取配置和日志
settings = get_settings()
logger = get_logger(__name__)

# 全局连接器实例
connectors = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时初始化连接器
    logger.info("正在初始化应用连接器...")
    
    try:
        # 初始化 Neo4j 连接
        connectors["neo4j"] = Neo4jClient(
            uri=settings.neo4j_url,
            user=settings.neo4j_user,
            password=settings.neo4j_password
        )
        await connectors["neo4j"].connect()
        logger.info("Neo4j 连接已建立")
        
        # 初始化 Redis 连接
        connectors["redis"] = RedisClient(
            url=settings.redis_url,
            password=settings.redis_password
        )
        await connectors["redis"].connect()
        logger.info("Redis 连接已建立")
        
        # StarRocks连接器已移除，核心业务模型已迁移到SQLAlchemy
        # 如需大数据分析功能，请使用专门的分析服务
        
        # 初始化 MinIO 连接
        connectors["minio"] = MinIOClient(
            endpoint=settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure
        )
        await connectors["minio"].connect()
        logger.info("MinIO 连接已建立")
        
        logger.info("所有连接器初始化完成")
        
    except Exception as e:
        logger.error(f"连接器初始化失败: {str(e)}")
        raise
    
    yield
    
    # 关闭时清理连接器
    logger.info("正在关闭应用连接器...")
    
    for name, connector in connectors.items():
        try:
            await connector.close()
            logger.info(f"{name} 连接已关闭")
        except Exception as e:
            logger.error(f"关闭 {name} 连接时出错: {str(e)}")
    
    logger.info("应用关闭完成")


# 创建 FastAPI 应用
app = FastAPI(
    title=settings.app_name,
    description="企业级智能知识库系统 API",
    version=settings.app_version,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)

# 添加 CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境中应该限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 添加受信任主机中间件
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"]  # 生产环境中应该限制具体主机
)


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """添加请求处理时间头"""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """记录请求日志"""
    start_time = time.time()
    
    # 记录请求信息
    logger.info(
        f"请求开始: {request.method} {request.url.path}",
        extra={
            "method": request.method,
            "path": request.url.path,
            "query_params": str(request.query_params),
            "client_ip": request.client.host if request.client else None
        }
    )
    
    response = await call_next(request)
    
    # 记录响应信息
    process_time = time.time() - start_time
    logger.info(
        f"请求完成: {request.method} {request.url.path} - {response.status_code}",
        extra={
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "process_time": process_time
        }
    )
    
    return response


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """全局异常处理器"""
    logger.error(
        f"未处理的异常: {str(exc)}",
        extra={
            "method": request.method,
            "path": request.url.path,
            "exception_type": type(exc).__name__
        },
        exc_info=True
    )
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "内部服务器错误",
            "message": "服务器遇到了一个错误，请稍后重试",
            "request_id": getattr(request.state, "request_id", None)
        }
    )


# 健康检查端点
@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "version": settings.app_version,
        "services": {
            "neo4j": "connected" if "neo4j" in connectors else "disconnected",
            "redis": "connected" if "redis" in connectors else "disconnected",
            # StarRocks已移除，核心业务模型已迁移到SQLAlchemy
            "minio": "connected" if "minio" in connectors else "disconnected"
        }
    }


# 根路径
@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "欢迎使用企业级智能知识库系统 API",
        "version": settings.app_version,
        "docs": "/docs",
        "health": "/health"
    }


# 注册 API 路由
app.include_router(
    knowledge_routes.router,
    prefix="/api/v1",
    tags=["knowledge"]
)

# 其他路由模块将在实现后添加


def get_connector(connector_type: str):
    """获取连接器实例"""
    return connectors.get(connector_type)


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.app_debug,
        log_level=settings.log_level.lower()
    )