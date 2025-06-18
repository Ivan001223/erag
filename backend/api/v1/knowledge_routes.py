"""知识管理 API 路由

提供知识库管理的 RESTful API 接口，包括：
- 文档管理（上传、删除、查询）
- 知识图谱操作（实体、关系管理）
- 向量搜索和相似性查询
- 知识推荐和发现
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File, Form
from fastapi.responses import JSONResponse
import asyncio
from datetime import datetime

from backend.api.deps import (
    get_neo4j_client,
    get_redis_client,
    # get_starrocks_client, # StarRocks已移除
    get_minio_client,
    get_current_user,
    get_pagination_params,
    get_cache_manager,
    require_permissions,
    rate_limit
)
from backend.config.database import get_db
from backend.models.knowledge import (
    DocumentCreate,
    DocumentUpdate,
    DocumentResponse,
    EntityCreate,
    EntityUpdate,
    EntityResponse,
    RelationCreate,
    RelationUpdate,
    RelationResponse,
    SearchQuery,
    SearchResponse,
    KnowledgeStats
)
from backend.models.base import PaginationParams, PaginatedResponse
from backend.models.response import SuccessResponse, ErrorResponse
from backend.services.knowledge_service import KnowledgeService
from backend.services.vector_service import VectorService
from backend.services.document_service import DocumentService
from backend.core.knowledge_graph.graph_manager import GraphManager
from backend.core.vector.similarity_search import SimilaritySearch
from backend.utils.logger import get_logger

# 创建路由器
router = APIRouter()
logger = get_logger(__name__)


# 依赖注入：服务实例
def get_knowledge_service(
    neo4j_client=Depends(get_neo4j_client),
    redis_client=Depends(get_redis_client),
    db_session=Depends(get_db)
) -> KnowledgeService:
    """获取知识服务实例"""
    return KnowledgeService(
        neo4j_client=neo4j_client,
        redis_client=redis_client,
        db_session=db_session
    )


def get_vector_service(
    redis_client=Depends(get_redis_client)
) -> VectorService:
    """获取向量服务实例"""
    return VectorService(redis_client=redis_client)


def get_document_service(
    minio_client=Depends(get_minio_client),
    db_session=Depends(get_db)
) -> DocumentService:
    """获取文档服务实例"""
    return DocumentService(
        minio_client=minio_client,
        db_session=db_session
    )


# 文档管理端点
@router.post(
    "/documents",
    response_model=SuccessResponse[DocumentResponse],
    summary="上传文档",
    description="上传新文档到知识库"
)
@rate_limit(limit=10, window=60)  # 每分钟最多10次上传
async def upload_document(
    file: UploadFile = File(..., description="要上传的文档文件"),
    title: Optional[str] = Form(None, description="文档标题"),
    description: Optional[str] = Form(None, description="文档描述"),
    tags: Optional[str] = Form(None, description="文档标签，用逗号分隔"),
    category: Optional[str] = Form(None, description="文档分类"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    document_service: DocumentService = Depends(get_document_service),
    knowledge_service: KnowledgeService = Depends(get_knowledge_service)
):
    """上传文档到知识库
    
    Args:
        file: 上传的文件
        title: 文档标题
        description: 文档描述
        tags: 文档标签
        category: 文档分类
        current_user: 当前用户信息
        document_service: 文档服务
        knowledge_service: 知识服务
        
    Returns:
        上传成功的文档信息
    """
    try:
        # 验证文件类型
        allowed_types = [
            "application/pdf",
            "application/msword",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "text/plain",
            "text/markdown"
        ]
        
        if file.content_type not in allowed_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"不支持的文件类型: {file.content_type}"
            )
        
        # 验证文件大小（最大 50MB）
        max_size = 50 * 1024 * 1024  # 50MB
        file_content = await file.read()
        if len(file_content) > max_size:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="文件过大，最大支持 50MB"
            )
        
        # 重置文件指针
        await file.seek(0)
        
        # 处理标签
        tag_list = []
        if tags:
            tag_list = [tag.strip() for tag in tags.split(",") if tag.strip()]
        
        # 创建文档对象
        document_data = DocumentCreate(
            title=title or file.filename,
            description=description,
            filename=file.filename,
            content_type=file.content_type,
            size=len(file_content),
            tags=tag_list,
            category=category,
            uploaded_by=current_user["user_id"]
        )
        
        # 上传文档
        document = await document_service.upload_document(
            document_data=document_data,
            file_content=file_content
        )
        
        # 异步处理文档（OCR、向量化等）
        asyncio.create_task(
            knowledge_service.process_document_async(document.id)
        )
        
        logger.info(
            f"文档上传成功: {document.id}",
            extra={
                "document_id": document.id,
                "filename": file.filename,
                "user_id": current_user["user_id"]
            }
        )
        
        return SuccessResponse(
            data=document,
            message="文档上传成功，正在后台处理"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"文档上传失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="文档上传失败"
        )


@router.get(
    "/documents",
    response_model=SuccessResponse[PaginatedResponse[DocumentResponse]],
    summary="获取文档列表",
    description="分页获取文档列表"
)
async def get_documents(
    category: Optional[str] = Query(None, description="文档分类过滤"),
    tags: Optional[str] = Query(None, description="标签过滤，用逗号分隔"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    pagination: PaginationParams = Depends(get_pagination_params),
    current_user: Dict[str, Any] = Depends(get_current_user),
    document_service: DocumentService = Depends(get_document_service),
    cache_manager = Depends(get_cache_manager)
):
    """获取文档列表
    
    Args:
        category: 分类过滤
        tags: 标签过滤
        search: 搜索关键词
        pagination: 分页参数
        current_user: 当前用户
        document_service: 文档服务
        cache_manager: 缓存管理器
        
    Returns:
        分页的文档列表
    """
    try:
        # 生成缓存键
        cache_key = cache_manager.cache_key(
            "documents",
            category=category,
            tags=tags,
            search=search,
            page=pagination.page,
            size=pagination.size,
            user_id=current_user["user_id"]
        )
        
        # 尝试从缓存获取
        cached_result = await cache_manager.get(cache_key)
        if cached_result:
            return SuccessResponse(
                data=cached_result,
                message="获取文档列表成功（缓存）"
            )
        
        # 处理标签过滤
        tag_list = []
        if tags:
            tag_list = [tag.strip() for tag in tags.split(",") if tag.strip()]
        
        # 获取文档列表
        result = await document_service.get_documents(
            category=category,
            tags=tag_list,
            search=search,
            pagination=pagination,
            user_id=current_user["user_id"]
        )
        
        # 缓存结果（5分钟）
        await cache_manager.set(cache_key, result, ttl=300)
        
        return SuccessResponse(
            data=result,
            message="获取文档列表成功"
        )
        
    except Exception as e:
        logger.error(f"获取文档列表失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取文档列表失败"
        )


@router.get(
    "/documents/{document_id}",
    response_model=SuccessResponse[DocumentResponse],
    summary="获取文档详情",
    description="根据ID获取文档详细信息"
)
async def get_document(
    document_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    document_service: DocumentService = Depends(get_document_service),
    cache_manager = Depends(get_cache_manager)
):
    """获取文档详情
    
    Args:
        document_id: 文档ID
        current_user: 当前用户
        document_service: 文档服务
        cache_manager: 缓存管理器
        
    Returns:
        文档详细信息
    """
    try:
        # 生成缓存键
        cache_key = cache_manager.cache_key(
            "document",
            document_id=document_id,
            user_id=current_user["user_id"]
        )
        
        # 尝试从缓存获取
        cached_result = await cache_manager.get(cache_key)
        if cached_result:
            return SuccessResponse(
                data=cached_result,
                message="获取文档详情成功（缓存）"
            )
        
        # 获取文档
        document = await document_service.get_document(
            document_id=document_id,
            user_id=current_user["user_id"]
        )
        
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="文档不存在"
            )
        
        # 缓存结果（10分钟）
        await cache_manager.set(cache_key, document, ttl=600)
        
        return SuccessResponse(
            data=document,
            message="获取文档详情成功"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取文档详情失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取文档详情失败"
        )


@router.put(
    "/documents/{document_id}",
    response_model=SuccessResponse[DocumentResponse],
    summary="更新文档",
    description="更新文档信息"
)
@require_permissions(["write"])
async def update_document(
    document_id: str,
    document_update: DocumentUpdate,
    current_user: Dict[str, Any] = Depends(get_current_user),
    document_service: DocumentService = Depends(get_document_service),
    cache_manager = Depends(get_cache_manager)
):
    """更新文档信息
    
    Args:
        document_id: 文档ID
        document_update: 更新数据
        current_user: 当前用户
        document_service: 文档服务
        cache_manager: 缓存管理器
        
    Returns:
        更新后的文档信息
    """
    try:
        # 更新文档
        document = await document_service.update_document(
            document_id=document_id,
            document_update=document_update,
            user_id=current_user["user_id"]
        )
        
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="文档不存在"
            )
        
        # 清除相关缓存
        cache_keys = [
            cache_manager.cache_key("document", document_id=document_id, user_id=current_user["user_id"]),
            cache_manager.cache_key("documents", user_id=current_user["user_id"])
        ]
        
        for key in cache_keys:
            await cache_manager.delete(key)
        
        logger.info(
            f"文档更新成功: {document_id}",
            extra={
                "document_id": document_id,
                "user_id": current_user["user_id"]
            }
        )
        
        return SuccessResponse(
            data=document,
            message="文档更新成功"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"文档更新失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="文档更新失败"
        )


@router.delete(
    "/documents/{document_id}",
    response_model=SuccessResponse[Dict[str, str]],
    summary="删除文档",
    description="删除指定文档"
)
@require_permissions(["delete"])
async def delete_document(
    document_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    document_service: DocumentService = Depends(get_document_service),
    cache_manager = Depends(get_cache_manager)
):
    """删除文档
    
    Args:
        document_id: 文档ID
        current_user: 当前用户
        document_service: 文档服务
        cache_manager: 缓存管理器
        
    Returns:
        删除结果
    """
    try:
        # 删除文档
        success = await document_service.delete_document(
            document_id=document_id,
            user_id=current_user["user_id"]
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="文档不存在"
            )
        
        # 清除相关缓存
        cache_keys = [
            cache_manager.cache_key("document", document_id=document_id, user_id=current_user["user_id"]),
            cache_manager.cache_key("documents", user_id=current_user["user_id"])
        ]
        
        for key in cache_keys:
            await cache_manager.delete(key)
        
        logger.info(
            f"文档删除成功: {document_id}",
            extra={
                "document_id": document_id,
                "user_id": current_user["user_id"]
            }
        )
        
        return SuccessResponse(
            data={"document_id": document_id},
            message="文档删除成功"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"文档删除失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="文档删除失败"
        )


# 知识搜索端点
@router.post(
    "/search",
    response_model=SuccessResponse[SearchResponse],
    summary="知识搜索",
    description="在知识库中搜索相关内容"
)
@rate_limit(limit=50, window=60)  # 每分钟最多50次搜索
async def search_knowledge(
    search_query: SearchQuery,
    current_user: Dict[str, Any] = Depends(get_current_user),
    knowledge_service: KnowledgeService = Depends(get_knowledge_service),
    vector_service: VectorService = Depends(get_vector_service),
    cache_manager = Depends(get_cache_manager)
):
    """在知识库中搜索
    
    Args:
        search_query: 搜索查询
        current_user: 当前用户
        knowledge_service: 知识服务
        vector_service: 向量服务
        cache_manager: 缓存管理器
        
    Returns:
        搜索结果
    """
    try:
        # 生成缓存键
        cache_key = cache_manager.cache_key(
            "search",
            query=search_query.query,
            search_type=search_query.search_type,
            filters=str(search_query.filters),
            limit=search_query.limit,
            user_id=current_user["user_id"]
        )
        
        # 尝试从缓存获取（搜索结果缓存时间较短）
        cached_result = await cache_manager.get(cache_key)
        if cached_result:
            return SuccessResponse(
                data=cached_result,
                message="搜索完成（缓存）"
            )
        
        # 执行搜索
        search_result = await knowledge_service.search(
            search_query=search_query,
            user_id=current_user["user_id"]
        )
        
        # 缓存结果（2分钟）
        await cache_manager.set(cache_key, search_result, ttl=120)
        
        logger.info(
            f"搜索完成: {search_query.query}",
            extra={
                "query": search_query.query,
                "search_type": search_query.search_type,
                "results_count": len(search_result.results),
                "user_id": current_user["user_id"]
            }
        )
        
        return SuccessResponse(
            data=search_result,
            message="搜索完成"
        )
        
    except Exception as e:
        logger.error(f"搜索失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="搜索失败"
        )


# 实体管理端点
@router.post(
    "/entities",
    response_model=SuccessResponse[EntityResponse],
    summary="创建实体",
    description="在知识图谱中创建新实体"
)
@require_permissions(["write"])
async def create_entity(
    entity_data: EntityCreate,
    current_user: Dict[str, Any] = Depends(get_current_user),
    knowledge_service: KnowledgeService = Depends(get_knowledge_service)
):
    """创建实体
    
    Args:
        entity_data: 实体数据
        current_user: 当前用户
        knowledge_service: 知识服务
        
    Returns:
        创建的实体信息
    """
    try:
        entity = await knowledge_service.create_entity(
            entity_data=entity_data,
            user_id=current_user["user_id"]
        )
        
        logger.info(
            f"实体创建成功: {entity.id}",
            extra={
                "entity_id": entity.id,
                "entity_name": entity.name,
                "entity_type": entity.type,
                "user_id": current_user["user_id"]
            }
        )
        
        return SuccessResponse(
            data=entity,
            message="实体创建成功"
        )
        
    except Exception as e:
        logger.error(f"实体创建失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="实体创建失败"
        )


@router.get(
    "/entities",
    response_model=SuccessResponse[PaginatedResponse[EntityResponse]],
    summary="获取实体列表",
    description="分页获取实体列表"
)
async def get_entities(
    entity_type: Optional[str] = Query(None, description="实体类型过滤"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    pagination: PaginationParams = Depends(get_pagination_params),
    current_user: Dict[str, Any] = Depends(get_current_user),
    knowledge_service: KnowledgeService = Depends(get_knowledge_service),
    cache_manager = Depends(get_cache_manager)
):
    """获取实体列表
    
    Args:
        entity_type: 实体类型过滤
        search: 搜索关键词
        pagination: 分页参数
        current_user: 当前用户
        knowledge_service: 知识服务
        cache_manager: 缓存管理器
        
    Returns:
        分页的实体列表
    """
    try:
        # 生成缓存键
        cache_key = cache_manager.cache_key(
            "entities",
            entity_type=entity_type,
            search=search,
            page=pagination.page,
            size=pagination.size,
            user_id=current_user["user_id"]
        )
        
        # 尝试从缓存获取
        cached_result = await cache_manager.get(cache_key)
        if cached_result:
            return SuccessResponse(
                data=cached_result,
                message="获取实体列表成功（缓存）"
            )
        
        # 获取实体列表
        result = await knowledge_service.get_entities(
            entity_type=entity_type,
            search=search,
            pagination=pagination,
            user_id=current_user["user_id"]
        )
        
        # 缓存结果（5分钟）
        await cache_manager.set(cache_key, result, ttl=300)
        
        return SuccessResponse(
            data=result,
            message="获取实体列表成功"
        )
        
    except Exception as e:
        logger.error(f"获取实体列表失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取实体列表失败"
        )


# 关系管理端点
@router.post(
    "/relations",
    response_model=SuccessResponse[RelationResponse],
    summary="创建关系",
    description="在知识图谱中创建实体间关系"
)
@require_permissions(["write"])
async def create_relation(
    relation_data: RelationCreate,
    current_user: Dict[str, Any] = Depends(get_current_user),
    knowledge_service: KnowledgeService = Depends(get_knowledge_service)
):
    """创建关系
    
    Args:
        relation_data: 关系数据
        current_user: 当前用户
        knowledge_service: 知识服务
        
    Returns:
        创建的关系信息
    """
    try:
        relation = await knowledge_service.create_relation(
            relation_data=relation_data,
            user_id=current_user["user_id"]
        )
        
        logger.info(
            f"关系创建成功: {relation.id}",
            extra={
                "relation_id": relation.id,
                "from_entity": relation.from_entity_id,
                "to_entity": relation.to_entity_id,
                "relation_type": relation.type,
                "user_id": current_user["user_id"]
            }
        )
        
        return SuccessResponse(
            data=relation,
            message="关系创建成功"
        )
        
    except Exception as e:
        logger.error(f"关系创建失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="关系创建失败"
        )


# 统计信息端点
@router.get(
    "/stats",
    response_model=SuccessResponse[KnowledgeStats],
    summary="获取知识库统计",
    description="获取知识库的统计信息"
)
async def get_knowledge_stats(
    current_user: Dict[str, Any] = Depends(get_current_user),
    knowledge_service: KnowledgeService = Depends(get_knowledge_service),
    cache_manager = Depends(get_cache_manager)
):
    """获取知识库统计信息
    
    Args:
        current_user: 当前用户
        knowledge_service: 知识服务
        cache_manager: 缓存管理器
        
    Returns:
        知识库统计信息
    """
    try:
        # 生成缓存键
        cache_key = cache_manager.cache_key(
            "knowledge_stats",
            user_id=current_user["user_id"]
        )
        
        # 尝试从缓存获取
        cached_result = await cache_manager.get(cache_key)
        if cached_result:
            return SuccessResponse(
                data=cached_result,
                message="获取统计信息成功（缓存）"
            )
        
        # 获取统计信息
        stats = await knowledge_service.get_stats(
            user_id=current_user["user_id"]
        )
        
        # 缓存结果（10分钟）
        await cache_manager.set(cache_key, stats, ttl=600)
        
        return SuccessResponse(
            data=stats,
            message="获取统计信息成功"
        )
        
    except Exception as e:
        logger.error(f"获取统计信息失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取统计信息失败"
        )