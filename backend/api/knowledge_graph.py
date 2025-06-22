from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Query, Path
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import asyncio
import logging
from datetime import datetime
import uuid

from backend.models.knowledge import Entity, Relation, KnowledgeGraph
from backend.core.knowledge_graph.graph_manager import GraphManager, GraphConfig
from backend.core.knowledge_graph.entity_extractor import EntityExtractor, ExtractionConfig, ExtractionMethod
from backend.core.knowledge_graph.relation_extractor import RelationExtractor, RelationExtractionConfig
from backend.core.knowledge_graph.graph_analytics import GraphAnalytics, AnalysisConfig, AnalysisType
from backend.core.knowledge_graph.graph_database import GraphDatabase, DatabaseConfig
from backend.api.deps import CacheManager
from backend.utils.auth import get_current_user
from backend.models.user import UserModel as User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/knowledge-graph", tags=["knowledge-graph"])

# 请求模型
class CreateGraphRequest(BaseModel):
    """创建图请求"""
    name: str = Field(..., description="图名称")
    description: Optional[str] = Field(None, description="图描述")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="元数据")

class AddEntityRequest(BaseModel):
    """添加实体请求"""
    name: str = Field(..., description="实体名称")
    entity_type: str = Field(..., description="实体类型")
    properties: Optional[Dict[str, Any]] = Field(default_factory=dict, description="实体属性")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="元数据")

class AddRelationRequest(BaseModel):
    """添加关系请求"""
    source_id: str = Field(..., description="源实体ID")
    target_id: str = Field(..., description="目标实体ID")
    relation_type: str = Field(..., description="关系类型")
    properties: Optional[Dict[str, Any]] = Field(default_factory=dict, description="关系属性")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="元数据")
    confidence: float = Field(1.0, ge=0.0, le=1.0, description="置信度")

class ExtractEntitiesRequest(BaseModel):
    """提取实体请求"""
    text: str = Field(..., description="文本内容")
    method: ExtractionMethod = Field(ExtractionMethod.HYBRID, description="提取方法")
    entity_types: Optional[List[str]] = Field(None, description="指定实体类型")
    language: str = Field("zh", description="语言")
    confidence_threshold: float = Field(0.7, ge=0.0, le=1.0, description="置信度阈值")

class ExtractRelationsRequest(BaseModel):
    """提取关系请求"""
    text: str = Field(..., description="文本内容")
    entities: List[Dict[str, Any]] = Field(..., description="实体列表")
    method: str = Field("hybrid", description="提取方法")
    relation_types: Optional[List[str]] = Field(None, description="指定关系类型")
    confidence_threshold: float = Field(0.7, ge=0.0, le=1.0, description="置信度阈值")

class BuildGraphFromTextRequest(BaseModel):
    """从文本构建图请求"""
    text: str = Field(..., description="文本内容")
    graph_name: str = Field(..., description="图名称")
    description: Optional[str] = Field(None, description="图描述")
    entity_config: Optional[Dict[str, Any]] = Field(default_factory=dict, description="实体提取配置")
    relation_config: Optional[Dict[str, Any]] = Field(default_factory=dict, description="关系提取配置")

class AnalyzeGraphRequest(BaseModel):
    """分析图请求"""
    analysis_types: List[AnalysisType] = Field(default_factory=lambda: [AnalysisType.CENTRALITY, AnalysisType.COMMUNITY], description="分析类型")
    centrality_metrics: Optional[List[str]] = Field(None, description="中心性指标")
    community_algorithm: str = Field("louvain", description="社区检测算法")
    max_path_length: int = Field(6, description="最大路径长度")
    similarity_threshold: float = Field(0.7, description="相似性阈值")
    top_k_results: int = Field(20, description="返回结果数量")
    enable_parallel: bool = Field(True, description="启用并行处理")

class SearchEntitiesRequest(BaseModel):
    """搜索实体请求"""
    query: Optional[str] = Field(None, description="搜索查询")
    entity_type: Optional[str] = Field(None, description="实体类型")
    limit: int = Field(100, ge=1, le=1000, description="返回数量限制")

# 响应模型
class GraphResponse(BaseModel):
    """图响应"""
    id: str
    name: str
    description: Optional[str]
    num_entities: int
    num_relations: int
    created_at: datetime
    updated_at: datetime
    metadata: Dict[str, Any]

class EntityResponse(BaseModel):
    """实体响应"""
    id: str
    name: str
    entity_type: str
    properties: Dict[str, Any]
    metadata: Dict[str, Any]

class RelationResponse(BaseModel):
    """关系响应"""
    id: str
    source_id: str
    target_id: str
    relation_type: str
    properties: Dict[str, Any]
    metadata: Dict[str, Any]
    confidence: float

class ExtractionResultResponse(BaseModel):
    """提取结果响应"""
    entities: List[EntityResponse]
    relations: List[RelationResponse]
    processing_time: float
    statistics: Dict[str, Any]

class AnalysisResultResponse(BaseModel):
    """分析结果响应"""
    analysis_id: str
    timestamp: datetime
    processing_time: float
    centrality_results: Optional[Dict[str, Any]]
    community_result: Optional[Dict[str, Any]]
    path_result: Optional[Dict[str, Any]]
    similarity_result: Optional[Dict[str, Any]]
    influence_result: Optional[Dict[str, Any]]
    anomaly_result: Optional[Dict[str, Any]]
    metadata: Dict[str, Any]
    errors: List[str]

# 全局变量
graph_manager: Optional[GraphManager] = None
entity_extractor: Optional[EntityExtractor] = None
relation_extractor: Optional[RelationExtractor] = None
graph_analytics: Optional[GraphAnalytics] = None
graph_database: Optional[GraphDatabase] = None
cache_manager: Optional[CacheManager] = None

# 后台任务存储
background_tasks_status = {}

async def get_graph_manager() -> GraphManager:
    """获取图管理器"""
    global graph_manager
    if not graph_manager:
        # 初始化组件
        config = GraphConfig()
        db_config = DatabaseConfig()
        
        global graph_database, cache_manager, entity_extractor, relation_extractor
        
        if not cache_manager:
            cache_manager = CacheManager()
            await cache_manager.initialize()
        
        if not graph_database:
            graph_database = GraphDatabase(db_config, cache_manager)
            await graph_database.initialize()
        
        if not entity_extractor:
            entity_extractor = EntityExtractor()
        
        if not relation_extractor:
            relation_extractor = RelationExtractor()
        
        graph_manager = GraphManager(
            config=config,
            entity_extractor=entity_extractor,
            relation_extractor=relation_extractor,
            graph_database=graph_database,
            cache_manager=cache_manager
        )
        await graph_manager.initialize()
    
    return graph_manager

async def get_graph_analytics() -> GraphAnalytics:
    """获取图分析器"""
    global graph_analytics
    if not graph_analytics:
        manager = await get_graph_manager()
        graph_analytics = GraphAnalytics(manager)
    return graph_analytics

@router.post("/graphs", response_model=GraphResponse)
async def create_graph(
    request: CreateGraphRequest,
    current_user: User = Depends(get_current_user)
):
    """创建知识图谱"""
    try:
        manager = await get_graph_manager()
        
        # 创建图对象
        graph = KnowledgeGraph(
            id=str(uuid.uuid4()),
            name=request.name,
            description=request.description,
            entities=[],
            relations=[],
            metadata={
                **request.metadata,
                "created_by": current_user.id,
                "created_at": datetime.now().isoformat()
            }
        )
        
        # 保存图
        result = await manager.create_graph(graph)
        
        if not result.success:
            raise HTTPException(status_code=400, detail=result.error)
        
        return GraphResponse(
            id=graph.id,
            name=graph.name,
            description=graph.description,
            num_entities=0,
            num_relations=0,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            metadata=graph.metadata
        )
        
    except Exception as e:
        logger.error(f"创建图失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/graphs/{graph_id}", response_model=GraphResponse)
async def get_graph(
    graph_id: str = Path(..., description="图ID"),
    current_user: User = Depends(get_current_user)
):
    """获取知识图谱"""
    try:
        manager = await get_graph_manager()
        
        result = await manager.get_graph(graph_id)
        
        if not result.success:
            raise HTTPException(status_code=404, detail=result.error)
        
        graph = result.data
        
        return GraphResponse(
            id=graph.id,
            name=graph.name,
            description=graph.description,
            num_entities=len(graph.entities),
            num_relations=len(graph.relations),
            created_at=datetime.now(),  # 从元数据中获取
            updated_at=datetime.now(),
            metadata=graph.metadata
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取图失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/graphs", response_model=List[GraphResponse])
async def list_graphs(
    limit: int = Query(50, ge=1, le=100, description="返回数量限制"),
    current_user: User = Depends(get_current_user)
):
    """列出知识图谱"""
    try:
        manager = await get_graph_manager()
        
        # 这里应该实现列出用户的图的功能
        # 暂时返回空列表
        return []
        
    except Exception as e:
        logger.error(f"列出图失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/graphs/{graph_id}/entities", response_model=EntityResponse)
async def add_entity(
    graph_id: str,
    request: AddEntityRequest,
    current_user: User = Depends(get_current_user)
):
    """添加实体"""
    try:
        manager = await get_graph_manager()
        
        # 创建实体对象
        entity = Entity(
            id=str(uuid.uuid4()),
            name=request.name,
            entity_type=request.entity_type,
            properties=request.properties,
            metadata={
                **request.metadata,
                "created_by": current_user.id,
                "created_at": datetime.now().isoformat()
            }
        )
        
        # 添加实体
        result = await manager.add_entity(graph_id, entity)
        
        if not result.success:
            raise HTTPException(status_code=400, detail=result.error)
        
        return EntityResponse(
            id=entity.id,
            name=entity.name,
            entity_type=entity.entity_type,
            properties=entity.properties,
            metadata=entity.metadata
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"添加实体失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/graphs/{graph_id}/relations", response_model=RelationResponse)
async def add_relation(
    graph_id: str,
    request: AddRelationRequest,
    current_user: User = Depends(get_current_user)
):
    """添加关系"""
    try:
        manager = await get_graph_manager()
        
        # 创建关系对象
        relation = Relation(
            id=str(uuid.uuid4()),
            source_id=request.source_id,
            target_id=request.target_id,
            relation_type=request.relation_type,
            properties=request.properties,
            metadata={
                **request.metadata,
                "created_by": current_user.id,
                "created_at": datetime.now().isoformat()
            },
            confidence=request.confidence
        )
        
        # 添加关系
        result = await manager.add_relation(graph_id, relation)
        
        if not result.success:
            raise HTTPException(status_code=400, detail=result.error)
        
        return RelationResponse(
            id=relation.id,
            source_id=relation.source_id,
            target_id=relation.target_id,
            relation_type=relation.relation_type,
            properties=relation.properties,
            metadata=relation.metadata,
            confidence=relation.confidence
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"添加关系失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/extract/entities", response_model=ExtractionResultResponse)
async def extract_entities(
    request: ExtractEntitiesRequest,
    current_user: User = Depends(get_current_user)
):
    """提取实体"""
    try:
        manager = await get_graph_manager()
        
        # 配置提取参数
        config = ExtractionConfig(
            method=request.method,
            entity_types=request.entity_types,
            language=request.language,
            confidence_threshold=request.confidence_threshold
        )
        
        # 提取实体
        start_time = datetime.now()
        result = await manager.entity_extractor.extract_entities(request.text, config)
        processing_time = (datetime.now() - start_time).total_seconds()
        
        if not result.success:
            raise HTTPException(status_code=400, detail=result.error)
        
        # 转换为响应格式
        entities = []
        for entity in result.entities:
            entities.append(EntityResponse(
                id=entity.id,
                name=entity.name,
                entity_type=entity.entity_type,
                properties=entity.properties,
                metadata=entity.metadata
            ))
        
        return ExtractionResultResponse(
            entities=entities,
            relations=[],
            processing_time=processing_time,
            statistics=result.statistics
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"提取实体失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/extract/relations", response_model=ExtractionResultResponse)
async def extract_relations(
    request: ExtractRelationsRequest,
    current_user: User = Depends(get_current_user)
):
    """提取关系"""
    try:
        manager = await get_graph_manager()
        
        # 转换实体格式
        entities = []
        for entity_dict in request.entities:
            entity = Entity(
                id=entity_dict.get("id", str(uuid.uuid4())),
                name=entity_dict["name"],
                entity_type=entity_dict["entity_type"],
                properties=entity_dict.get("properties", {}),
                metadata=entity_dict.get("metadata", {})
            )
            entities.append(entity)
        
        # 配置提取参数
        config = RelationExtractionConfig(
            method=request.method,
            relation_types=request.relation_types,
            confidence_threshold=request.confidence_threshold
        )
        
        # 提取关系
        start_time = datetime.now()
        result = await manager.relation_extractor.extract_relations(
            request.text, entities, config
        )
        processing_time = (datetime.now() - start_time).total_seconds()
        
        if not result.success:
            raise HTTPException(status_code=400, detail=result.error)
        
        # 转换为响应格式
        relations = []
        for relation in result.relations:
            relations.append(RelationResponse(
                id=relation.id,
                source_id=relation.source_id,
                target_id=relation.target_id,
                relation_type=relation.relation_type,
                properties=relation.properties,
                metadata=relation.metadata,
                confidence=relation.confidence
            ))
        
        return ExtractionResultResponse(
            entities=[],
            relations=relations,
            processing_time=processing_time,
            statistics=result.statistics
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"提取关系失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/graphs/build-from-text", response_model=GraphResponse)
async def build_graph_from_text(
    request: BuildGraphFromTextRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
):
    """从文本构建知识图谱"""
    try:
        task_id = str(uuid.uuid4())
        
        # 启动后台任务
        background_tasks.add_task(
            _build_graph_from_text_task,
            task_id,
            request,
            current_user.id
        )
        
        # 记录任务状态
        background_tasks_status[task_id] = {
            "status": "processing",
            "created_at": datetime.now(),
            "graph_name": request.graph_name
        }
        
        return JSONResponse(
            status_code=202,
            content={
                "task_id": task_id,
                "status": "processing",
                "message": "图构建任务已启动"
            }
        )
        
    except Exception as e:
        logger.error(f"启动图构建任务失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

async def _build_graph_from_text_task(
    task_id: str,
    request: BuildGraphFromTextRequest,
    user_id: str
):
    """构建图的后台任务"""
    try:
        manager = await get_graph_manager()
        
        # 更新任务状态
        background_tasks_status[task_id]["status"] = "extracting_entities"
        
        # 提取实体
        entity_config = ExtractionConfig(**request.entity_config)
        entity_result = await manager.entity_extractor.extract_entities(
            request.text, entity_config
        )
        
        if not entity_result.success:
            background_tasks_status[task_id]["status"] = "failed"
            background_tasks_status[task_id]["error"] = entity_result.error
            return
        
        # 更新任务状态
        background_tasks_status[task_id]["status"] = "extracting_relations"
        
        # 提取关系
        relation_config = RelationExtractionConfig(**request.relation_config)
        relation_result = await manager.relation_extractor.extract_relations(
            request.text, entity_result.entities, relation_config
        )
        
        if not relation_result.success:
            background_tasks_status[task_id]["status"] = "failed"
            background_tasks_status[task_id]["error"] = relation_result.error
            return
        
        # 更新任务状态
        background_tasks_status[task_id]["status"] = "building_graph"
        
        # 创建图
        graph = KnowledgeGraph(
            id=str(uuid.uuid4()),
            name=request.graph_name,
            description=request.description,
            entities=entity_result.entities,
            relations=relation_result.relations,
            metadata={
                "created_by": user_id,
                "created_at": datetime.now().isoformat(),
                "source_text_length": len(request.text),
                "extraction_statistics": {
                    "entity_stats": entity_result.statistics,
                    "relation_stats": relation_result.statistics
                }
            }
        )
        
        # 保存图
        create_result = await manager.create_graph(graph)
        
        if not create_result.success:
            background_tasks_status[task_id]["status"] = "failed"
            background_tasks_status[task_id]["error"] = create_result.error
            return
        
        # 更新任务状态
        background_tasks_status[task_id]["status"] = "completed"
        background_tasks_status[task_id]["graph_id"] = graph.id
        background_tasks_status[task_id]["completed_at"] = datetime.now()
        
    except Exception as e:
        logger.error(f"构建图任务失败: {str(e)}")
        background_tasks_status[task_id]["status"] = "failed"
        background_tasks_status[task_id]["error"] = str(e)

@router.get("/tasks/{task_id}/status")
async def get_task_status(
    task_id: str = Path(..., description="任务ID"),
    current_user: User = Depends(get_current_user)
):
    """获取任务状态"""
    try:
        if task_id not in background_tasks_status:
            raise HTTPException(status_code=404, detail="任务不存在")
        
        return background_tasks_status[task_id]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取任务状态失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/graphs/{graph_id}/analyze", response_model=AnalysisResultResponse)
async def analyze_graph(
    graph_id: str,
    request: AnalyzeGraphRequest,
    current_user: User = Depends(get_current_user)
):
    """分析知识图谱"""
    try:
        analytics = await get_graph_analytics()
        
        # 配置分析参数
        config = AnalysisConfig(
            analysis_types=request.analysis_types,
            max_path_length=request.max_path_length,
            similarity_threshold=request.similarity_threshold,
            top_k_results=request.top_k_results,
            enable_parallel=request.enable_parallel
        )
        
        # 执行分析
        result = await analytics.analyze_graph(graph_id, config)
        
        # 转换为响应格式
        response = AnalysisResultResponse(
            analysis_id=result.analysis_id,
            timestamp=result.timestamp,
            processing_time=result.processing_time,
            centrality_results=None,
            community_result=None,
            path_result=None,
            similarity_result=None,
            influence_result=None,
            anomaly_result=None,
            metadata=result.metadata,
            errors=result.errors
        )
        
        # 添加中心性结果
        if result.centrality_results:
            centrality_data = {}
            for metric, centrality_result in result.centrality_results.items():
                centrality_data[metric.value] = {
                    "top_entities": centrality_result.top_entities,
                    "statistics": centrality_result.statistics
                }
            response.centrality_results = centrality_data
        
        # 添加社区结果
        if result.community_result:
            response.community_result = {
                "algorithm": result.community_result.algorithm.value,
                "num_communities": result.community_result.num_communities,
                "modularity": result.community_result.modularity,
                "community_sizes": result.community_result.community_sizes
            }
        
        return response
        
    except Exception as e:
        logger.error(f"分析图失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/graphs/{graph_id}/search/entities", response_model=List[EntityResponse])
async def search_entities(
    graph_id: str,
    request: SearchEntitiesRequest,
    current_user: User = Depends(get_current_user)
):
    """搜索实体"""
    try:
        manager = await get_graph_manager()
        
        # 搜索实体
        result = await manager.search_entities(
            graph_id=graph_id,
            query=request.query,
            entity_type=request.entity_type,
            limit=request.limit
        )
        
        if not result.success:
            raise HTTPException(status_code=400, detail=result.error)
        
        # 转换为响应格式
        entities = []
        for entity in result.entities:
            entities.append(EntityResponse(
                id=entity.id,
                name=entity.name,
                entity_type=entity.entity_type,
                properties=entity.properties,
                metadata=entity.metadata
            ))
        
        return entities
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"搜索实体失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/graphs/{graph_id}/entities/{entity_id}/neighbors", response_model=List[EntityResponse])
async def get_entity_neighbors(
    graph_id: str,
    entity_id: str,
    relation_types: Optional[List[str]] = Query(None, description="关系类型过滤"),
    max_depth: int = Query(1, ge=1, le=3, description="最大深度"),
    current_user: User = Depends(get_current_user)
):
    """获取实体邻居"""
    try:
        manager = await get_graph_manager()
        
        # 获取邻居
        result = await manager.get_entity_neighbors(
            graph_id=graph_id,
            entity_id=entity_id,
            relation_types=relation_types,
            max_depth=max_depth
        )
        
        if not result.success:
            raise HTTPException(status_code=400, detail=result.error)
        
        # 转换为响应格式
        neighbors = []
        for entity in result.neighbors:
            neighbors.append(EntityResponse(
                id=entity.id,
                name=entity.name,
                entity_type=entity.entity_type,
                properties=entity.properties,
                metadata=entity.metadata
            ))
        
        return neighbors
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取实体邻居失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/graphs/{graph_id}/statistics")
async def get_graph_statistics(
    graph_id: str = Path(..., description="图ID"),
    current_user: User = Depends(get_current_user)
):
    """获取图统计信息"""
    try:
        manager = await get_graph_manager()
        
        # 获取统计信息
        result = await manager.get_graph_metrics(graph_id)
        
        if not result.success:
            raise HTTPException(status_code=400, detail=result.error)
        
        return result.metrics
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取图统计信息失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/graphs/{graph_id}")
async def delete_graph(
    graph_id: str = Path(..., description="图ID"),
    current_user: User = Depends(get_current_user)
):
    """删除知识图谱"""
    try:
        manager = await get_graph_manager()
        
        # 删除图
        result = await manager.delete_graph(graph_id)
        
        if not result.success:
            raise HTTPException(status_code=400, detail=result.error)
        
        return {"message": "图删除成功"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除图失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/graphs/{graph_id}/entities/{entity_id}")
async def delete_entity(
    graph_id: str,
    entity_id: str,
    current_user: User = Depends(get_current_user)
):
    """删除实体"""
    try:
        manager = await get_graph_manager()
        
        # 删除实体
        result = await manager.delete_entity(graph_id, entity_id)
        
        if not result.success:
            raise HTTPException(status_code=400, detail=result.error)
        
        return {"message": "实体删除成功"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除实体失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/graphs/{graph_id}/relations/{relation_id}")
async def delete_relation(
    graph_id: str,
    relation_id: str,
    current_user: User = Depends(get_current_user)
):
    """删除关系"""
    try:
        manager = await get_graph_manager()
        
        # 删除关系
        result = await manager.delete_relation(graph_id, relation_id)
        
        if not result.success:
            raise HTTPException(status_code=400, detail=result.error)
        
        return {"message": "关系删除成功"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除关系失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))