from typing import Any, Dict, List, Optional, Union, Tuple
from datetime import datetime, timedelta
from enum import Enum
import asyncio
import json
import math
from dataclasses import dataclass, field
from collections import defaultdict, Counter
import numpy as np

from backend.connectors.redis_client import RedisClient
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from backend.connectors.neo4j_client import Neo4jClient
from backend.services.vector_service import VectorService, VectorSearchRequest, VectorType, VectorModel
from backend.services.cache_service import CacheService
from backend.services.search_service import SearchService
from backend.utils.logger import get_logger

logger = get_logger(__name__)


class RecommendationType(str, Enum):
    """推荐类型枚举"""
    CONTENT_BASED = "content_based"  # 基于内容的推荐
    COLLABORATIVE = "collaborative"  # 协同过滤推荐
    HYBRID = "hybrid"  # 混合推荐
    KNOWLEDGE_GRAPH = "knowledge_graph"  # 基于知识图谱的推荐
    TRENDING = "trending"  # 热门推荐
    PERSONALIZED = "personalized"  # 个性化推荐
    SIMILAR_USERS = "similar_users"  # 相似用户推荐
    CONTEXTUAL = "contextual"  # 上下文推荐


class RecommendationScope(str, Enum):
    """推荐范围枚举"""
    DOCUMENTS = "documents"
    ENTITIES = "entities"
    RELATIONS = "relations"
    TOPICS = "topics"
    USERS = "users"
    QUERIES = "queries"
    ALL = "all"


class InteractionType(str, Enum):
    """交互类型枚举"""
    VIEW = "view"  # 查看
    SEARCH = "search"  # 搜索
    DOWNLOAD = "download"  # 下载
    BOOKMARK = "bookmark"  # 收藏
    SHARE = "share"  # 分享
    COMMENT = "comment"  # 评论
    RATE = "rate"  # 评分
    CLICK = "click"  # 点击
    DWELL_TIME = "dwell_time"  # 停留时间


@dataclass
class UserInteraction:
    """用户交互记录"""
    user_id: str
    item_id: str
    item_type: str  # document, entity, relation, etc.
    interaction_type: InteractionType
    value: float = 1.0  # 交互强度值
    context: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    session_id: Optional[str] = None
    source: Optional[str] = None  # 来源页面或功能


@dataclass
class UserProfile:
    """用户画像"""
    user_id: str
    interests: Dict[str, float] = field(default_factory=dict)  # 兴趣主题及权重
    preferences: Dict[str, Any] = field(default_factory=dict)  # 偏好设置
    interaction_history: List[UserInteraction] = field(default_factory=list)
    demographic_info: Dict[str, Any] = field(default_factory=dict)
    behavior_patterns: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


@dataclass
class RecommendationItem:
    """推荐项"""
    id: str
    title: str
    content: Optional[str] = None
    item_type: str = ""  # document, entity, relation, etc.
    score: float = 0.0
    confidence: float = 0.0
    reason: str = ""  # 推荐理由
    source: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class RecommendationRequest:
    """推荐请求"""
    user_id: str
    recommendation_type: RecommendationType = RecommendationType.HYBRID
    recommendation_scope: RecommendationScope = RecommendationScope.ALL
    top_k: int = 20
    diversity_threshold: float = 0.7  # 多样性阈值
    novelty_weight: float = 0.3  # 新颖性权重
    popularity_weight: float = 0.2  # 流行度权重
    recency_weight: float = 0.1  # 时效性权重
    exclude_seen: bool = True  # 排除已看过的内容
    include_explanations: bool = True  # 包含推荐解释
    context: Dict[str, Any] = field(default_factory=dict)
    filters: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RecommendationResponse:
    """推荐响应"""
    user_id: str
    recommendations: List[RecommendationItem]
    recommendation_type: RecommendationType
    recommendation_scope: RecommendationScope
    total_count: int
    generation_time: float
    diversity_score: float = 0.0
    novelty_score: float = 0.0
    coverage_score: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    explanations: List[str] = field(default_factory=list)


@dataclass
class RecommendationStats:
    """推荐统计"""
    total_recommendations: int = 0
    recommendations_by_type: Dict[RecommendationType, int] = field(default_factory=dict)
    avg_generation_time: float = 0.0
    avg_diversity_score: float = 0.0
    avg_novelty_score: float = 0.0
    click_through_rate: float = 0.0
    conversion_rate: float = 0.0
    user_satisfaction: float = 0.0
    last_updated: datetime = field(default_factory=datetime.now)


class RecommendationService:
    """推荐服务"""
    
    def __init__(
        self,
        redis_client: RedisClient,
        db: Session,
        neo4j_client: Neo4jClient,
        vector_service: VectorService,
        cache_service: CacheService,
        search_service: SearchService
    ):
        self.redis = redis_client
        self.db = db
        self.neo4j = neo4j_client
        self.vector_service = vector_service
        self.cache_service = cache_service
        self.search_service = search_service
        
        # 推荐统计
        self.recommendation_stats = RecommendationStats()
        
        # 用户画像缓存
        self.user_profiles: Dict[str, UserProfile] = {}
        
        # 推荐模型参数
        self.model_params = {
            "content_similarity_threshold": 0.7,
            "collaborative_min_interactions": 5,
            "hybrid_content_weight": 0.6,
            "hybrid_collaborative_weight": 0.4,
            "trending_time_window": 7,  # 天数
            "personalized_history_window": 30,  # 天数
            "similar_users_threshold": 0.8,
            "contextual_decay_factor": 0.9
        }
    
    async def initialize(self):
        """初始化推荐服务"""
        try:
            # 加载推荐统计
            await self._load_recommendation_stats()
            
            # 预热用户画像缓存
            await self._preload_user_profiles()
            
            # 初始化推荐模型
            await self._initialize_recommendation_models()
            
            logger.info("Recommendation service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize recommendation service: {str(e)}")
            raise
    
    async def get_recommendations(
        self,
        request: RecommendationRequest
    ) -> RecommendationResponse:
        """获取推荐"""
        try:
            start_time = datetime.now()
            
            # 获取用户画像
            user_profile = await self._get_user_profile(request.user_id)
            
            # 根据推荐类型生成推荐
            if request.recommendation_type == RecommendationType.CONTENT_BASED:
                recommendations = await self._content_based_recommendation(request, user_profile)
            elif request.recommendation_type == RecommendationType.COLLABORATIVE:
                recommendations = await self._collaborative_filtering_recommendation(request, user_profile)
            elif request.recommendation_type == RecommendationType.HYBRID:
                recommendations = await self._hybrid_recommendation(request, user_profile)
            elif request.recommendation_type == RecommendationType.KNOWLEDGE_GRAPH:
                recommendations = await self._knowledge_graph_recommendation(request, user_profile)
            elif request.recommendation_type == RecommendationType.TRENDING:
                recommendations = await self._trending_recommendation(request, user_profile)
            elif request.recommendation_type == RecommendationType.PERSONALIZED:
                recommendations = await self._personalized_recommendation(request, user_profile)
            elif request.recommendation_type == RecommendationType.SIMILAR_USERS:
                recommendations = await self._similar_users_recommendation(request, user_profile)
            elif request.recommendation_type == RecommendationType.CONTEXTUAL:
                recommendations = await self._contextual_recommendation(request, user_profile)
            else:
                recommendations = []
            
            # 后处理：多样性、新颖性、去重等
            processed_recommendations = await self._post_process_recommendations(
                recommendations, request, user_profile
            )
            
            # 限制结果数量
            final_recommendations = processed_recommendations[:request.top_k]
            
            # 计算推荐质量指标
            diversity_score = self._calculate_diversity_score(final_recommendations)
            novelty_score = self._calculate_novelty_score(final_recommendations, user_profile)
            coverage_score = self._calculate_coverage_score(final_recommendations)
            
            # 生成推荐解释
            explanations = []
            if request.include_explanations:
                explanations = await self._generate_explanations(
                    final_recommendations, request, user_profile
                )
            
            # 计算生成时间
            generation_time = (datetime.now() - start_time).total_seconds()
            
            # 构建响应
            response = RecommendationResponse(
                user_id=request.user_id,
                recommendations=final_recommendations,
                recommendation_type=request.recommendation_type,
                recommendation_scope=request.recommendation_scope,
                total_count=len(recommendations),
                generation_time=generation_time,
                diversity_score=diversity_score,
                novelty_score=novelty_score,
                coverage_score=coverage_score,
                explanations=explanations
            )
            
            # 记录推荐日志
            await self._log_recommendation(request, response)
            
            # 更新推荐统计
            await self._update_recommendation_stats(request, response)
            
            return response
            
        except Exception as e:
            logger.error(f"Get recommendations failed: {str(e)}")
            raise
    
    async def record_interaction(
        self,
        interaction: UserInteraction
    ):
        """记录用户交互"""
        try:
            # 存储交互记录到数据库
            await self._store_interaction(interaction)
            
            # 更新用户画像
            await self._update_user_profile(interaction)
            
            # 更新实时推荐缓存
            await self._update_realtime_recommendations(interaction)
            
            logger.debug(f"Recorded interaction: {interaction.user_id} -> {interaction.item_id}")
            
        except Exception as e:
            logger.error(f"Record interaction failed: {str(e)}")
    
    async def get_user_profile(
        self,
        user_id: str
    ) -> UserProfile:
        """获取用户画像"""
        try:
            return await self._get_user_profile(user_id)
            
        except Exception as e:
            logger.error(f"Get user profile failed: {str(e)}")
            return UserProfile(user_id=user_id)
    
    async def update_user_preferences(
        self,
        user_id: str,
        preferences: Dict[str, Any]
    ):
        """更新用户偏好"""
        try:
            user_profile = await self._get_user_profile(user_id)
            user_profile.preferences.update(preferences)
            user_profile.updated_at = datetime.now()
            
            # 保存用户画像
            await self._save_user_profile(user_profile)
            
            # 清除相关推荐缓存
            await self._clear_user_recommendation_cache(user_id)
            
            logger.info(f"Updated user preferences for {user_id}")
            
        except Exception as e:
            logger.error(f"Update user preferences failed: {str(e)}")
    
    async def get_recommendation_stats(self) -> RecommendationStats:
        """获取推荐统计"""
        try:
            # 计算最新统计
            stats = await self._calculate_recommendation_stats()
            return stats
            
        except Exception as e:
            logger.error(f"Get recommendation stats failed: {str(e)}")
            return RecommendationStats()
    
    async def get_trending_items(
        self,
        item_type: str = "all",
        time_window: int = 7,
        limit: int = 20
    ) -> List[RecommendationItem]:
        """获取热门项目"""
        try:
            return await self._get_trending_items_from_db(item_type, time_window, limit)
            
        except Exception as e:
            logger.error(f"Get trending items failed: {str(e)}")
            return []
    
    async def get_similar_users(
        self,
        user_id: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """获取相似用户"""
        try:
            user_profile = await self._get_user_profile(user_id)
            similar_users = await self._find_similar_users(user_profile, limit)
            return similar_users
            
        except Exception as e:
            logger.error(f"Get similar users failed: {str(e)}")
            return []
    
    async def clear_recommendation_cache(
        self,
        user_id: Optional[str] = None
    ):
        """清除推荐缓存"""
        try:
            if user_id:
                await self._clear_user_recommendation_cache(user_id)
            else:
                await self.cache_service.delete_pattern("recommendation:*")
                await self.cache_service.delete_pattern("user_profile:*")
            
            logger.info(f"Recommendation cache cleared for user: {user_id or 'all'}")
            
        except Exception as e:
            logger.error(f"Clear recommendation cache failed: {str(e)}")
    
    # 私有方法
    
    async def _content_based_recommendation(
        self,
        request: RecommendationRequest,
        user_profile: UserProfile
    ) -> List[RecommendationItem]:
        """基于内容的推荐"""
        try:
            recommendations = []
            
            # 获取用户历史交互的内容
            user_items = await self._get_user_interacted_items(request.user_id)
            
            if not user_items:
                # 如果没有历史记录，返回热门内容
                return await self._get_trending_items_from_db(
                    request.recommendation_scope.value,
                    self.model_params["trending_time_window"],
                    request.top_k * 2
                )
            
            # 为每个历史项目找相似内容
            for item in user_items[:10]:  # 限制历史项目数量
                similar_items = await self._find_similar_items_by_content(
                    item["id"], item["type"], request.recommendation_scope
                )
                
                for similar_item in similar_items:
                    # 计算推荐分数
                    score = similar_item["similarity"] * item["interaction_weight"]
                    
                    recommendation = RecommendationItem(
                        id=similar_item["id"],
                        title=similar_item["title"],
                        content=similar_item.get("content"),
                        item_type=similar_item["type"],
                        score=score,
                        confidence=similar_item["similarity"],
                        reason=f"因为您对'{item['title']}'感兴趣",
                        metadata=similar_item.get("metadata", {})
                    )
                    recommendations.append(recommendation)
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Content-based recommendation failed: {str(e)}")
            return []
    
    async def _collaborative_filtering_recommendation(
        self,
        request: RecommendationRequest,
        user_profile: UserProfile
    ) -> List[RecommendationItem]:
        """协同过滤推荐"""
        try:
            recommendations = []
            
            # 找到相似用户
            similar_users = await self._find_similar_users(user_profile, 20)
            
            if not similar_users:
                return []
            
            # 获取相似用户喜欢的内容
            item_scores = defaultdict(float)
            item_info = {}
            
            for similar_user in similar_users:
                user_items = await self._get_user_interacted_items(similar_user["user_id"])
                similarity = similar_user["similarity"]
                
                for item in user_items:
                    item_id = item["id"]
                    
                    # 跳过当前用户已交互的内容
                    if await self._user_has_interacted(request.user_id, item_id):
                        continue
                    
                    # 累积评分
                    item_scores[item_id] += item["interaction_weight"] * similarity
                    
                    if item_id not in item_info:
                        item_info[item_id] = item
            
            # 转换为推荐项
            for item_id, score in sorted(item_scores.items(), key=lambda x: x[1], reverse=True):
                if len(recommendations) >= request.top_k * 2:
                    break
                
                item = item_info[item_id]
                recommendation = RecommendationItem(
                    id=item_id,
                    title=item["title"],
                    content=item.get("content"),
                    item_type=item["type"],
                    score=score,
                    confidence=min(1.0, score),
                    reason="基于相似用户的喜好推荐",
                    metadata=item.get("metadata", {})
                )
                recommendations.append(recommendation)
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Collaborative filtering recommendation failed: {str(e)}")
            return []
    
    async def _hybrid_recommendation(
        self,
        request: RecommendationRequest,
        user_profile: UserProfile
    ) -> List[RecommendationItem]:
        """混合推荐"""
        try:
            # 并行执行基于内容和协同过滤的推荐
            content_task = self._content_based_recommendation(request, user_profile)
            collaborative_task = self._collaborative_filtering_recommendation(request, user_profile)
            
            content_recommendations, collaborative_recommendations = await asyncio.gather(
                content_task, collaborative_task
            )
            
            # 合并推荐结果
            merged_recommendations = await self._merge_recommendations(
                content_recommendations,
                collaborative_recommendations,
                self.model_params["hybrid_content_weight"],
                self.model_params["hybrid_collaborative_weight"]
            )
            
            return merged_recommendations
            
        except Exception as e:
            logger.error(f"Hybrid recommendation failed: {str(e)}")
            return []
    
    async def _knowledge_graph_recommendation(
        self,
        request: RecommendationRequest,
        user_profile: UserProfile
    ) -> List[RecommendationItem]:
        """基于知识图谱的推荐"""
        try:
            recommendations = []
            
            # 获取用户感兴趣的实体
            user_entities = await self._get_user_interested_entities(request.user_id)
            
            if not user_entities:
                return []
            
            # 通过知识图谱扩展相关实体和关系
            for entity in user_entities[:5]:  # 限制实体数量
                # 查找相关实体
                related_entities = await self._find_related_entities_in_graph(
                    entity["id"], max_depth=2, limit=10
                )
                
                for related_entity in related_entities:
                    # 查找包含该实体的文档
                    documents = await self._find_documents_containing_entity(
                        related_entity["id"]
                    )
                    
                    for doc in documents:
                        score = (
                            entity["interest_score"] * 
                            related_entity["relation_strength"] * 
                            doc["relevance"]
                        )
                        
                        recommendation = RecommendationItem(
                            id=doc["id"],
                            title=doc["title"],
                            content=doc.get("content"),
                            item_type="document",
                            score=score,
                            confidence=related_entity["relation_strength"],
                            reason=f"与您感兴趣的'{entity['name']}'相关",
                            metadata=doc.get("metadata", {})
                        )
                        recommendations.append(recommendation)
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Knowledge graph recommendation failed: {str(e)}")
            return []
    
    async def _trending_recommendation(
        self,
        request: RecommendationRequest,
        user_profile: UserProfile
    ) -> List[RecommendationItem]:
        """热门推荐"""
        try:
            trending_items = await self._get_trending_items_from_db(
                request.recommendation_scope.value,
                self.model_params["trending_time_window"],
                request.top_k * 2
            )
            
            # 根据用户兴趣调整热门内容的分数
            for item in trending_items:
                # 计算与用户兴趣的匹配度
                interest_match = self._calculate_interest_match(item, user_profile)
                
                # 调整分数
                item.score = item.score * (0.7 + 0.3 * interest_match)
                item.reason = "当前热门内容"
                
                if interest_match > 0.5:
                    item.reason += "，符合您的兴趣"
            
            return trending_items
            
        except Exception as e:
            logger.error(f"Trending recommendation failed: {str(e)}")
            return []
    
    async def _personalized_recommendation(
        self,
        request: RecommendationRequest,
        user_profile: UserProfile
    ) -> List[RecommendationItem]:
        """个性化推荐"""
        try:
            # 综合多种推荐策略
            strategies = [
                self._content_based_recommendation(request, user_profile),
                self._collaborative_filtering_recommendation(request, user_profile),
                self._knowledge_graph_recommendation(request, user_profile),
                self._trending_recommendation(request, user_profile)
            ]
            
            results = await asyncio.gather(*strategies)
            
            # 合并所有推荐结果
            all_recommendations = []
            weights = [0.3, 0.3, 0.25, 0.15]  # 各策略权重
            
            for i, recommendations in enumerate(results):
                for rec in recommendations:
                    rec.score *= weights[i]
                    all_recommendations.append(rec)
            
            # 去重并重新排序
            unique_recommendations = self._deduplicate_recommendations(all_recommendations)
            
            return sorted(unique_recommendations, key=lambda x: x.score, reverse=True)
            
        except Exception as e:
            logger.error(f"Personalized recommendation failed: {str(e)}")
            return []
    
    async def _similar_users_recommendation(
        self,
        request: RecommendationRequest,
        user_profile: UserProfile
    ) -> List[RecommendationItem]:
        """相似用户推荐"""
        try:
            # 找到最相似的用户
            similar_users = await self._find_similar_users(user_profile, 5)
            
            if not similar_users:
                return []
            
            recommendations = []
            
            # 获取相似用户最近的交互内容
            for similar_user in similar_users:
                recent_items = await self._get_user_recent_interactions(
                    similar_user["user_id"], days=7, limit=10
                )
                
                for item in recent_items:
                    # 跳过当前用户已交互的内容
                    if await self._user_has_interacted(request.user_id, item["item_id"]):
                        continue
                    
                    score = similar_user["similarity"] * item["interaction_weight"]
                    
                    recommendation = RecommendationItem(
                        id=item["item_id"],
                        title=item["title"],
                        content=item.get("content"),
                        item_type=item["item_type"],
                        score=score,
                        confidence=similar_user["similarity"],
                        reason=f"相似用户最近关注的内容",
                        metadata=item.get("metadata", {})
                    )
                    recommendations.append(recommendation)
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Similar users recommendation failed: {str(e)}")
            return []
    
    async def _contextual_recommendation(
        self,
        request: RecommendationRequest,
        user_profile: UserProfile
    ) -> List[RecommendationItem]:
        """上下文推荐"""
        try:
            recommendations = []
            
            # 获取上下文信息
            context = request.context
            current_time = datetime.now()
            
            # 基于时间上下文
            if "time_context" in context:
                time_based_items = await self._get_time_based_recommendations(
                    context["time_context"], request.top_k
                )
                recommendations.extend(time_based_items)
            
            # 基于位置上下文
            if "location_context" in context:
                location_based_items = await self._get_location_based_recommendations(
                    context["location_context"], request.top_k
                )
                recommendations.extend(location_based_items)
            
            # 基于设备上下文
            if "device_context" in context:
                device_based_items = await self._get_device_based_recommendations(
                    context["device_context"], request.top_k
                )
                recommendations.extend(device_based_items)
            
            # 基于会话上下文
            if "session_context" in context:
                session_based_items = await self._get_session_based_recommendations(
                    context["session_context"], request.user_id, request.top_k
                )
                recommendations.extend(session_based_items)
            
            # 应用上下文衰减因子
            decay_factor = self.model_params["contextual_decay_factor"]
            for rec in recommendations:
                rec.score *= decay_factor
                rec.reason = "基于当前上下文推荐"
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Contextual recommendation failed: {str(e)}")
            return []
    
    async def _post_process_recommendations(
        self,
        recommendations: List[RecommendationItem],
        request: RecommendationRequest,
        user_profile: UserProfile
    ) -> List[RecommendationItem]:
        """后处理推荐结果"""
        try:
            # 去重
            unique_recommendations = self._deduplicate_recommendations(recommendations)
            
            # 过滤已看过的内容
            if request.exclude_seen:
                filtered_recommendations = []
                for rec in unique_recommendations:
                    if not await self._user_has_interacted(request.user_id, rec.id):
                        filtered_recommendations.append(rec)
                unique_recommendations = filtered_recommendations
            
            # 应用过滤器
            if request.filters:
                unique_recommendations = self._apply_filters(
                    unique_recommendations, request.filters
                )
            
            # 多样性处理
            diverse_recommendations = self._ensure_diversity(
                unique_recommendations, request.diversity_threshold
            )
            
            # 新颖性和流行度平衡
            balanced_recommendations = self._balance_novelty_popularity(
                diverse_recommendations,
                request.novelty_weight,
                request.popularity_weight,
                request.recency_weight
            )
            
            # 最终排序
            final_recommendations = sorted(
                balanced_recommendations,
                key=lambda x: x.score,
                reverse=True
            )
            
            return final_recommendations
            
        except Exception as e:
            logger.error(f"Post-process recommendations failed: {str(e)}")
            return recommendations
    
    def _deduplicate_recommendations(
        self,
        recommendations: List[RecommendationItem]
    ) -> List[RecommendationItem]:
        """去重推荐结果"""
        try:
            seen_ids = set()
            unique_recommendations = []
            
            for rec in recommendations:
                if rec.id not in seen_ids:
                    seen_ids.add(rec.id)
                    unique_recommendations.append(rec)
                else:
                    # 如果ID重复，合并分数
                    for existing_rec in unique_recommendations:
                        if existing_rec.id == rec.id:
                            existing_rec.score = max(existing_rec.score, rec.score)
                            break
            
            return unique_recommendations
            
        except Exception as e:
            logger.error(f"Deduplicate recommendations failed: {str(e)}")
            return recommendations
    
    def _ensure_diversity(
        self,
        recommendations: List[RecommendationItem],
        diversity_threshold: float
    ) -> List[RecommendationItem]:
        """确保推荐多样性"""
        try:
            if not recommendations:
                return recommendations
            
            diverse_recommendations = [recommendations[0]]  # 添加第一个
            
            for rec in recommendations[1:]:
                # 检查与已选择项目的相似性
                is_diverse = True
                
                for selected_rec in diverse_recommendations:
                    similarity = self._calculate_item_similarity(rec, selected_rec)
                    if similarity > diversity_threshold:
                        is_diverse = False
                        break
                
                if is_diverse:
                    diverse_recommendations.append(rec)
            
            return diverse_recommendations
            
        except Exception as e:
            logger.error(f"Ensure diversity failed: {str(e)}")
            return recommendations
    
    def _balance_novelty_popularity(
        self,
        recommendations: List[RecommendationItem],
        novelty_weight: float,
        popularity_weight: float,
        recency_weight: float
    ) -> List[RecommendationItem]:
        """平衡新颖性和流行度"""
        try:
            for rec in recommendations:
                # 计算新颖性分数（基于创建时间）
                novelty_score = 0.5  # 默认值
                if rec.created_at:
                    days_old = (datetime.now() - rec.created_at).days
                    novelty_score = max(0, 1 - days_old / 365)  # 一年内的内容有新颖性加分
                
                # 计算流行度分数（基于元数据中的交互次数）
                popularity_score = min(1.0, rec.metadata.get("interaction_count", 0) / 1000)
                
                # 计算时效性分数
                recency_score = 0.5  # 默认值
                if rec.updated_at:
                    days_since_update = (datetime.now() - rec.updated_at).days
                    recency_score = max(0, 1 - days_since_update / 30)  # 30天内更新的内容有时效性加分
                
                # 调整最终分数
                rec.score = (
                    rec.score * (1 - novelty_weight - popularity_weight - recency_weight) +
                    novelty_score * novelty_weight +
                    popularity_score * popularity_weight +
                    recency_score * recency_weight
                )
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Balance novelty popularity failed: {str(e)}")
            return recommendations
    
    def _apply_filters(
        self,
        recommendations: List[RecommendationItem],
        filters: Dict[str, Any]
    ) -> List[RecommendationItem]:
        """应用过滤器"""
        try:
            filtered_recommendations = []
            
            for rec in recommendations:
                include_item = True
                
                # 应用各种过滤条件
                if "item_types" in filters:
                    if rec.item_type not in filters["item_types"]:
                        include_item = False
                
                if "min_score" in filters:
                    if rec.score < filters["min_score"]:
                        include_item = False
                
                if "tags" in filters:
                    if not any(tag in rec.tags for tag in filters["tags"]):
                        include_item = False
                
                if "date_range" in filters:
                    start_date, end_date = filters["date_range"]
                    if rec.created_at and not (start_date <= rec.created_at <= end_date):
                        include_item = False
                
                if include_item:
                    filtered_recommendations.append(rec)
            
            return filtered_recommendations
            
        except Exception as e:
            logger.error(f"Apply filters failed: {str(e)}")
            return recommendations
    
    def _calculate_diversity_score(
        self,
        recommendations: List[RecommendationItem]
    ) -> float:
        """计算推荐多样性分数"""
        try:
            if len(recommendations) < 2:
                return 1.0
            
            total_similarity = 0.0
            pair_count = 0
            
            for i in range(len(recommendations)):
                for j in range(i + 1, len(recommendations)):
                    similarity = self._calculate_item_similarity(
                        recommendations[i], recommendations[j]
                    )
                    total_similarity += similarity
                    pair_count += 1
            
            avg_similarity = total_similarity / pair_count if pair_count > 0 else 0
            diversity_score = 1 - avg_similarity
            
            return max(0, min(1, diversity_score))
            
        except Exception as e:
            logger.error(f"Calculate diversity score failed: {str(e)}")
            return 0.5
    
    def _calculate_novelty_score(
        self,
        recommendations: List[RecommendationItem],
        user_profile: UserProfile
    ) -> float:
        """计算推荐新颖性分数"""
        try:
            if not recommendations:
                return 0.0
            
            novelty_scores = []
            
            for rec in recommendations:
                # 基于用户历史交互计算新颖性
                novelty = 1.0  # 默认新颖性
                
                # 检查用户是否接触过相似内容
                for interaction in user_profile.interaction_history[-50:]:  # 检查最近50次交互
                    if interaction.item_type == rec.item_type:
                        # 这里可以计算内容相似性，简化为类型匹配
                        novelty *= 0.9
                
                # 基于创建时间的新颖性
                if rec.created_at:
                    days_old = (datetime.now() - rec.created_at).days
                    time_novelty = max(0, 1 - days_old / 365)
                    novelty = (novelty + time_novelty) / 2
                
                novelty_scores.append(novelty)
            
            return sum(novelty_scores) / len(novelty_scores)
            
        except Exception as e:
            logger.error(f"Calculate novelty score failed: {str(e)}")
            return 0.5
    
    def _calculate_coverage_score(
        self,
        recommendations: List[RecommendationItem]
    ) -> float:
        """计算推荐覆盖度分数"""
        try:
            if not recommendations:
                return 0.0
            
            # 统计不同类型的推荐项
            item_types = set(rec.item_type for rec in recommendations)
            
            # 统计不同来源的推荐项
            sources = set(rec.source for rec in recommendations if rec.source)
            
            # 统计不同标签的推荐项
            all_tags = set()
            for rec in recommendations:
                all_tags.update(rec.tags)
            
            # 计算覆盖度（基于类型、来源、标签的多样性）
            type_coverage = min(1.0, len(item_types) / 5)  # 假设最多5种类型
            source_coverage = min(1.0, len(sources) / 10)  # 假设最多10个来源
            tag_coverage = min(1.0, len(all_tags) / 20)  # 假设最多20个标签
            
            coverage_score = (type_coverage + source_coverage + tag_coverage) / 3
            
            return coverage_score
            
        except Exception as e:
            logger.error(f"Calculate coverage score failed: {str(e)}")
            return 0.5
    
    def _calculate_item_similarity(
        self,
        item1: RecommendationItem,
        item2: RecommendationItem
    ) -> float:
        """计算两个推荐项的相似性"""
        try:
            # 类型相似性
            type_similarity = 1.0 if item1.item_type == item2.item_type else 0.0
            
            # 标签相似性
            tags1 = set(item1.tags)
            tags2 = set(item2.tags)
            if tags1 or tags2:
                tag_similarity = len(tags1 & tags2) / len(tags1 | tags2)
            else:
                tag_similarity = 0.0
            
            # 来源相似性
            source_similarity = 1.0 if item1.source == item2.source else 0.0
            
            # 综合相似性
            similarity = (type_similarity * 0.5 + tag_similarity * 0.3 + source_similarity * 0.2)
            
            return similarity
            
        except Exception as e:
            logger.error(f"Calculate item similarity failed: {str(e)}")
            return 0.0
    
    def _calculate_interest_match(
        self,
        item: RecommendationItem,
        user_profile: UserProfile
    ) -> float:
        """计算项目与用户兴趣的匹配度"""
        try:
            if not user_profile.interests:
                return 0.5  # 默认匹配度
            
            match_score = 0.0
            
            # 基于标签匹配
            for tag in item.tags:
                if tag in user_profile.interests:
                    match_score += user_profile.interests[tag]
            
            # 基于内容类型匹配
            if item.item_type in user_profile.interests:
                match_score += user_profile.interests[item.item_type]
            
            # 标准化分数
            max_possible_score = sum(user_profile.interests.values())
            if max_possible_score > 0:
                match_score = min(1.0, match_score / max_possible_score)
            
            return match_score
            
        except Exception as e:
            logger.error(f"Calculate interest match failed: {str(e)}")
            return 0.5
    
    async def _merge_recommendations(
        self,
        content_recommendations: List[RecommendationItem],
        collaborative_recommendations: List[RecommendationItem],
        content_weight: float,
        collaborative_weight: float
    ) -> List[RecommendationItem]:
        """合并推荐结果"""
        try:
            # 创建推荐字典，以ID为键
            merged_dict = {}
            
            # 添加基于内容的推荐
            for rec in content_recommendations:
                rec.score *= content_weight
                merged_dict[rec.id] = rec
            
            # 添加协同过滤推荐
            for rec in collaborative_recommendations:
                if rec.id in merged_dict:
                    # 合并分数
                    merged_dict[rec.id].score += rec.score * collaborative_weight
                    merged_dict[rec.id].reason += " + 相似用户推荐"
                else:
                    rec.score *= collaborative_weight
                    merged_dict[rec.id] = rec
            
            return list(merged_dict.values())
            
        except Exception as e:
            logger.error(f"Merge recommendations failed: {str(e)}")
            return content_recommendations + collaborative_recommendations
    
    async def _generate_explanations(
        self,
        recommendations: List[RecommendationItem],
        request: RecommendationRequest,
        user_profile: UserProfile
    ) -> List[str]:
        """生成推荐解释"""
        try:
            explanations = []
            
            # 分析推荐来源
            type_counts = Counter(rec.item_type for rec in recommendations)
            source_counts = Counter(rec.source for rec in recommendations if rec.source)
            
            # 生成总体解释
            if request.recommendation_type == RecommendationType.HYBRID:
                explanations.append("基于您的兴趣偏好和相似用户行为的综合推荐")
            elif request.recommendation_type == RecommendationType.CONTENT_BASED:
                explanations.append("基于您历史浏览内容的相似性推荐")
            elif request.recommendation_type == RecommendationType.COLLABORATIVE:
                explanations.append("基于与您兴趣相似的用户喜好推荐")
            elif request.recommendation_type == RecommendationType.TRENDING:
                explanations.append("当前热门和趋势内容推荐")
            
            # 生成内容类型解释
            if type_counts:
                most_common_type = type_counts.most_common(1)[0]
                explanations.append(f"主要推荐{most_common_type[0]}类型内容({most_common_type[1]}项)")
            
            # 生成个性化解释
            if user_profile.interests:
                top_interests = sorted(
                    user_profile.interests.items(),
                    key=lambda x: x[1],
                    reverse=True
                )[:3]
                
                interest_names = [interest[0] for interest in top_interests]
                explanations.append(f"根据您对{', '.join(interest_names)}的兴趣推荐")
            
            return explanations
            
        except Exception as e:
            logger.error(f"Generate explanations failed: {str(e)}")
            return ["基于智能算法的个性化推荐"]
    
    # 数据访问方法
    
    async def _get_user_profile(self, user_id: str) -> UserProfile:
        """获取用户画像"""
        try:
            # 先从缓存获取
            if user_id in self.user_profiles:
                return self.user_profiles[user_id]
            
            # 从缓存服务获取
            cache_key = f"user_profile:{user_id}"
            cached_profile = await self.cache_service.get(cache_key)
            
            if cached_profile:
                profile = UserProfile(**cached_profile)
                self.user_profiles[user_id] = profile
                return profile
            
            # 从数据库构建用户画像
            profile = await self._build_user_profile_from_db(user_id)
            
            # 缓存用户画像
            await self.cache_service.set(
                cache_key,
                profile.__dict__,
                ttl=3600  # 1小时
            )
            
            self.user_profiles[user_id] = profile
            return profile
            
        except Exception as e:
            logger.error(f"Get user profile failed: {str(e)}")
            return UserProfile(user_id=user_id)
    
    async def _build_user_profile_from_db(self, user_id: str) -> UserProfile:
        """从数据库构建用户画像"""
        try:
            # 获取用户基本信息
            from backend.models.user import User
            from backend.models.user import UserInteraction as UserInteractionModel
            
            user_info = self.db.query(User).filter(User.id == user_id).first()
            
            # 获取用户交互历史
            interactions_data = (
                self.db.query(UserInteractionModel)
                .filter(UserInteractionModel.user_id == user_id)
                .order_by(UserInteractionModel.timestamp.desc())
                .limit(1000)
                .all()
            )
            
            interactions = []
            for row in interactions_data:
                interaction = UserInteraction(
                    user_id=user_id,
                    item_id=row.item_id,
                    item_type=row.item_type,
                    interaction_type=InteractionType(row.interaction_type),
                    value=float(row.value),
                    context=json.loads(row.context) if row.context else {},
                    timestamp=row.timestamp
                )
                interactions.append(interaction)
            
            # 分析用户兴趣
            interests = self._analyze_user_interests(interactions)
            
            # 分析行为模式
            behavior_patterns = self._analyze_behavior_patterns(interactions)
            
            # 构建用户画像
            profile = UserProfile(
                user_id=user_id,
                interests=interests,
                interaction_history=interactions,
                behavior_patterns=behavior_patterns,
                demographic_info=json.loads(user_info.demographic_info) if user_info and user_info.demographic_info else {},
                preferences=json.loads(user_info.preferences) if user_info and user_info.preferences else {}
            )
            
            return profile
            
        except Exception as e:
            logger.error(f"Build user profile from DB failed: {str(e)}")
            return UserProfile(user_id=user_id)
    
    def _analyze_user_interests(self, interactions: List[UserInteraction]) -> Dict[str, float]:
        """分析用户兴趣"""
        try:
            interests = defaultdict(float)
            
            # 定义交互类型权重
            interaction_weights = {
                InteractionType.VIEW: 1.0,
                InteractionType.SEARCH: 1.5,
                InteractionType.DOWNLOAD: 2.0,
                InteractionType.BOOKMARK: 3.0,
                InteractionType.SHARE: 2.5,
                InteractionType.COMMENT: 2.0,
                InteractionType.RATE: 2.0,
                InteractionType.CLICK: 0.5,
                InteractionType.DWELL_TIME: 1.0
            }
            
            # 时间衰减因子
            now = datetime.now()
            
            for interaction in interactions:
                # 计算时间衰减
                days_ago = (now - interaction.timestamp).days
                time_decay = math.exp(-days_ago / 30)  # 30天半衰期
                
                # 计算兴趣权重
                weight = (
                    interaction_weights.get(interaction.interaction_type, 1.0) *
                    interaction.value *
                    time_decay
                )
                
                # 基于项目类型累积兴趣
                interests[interaction.item_type] += weight
                
                # 基于上下文信息累积兴趣
                if "tags" in interaction.context:
                    for tag in interaction.context["tags"]:
                        interests[tag] += weight * 0.5
                
                if "category" in interaction.context:
                    interests[interaction.context["category"]] += weight * 0.7
            
            # 标准化兴趣分数
            if interests:
                max_interest = max(interests.values())
                interests = {k: v / max_interest for k, v in interests.items()}
            
            return dict(interests)
            
        except Exception as e:
            logger.error(f"Analyze user interests failed: {str(e)}")
            return {}
    
    def _analyze_behavior_patterns(self, interactions: List[UserInteraction]) -> Dict[str, Any]:
        """分析用户行为模式"""
        try:
            patterns = {}
            
            if not interactions:
                return patterns
            
            # 活跃时间分析
            hour_counts = defaultdict(int)
            day_counts = defaultdict(int)
            
            for interaction in interactions:
                hour_counts[interaction.timestamp.hour] += 1
                day_counts[interaction.timestamp.weekday()] += 1
            
            patterns["active_hours"] = dict(hour_counts)
            patterns["active_days"] = dict(day_counts)
            
            # 交互频率分析
            interaction_type_counts = defaultdict(int)
            for interaction in interactions:
                interaction_type_counts[interaction.interaction_type.value] += 1
            
            patterns["interaction_frequencies"] = dict(interaction_type_counts)
            
            # 会话长度分析
            sessions = defaultdict(list)
            for interaction in interactions:
                if interaction.session_id:
                    sessions[interaction.session_id].append(interaction.timestamp)
            
            session_durations = []
            for session_times in sessions.values():
                if len(session_times) > 1:
                    duration = (max(session_times) - min(session_times)).total_seconds() / 60
                    session_durations.append(duration)
            
            if session_durations:
                patterns["avg_session_duration"] = sum(session_durations) / len(session_durations)
                patterns["max_session_duration"] = max(session_durations)
            
            # 内容偏好分析
            item_type_preferences = defaultdict(float)
            for interaction in interactions:
                weight = interaction.value
                item_type_preferences[interaction.item_type] += weight
            
            patterns["content_preferences"] = dict(item_type_preferences)
            
            return patterns
            
        except Exception as e:
            logger.error(f"Analyze behavior patterns failed: {str(e)}")
            return {}
    
    async def _save_user_profile(self, profile: UserProfile):
        """保存用户画像"""
        try:
            # 更新内存缓存
            self.user_profiles[profile.user_id] = profile
            
            # 更新缓存服务
            cache_key = f"user_profile:{profile.user_id}"
            await self.cache_service.set(
                cache_key,
                profile.__dict__,
                ttl=3600
            )
            
            # 更新数据库
            try:
                from backend.models.user import User
                
                user = self.db.query(User).filter(User.id == profile.user_id).first()
                if user:
                    user.interests = json.dumps(profile.interests)
                    user.preferences = json.dumps(profile.preferences)
                    user.behavior_patterns = json.dumps(profile.behavior_patterns)
                    user.updated_at = profile.updated_at
                    self.db.commit()
            except IntegrityError as e:
                self.db.rollback()
                logger.error(f"Database integrity error when saving user profile: {str(e)}")
                raise
            
        except Exception as e:
            logger.error(f"Save user profile failed: {str(e)}")
    
    async def _store_interaction(self, interaction: UserInteraction):
        """存储用户交互记录"""
        try:
            from backend.models.user import UserInteraction as UserInteractionModel
            
            db_interaction = UserInteractionModel(
                user_id=interaction.user_id,
                item_id=interaction.item_id,
                item_type=interaction.item_type,
                interaction_type=interaction.interaction_type.value,
                value=interaction.value,
                context=json.dumps(interaction.context),
                timestamp=interaction.timestamp,
                session_id=interaction.session_id,
                source=interaction.source
            )
            self.db.add(db_interaction)
            self.db.commit()
            
        except Exception as e:
            logger.error(f"Store interaction failed: {str(e)}")
    
    async def _update_user_profile(self, interaction: UserInteraction):
        """更新用户画像"""
        try:
            user_profile = await self._get_user_profile(interaction.user_id)
            
            # 添加新的交互记录
            user_profile.interaction_history.append(interaction)
            
            # 保持历史记录在合理范围内
            if len(user_profile.interaction_history) > 1000:
                user_profile.interaction_history = user_profile.interaction_history[-1000:]
            
            # 重新分析兴趣和行为模式
            user_profile.interests = self._analyze_user_interests(user_profile.interaction_history)
            user_profile.behavior_patterns = self._analyze_behavior_patterns(user_profile.interaction_history)
            user_profile.updated_at = datetime.now()
            
            # 保存更新后的用户画像
            await self._save_user_profile(user_profile)
            
        except Exception as e:
            logger.error(f"Update user profile failed: {str(e)}")
    
    async def _update_realtime_recommendations(self, interaction: UserInteraction):
        """更新实时推荐缓存"""
        try:
            # 清除用户相关的推荐缓存
            await self._clear_user_recommendation_cache(interaction.user_id)
            
        except Exception as e:
            logger.error(f"Update realtime recommendations failed: {str(e)}")