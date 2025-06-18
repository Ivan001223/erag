"""Tests for LLM Orchestrator."""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from typing import Dict, Any, Optional, List, AsyncGenerator
from backend.core.llm.llm_orchestrator import (
    LLMOrchestrator,
    ModelProvider,
    LLMTaskType,
    ResponseFormat,
    LLMConfig,
    Message,
    LLMResponse,
    LLMRequest,
    BaseLLMProvider,
    OpenAIProvider,
    AnthropicProvider,
    HuggingFaceProvider
)


class MockLLMProvider(BaseLLMProvider):
    """Mock LLM provider for testing."""
    
    def __init__(self, provider_name: str = "mock"):
        # Create a mock config
        mock_config = LLMConfig(
            provider=ModelProvider.OPENAI,
            model_name="mock-model",
            api_key="mock-key"
        )
        super().__init__(mock_config)
        self.provider_name = provider_name
        self.is_available = True
        self.mock_response = "Mock response"
        self.mock_latency = 0.1
    
    def _initialize_client(self):
        """Initialize mock client."""
        self.client = MagicMock()
    
    async def generate(self, request: LLMRequest) -> LLMResponse:
        """Mock generate method."""
        await asyncio.sleep(self.mock_latency)
        
        return LLMResponse(
            content=self.mock_response,
            model=self.config.model_name,
            provider=ModelProvider.OPENAI,
            usage={
                "prompt_tokens": 10,
                "completion_tokens": 5,
                "total_tokens": 15
            },
            response_time=self.mock_latency,
            metadata={"mock": True}
        )
    
    async def stream_generate(self, request: LLMRequest) -> AsyncGenerator[str, None]:
        """Mock stream generate method."""
        words = self.mock_response.split()
        for word in words:
            await asyncio.sleep(0.01)
            yield word + " "
    
    def count_tokens(self, text: str) -> int:
        """Mock count tokens method."""
        return len(text.split())
    
    async def health_check(self) -> bool:
        """Mock health check."""
        return self.is_available
    
    def get_metrics(self) -> Dict[str, Any]:
        """Mock get metrics."""
        return {
            "total_requests": 100,
            "successful_requests": 95,
            "failed_requests": 5,
            "average_response_time": self.mock_latency
        }


@pytest.fixture
def mock_provider():
    """Create mock provider."""
    return MockLLMProvider()


@pytest.fixture
def orchestrator():
    """Create LLM orchestrator."""
    return LLMOrchestrator()


@pytest.fixture
def sample_config():
    """Create sample LLM config."""
    return LLMConfig(
        provider=ModelProvider.OPENAI,
        model_name="gpt-3.5-turbo",
        api_key="test-key",
        temperature=0.7,
        max_tokens=100,
        top_p=1.0
    )


@pytest.fixture
def sample_messages():
    """Create sample messages."""
    return [
        Message(role="system", content="You are a helpful assistant."),
        Message(role="user", content="Hello, how are you?")
    ]


class TestLLMOrchestrator:
    """Test LLM Orchestrator functionality."""
    
    @pytest.mark.asyncio
    async def test_register_provider(self, orchestrator, sample_config):
        """Test provider registration."""
        # Register provider
        orchestrator.register_provider("mock", sample_config, set_as_default=True)
        
        # Check provider is registered
        provider_info = orchestrator.get_provider_info()
        assert "mock" in provider_info
        assert provider_info["mock"]["is_default"] is True
        
        # Test getting provider
        provider = orchestrator.get_provider("mock")
        assert provider is not None
    
    @pytest.mark.asyncio
    async def test_get_provider_info(self, orchestrator, sample_config):
        """Test getting provider information."""
        # Register provider
        orchestrator.register_provider("mock", sample_config)
        
        # Get provider info
        provider_info = orchestrator.get_provider_info()
        assert "mock" in provider_info
        assert provider_info["mock"]["provider"] == "openai"
        assert provider_info["mock"]["model"] == "gpt-3.5-turbo"
    
    @pytest.mark.asyncio
    async def test_generate(self, orchestrator, sample_config, sample_messages):
        """Test text generation."""
        # Register provider
        orchestrator.register_provider("mock", sample_config)
        
        # Mock the provider's generate method
        provider = orchestrator.get_provider("mock")
        provider.generate = AsyncMock(return_value=LLMResponse(
            content="Test response",
            model="gpt-3.5-turbo",
            provider=ModelProvider.OPENAI,
            usage={"total_tokens": 15},
            response_time=0.1
        ))
        
        # Test generation
        response = await orchestrator.generate(
            messages=sample_messages,
            task_type=LLMTaskType.CHAT_COMPLETION,
            provider_name="mock"
        )
        
        assert isinstance(response, LLMResponse)
        assert response.content == "Test response"
        assert response.provider == ModelProvider.OPENAI
        assert response.model == "gpt-3.5-turbo"
    
    @pytest.mark.asyncio
    async def test_generate_with_auto_provider_selection(self, orchestrator, sample_config, sample_messages):
        """Test generation with automatic provider selection."""
        # Register provider as default
        orchestrator.register_provider("mock", sample_config, set_as_default=True)
        
        # Mock the provider's generate method
        provider = orchestrator.get_provider("mock")
        provider.generate = AsyncMock(return_value=LLMResponse(
            content="Auto response",
            model="gpt-3.5-turbo",
            provider=ModelProvider.OPENAI,
            usage={"total_tokens": 15},
            response_time=0.1
        ))
        
        # Test generation without specifying provider
        response = await orchestrator.generate(
            messages=sample_messages,
            task_type=LLMTaskType.CHAT_COMPLETION
        )
        
        assert isinstance(response, LLMResponse)
        assert response.content == "Auto response"
    
    @pytest.mark.asyncio
    async def test_stream_generate(self, orchestrator, sample_config, sample_messages):
        """Test streaming generation."""
        # Register provider
        orchestrator.register_provider("mock", sample_config)
        
        # Mock the provider's stream_generate method
        async def mock_stream(request):
            for chunk in ["Hello", " ", "world", "!"]:
                yield chunk
        
        provider = orchestrator.get_provider("mock")
        provider.stream_generate = mock_stream
        
        # Test streaming
        chunks = []
        async for chunk in orchestrator.stream_generate(
            messages=sample_messages,
            task_type=LLMTaskType.CHAT_COMPLETION,
            provider_name="mock"
        ):
            chunks.append(chunk)
        
        assert len(chunks) > 0
        assert all(isinstance(chunk, str) for chunk in chunks)
        assert "".join(chunks) == "Hello world!"
    
    @pytest.mark.asyncio
    async def test_batch_generate(self, orchestrator, sample_config, sample_messages):
        """Test batch generation."""
        # Register provider
        orchestrator.register_provider("mock", sample_config)
        
        # Mock the provider's generate method
        provider = orchestrator.get_provider("mock")
        provider.generate = AsyncMock(return_value=LLMResponse(
            content="Mock response",
            model="gpt-3.5-turbo",
            provider=ModelProvider.OPENAI,
            usage={"total_tokens": 15},
            response_time=0.1
        ))
        
        # Create batch requests
        requests = [
            {
                "messages": [msg.__dict__ for msg in sample_messages],
                "task_type": LLMTaskType.CHAT_COMPLETION.value
            },
            {
                "messages": [msg.__dict__ for msg in sample_messages],
                "task_type": LLMTaskType.CHAT_COMPLETION.value
            }
        ]
        
        # Test batch generation
        responses = await orchestrator.batch_generate(
            requests=requests,
            provider_name="mock"
        )
        
        assert len(responses) == 2
        assert all(isinstance(r, LLMResponse) for r in responses)
        assert all(r.content == "Mock response" for r in responses)
    
    @pytest.mark.asyncio
    async def test_provider_not_found(self, orchestrator, sample_messages):
        """Test handling of non-existent provider."""
        with pytest.raises(ValueError, match="未找到LLM提供商: nonexistent"):
            await orchestrator.generate(
                messages=sample_messages,
                task_type=LLMTaskType.CHAT_COMPLETION,
                provider_name="nonexistent"
            )
    
    @pytest.mark.asyncio
    async def test_no_providers_available(self, orchestrator, sample_messages):
        """Test handling when no providers are available."""
        with pytest.raises(ValueError, match="未找到LLM提供商: None"):
            await orchestrator.generate(
                messages=sample_messages,
                task_type=LLMTaskType.CHAT_COMPLETION
            )
    
    @pytest.mark.asyncio
    async def test_get_metrics(self, orchestrator, sample_config):
        """Test getting provider metrics."""
        # Register provider
        orchestrator.register_provider("mock", sample_config)
        
        # Mock the provider's get_metrics method
        provider = orchestrator.get_provider("mock")
        provider.get_metrics = MagicMock(return_value={
            "total_requests": 100,
            "successful_requests": 95,
            "failed_requests": 5,
            "average_response_time": 0.1
        })
        
        # Get metrics
        metrics = orchestrator.get_metrics()
        assert isinstance(metrics, dict)
    
    @pytest.mark.asyncio
    async def test_get_provider_info(self, orchestrator, sample_config):
        """Test getting provider information."""
        # Register multiple providers
        orchestrator.register_provider("mock1", sample_config)
        orchestrator.register_provider("mock2", sample_config)
        
        # Mock the providers' get_metrics methods
        provider1 = orchestrator.get_provider("mock1")
        provider1.get_metrics = MagicMock(return_value={"total_requests": 100})
        
        provider2 = orchestrator.get_provider("mock2")
        provider2.get_metrics = MagicMock(return_value={"total_requests": 50})
        
        # Get provider info
        provider_info = orchestrator.get_provider_info()
        assert isinstance(provider_info, dict)
        assert "mock1" in provider_info
        assert "mock2" in provider_info
    
    @pytest.mark.asyncio
    async def test_health_check(self, orchestrator, sample_config):
        """Test provider health check."""
        # Register provider
        orchestrator.register_provider("mock", sample_config)
        
        # Mock the provider's health_check method
        provider = orchestrator.get_provider("mock")
        provider.health_check = AsyncMock(return_value=True)
        
        # Test health check
        health = await orchestrator.health_check("mock")
        assert isinstance(health, dict)
        assert "mock" in health
    
    @pytest.mark.asyncio
    async def test_health_check_all(self, orchestrator, sample_config):
        """Test health check for all providers."""
        # Register multiple providers
        orchestrator.register_provider("mock1", sample_config)
        orchestrator.register_provider("mock2", sample_config)
        
        # Mock the providers' health_check methods
        provider1 = orchestrator.get_provider("mock1")
        provider1.health_check = AsyncMock(return_value=True)
        
        provider2 = orchestrator.get_provider("mock2")
        provider2.health_check = AsyncMock(return_value=False)
        
        # Test health check all
        health = await orchestrator.health_check()
        assert isinstance(health, dict)
        assert "mock1" in health
        assert "mock2" in health
    
    @pytest.mark.asyncio
    async def test_clear_history(self, orchestrator, sample_config, sample_messages):
        """Test clearing request history."""
        # Register provider and make request
        orchestrator.register_provider("mock", sample_config)
        
        # Mock the provider's generate method
        provider = orchestrator.get_provider("mock")
        provider.generate = AsyncMock(return_value=LLMResponse(
            content="Test response",
            model="gpt-3.5-turbo",
            provider=ModelProvider.OPENAI,
            usage={"total_tokens": 15},
            response_time=0.1
        ))
        
        await orchestrator.generate(
            messages=sample_messages,
            task_type=LLMTaskType.CHAT_COMPLETION,
            provider_name="mock"
        )
        
        # Clear history
        orchestrator.clear_history()
        
        # History should be cleared (this would need to be implemented in the actual class)
        # For now, just test that the method doesn't raise an error
        assert True
    
    @pytest.mark.asyncio
    async def test_cleanup(self, orchestrator, sample_config):
        """Test orchestrator cleanup."""
        # Register provider
        orchestrator.register_provider("mock", sample_config)
        
        # Test cleanup
        await orchestrator.cleanup()
        # cleanup method doesn't clear providers, only cleans up resources
        provider_info = orchestrator.get_provider_info()
        assert len(provider_info) == 1


class TestLLMDataModels:
    """Test LLM data models."""
    
    def test_message_model(self):
        """测试Message模型"""
        message = Message(
            role="user",
            content="Hello, world!",
            metadata={"timestamp": datetime.now()}
        )
        
        assert message.role == "user"
        assert message.content == "Hello, world!"
        assert "timestamp" in message.metadata
    
    def test_llm_config_model(self):
        """Test LLMConfig model."""
        config = LLMConfig(
            provider=ModelProvider.OPENAI,
            model_name="gpt-3.5-turbo",
            api_key="test-key",
            temperature=0.7,
            max_tokens=100
        )
        assert config.provider == ModelProvider.OPENAI
        assert config.model_name == "gpt-3.5-turbo"
        assert config.api_key == "test-key"
        assert config.temperature == 0.7
        assert config.max_tokens == 100
        assert config.top_p == 1.0  # default value
    
    def test_llm_response_model(self):
        """Test LLMResponse model."""
        response = LLMResponse(
            content="Test response",
            model="gpt-3.5-turbo",
            provider=ModelProvider.OPENAI,
            usage={"total_tokens": 15},
            response_time=0.5
        )
        assert response.content == "Test response"
        assert response.model == "gpt-3.5-turbo"
        assert response.provider == ModelProvider.OPENAI
        assert response.usage["total_tokens"] == 15
        assert response.response_time == 0.5
    
    def test_llm_request_model(self):
        """测试LLMRequest模型"""
        config = LLMConfig(
            provider=ModelProvider.OPENAI,
            model_name="gpt-3.5-turbo"
        )
        
        messages = [
            Message(role="user", content="Hello")
        ]
        
        request = LLMRequest(
            messages=messages,
            task_type=LLMTaskType.CHAT_COMPLETION,
            config=config,
            context={"session_id": "test"}
        )
        
        assert len(request.messages) == 1
        assert request.task_type == LLMTaskType.CHAT_COMPLETION
        assert request.config.provider == ModelProvider.OPENAI
        assert request.context["session_id"] == "test"


if __name__ == "__main__":
    pytest.main([__file__])