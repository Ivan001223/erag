from typing import Dict, List, Optional, Any, Union, AsyncGenerator
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
import asyncio
import logging
import json
import time
from abc import ABC, abstractmethod

import openai
import anthropic
from transformers import AutoTokenizer, AutoModelForCausalLM
import torch

logger = logging.getLogger(__name__)


class ModelProvider(Enum):
    """模型提供商"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    HUGGINGFACE = "huggingface"
    LOCAL = "local"
    AZURE_OPENAI = "azure_openai"
    GOOGLE = "google"
    COHERE = "cohere"


class LLMTaskType(Enum):
    """LLM任务类型"""
    TEXT_GENERATION = "text_generation"
    CHAT_COMPLETION = "chat_completion"
    SUMMARIZATION = "summarization"
    TRANSLATION = "translation"
    QUESTION_ANSWERING = "question_answering"
    ENTITY_EXTRACTION = "entity_extraction"
    RELATION_EXTRACTION = "relation_extraction"
    CLASSIFICATION = "classification"
    EMBEDDING = "embedding"
    CODE_GENERATION = "code_generation"


class ResponseFormat(Enum):
    """响应格式"""
    TEXT = "text"
    JSON = "json"
    STRUCTURED = "structured"
    STREAMING = "streaming"


@dataclass
class LLMConfig:
    """LLM配置"""
    provider: ModelProvider
    model_name: str
    api_key: Optional[str] = None
    api_base: Optional[str] = None
    api_version: Optional[str] = None
    organization: Optional[str] = None
    max_tokens: int = 2048
    temperature: float = 0.7
    top_p: float = 1.0
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    stop_sequences: Optional[List[str]] = None
    timeout: int = 60
    max_retries: int = 3
    retry_delay: float = 1.0
    enable_streaming: bool = False
    response_format: ResponseFormat = ResponseFormat.TEXT
    custom_headers: Optional[Dict[str, str]] = None
    model_kwargs: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Message:
    """消息"""
    role: str  # system, user, assistant
    content: str
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class LLMResponse:
    """LLM响应"""
    content: str
    model: str
    provider: ModelProvider
    usage: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
    response_time: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    finish_reason: Optional[str] = None
    error: Optional[str] = None
    raw_response: Optional[Any] = None


@dataclass
class LLMRequest:
    """LLM请求"""
    messages: List[Message]
    task_type: LLMTaskType
    config: LLMConfig
    context: Optional[Dict[str, Any]] = None
    request_id: Optional[str] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None


class BaseLLMProvider(ABC):
    """LLM提供商基类"""
    
    def __init__(self, config: LLMConfig):
        self.config = config
        self.client = None
        self._initialize_client()
    
    @abstractmethod
    def _initialize_client(self):
        """初始化客户端"""
        pass
    
    @abstractmethod
    async def generate(self, request: LLMRequest) -> LLMResponse:
        """生成响应"""
        pass
    
    @abstractmethod
    async def stream_generate(self, request: LLMRequest) -> AsyncGenerator[str, None]:
        """流式生成响应"""
        pass
    
    @abstractmethod
    def count_tokens(self, text: str) -> int:
        """计算token数量"""
        pass
    
    def validate_request(self, request: LLMRequest) -> bool:
        """验证请求"""
        if not request.messages:
            return False
        
        for message in request.messages:
            if not message.role or not message.content:
                return False
        
        return True


class OpenAIProvider(BaseLLMProvider):
    """OpenAI提供商"""
    
    def _initialize_client(self):
        """初始化OpenAI客户端"""
        self.client = openai.AsyncOpenAI(
            api_key=self.config.api_key,
            base_url=self.config.api_base,
            organization=self.config.organization,
            timeout=self.config.timeout,
            max_retries=self.config.max_retries
        )
    
    async def generate(self, request: LLMRequest) -> LLMResponse:
        """生成响应"""
        start_time = time.time()
        
        try:
            # 转换消息格式
            messages = [
                {"role": msg.role, "content": msg.content}
                for msg in request.messages
            ]
            
            # 构建请求参数
            params = {
                "model": self.config.model_name,
                "messages": messages,
                "max_tokens": self.config.max_tokens,
                "temperature": self.config.temperature,
                "top_p": self.config.top_p,
                "frequency_penalty": self.config.frequency_penalty,
                "presence_penalty": self.config.presence_penalty,
                **self.config.model_kwargs
            }
            
            if self.config.stop_sequences:
                params["stop"] = self.config.stop_sequences
            
            if self.config.response_format == ResponseFormat.JSON:
                params["response_format"] = {"type": "json_object"}
            
            # 发送请求
            response = await self.client.chat.completions.create(**params)
            
            response_time = time.time() - start_time
            
            return LLMResponse(
                content=response.choices[0].message.content,
                model=response.model,
                provider=ModelProvider.OPENAI,
                usage={
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                } if response.usage else None,
                response_time=response_time,
                finish_reason=response.choices[0].finish_reason,
                raw_response=response
            )
            
        except Exception as e:
            logger.error(f"OpenAI API调用失败: {str(e)}")
            return LLMResponse(
                content="",
                model=self.config.model_name,
                provider=ModelProvider.OPENAI,
                response_time=time.time() - start_time,
                error=str(e)
            )
    
    async def stream_generate(self, request: LLMRequest) -> AsyncGenerator[str, None]:
        """流式生成响应"""
        try:
            messages = [
                {"role": msg.role, "content": msg.content}
                for msg in request.messages
            ]
            
            params = {
                "model": self.config.model_name,
                "messages": messages,
                "max_tokens": self.config.max_tokens,
                "temperature": self.config.temperature,
                "stream": True,
                **self.config.model_kwargs
            }
            
            stream = await self.client.chat.completions.create(**params)
            
            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            logger.error(f"OpenAI流式API调用失败: {str(e)}")
            yield f"错误: {str(e)}"
    
    def count_tokens(self, text: str) -> int:
        """计算token数量"""
        # 简单估算，实际应该使用tiktoken
        return len(text) // 4


class AnthropicProvider(BaseLLMProvider):
    """Anthropic提供商"""
    
    def _initialize_client(self):
        """初始化Anthropic客户端"""
        self.client = anthropic.AsyncAnthropic(
            api_key=self.config.api_key,
            timeout=self.config.timeout,
            max_retries=self.config.max_retries
        )
    
    async def generate(self, request: LLMRequest) -> LLMResponse:
        """生成响应"""
        start_time = time.time()
        
        try:
            # 转换消息格式
            messages = []
            system_message = None
            
            for msg in request.messages:
                if msg.role == "system":
                    system_message = msg.content
                else:
                    messages.append({"role": msg.role, "content": msg.content})
            
            # 构建请求参数
            params = {
                "model": self.config.model_name,
                "messages": messages,
                "max_tokens": self.config.max_tokens,
                "temperature": self.config.temperature,
                "top_p": self.config.top_p,
                **self.config.model_kwargs
            }
            
            if system_message:
                params["system"] = system_message
            
            if self.config.stop_sequences:
                params["stop_sequences"] = self.config.stop_sequences
            
            # 发送请求
            response = await self.client.messages.create(**params)
            
            response_time = time.time() - start_time
            
            return LLMResponse(
                content=response.content[0].text,
                model=response.model,
                provider=ModelProvider.ANTHROPIC,
                usage={
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens,
                    "total_tokens": response.usage.input_tokens + response.usage.output_tokens
                } if response.usage else None,
                response_time=response_time,
                finish_reason=response.stop_reason,
                raw_response=response
            )
            
        except Exception as e:
            logger.error(f"Anthropic API调用失败: {str(e)}")
            return LLMResponse(
                content="",
                model=self.config.model_name,
                provider=ModelProvider.ANTHROPIC,
                response_time=time.time() - start_time,
                error=str(e)
            )
    
    async def stream_generate(self, request: LLMRequest) -> AsyncGenerator[str, None]:
        """流式生成响应"""
        try:
            messages = []
            system_message = None
            
            for msg in request.messages:
                if msg.role == "system":
                    system_message = msg.content
                else:
                    messages.append({"role": msg.role, "content": msg.content})
            
            params = {
                "model": self.config.model_name,
                "messages": messages,
                "max_tokens": self.config.max_tokens,
                "temperature": self.config.temperature,
                "stream": True,
                **self.config.model_kwargs
            }
            
            if system_message:
                params["system"] = system_message
            
            async with self.client.messages.stream(**params) as stream:
                async for text in stream.text_stream:
                    yield text
                    
        except Exception as e:
            logger.error(f"Anthropic流式API调用失败: {str(e)}")
            yield f"错误: {str(e)}"
    
    def count_tokens(self, text: str) -> int:
        """计算token数量"""
        # 简单估算
        return len(text) // 4


class HuggingFaceProvider(BaseLLMProvider):
    """HuggingFace提供商"""
    
    def _initialize_client(self):
        """初始化HuggingFace模型"""
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(self.config.model_name)
            self.model = AutoModelForCausalLM.from_pretrained(
                self.config.model_name,
                torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
                device_map="auto" if torch.cuda.is_available() else None
            )
            
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token
                
        except Exception as e:
            logger.error(f"初始化HuggingFace模型失败: {str(e)}")
            raise
    
    async def generate(self, request: LLMRequest) -> LLMResponse:
        """生成响应"""
        start_time = time.time()
        
        try:
            # 构建提示
            prompt = self._build_prompt(request.messages)
            
            # 编码输入
            inputs = self.tokenizer.encode(prompt, return_tensors="pt")
            
            if torch.cuda.is_available():
                inputs = inputs.cuda()
            
            # 生成响应
            with torch.no_grad():
                outputs = self.model.generate(
                    inputs,
                    max_new_tokens=self.config.max_tokens,
                    temperature=self.config.temperature,
                    top_p=self.config.top_p,
                    do_sample=True,
                    pad_token_id=self.tokenizer.eos_token_id,
                    **self.config.model_kwargs
                )
            
            # 解码输出
            generated_text = self.tokenizer.decode(
                outputs[0][len(inputs[0]):], 
                skip_special_tokens=True
            )
            
            response_time = time.time() - start_time
            
            return LLMResponse(
                content=generated_text.strip(),
                model=self.config.model_name,
                provider=ModelProvider.HUGGINGFACE,
                usage={
                    "prompt_tokens": len(inputs[0]),
                    "completion_tokens": len(outputs[0]) - len(inputs[0]),
                    "total_tokens": len(outputs[0])
                },
                response_time=response_time
            )
            
        except Exception as e:
            logger.error(f"HuggingFace模型生成失败: {str(e)}")
            return LLMResponse(
                content="",
                model=self.config.model_name,
                provider=ModelProvider.HUGGINGFACE,
                response_time=time.time() - start_time,
                error=str(e)
            )
    
    async def stream_generate(self, request: LLMRequest) -> AsyncGenerator[str, None]:
        """流式生成响应"""
        # HuggingFace本地模型的流式生成实现
        try:
            prompt = self._build_prompt(request.messages)
            inputs = self.tokenizer.encode(prompt, return_tensors="pt")
            
            if torch.cuda.is_available():
                inputs = inputs.cuda()
            
            # 简单的流式生成实现
            generated_tokens = []
            
            for _ in range(self.config.max_tokens):
                with torch.no_grad():
                    outputs = self.model(inputs)
                    next_token_logits = outputs.logits[0, -1, :]
                    
                    # 应用温度
                    next_token_logits = next_token_logits / self.config.temperature
                    
                    # 采样
                    probs = torch.softmax(next_token_logits, dim=-1)
                    next_token = torch.multinomial(probs, num_samples=1)
                    
                    # 检查是否结束
                    if next_token.item() == self.tokenizer.eos_token_id:
                        break
                    
                    generated_tokens.append(next_token.item())
                    
                    # 解码并yield
                    token_text = self.tokenizer.decode([next_token.item()], skip_special_tokens=True)
                    yield token_text
                    
                    # 更新输入
                    inputs = torch.cat([inputs, next_token.unsqueeze(0)], dim=1)
                    
        except Exception as e:
            logger.error(f"HuggingFace流式生成失败: {str(e)}")
            yield f"错误: {str(e)}"
    
    def count_tokens(self, text: str) -> int:
        """计算token数量"""
        return len(self.tokenizer.encode(text))
    
    def _build_prompt(self, messages: List[Message]) -> str:
        """构建提示"""
        prompt_parts = []
        
        for message in messages:
            if message.role == "system":
                prompt_parts.append(f"System: {message.content}")
            elif message.role == "user":
                prompt_parts.append(f"Human: {message.content}")
            elif message.role == "assistant":
                prompt_parts.append(f"Assistant: {message.content}")
        
        prompt_parts.append("Assistant:")
        return "\n\n".join(prompt_parts)


class LLMOrchestrator:
    """LLM编排器"""
    
    def __init__(self):
        self.providers: Dict[str, BaseLLMProvider] = {}
        self.default_provider: Optional[str] = None
        self.request_history: List[LLMRequest] = []
        self.response_history: List[LLMResponse] = []
        self.metrics = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_tokens": 0,
            "total_cost": 0.0,
            "average_response_time": 0.0
        }
    
    def register_provider(self, name: str, config: LLMConfig, set_as_default: bool = False):
        """注册LLM提供商"""
        try:
            if config.provider == ModelProvider.OPENAI:
                provider = OpenAIProvider(config)
            elif config.provider == ModelProvider.ANTHROPIC:
                provider = AnthropicProvider(config)
            elif config.provider == ModelProvider.HUGGINGFACE:
                provider = HuggingFaceProvider(config)
            else:
                raise ValueError(f"不支持的提供商: {config.provider}")
            
            self.providers[name] = provider
            
            if set_as_default or not self.default_provider:
                self.default_provider = name
            
            logger.info(f"已注册LLM提供商: {name} ({config.provider.value})")
            
        except Exception as e:
            logger.error(f"注册LLM提供商失败: {str(e)}")
            raise
    
    def get_provider(self, name: Optional[str] = None) -> BaseLLMProvider:
        """获取LLM提供商"""
        provider_name = name or self.default_provider
        
        if not provider_name or provider_name not in self.providers:
            raise ValueError(f"未找到LLM提供商: {provider_name}")
        
        return self.providers[provider_name]
    
    async def generate(self, 
                      messages: List[Message],
                      task_type: LLMTaskType = LLMTaskType.CHAT_COMPLETION,
                      provider_name: Optional[str] = None,
                      **kwargs) -> LLMResponse:
        """生成响应"""
        try:
            provider = self.get_provider(provider_name)
            
            # 创建请求
            request = LLMRequest(
                messages=messages,
                task_type=task_type,
                config=provider.config,
                **kwargs
            )
            
            # 验证请求
            if not provider.validate_request(request):
                raise ValueError("无效的请求")
            
            # 记录请求
            self.request_history.append(request)
            self.metrics["total_requests"] += 1
            
            # 生成响应
            response = await provider.generate(request)
            
            # 记录响应
            self.response_history.append(response)
            
            # 更新指标
            if response.error:
                self.metrics["failed_requests"] += 1
            else:
                self.metrics["successful_requests"] += 1
                
                if response.usage:
                    self.metrics["total_tokens"] += response.usage.get("total_tokens", 0)
            
            # 更新平均响应时间
            total_time = sum(r.response_time for r in self.response_history)
            self.metrics["average_response_time"] = total_time / len(self.response_history)
            
            return response
            
        except ValueError as e:
            # 重新抛出 ValueError（如提供商未找到等）
            logger.error(f"生成响应失败: {str(e)}")
            self.metrics["failed_requests"] += 1
            raise
        except Exception as e:
            logger.error(f"生成响应失败: {str(e)}")
            self.metrics["failed_requests"] += 1
            
            return LLMResponse(
                content="",
                model="unknown",
                provider=ModelProvider.OPENAI,  # 默认值
                error=str(e)
            )
    
    async def stream_generate(self, 
                             messages: List[Message],
                             task_type: LLMTaskType = LLMTaskType.CHAT_COMPLETION,
                             provider_name: Optional[str] = None,
                             **kwargs) -> AsyncGenerator[str, None]:
        """流式生成响应"""
        try:
            provider = self.get_provider(provider_name)
            
            request = LLMRequest(
                messages=messages,
                task_type=task_type,
                config=provider.config,
                **kwargs
            )
            
            if not provider.validate_request(request):
                yield "错误: 无效的请求"
                return
            
            self.request_history.append(request)
            self.metrics["total_requests"] += 1
            
            async for chunk in provider.stream_generate(request):
                yield chunk
                
        except Exception as e:
            logger.error(f"流式生成失败: {str(e)}")
            self.metrics["failed_requests"] += 1
            yield f"错误: {str(e)}"
    
    async def batch_generate(self, 
                            requests: List[Dict[str, Any]],
                            provider_name: Optional[str] = None,
                            max_concurrent: int = 5) -> List[LLMResponse]:
        """批量生成响应"""
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def _generate_single(req_data):
            async with semaphore:
                messages = [Message(**msg) for msg in req_data["messages"]]
                task_type = LLMTaskType(req_data.get("task_type", "chat_completion"))
                return await self.generate(messages, task_type, provider_name)
        
        tasks = [_generate_single(req) for req in requests]
        return await asyncio.gather(*tasks, return_exceptions=True)
    
    def get_metrics(self) -> Dict[str, Any]:
        """获取指标"""
        return self.metrics.copy()
    
    def get_provider_info(self) -> Dict[str, Dict[str, Any]]:
        """获取提供商信息"""
        info = {}
        
        for name, provider in self.providers.items():
            info[name] = {
                "provider": provider.config.provider.value,
                "model": provider.config.model_name,
                "max_tokens": provider.config.max_tokens,
                "temperature": provider.config.temperature,
                "is_default": name == self.default_provider
            }
        
        return info
    
    def clear_history(self):
        """清除历史记录"""
        self.request_history.clear()
        self.response_history.clear()
        
        # 重置指标
        self.metrics = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_tokens": 0,
            "total_cost": 0.0,
            "average_response_time": 0.0
        }
    
    async def health_check(self, provider_name: Optional[str] = None) -> Dict[str, bool]:
        """健康检查"""
        results = {}
        
        providers_to_check = [provider_name] if provider_name else list(self.providers.keys())
        
        for name in providers_to_check:
            try:
                provider = self.providers[name]
                
                # 发送简单的测试请求
                test_messages = [Message(role="user", content="Hello")]
                test_request = LLMRequest(
                    messages=test_messages,
                    task_type=LLMTaskType.CHAT_COMPLETION,
                    config=provider.config
                )
                
                response = await provider.generate(test_request)
                results[name] = response.error is None
                
            except Exception as e:
                logger.error(f"健康检查失败 {name}: {str(e)}")
                results[name] = False
        
        return results
    
    async def cleanup(self):
        """清理资源"""
        # 清理HuggingFace模型
        for provider in self.providers.values():
            if hasattr(provider, 'model') and provider.model:
                del provider.model
            if hasattr(provider, 'tokenizer') and provider.tokenizer:
                del provider.tokenizer
        
        # 清空CUDA缓存
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        
        logger.info("LLM编排器资源已清理")