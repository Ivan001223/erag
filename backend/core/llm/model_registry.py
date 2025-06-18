"""Model Registry for LLM management.

This module provides a centralized registry for managing LLM models,
their configurations, capabilities, and lifecycle.
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor

import aiofiles
import yaml
from pydantic import BaseModel, Field, validator

logger = logging.getLogger(__name__)


class ModelStatus(str, Enum):
    """Model status enumeration."""
    AVAILABLE = "available"
    LOADING = "loading"
    ERROR = "error"
    DEPRECATED = "deprecated"
    MAINTENANCE = "maintenance"


class ModelType(str, Enum):
    """Model type enumeration."""
    CHAT = "chat"
    COMPLETION = "completion"
    EMBEDDING = "embedding"
    CLASSIFICATION = "classification"
    SUMMARIZATION = "summarization"
    TRANSLATION = "translation"
    CODE_GENERATION = "code_generation"
    MULTIMODAL = "multimodal"


class ModelProvider(str, Enum):
    """Model provider enumeration."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    HUGGINGFACE = "huggingface"
    GOOGLE = "google"
    COHERE = "cohere"
    AZURE = "azure"
    LOCAL = "local"
    CUSTOM = "custom"


class ModelCapability(str, Enum):
    """Model capability enumeration."""
    TEXT_GENERATION = "text_generation"
    TEXT_EMBEDDING = "text_embedding"
    IMAGE_UNDERSTANDING = "image_understanding"
    CODE_GENERATION = "code_generation"
    FUNCTION_CALLING = "function_calling"
    JSON_MODE = "json_mode"
    STREAMING = "streaming"
    BATCH_PROCESSING = "batch_processing"
    FINE_TUNING = "fine_tuning"


@dataclass
class ModelLimits:
    """Model usage limits."""
    max_tokens: Optional[int] = None
    max_requests_per_minute: Optional[int] = None
    max_requests_per_day: Optional[int] = None
    max_concurrent_requests: Optional[int] = None
    context_window: Optional[int] = None
    max_output_tokens: Optional[int] = None


@dataclass
class ModelPricing:
    """Model pricing information."""
    input_cost_per_token: Optional[float] = None
    output_cost_per_token: Optional[float] = None
    cost_per_request: Optional[float] = None
    currency: str = "USD"
    billing_unit: str = "token"


@dataclass
class ModelMetrics:
    """Model performance metrics."""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    average_latency: float = 0.0
    average_tokens_per_request: float = 0.0
    total_tokens_processed: int = 0
    last_used: Optional[datetime] = None
    error_rate: float = 0.0
    uptime_percentage: float = 100.0


class ModelConfig(BaseModel):
    """Model configuration."""
    model_id: str = Field(..., description="Unique model identifier")
    name: str = Field(..., description="Human-readable model name")
    provider: ModelProvider = Field(..., description="Model provider")
    model_type: ModelType = Field(..., description="Type of model")
    version: str = Field(default="latest", description="Model version")
    
    # Model specifications
    capabilities: List[ModelCapability] = Field(default_factory=list)
    limits: ModelLimits = Field(default_factory=ModelLimits)
    pricing: ModelPricing = Field(default_factory=ModelPricing)
    
    # Configuration
    endpoint_url: Optional[str] = None
    api_key_env: Optional[str] = None
    model_path: Optional[str] = None
    config_params: Dict[str, Any] = Field(default_factory=dict)
    
    # Metadata
    description: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    # Status
    status: ModelStatus = ModelStatus.AVAILABLE
    health_check_url: Optional[str] = None
    last_health_check: Optional[datetime] = None
    
    @validator('model_id')
    def validate_model_id(cls, v):
        if not v or not v.strip():
            raise ValueError("Model ID cannot be empty")
        return v.strip()
    
    @validator('capabilities')
    def validate_capabilities(cls, v):
        return list(set(v))  # Remove duplicates


class ModelRegistry:
    """Centralized registry for managing LLM models."""
    
    def __init__(
        self,
        registry_path: Optional[Path] = None,
        auto_save: bool = True,
        health_check_interval: int = 300  # 5 minutes
    ):
        self.registry_path = registry_path or Path("models_registry.yaml")
        self.auto_save = auto_save
        self.health_check_interval = health_check_interval
        
        self._models: Dict[str, ModelConfig] = {}
        self._metrics: Dict[str, ModelMetrics] = {}
        self._aliases: Dict[str, str] = {}  # alias -> model_id
        self._tags_index: Dict[str, Set[str]] = {}  # tag -> set of model_ids
        self._provider_index: Dict[ModelProvider, Set[str]] = {}
        self._type_index: Dict[ModelType, Set[str]] = {}
        
        self._executor = ThreadPoolExecutor(max_workers=4)
        self._health_check_task: Optional[asyncio.Task] = None
        
        # Load existing registry
        asyncio.create_task(self._load_registry())
    
    async def register_model(self, config: ModelConfig) -> bool:
        """Register a new model."""
        try:
            # Validate model doesn't already exist
            if config.model_id in self._models:
                logger.warning(f"Model {config.model_id} already registered")
                return False
            
            # Add to registry
            self._models[config.model_id] = config
            self._metrics[config.model_id] = ModelMetrics()
            
            # Update indices
            self._update_indices(config)
            
            # Perform initial health check
            await self._health_check_model(config.model_id)
            
            # Auto-save if enabled
            if self.auto_save:
                await self._save_registry()
            
            logger.info(f"Model {config.model_id} registered successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to register model {config.model_id}: {e}")
            return False
    
    async def unregister_model(self, model_id: str) -> bool:
        """Unregister a model."""
        try:
            if model_id not in self._models:
                logger.warning(f"Model {model_id} not found")
                return False
            
            config = self._models[model_id]
            
            # Remove from registry
            del self._models[model_id]
            del self._metrics[model_id]
            
            # Remove from indices
            self._remove_from_indices(config)
            
            # Remove aliases
            aliases_to_remove = [alias for alias, mid in self._aliases.items() if mid == model_id]
            for alias in aliases_to_remove:
                del self._aliases[alias]
            
            # Auto-save if enabled
            if self.auto_save:
                await self._save_registry()
            
            logger.info(f"Model {model_id} unregistered successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to unregister model {model_id}: {e}")
            return False
    
    async def update_model(self, model_id: str, updates: Dict[str, Any]) -> bool:
        """Update model configuration."""
        try:
            if model_id not in self._models:
                logger.warning(f"Model {model_id} not found")
                return False
            
            config = self._models[model_id]
            old_config = config.copy()
            
            # Update configuration
            for key, value in updates.items():
                if hasattr(config, key):
                    setattr(config, key, value)
            
            config.updated_at = datetime.now()
            
            # Update indices if necessary
            self._remove_from_indices(old_config)
            self._update_indices(config)
            
            # Auto-save if enabled
            if self.auto_save:
                await self._save_registry()
            
            logger.info(f"Model {model_id} updated successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update model {model_id}: {e}")
            return False
    
    def get_model(self, model_id: str) -> Optional[ModelConfig]:
        """Get model configuration by ID or alias."""
        # Check direct ID
        if model_id in self._models:
            return self._models[model_id]
        
        # Check alias
        if model_id in self._aliases:
            return self._models[self._aliases[model_id]]
        
        return None
    
    def list_models(
        self,
        provider: Optional[ModelProvider] = None,
        model_type: Optional[ModelType] = None,
        status: Optional[ModelStatus] = None,
        tags: Optional[List[str]] = None,
        capabilities: Optional[List[ModelCapability]] = None
    ) -> List[ModelConfig]:
        """List models with optional filtering."""
        models = list(self._models.values())
        
        # Apply filters
        if provider:
            models = [m for m in models if m.provider == provider]
        
        if model_type:
            models = [m for m in models if m.model_type == model_type]
        
        if status:
            models = [m for m in models if m.status == status]
        
        if tags:
            models = [m for m in models if any(tag in m.tags for tag in tags)]
        
        if capabilities:
            models = [
                m for m in models 
                if all(cap in m.capabilities for cap in capabilities)
            ]
        
        return models
    
    def search_models(self, query: str) -> List[ModelConfig]:
        """Search models by name, description, or tags."""
        query_lower = query.lower()
        results = []
        
        for model in self._models.values():
            # Search in name
            if query_lower in model.name.lower():
                results.append(model)
                continue
            
            # Search in description
            if model.description and query_lower in model.description.lower():
                results.append(model)
                continue
            
            # Search in tags
            if any(query_lower in tag.lower() for tag in model.tags):
                results.append(model)
                continue
        
        return results
    
    async def add_alias(self, alias: str, model_id: str) -> bool:
        """Add an alias for a model."""
        if model_id not in self._models:
            logger.warning(f"Model {model_id} not found")
            return False
        
        if alias in self._aliases:
            logger.warning(f"Alias {alias} already exists")
            return False
        
        self._aliases[alias] = model_id
        
        if self.auto_save:
            await self._save_registry()
        
        return True
    
    async def remove_alias(self, alias: str) -> bool:
        """Remove an alias."""
        if alias not in self._aliases:
            logger.warning(f"Alias {alias} not found")
            return False
        
        del self._aliases[alias]
        
        if self.auto_save:
            await self._save_registry()
        
        return True
    
    def get_metrics(self, model_id: str) -> Optional[ModelMetrics]:
        """Get model metrics."""
        return self._metrics.get(model_id)
    
    async def update_metrics(
        self,
        model_id: str,
        success: bool,
        latency: float,
        tokens_processed: int = 0
    ) -> None:
        """Update model metrics."""
        if model_id not in self._metrics:
            return
        
        metrics = self._metrics[model_id]
        metrics.total_requests += 1
        metrics.last_used = datetime.now()
        
        if success:
            metrics.successful_requests += 1
        else:
            metrics.failed_requests += 1
        
        # Update averages
        total_requests = metrics.total_requests
        metrics.average_latency = (
            (metrics.average_latency * (total_requests - 1) + latency) / total_requests
        )
        
        if tokens_processed > 0:
            metrics.total_tokens_processed += tokens_processed
            metrics.average_tokens_per_request = (
                metrics.total_tokens_processed / total_requests
            )
        
        # Update error rate
        metrics.error_rate = metrics.failed_requests / total_requests * 100
    
    async def get_model_recommendations(
        self,
        task_type: ModelType,
        requirements: Optional[Dict[str, Any]] = None
    ) -> List[ModelConfig]:
        """Get model recommendations for a specific task."""
        candidates = self.list_models(model_type=task_type, status=ModelStatus.AVAILABLE)
        
        if not requirements:
            return sorted(candidates, key=lambda m: self._calculate_model_score(m), reverse=True)
        
        # Filter by requirements
        filtered = []
        for model in candidates:
            if self._meets_requirements(model, requirements):
                filtered.append(model)
        
        # Sort by score
        return sorted(filtered, key=lambda m: self._calculate_model_score(m), reverse=True)
    
    async def health_check(self, model_id: Optional[str] = None) -> Dict[str, bool]:
        """Perform health check on models."""
        if model_id:
            result = await self._health_check_model(model_id)
            return {model_id: result}
        
        # Check all models
        results = {}
        for mid in self._models.keys():
            results[mid] = await self._health_check_model(mid)
        
        return results
    
    async def export_registry(self, path: Optional[Path] = None) -> bool:
        """Export registry to file."""
        try:
            export_path = path or self.registry_path.with_suffix('.export.yaml')
            
            export_data = {
                'models': {mid: config.dict() for mid, config in self._models.items()},
                'aliases': self._aliases,
                'exported_at': datetime.now().isoformat()
            }
            
            async with aiofiles.open(export_path, 'w') as f:
                await f.write(yaml.dump(export_data, default_flow_style=False))
            
            logger.info(f"Registry exported to {export_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to export registry: {e}")
            return False
    
    async def import_registry(self, path: Path, merge: bool = False) -> bool:
        """Import registry from file."""
        try:
            async with aiofiles.open(path, 'r') as f:
                content = await f.read()
                data = yaml.safe_load(content)
            
            if not merge:
                self._models.clear()
                self._metrics.clear()
                self._aliases.clear()
                self._clear_indices()
            
            # Import models
            for model_id, model_data in data.get('models', {}).items():
                config = ModelConfig(**model_data)
                await self.register_model(config)
            
            # Import aliases
            for alias, model_id in data.get('aliases', {}).items():
                await self.add_alias(alias, model_id)
            
            logger.info(f"Registry imported from {path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to import registry: {e}")
            return False
    
    async def start_health_monitoring(self) -> None:
        """Start periodic health monitoring."""
        if self._health_check_task:
            return
        
        self._health_check_task = asyncio.create_task(self._health_monitor_loop())
        logger.info("Health monitoring started")
    
    async def stop_health_monitoring(self) -> None:
        """Stop health monitoring."""
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
            self._health_check_task = None
            logger.info("Health monitoring stopped")
    
    async def cleanup(self) -> None:
        """Cleanup resources."""
        await self.stop_health_monitoring()
        
        if self.auto_save:
            await self._save_registry()
        
        self._executor.shutdown(wait=True)
        logger.info("Model registry cleaned up")
    
    # Private methods
    
    def _update_indices(self, config: ModelConfig) -> None:
        """Update search indices."""
        model_id = config.model_id
        
        # Tags index
        for tag in config.tags:
            if tag not in self._tags_index:
                self._tags_index[tag] = set()
            self._tags_index[tag].add(model_id)
        
        # Provider index
        if config.provider not in self._provider_index:
            self._provider_index[config.provider] = set()
        self._provider_index[config.provider].add(model_id)
        
        # Type index
        if config.model_type not in self._type_index:
            self._type_index[config.model_type] = set()
        self._type_index[config.model_type].add(model_id)
    
    def _remove_from_indices(self, config: ModelConfig) -> None:
        """Remove from search indices."""
        model_id = config.model_id
        
        # Tags index
        for tag in config.tags:
            if tag in self._tags_index:
                self._tags_index[tag].discard(model_id)
                if not self._tags_index[tag]:
                    del self._tags_index[tag]
        
        # Provider index
        if config.provider in self._provider_index:
            self._provider_index[config.provider].discard(model_id)
            if not self._provider_index[config.provider]:
                del self._provider_index[config.provider]
        
        # Type index
        if config.model_type in self._type_index:
            self._type_index[config.model_type].discard(model_id)
            if not self._type_index[config.model_type]:
                del self._type_index[config.model_type]
    
    def _clear_indices(self) -> None:
        """Clear all indices."""
        self._tags_index.clear()
        self._provider_index.clear()
        self._type_index.clear()
    
    async def _load_registry(self) -> None:
        """Load registry from file."""
        try:
            if not self.registry_path.exists():
                logger.info("Registry file not found, starting with empty registry")
                return
            
            async with aiofiles.open(self.registry_path, 'r') as f:
                content = await f.read()
                data = yaml.safe_load(content)
            
            # Load models
            for model_id, model_data in data.get('models', {}).items():
                config = ModelConfig(**model_data)
                self._models[model_id] = config
                self._metrics[model_id] = ModelMetrics()
                self._update_indices(config)
            
            # Load aliases
            self._aliases = data.get('aliases', {})
            
            logger.info(f"Loaded {len(self._models)} models from registry")
            
        except Exception as e:
            logger.error(f"Failed to load registry: {e}")
    
    async def _save_registry(self) -> None:
        """Save registry to file."""
        try:
            data = {
                'models': {mid: config.dict() for mid, config in self._models.items()},
                'aliases': self._aliases,
                'saved_at': datetime.now().isoformat()
            }
            
            # Ensure directory exists
            self.registry_path.parent.mkdir(parents=True, exist_ok=True)
            
            async with aiofiles.open(self.registry_path, 'w') as f:
                await f.write(yaml.dump(data, default_flow_style=False))
            
        except Exception as e:
            logger.error(f"Failed to save registry: {e}")
    
    async def _health_check_model(self, model_id: str) -> bool:
        """Perform health check on a specific model."""
        try:
            config = self._models.get(model_id)
            if not config:
                return False
            
            # Update last health check time
            config.last_health_check = datetime.now()
            
            # Simple availability check
            if config.status == ModelStatus.MAINTENANCE:
                return False
            
            # If health check URL is provided, use it
            if config.health_check_url:
                # This would typically make an HTTP request
                # For now, we'll simulate it
                await asyncio.sleep(0.1)
                return True
            
            # Default to available if no specific check
            return config.status == ModelStatus.AVAILABLE
            
        except Exception as e:
            logger.error(f"Health check failed for model {model_id}: {e}")
            if model_id in self._models:
                self._models[model_id].status = ModelStatus.ERROR
            return False
    
    async def _health_monitor_loop(self) -> None:
        """Periodic health monitoring loop."""
        while True:
            try:
                await asyncio.sleep(self.health_check_interval)
                await self.health_check()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health monitor error: {e}")
    
    def _calculate_model_score(self, model: ModelConfig) -> float:
        """Calculate model score for recommendations."""
        score = 0.0
        
        # Base score from metrics
        metrics = self._metrics.get(model.model_id)
        if metrics:
            # Higher success rate = higher score
            if metrics.total_requests > 0:
                success_rate = metrics.successful_requests / metrics.total_requests
                score += success_rate * 50
            
            # Lower latency = higher score
            if metrics.average_latency > 0:
                score += max(0, 20 - metrics.average_latency)
            
            # Recent usage = higher score
            if metrics.last_used:
                days_since_use = (datetime.now() - metrics.last_used).days
                score += max(0, 10 - days_since_use)
        
        # Status bonus
        if model.status == ModelStatus.AVAILABLE:
            score += 20
        
        # Capability bonus
        score += len(model.capabilities) * 2
        
        return score
    
    def _meets_requirements(self, model: ModelConfig, requirements: Dict[str, Any]) -> bool:
        """Check if model meets requirements."""
        # Check capabilities
        required_caps = requirements.get('capabilities', [])
        if required_caps and not all(cap in model.capabilities for cap in required_caps):
            return False
        
        # Check limits
        if 'max_tokens' in requirements:
            if not model.limits.max_tokens or model.limits.max_tokens < requirements['max_tokens']:
                return False
        
        if 'context_window' in requirements:
            if not model.limits.context_window or model.limits.context_window < requirements['context_window']:
                return False
        
        # Check provider
        if 'provider' in requirements and model.provider != requirements['provider']:
            return False
        
        return True


# Global registry instance
_registry: Optional[ModelRegistry] = None


def get_registry() -> ModelRegistry:
    """Get global model registry instance."""
    global _registry
    if _registry is None:
        _registry = ModelRegistry()
    return _registry


async def initialize_registry(
    registry_path: Optional[Path] = None,
    auto_save: bool = True,
    health_check_interval: int = 300
) -> ModelRegistry:
    """Initialize global model registry."""
    global _registry
    _registry = ModelRegistry(
        registry_path=registry_path,
        auto_save=auto_save,
        health_check_interval=health_check_interval
    )
    await _registry.start_health_monitoring()
    return _registry


async def cleanup_registry() -> None:
    """Cleanup global model registry."""
    global _registry
    if _registry:
        await _registry.cleanup()
        _registry = None