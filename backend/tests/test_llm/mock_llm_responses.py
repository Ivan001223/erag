"""Mock LLM responses for testing.

This module provides mock responses and utilities for testing LLM functionality
without making actual API calls.
"""

import json
import random
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum

from backend.core.llm.llm_orchestrator import LLMResponse, Message, LLMConfig


class MockResponseType(str, Enum):
    """Types of mock responses."""
    SUCCESS = "success"
    ERROR = "error"
    TIMEOUT = "timeout"
    RATE_LIMIT = "rate_limit"
    STREAMING = "streaming"


@dataclass
class MockResponseConfig:
    """Configuration for mock responses."""
    response_type: MockResponseType = MockResponseType.SUCCESS
    latency_range: tuple[float, float] = (0.1, 2.0)
    error_rate: float = 0.0
    content_length_range: tuple[int, int] = (10, 500)
    include_usage: bool = True
    include_metadata: bool = True


class MockLLMResponses:
    """Mock LLM responses generator."""
    
    def __init__(self, config: Optional[MockResponseConfig] = None):
        self.config = config or MockResponseConfig()
        self._response_templates = self._load_response_templates()
        self._conversation_context = {}
    
    def generate_response(
        self,
        messages: List[Message],
        config: LLMConfig,
        provider: str = "mock",
        **kwargs
    ) -> LLMResponse:
        """Generate a mock LLM response."""
        # Simulate error conditions
        if random.random() < self.config.error_rate:
            return self._generate_error_response(config, provider)
        
        # Generate content based on input
        content = self._generate_content(messages, config)
        
        # Calculate mock latency
        latency = random.uniform(*self.config.latency_range)
        
        # Generate usage statistics
        usage = self._generate_usage(messages, content) if self.config.include_usage else {}
        
        # Generate metadata
        metadata = self._generate_metadata() if self.config.include_metadata else {}
        
        return LLMResponse(
            content=content,
            model=config.model,
            provider=provider,
            usage=usage,
            latency=latency,
            metadata=metadata,
            timestamp=datetime.now()
        )
    
    def generate_streaming_response(
        self,
        messages: List[Message],
        config: LLMConfig,
        provider: str = "mock",
        **kwargs
    ):
        """Generate streaming mock responses."""
        content = self._generate_content(messages, config)
        words = content.split()
        
        accumulated_content = ""
        for i, word in enumerate(words):
            accumulated_content += word + (" " if i < len(words) - 1 else "")
            
            yield LLMResponse(
                content=word + (" " if i < len(words) - 1 else ""),
                model=config.model,
                provider=provider,
                usage={
                    "prompt_tokens": len(" ".join([m.content for m in messages]).split()),
                    "completion_tokens": i + 1,
                    "total_tokens": len(" ".join([m.content for m in messages]).split()) + i + 1
                },
                latency=0.05,
                metadata={
                    "streaming": True,
                    "chunk_index": i,
                    "is_final": i == len(words) - 1
                },
                timestamp=datetime.now()
            )
    
    def generate_batch_responses(
        self,
        requests: List[tuple[List[Message], LLMConfig]],
        provider: str = "mock",
        **kwargs
    ) -> List[LLMResponse]:
        """Generate batch mock responses."""
        responses = []
        for messages, config in requests:
            response = self.generate_response(messages, config, provider, **kwargs)
            responses.append(response)
        return responses
    
    def set_conversation_context(self, context_id: str, context: Dict[str, Any]):
        """Set conversation context for more realistic responses."""
        self._conversation_context[context_id] = context
    
    def get_conversation_context(self, context_id: str) -> Dict[str, Any]:
        """Get conversation context."""
        return self._conversation_context.get(context_id, {})
    
    def clear_conversation_context(self, context_id: Optional[str] = None):
        """Clear conversation context."""
        if context_id:
            self._conversation_context.pop(context_id, None)
        else:
            self._conversation_context.clear()
    
    def _generate_content(self, messages: List[Message], config: LLMConfig) -> str:
        """Generate mock content based on input messages."""
        if not messages:
            return "Hello! How can I help you today?"
        
        last_message = messages[-1]
        user_content = last_message.content.lower()
        
        # Pattern-based responses
        if "hello" in user_content or "hi" in user_content:
            return random.choice([
                "Hello! How can I assist you today?",
                "Hi there! What can I help you with?",
                "Greetings! How may I be of service?"
            ])
        
        elif "how are you" in user_content:
            return random.choice([
                "I'm doing well, thank you for asking!",
                "I'm functioning optimally, thanks!",
                "All systems are running smoothly!"
            ])
        
        elif "weather" in user_content:
            return random.choice([
                "I don't have access to real-time weather data, but you can check a weather service for current conditions.",
                "For accurate weather information, I'd recommend checking your local weather app or website.",
                "Weather conditions vary by location. What's your area?"
            ])
        
        elif "code" in user_content or "programming" in user_content:
            return random.choice([
                "I'd be happy to help with coding! What programming language or specific problem are you working on?",
                "Programming assistance is one of my strengths. What kind of code are you looking to write or debug?",
                "Let's dive into some code! What's the challenge you're facing?"
            ])
        
        elif "explain" in user_content:
            return random.choice([
                "I'll do my best to explain that concept clearly. Let me break it down for you.",
                "Great question! Here's how I understand it:",
                "Let me provide a detailed explanation of that topic."
            ])
        
        elif "thank" in user_content:
            return random.choice([
                "You're very welcome!",
                "Happy to help!",
                "Glad I could assist!"
            ])
        
        elif "?" in user_content:
            # Question detected
            return random.choice([
                "That's an interesting question. Let me think about that...",
                "Based on the information available, here's what I can tell you:",
                "Good question! Here's my understanding:"
            ])
        
        else:
            # Generic responses
            return random.choice([
                "I understand what you're saying. Could you provide more details?",
                "That's an interesting point. Let me elaborate on that.",
                "I see what you mean. Here's my perspective on that.",
                "Thank you for sharing that. How can I help you further?",
                "I appreciate your input. What would you like to know more about?"
            ])
    
    def _generate_error_response(self, config: LLMConfig, provider: str) -> LLMResponse:
        """Generate an error response."""
        error_types = [
            "rate_limit_exceeded",
            "invalid_request",
            "model_unavailable",
            "timeout",
            "authentication_failed"
        ]
        
        error_type = random.choice(error_types)
        error_messages = {
            "rate_limit_exceeded": "Rate limit exceeded. Please try again later.",
            "invalid_request": "Invalid request format or parameters.",
            "model_unavailable": "The requested model is currently unavailable.",
            "timeout": "Request timed out. Please try again.",
            "authentication_failed": "Authentication failed. Please check your API key."
        }
        
        return LLMResponse(
            content="",
            model=config.model,
            provider=provider,
            usage={},
            latency=random.uniform(0.1, 1.0),
            metadata={
                "error": True,
                "error_type": error_type,
                "error_message": error_messages[error_type]
            },
            timestamp=datetime.now()
        )
    
    def _generate_usage(self, messages: List[Message], content: str) -> Dict[str, int]:
        """Generate mock usage statistics."""
        # Rough token estimation (1 token ≈ 4 characters)
        prompt_text = " ".join([m.content for m in messages])
        prompt_tokens = max(1, len(prompt_text) // 4)
        completion_tokens = max(1, len(content) // 4)
        
        return {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens
        }
    
    def _generate_metadata(self) -> Dict[str, Any]:
        """Generate mock metadata."""
        return {
            "mock_response": True,
            "response_id": f"mock_{random.randint(1000, 9999)}",
            "model_version": "mock-v1.0",
            "processing_time_ms": random.randint(50, 500),
            "server_id": f"server_{random.randint(1, 10)}",
            "timestamp": datetime.now().isoformat()
        }
    
    def _load_response_templates(self) -> Dict[str, List[str]]:
        """Load response templates for different scenarios."""
        return {
            "greetings": [
                "Hello! How can I help you today?",
                "Hi there! What can I assist you with?",
                "Greetings! How may I be of service?"
            ],
            "questions": [
                "That's a great question. Let me think about that.",
                "Interesting question! Here's what I think:",
                "Good point. Based on my understanding:"
            ],
            "explanations": [
                "Let me explain that step by step.",
                "Here's how I understand it:",
                "I'll break this down for you:"
            ],
            "code_help": [
                "I'd be happy to help with that code!",
                "Let's work through this programming challenge.",
                "Here's how you might approach this:"
            ],
            "farewells": [
                "You're welcome! Feel free to ask if you need more help.",
                "Happy to help! Let me know if you have other questions.",
                "Glad I could assist! Have a great day!"
            ]
        }


# Predefined mock responses for specific test scenarios
MOCK_RESPONSES = {
    "simple_greeting": {
        "content": "Hello! How can I help you today?",
        "usage": {"prompt_tokens": 5, "completion_tokens": 8, "total_tokens": 13}
    },
    "code_explanation": {
        "content": "This code defines a function that takes two parameters and returns their sum. The function uses type hints to specify that both parameters should be integers and the return value will also be an integer.",
        "usage": {"prompt_tokens": 20, "completion_tokens": 35, "total_tokens": 55}
    },
    "json_response": {
        "content": json.dumps({
            "status": "success",
            "data": {
                "message": "Operation completed successfully",
                "timestamp": datetime.now().isoformat(),
                "results": [1, 2, 3, 4, 5]
            }
        }),
        "usage": {"prompt_tokens": 15, "completion_tokens": 25, "total_tokens": 40}
    },
    "long_response": {
        "content": "This is a longer response that simulates a detailed explanation or analysis. " * 20,
        "usage": {"prompt_tokens": 30, "completion_tokens": 200, "total_tokens": 230}
    },
    "error_response": {
        "content": "",
        "usage": {},
        "metadata": {
            "error": True,
            "error_type": "rate_limit_exceeded",
            "error_message": "Rate limit exceeded. Please try again later."
        }
    }
}


def get_mock_response(
    response_key: str,
    model: str = "mock-model",
    provider: str = "mock"
) -> LLMResponse:
    """Get a predefined mock response."""
    if response_key not in MOCK_RESPONSES:
        raise ValueError(f"Mock response '{response_key}' not found")
    
    response_data = MOCK_RESPONSES[response_key]
    
    return LLMResponse(
        content=response_data["content"],
        model=model,
        provider=provider,
        usage=response_data["usage"],
        latency=random.uniform(0.1, 1.0),
        metadata=response_data.get("metadata", {"mock": True}),
        timestamp=datetime.now()
    )


def create_mock_conversation(
    turns: int = 3,
    model: str = "mock-model",
    provider: str = "mock"
) -> List[tuple[List[Message], LLMResponse]]:
    """Create a mock conversation with multiple turns."""
    conversation = []
    mock_generator = MockLLMResponses()
    
    conversation_starters = [
        "Hello, how are you?",
        "Can you help me with a coding problem?",
        "What's the weather like today?",
        "Explain machine learning to me.",
        "How do I write a Python function?"
    ]
    
    for i in range(turns):
        if i == 0:
            user_message = random.choice(conversation_starters)
        else:
            user_message = f"Follow-up question {i}: Can you elaborate on that?"
        
        messages = [
            Message(role="system", content="You are a helpful assistant."),
            Message(role="user", content=user_message)
        ]
        
        config = LLMConfig(model=model, temperature=0.7)
        response = mock_generator.generate_response(messages, config, provider)
        
        conversation.append((messages, response))
    
    return conversation


def create_mock_batch_responses(
    batch_size: int = 5,
    model: str = "mock-model",
    provider: str = "mock"
) -> List[LLMResponse]:
    """Create a batch of mock responses."""
    mock_generator = MockLLMResponses()
    
    requests = []
    for i in range(batch_size):
        messages = [
            Message(role="system", content="You are a helpful assistant."),
            Message(role="user", content=f"This is batch request {i + 1}")
        ]
        config = LLMConfig(model=model, temperature=0.7)
        requests.append((messages, config))
    
    return mock_generator.generate_batch_responses(requests, provider)


# Test utilities
def assert_valid_llm_response(response: LLMResponse):
    """Assert that an LLM response is valid."""
    assert isinstance(response, LLMResponse)
    assert response.content is not None
    assert response.model is not None
    assert response.provider is not None
    assert isinstance(response.usage, dict)
    assert response.latency >= 0
    assert isinstance(response.metadata, dict)
    assert response.timestamp is not None


def assert_valid_streaming_responses(responses: List[LLMResponse]):
    """Assert that streaming responses are valid."""
    assert len(responses) > 0
    
    for response in responses:
        assert_valid_llm_response(response)
        assert response.metadata.get("streaming") is True
    
    # Check that chunk indices are sequential
    chunk_indices = [r.metadata.get("chunk_index", 0) for r in responses]
    assert chunk_indices == list(range(len(responses)))
    
    # Check that only the last response is marked as final
    final_responses = [r for r in responses if r.metadata.get("is_final")]
    assert len(final_responses) == 1
    assert final_responses[0] == responses[-1]


def create_test_messages(count: int = 3) -> List[Message]:
    """Create test messages for testing."""
    messages = [
        Message(role="system", content="You are a helpful assistant.")
    ]
    
    for i in range(count):
        if i % 2 == 0:
            messages.append(Message(role="user", content=f"User message {i + 1}"))
        else:
            messages.append(Message(role="assistant", content=f"Assistant response {i}"))
    
    return messages


def create_test_config(**kwargs) -> LLMConfig:
    """Create test LLM config with defaults."""
    defaults = {
        "model": "mock-model",
        "temperature": 0.7,
        "max_tokens": 100,
        "top_p": 1.0
    }
    defaults.update(kwargs)
    return LLMConfig(**defaults)