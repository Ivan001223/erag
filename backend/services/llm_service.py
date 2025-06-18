from typing import List, Dict, Any, Optional, Union, AsyncGenerator
from datetime import datetime
import asyncio
import json
from enum import Enum
from abc import ABC, abstractmethod

from backend.connectors.redis_client import RedisClient
from backend.models.base import BaseModel
from backend.utils.logger import get_logger

logger = get_logger(__name__)


class ModelProvider(str, Enum):
    """模型提供商枚举"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    AZURE_OPENAI = "azure_openai"
    HUGGINGFACE = "huggingface"
    OLLAMA = "ollama"
    QWEN = "qwen"
    BAIDU = "baidu"
    ZHIPU = "zhipu"
    MOONSHOT = "moonshot"


class ModelType(str, Enum):
    """模型类型枚举"""
    CHAT = "chat"
    COMPLETION = "completion"
    EMBEDDING = "embedding"
    RERANK = "rerank"
    VISION = "vision"
    CODE = "code"


class MessageRole(str, Enum):
    """消息角色枚举"""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    FUNCTION = "function"
    TOOL = "tool"


class ChatMessage(BaseModel):
    """聊天消息模型"""
    role: MessageRole
    content: str
    name: Optional[str] = None
    function_call: Optional[Dict[str, Any]] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_call_id: Optional[str] = None


class ModelConfig(BaseModel):
    """模型配置"""
    provider: ModelProvider
    model_name: str
    model_type: ModelType
    api_key: Optional[str] = None
    api_base: Optional[str] = None
    api_version: Optional[str] = None
    max_tokens: int = 4096
    temperature: float = 0.7
    top_p: float = 1.0
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    timeout: int = 60
    max_retries: int = 3
    is_active: bool = True
    priority: int = 1  # 优先级，数字越小优先级越高
    rate_limit: Optional[int] = None  # 每分钟请求限制
    cost_per_1k_tokens: float = 0.0  # 每1K token的成本
    context_window: int = 4096  # 上下文窗口大小
    supports_streaming: bool = True
    supports_functions: bool = False
    supports_vision: bool = False


class LLMRequest(BaseModel):
    """LLM请求模型"""
    messages: List[ChatMessage]
    model_configuration: Optional[ModelConfig] = None
    model_name: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    stream: bool = False
    functions: Optional[List[Dict[str, Any]]] = None
    function_call: Optional[Union[str, Dict[str, Any]]] = None
    tools: Optional[List[Dict[str, Any]]] = None
    tool_choice: Optional[Union[str, Dict[str, Any]]] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    metadata: Dict[str, Any] = {}


class LLMResponse(BaseModel):
    """LLM响应模型"""
    id: str
    content: str
    role: MessageRole = MessageRole.ASSISTANT
    function_call: Optional[Dict[str, Any]] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None
    model: str
    provider: ModelProvider
    usage: Dict[str, int] = {}  # prompt_tokens, completion_tokens, total_tokens
    finish_reason: Optional[str] = None
    created_at: datetime
    latency_ms: int
    cost: float = 0.0
    metadata: Dict[str, Any] = {}


class LLMProvider(ABC):
    """LLM提供商抽象基类"""
    
    def __init__(self, config: ModelConfig):
        self.config = config
        
    @abstractmethod
    async def chat_completion(
        self,
        messages: List[ChatMessage],
        **kwargs
    ) -> LLMResponse:
        """聊天补全"""
        pass
    
    @abstractmethod
    async def stream_chat_completion(
        self,
        messages: List[ChatMessage],
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """流式聊天补全"""
        pass
    
    @abstractmethod
    async def embedding(
        self,
        texts: List[str],
        **kwargs
    ) -> List[List[float]]:
        """文本嵌入"""
        pass
    
    async def health_check(self) -> bool:
        """健康检查"""
        try:
            test_messages = [
                ChatMessage(role=MessageRole.USER, content="Hello")
            ]
            response = await self.chat_completion(test_messages, max_tokens=10)
            return response is not None
        except Exception:
            return False


class OpenAIProvider(LLMProvider):
    """OpenAI提供商实现"""
    
    def __init__(self, config: ModelConfig):
        super().__init__(config)
        # TODO: 初始化OpenAI客户端
        
    async def chat_completion(
        self,
        messages: List[ChatMessage],
        **kwargs
    ) -> LLMResponse:
        """OpenAI聊天补全实现"""
        start_time = datetime.now()
        
        try:
            # TODO: 实现OpenAI API调用
            # 这里是示例实现
            response_content = "This is a mock response from OpenAI"
            
            end_time = datetime.now()
            latency_ms = int((end_time - start_time).total_seconds() * 1000)
            
            return LLMResponse(
                id=f"openai_{int(datetime.now().timestamp() * 1000)}",
                content=response_content,
                model=self.config.model_name,
                provider=self.config.provider,
                usage={"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
                finish_reason="stop",
                created_at=end_time,
                latency_ms=latency_ms,
                cost=self._calculate_cost(150)
            )
            
        except Exception as e:
            logger.error(f"OpenAI chat completion failed: {str(e)}")
            raise
    
    async def stream_chat_completion(
        self,
        messages: List[ChatMessage],
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """OpenAI流式聊天补全实现"""
        try:
            # TODO: 实现OpenAI流式API调用
            # 这里是示例实现
            response_parts = ["This ", "is ", "a ", "mock ", "streaming ", "response"]
            
            for part in response_parts:
                yield part
                await asyncio.sleep(0.1)
                
        except Exception as e:
            logger.error(f"OpenAI stream chat completion failed: {str(e)}")
            raise
    
    async def embedding(
        self,
        texts: List[str],
        **kwargs
    ) -> List[List[float]]:
        """OpenAI嵌入实现"""
        try:
            # TODO: 实现OpenAI嵌入API调用
            # 这里是示例实现
            embeddings = []
            for text in texts:
                # 生成模拟的768维嵌入向量
                embedding = [0.1] * 768
                embeddings.append(embedding)
                
            return embeddings
            
        except Exception as e:
            logger.error(f"OpenAI embedding failed: {str(e)}")
            raise
    
    def _calculate_cost(self, total_tokens: int) -> float:
        """计算成本"""
        return (total_tokens / 1000) * self.config.cost_per_1k_tokens


class AnthropicProvider(LLMProvider):
    """Anthropic提供商实现"""
    
    def __init__(self, config: ModelConfig):
        super().__init__(config)
        # TODO: 初始化Anthropic客户端
        
    async def chat_completion(
        self,
        messages: List[ChatMessage],
        **kwargs
    ) -> LLMResponse:
        """Anthropic聊天补全实现"""
        start_time = datetime.now()
        
        try:
            # TODO: 实现Anthropic API调用
            response_content = "This is a mock response from Anthropic"
            
            end_time = datetime.now()
            latency_ms = int((end_time - start_time).total_seconds() * 1000)
            
            return LLMResponse(
                id=f"anthropic_{int(datetime.now().timestamp() * 1000)}",
                content=response_content,
                model=self.config.model_name,
                provider=self.config.provider,
                usage={"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
                finish_reason="stop",
                created_at=end_time,
                latency_ms=latency_ms,
                cost=self._calculate_cost(150)
            )
            
        except Exception as e:
            logger.error(f"Anthropic chat completion failed: {str(e)}")
            raise
    
    async def stream_chat_completion(
        self,
        messages: List[ChatMessage],
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """Anthropic流式聊天补全实现"""
        try:
            # TODO: 实现Anthropic流式API调用
            response_parts = ["This ", "is ", "a ", "mock ", "streaming ", "response"]
            
            for part in response_parts:
                yield part
                await asyncio.sleep(0.1)
                
        except Exception as e:
            logger.error(f"Anthropic stream chat completion failed: {str(e)}")
            raise
    
    async def embedding(
        self,
        texts: List[str],
        **kwargs
    ) -> List[List[float]]:
        """Anthropic嵌入实现（如果支持）"""
        # Anthropic目前不提供嵌入服务
        raise NotImplementedError("Anthropic does not provide embedding service")
    
    def _calculate_cost(self, total_tokens: int) -> float:
        """计算成本"""
        return (total_tokens / 1000) * self.config.cost_per_1k_tokens


class LLMService:
    """LLM服务"""
    
    def __init__(self, redis_client: RedisClient):
        self.redis = redis_client
        self.providers: Dict[str, LLMProvider] = {}
        self.model_configs: Dict[str, ModelConfig] = {}
        self.rate_limiters: Dict[str, Dict] = {}  # 速率限制器
        
    async def initialize(self):
        """初始化服务"""
        await self._load_model_configs()
        await self._initialize_providers()
        
    async def register_model(
        self,
        model_name: str,
        config: ModelConfig
    ):
        """注册模型"""
        try:
            self.model_configs[model_name] = config
            
            # 初始化提供商
            provider = self._create_provider(config)
            self.providers[model_name] = provider
            
            # 初始化速率限制器
            if config.rate_limit:
                self.rate_limiters[model_name] = {
                    "requests": 0,
                    "reset_time": datetime.now().timestamp() + 60
                }
                
            # 缓存配置
            await self.redis.setex(
                f"llm:config:{model_name}",
                3600,
                config.json()
            )
            
            logger.info(f"Model {model_name} registered successfully")
            
        except Exception as e:
            logger.error(f"Failed to register model {model_name}: {str(e)}")
            raise
    
    async def chat_completion(
        self,
        request: LLMRequest
    ) -> LLMResponse:
        """聊天补全"""
        try:
            # 选择模型
            model_name = request.model_name or self._select_best_model(ModelType.CHAT)
            provider = self.providers.get(model_name)
            
            if not provider:
                raise ValueError(f"Model {model_name} not found")
                
            # 检查速率限制
            await self._check_rate_limit(model_name)
            
            # 合并配置
            config = self._merge_config(request, self.model_configs[model_name])
            
            # 记录请求
            await self._log_request(request, model_name)
            
            # 调用提供商
            response = await provider.chat_completion(
                request.messages,
                temperature=config.get("temperature"),
                max_tokens=config.get("max_tokens"),
                functions=request.functions,
                function_call=request.function_call,
                tools=request.tools,
                tool_choice=request.tool_choice
            )
            
            # 记录响应
            await self._log_response(response, request)
            
            # 更新速率限制计数
            await self._update_rate_limit(model_name)
            
            return response
            
        except Exception as e:
            logger.error(f"Chat completion failed: {str(e)}")
            raise
    
    async def stream_chat_completion(
        self,
        request: LLMRequest
    ) -> AsyncGenerator[str, None]:
        """流式聊天补全"""
        try:
            # 选择模型
            model_name = request.model_name or self._select_best_model(ModelType.CHAT)
            provider = self.providers.get(model_name)
            
            if not provider:
                raise ValueError(f"Model {model_name} not found")
                
            # 检查速率限制
            await self._check_rate_limit(model_name)
            
            # 合并配置
            config = self._merge_config(request, self.model_configs[model_name])
            
            # 记录请求
            await self._log_request(request, model_name)
            
            # 流式调用提供商
            async for chunk in provider.stream_chat_completion(
                request.messages,
                temperature=config.get("temperature"),
                max_tokens=config.get("max_tokens"),
                functions=request.functions,
                function_call=request.function_call,
                tools=request.tools,
                tool_choice=request.tool_choice
            ):
                yield chunk
                
            # 更新速率限制计数
            await self._update_rate_limit(model_name)
            
        except Exception as e:
            logger.error(f"Stream chat completion failed: {str(e)}")
            raise
    
    async def embedding(
        self,
        texts: List[str],
        model_name: Optional[str] = None
    ) -> List[List[float]]:
        """文本嵌入"""
        try:
            # 选择模型
            model_name = model_name or self._select_best_model(ModelType.EMBEDDING)
            provider = self.providers.get(model_name)
            
            if not provider:
                raise ValueError(f"Model {model_name} not found")
                
            # 检查速率限制
            await self._check_rate_limit(model_name)
            
            # 批量处理文本
            embeddings = []
            batch_size = 100  # 每批处理100个文本
            
            for i in range(0, len(texts), batch_size):
                batch = texts[i:i + batch_size]
                batch_embeddings = await provider.embedding(batch)
                embeddings.extend(batch_embeddings)
                
                # 更新速率限制计数
                await self._update_rate_limit(model_name)
                
            return embeddings
            
        except Exception as e:
            logger.error(f"Embedding failed: {str(e)}")
            raise
    
    async def get_available_models(
        self,
        model_type: Optional[ModelType] = None
    ) -> List[Dict[str, Any]]:
        """获取可用模型列表"""
        models = []
        
        for name, config in self.model_configs.items():
            if not config.is_active:
                continue
                
            if model_type and config.model_type != model_type:
                continue
                
            # 检查健康状态
            provider = self.providers.get(name)
            is_healthy = await provider.health_check() if provider else False
            
            models.append({
                "name": name,
                "provider": config.provider.value,
                "type": config.model_type.value,
                "context_window": config.context_window,
                "supports_streaming": config.supports_streaming,
                "supports_functions": config.supports_functions,
                "supports_vision": config.supports_vision,
                "cost_per_1k_tokens": config.cost_per_1k_tokens,
                "is_healthy": is_healthy,
                "priority": config.priority
            })
            
        # 按优先级排序
        models.sort(key=lambda x: x["priority"])
        return models
    
    async def get_usage_stats(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """获取使用统计"""
        try:
            # 从Redis获取统计数据
            stats = {}
            
            for model_name in self.model_configs.keys():
                model_stats = await self.redis.hgetall(f"llm:stats:{model_name}")
                if model_stats:
                    stats[model_name] = {
                        "total_requests": int(model_stats.get("total_requests", 0)),
                        "total_tokens": int(model_stats.get("total_tokens", 0)),
                        "total_cost": float(model_stats.get("total_cost", 0)),
                        "avg_latency_ms": float(model_stats.get("avg_latency_ms", 0)),
                        "error_count": int(model_stats.get("error_count", 0))
                    }
                    
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get usage stats: {str(e)}")
            return {}
    
    def _create_provider(self, config: ModelConfig) -> LLMProvider:
        """创建提供商实例"""
        if config.provider == ModelProvider.OPENAI:
            return OpenAIProvider(config)
        elif config.provider == ModelProvider.ANTHROPIC:
            return AnthropicProvider(config)
        # TODO: 添加其他提供商
        else:
            raise ValueError(f"Unsupported provider: {config.provider}")
    
    def _select_best_model(self, model_type: ModelType) -> str:
        """选择最佳模型"""
        candidates = []
        
        for name, config in self.model_configs.items():
            if config.model_type == model_type and config.is_active:
                candidates.append((name, config.priority))
                
        if not candidates:
            raise ValueError(f"No available models for type {model_type}")
            
        # 按优先级排序，选择优先级最高的
        candidates.sort(key=lambda x: x[1])
        return candidates[0][0]
    
    def _merge_config(
        self,
        request: LLMRequest,
        model_config: ModelConfig
    ) -> Dict[str, Any]:
        """合并请求配置和模型配置"""
        config = {
            "temperature": request.temperature or model_config.temperature,
            "max_tokens": request.max_tokens or model_config.max_tokens,
            "top_p": model_config.top_p,
            "frequency_penalty": model_config.frequency_penalty,
            "presence_penalty": model_config.presence_penalty
        }
        return config
    
    async def _check_rate_limit(self, model_name: str):
        """检查速率限制"""
        config = self.model_configs.get(model_name)
        if not config or not config.rate_limit:
            return
            
        limiter = self.rate_limiters.get(model_name)
        if not limiter:
            return
            
        current_time = datetime.now().timestamp()
        
        # 重置计数器
        if current_time >= limiter["reset_time"]:
            limiter["requests"] = 0
            limiter["reset_time"] = current_time + 60
            
        # 检查限制
        if limiter["requests"] >= config.rate_limit:
            wait_time = limiter["reset_time"] - current_time
            raise Exception(f"Rate limit exceeded. Wait {wait_time:.1f} seconds")
    
    async def _update_rate_limit(self, model_name: str):
        """更新速率限制计数"""
        limiter = self.rate_limiters.get(model_name)
        if limiter:
            limiter["requests"] += 1
    
    async def _log_request(self, request: LLMRequest, model_name: str):
        """记录请求"""
        try:
            log_data = {
                "model_name": model_name,
                "user_id": request.user_id,
                "session_id": request.session_id,
                "message_count": len(request.messages),
                "timestamp": datetime.now().isoformat(),
                "metadata": request.metadata
            }
            
            await self.redis.lpush(
                "llm:requests",
                json.dumps(log_data)
            )
            
            # 保持最近1000条记录
            await self.redis.ltrim("llm:requests", 0, 999)
            
        except Exception as e:
            logger.error(f"Failed to log request: {str(e)}")
    
    async def _log_response(self, response: LLMResponse, request: LLMRequest):
        """记录响应"""
        try:
            # 更新统计数据
            stats_key = f"llm:stats:{response.model}"
            
            await self.redis.hincrby(stats_key, "total_requests", 1)
            await self.redis.hincrby(stats_key, "total_tokens", response.usage.get("total_tokens", 0))
            await self.redis.hincrbyfloat(stats_key, "total_cost", response.cost)
            
            # 更新平均延迟
            current_avg = float(await self.redis.hget(stats_key, "avg_latency_ms") or 0)
            total_requests = int(await self.redis.hget(stats_key, "total_requests") or 1)
            new_avg = ((current_avg * (total_requests - 1)) + response.latency_ms) / total_requests
            await self.redis.hset(stats_key, "avg_latency_ms", new_avg)
            
            # 记录响应日志
            log_data = {
                "response_id": response.id,
                "model": response.model,
                "provider": response.provider.value,
                "usage": response.usage,
                "latency_ms": response.latency_ms,
                "cost": response.cost,
                "finish_reason": response.finish_reason,
                "timestamp": response.created_at.isoformat(),
                "user_id": request.user_id,
                "session_id": request.session_id
            }
            
            await self.redis.lpush(
                "llm:responses",
                json.dumps(log_data)
            )
            
            # 保持最近1000条记录
            await self.redis.ltrim("llm:responses", 0, 999)
            
        except Exception as e:
            logger.error(f"Failed to log response: {str(e)}")
    
    async def _load_model_configs(self):
        """加载模型配置"""
        try:
            # 从Redis加载缓存的配置
            keys = await self.redis.keys("llm:config:*")
            
            for key in keys:
                config_data = await self.redis.get(key)
                if config_data:
                    config = ModelConfig(**json.loads(config_data))
                    model_name = key.split(":")[-1]
                    self.model_configs[model_name] = config
                    
            logger.info(f"Loaded {len(self.model_configs)} model configurations")
            
        except Exception as e:
            logger.error(f"Failed to load model configs: {str(e)}")
    
    async def _initialize_providers(self):
        """初始化提供商"""
        for model_name, config in self.model_configs.items():
            try:
                provider = self._create_provider(config)
                self.providers[model_name] = provider
                
                # 初始化速率限制器
                if config.rate_limit:
                    self.rate_limiters[model_name] = {
                        "requests": 0,
                        "reset_time": datetime.now().timestamp() + 60
                    }
                    
            except Exception as e:
                logger.error(f"Failed to initialize provider for {model_name}: {str(e)}")
                
        logger.info(f"Initialized {len(self.providers)} providers")