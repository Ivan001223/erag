"""FastAPI 主应用程序

优化后的主应用程序，集成了完整的服务架构、健康检查和监控功能。
"""

import uvicorn
import asyncio
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from typing import Dict, Any
import time
import traceback

from backend.config.settings import get_settings
from backend.utils.logger import get_logger
from backend.api.v1 import knowledge_routes
from backend.api import etl_routes, knowledge_graph, ocr
from backend.connectors.neo4j_client import Neo4jClient
from backend.connectors.redis_client import RedisClient
from backend.connectors.minio_client import MinIOClient
from backend.core.base_service import service_registry
from backend.services.knowledge_service import KnowledgeService
from backend.services.llm_service import LLMService
from backend.services.vector_service import VectorService
from backend.services.document_service import DocumentService
from backend.config.database import get_db

# 获取配置和日志
settings = get_settings()
logger = get_logger(__name__)

# 全局连接器实例
connectors = {}
app_state = {
    "startup_time": None,
    "shutdown_time": None,
    "request_count": 0,
    "error_count": 0
}


async def init_connectors():
    """初始化连接器"""
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


async def init_services():
    """初始化服务"""
    logger.info("正在初始化应用服务...")
    
    try:
        # 获取数据库会话
        db_session = next(get_db())
        
        # 初始化核心服务
        llm_service = LLMService()
        vector_service = VectorService(connectors["redis"])
        document_service = DocumentService(connectors["minio"], db_session)
        knowledge_service = KnowledgeService(
            neo4j_client=connectors["neo4j"],
            redis_client=connectors["redis"],
            db_session=db_session,
            llm_service=llm_service,
            vector_service=vector_service
        )
        
        # 注册服务
        service_registry.register(llm_service, "llm")
        service_registry.register(vector_service, "vector")
        service_registry.register(document_service, "document")
        service_registry.register(knowledge_service, "knowledge")
        
        # 初始化所有服务
        await service_registry.initialize_all()
        
        logger.info("所有服务初始化完成")
        
    except Exception as e:
        logger.error(f"服务初始化失败: {str(e)}")
        raise


async def cleanup_connectors():
    """清理连接器"""
    logger.info("正在关闭应用连接器...")
    
    for name, connector in connectors.items():
        try:
            await connector.close()
            logger.info(f"{name} 连接已关闭")
        except Exception as e:
            logger.error(f"关闭 {name} 连接时出错: {str(e)}")


async def cleanup_services():
    """清理服务"""
    logger.info("正在清理应用服务...")
    
    try:
        await service_registry.cleanup_all()
        logger.info("所有服务清理完成")
    except Exception as e:
        logger.error(f"服务清理失败: {str(e)}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    app_state["startup_time"] = time.time()
    
    try:
        # 启动时初始化
        await init_connectors()
        await init_services()
        
        logger.info("应用启动完成")
        yield
        
    except Exception as e:
        logger.error(f"应用启动失败: {str(e)}")
        raise
    finally:
        # 关闭时清理
        app_state["shutdown_time"] = time.time()
        
        await cleanup_services()
        await cleanup_connectors()
        
        logger.info("应用关闭完成")


# 创建 FastAPI 应用
app = FastAPI(
    title=settings.app_name,
    description="企业级智能知识库系统 API - 优化版本",
    version=settings.app_version,
    docs_url="/docs" if settings.app_debug else None,
    redoc_url="/redoc" if settings.app_debug else None,
    openapi_url="/openapi.json" if settings.app_debug else None,
    lifespan=lifespan
)

# 安全的CORS配置 - 即使在调试模式下也限制域名
def get_secure_cors_origins(debug_mode: bool = False):
    """获取安全的CORS配置"""
    # 生产环境的受信任域名
    production_origins = [
        "https://yourdomain.com",
        "https://www.yourdomain.com", 
        "https://api.yourdomain.com",
    ]
    
    # 开发环境的域名（仍然限制，不使用通配符）
    development_origins = [
        "http://localhost:3000",
        "http://localhost:8080",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8080",
        "http://localhost:5173",  # Vite开发服务器
    ]
    
    if debug_mode:
        return production_origins + development_origins
    else:
        return production_origins

cors_origins = get_secure_cors_origins(settings.app_debug)

# 添加安全的 CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=[
        "Accept",
        "Accept-Language",
        "Content-Language", 
        "Content-Type",
        "Authorization",
        "X-Requested-With",
        "X-CSRF-Token"
    ],
    expose_headers=["X-Process-Time", "X-Request-ID"],
    max_age=86400,  # 24小时
)

# 添加受信任主机中间件
trusted_hosts = ["*"] if settings.app_debug else [
    "localhost",
    "127.0.0.1",
    # 添加生产环境主机
]

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=trusted_hosts
)


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    """添加请求ID"""
    import uuid
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    
    return response


@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    """请求指标中间件"""
    start_time = time.time()
    app_state["request_count"] += 1
    
    # 记录请求信息
    logger.info(
        f"请求开始: {request.method} {request.url.path}",
        extra={
            "method": request.method,
            "path": request.url.path,
            "query_params": str(request.query_params),
            "client_ip": request.client.host if request.client else None,
            "request_id": getattr(request.state, "request_id", None),
            "user_agent": request.headers.get("user-agent")
        }
    )
    
    try:
        response = await call_next(request)
        
        # 记录成功响应
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(process_time)
        
        logger.info(
            f"请求完成: {request.method} {request.url.path} - {response.status_code}",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "process_time": process_time,
                "request_id": getattr(request.state, "request_id", None)
            }
        )
        
        return response
        
    except Exception as e:
        # 记录错误响应
        app_state["error_count"] += 1
        process_time = time.time() - start_time
        
        logger.error(
            f"请求错误: {request.method} {request.url.path} - {str(e)}",
            extra={
                "method": request.method,
                "path": request.url.path,
                "error": str(e),
                "process_time": process_time,
                "request_id": getattr(request.state, "request_id", None),
                "traceback": traceback.format_exc()
            }
        )
        
        raise


@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    """安全头中间件"""
    response = await call_next(request)
    
    # 添加安全头
    if not settings.app_debug:
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    
    return response


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """HTTP异常处理器"""
    logger.warning(
        f"HTTP异常: {exc.status_code} - {exc.detail}",
        extra={
            "method": request.method,
            "path": request.url.path,
            "status_code": exc.status_code,
            "detail": exc.detail,
            "request_id": getattr(request.state, "request_id", None)
        }
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code,
            "request_id": getattr(request.state, "request_id", None),
            "timestamp": time.time()
        }
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """全局异常处理器"""
    app_state["error_count"] += 1
    
    logger.error(
        f"未处理的异常: {str(exc)}",
        extra={
            "method": request.method,
            "path": request.url.path,
            "exception_type": type(exc).__name__,
            "request_id": getattr(request.state, "request_id", None),
            "traceback": traceback.format_exc()
        }
    )
    
    # 生产环境隐藏详细错误信息
    if settings.app_debug:
        error_detail = str(exc)
    else:
        error_detail = "内部服务器错误"
    
    return JSONResponse(
        status_code=500,
        content={
            "error": error_detail,
            "message": "服务器遇到了一个错误，请稍后重试",
            "status_code": 500,
            "request_id": getattr(request.state, "request_id", None),
            "timestamp": time.time()
        }
    )


# 健康检查端点
@app.get("/health")
async def health_check():
    """基础健康检查端点"""
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "version": settings.app_version,
        "uptime": time.time() - app_state["startup_time"] if app_state["startup_time"] else 0
    }


@app.get("/health/detailed")
async def detailed_health_check():
    """详细健康检查端点"""
    health_status = {
        "status": "healthy",
        "timestamp": time.time(),
        "version": settings.app_version,
        "uptime": time.time() - app_state["startup_time"] if app_state["startup_time"] else 0,
        "environment": "development" if settings.app_debug else "production"
    }
    
    # 检查连接器状态
    connector_status = {}
    overall_healthy = True
    
    for name, connector in connectors.items():
        try:
            if hasattr(connector, 'get_health_status'):
                status = await connector.get_health_status()
                connector_status[name] = status
                if status.get("status") != "healthy":
                    overall_healthy = False
            else:
                connector_status[name] = {"status": "unknown", "message": "健康检查方法不可用"}
        except Exception as e:
            connector_status[name] = {"status": "unhealthy", "error": str(e)}
            overall_healthy = False
    
    health_status["connectors"] = connector_status
    
    # 检查服务状态
    service_status = service_registry.get_all_health_status()
    health_status["services"] = service_status
    
    # 检查服务是否有问题
    for service_health in service_status.values():
        if service_health.get("status") != "healthy":
            overall_healthy = False
    
    # 应用指标
    health_status["metrics"] = {
        "request_count": app_state["request_count"],
        "error_count": app_state["error_count"],
        "error_rate": app_state["error_count"] / max(app_state["request_count"], 1),
        "memory_usage": get_memory_usage()
    }
    
    if not overall_healthy:
        health_status["status"] = "degraded"
    
    return health_status


@app.get("/health/readiness")
async def readiness_check():
    """就绪检查端点"""
    try:
        # 检查关键服务是否可用
        critical_checks = []
        
        # 检查数据库连接
        if "neo4j" in connectors:
            neo4j_healthy = await connectors["neo4j"].verify_connectivity()
            critical_checks.append(neo4j_healthy)
        
        if "redis" in connectors:
            redis_healthy = await connectors["redis"].ping()
            critical_checks.append(redis_healthy)
        
        all_critical_healthy = all(critical_checks)
        
        return {
            "ready": all_critical_healthy,
            "timestamp": time.time(),
            "checks": len(critical_checks),
            "passed": sum(critical_checks)
        }
        
    except Exception as e:
        logger.error(f"就绪检查失败: {str(e)}")
        return {
            "ready": False,
            "timestamp": time.time(),
            "error": str(e)
        }


@app.get("/health/liveness")
async def liveness_check():
    """存活检查端点"""
    return {
        "alive": True,
        "timestamp": time.time(),
        "uptime": time.time() - app_state["startup_time"] if app_state["startup_time"] else 0
    }


@app.get("/metrics")
async def get_metrics():
    """应用指标端点"""
    uptime = time.time() - app_state["startup_time"] if app_state["startup_time"] else 0
    
    metrics = {
        "application": {
            "uptime_seconds": uptime,
            "request_count": app_state["request_count"],
            "error_count": app_state["error_count"],
            "error_rate": app_state["error_count"] / max(app_state["request_count"], 1),
            "requests_per_second": app_state["request_count"] / max(uptime, 1)
        },
        "system": {
            "memory_usage": get_memory_usage(),
            "cpu_count": get_cpu_count()
        }
    }
    
    # 添加连接器指标
    for name, connector in connectors.items():
        if hasattr(connector, 'get_statistics'):
            try:
                connector_stats = await connector.get_statistics()
                metrics[f"connector_{name}"] = connector_stats
            except Exception as e:
                metrics[f"connector_{name}"] = {"error": str(e)}
    
    # 添加服务指标
    for name, service in service_registry._services.items():
        if hasattr(service, 'get_metrics'):
            service_metrics = service.get_metrics()
            metrics[f"service_{name}"] = {
                "total_calls": service_metrics.total_calls,
                "success_calls": service_metrics.success_calls,
                "error_calls": service_metrics.error_calls,
                "error_rate": service_metrics.error_rate,
                "average_response_time_ms": service_metrics.average_response_time_ms
            }
    
    return metrics


def get_memory_usage() -> Dict[str, Any]:
    """获取内存使用情况"""
    try:
        import psutil
        process = psutil.Process()
        memory_info = process.memory_info()
        
        return {
            "rss_mb": memory_info.rss / 1024 / 1024,
            "vms_mb": memory_info.vms / 1024 / 1024,
            "percent": process.memory_percent()
        }
    except ImportError:
        return {"error": "psutil not available"}
    except Exception as e:
        return {"error": str(e)}


def get_cpu_count() -> int:
    """获取CPU核心数"""
    try:
        import os
        return os.cpu_count() or 1
    except:
        return 1


# 根路径
@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "欢迎使用企业级智能知识库系统 API",
        "version": settings.app_version,
        "docs_url": "/docs" if settings.app_debug else None,
        "health_check": "/health",
        "timestamp": time.time()
    }


# 获取连接器实例的依赖函数
def get_connector(connector_type: str):
    """获取连接器实例"""
    connector = connectors.get(connector_type)
    if not connector:
        raise HTTPException(
            status_code=503,
            detail=f"连接器 {connector_type} 不可用"
        )
    return connector


def get_neo4j_client() -> Neo4jClient:
    """获取Neo4j客户端"""
    return get_connector("neo4j")


def get_redis_client() -> RedisClient:
    """获取Redis客户端"""
    return get_connector("redis")


def get_minio_client() -> MinIOClient:
    """获取MinIO客户端"""
    return get_connector("minio")


# 注册API路由
app.include_router(
    knowledge_routes.router,
    prefix="/api/v1/knowledge",
    tags=["知识管理"]
)

app.include_router(
    etl_routes.router,
    prefix="/api/etl",
    tags=["ETL处理"]
)

app.include_router(
    knowledge_graph.router,
    prefix="/api/knowledge-graph",
    tags=["知识图谱"]
)

app.include_router(
    ocr.router,
    prefix="/api/ocr",
    tags=["OCR识别"]
)


if __name__ == "__main__":
    # 开发模式启动配置
    uvicorn.run(
        "backend.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.app_debug,
        log_level=settings.log_level.lower(),
        access_log=True,
        loop="asyncio"
    )