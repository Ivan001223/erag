"""Tests for model registry functionality.

This module contains tests for the ModelRegistry class and related functionality.
"""

import pytest
import asyncio
import json
import tempfile
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, List, Any

from backend.core.llm.model_registry import (
    ModelRegistry,
    ModelStatus,
    ModelType,
    ModelProvider,
    ModelCapability,
    ModelLimits,
    ModelPricing,
    ModelMetrics,
    ModelConfig
)


class TestModelConfig:
    """Test ModelConfig data model."""
    
    def test_model_config_creation(self):
        """Test creating a model config."""
        config = ModelConfig(
            model_id="test-model",
            name="Test Model",
            provider=ModelProvider.OPENAI,
            model_type=ModelType.CHAT,
            status=ModelStatus.ACTIVE,
            capabilities=[ModelCapability.TEXT_GENERATION],
            limits=ModelLimits(
                max_tokens=4096,
                max_requests_per_minute=60,
                max_tokens_per_minute=40000
            ),
            pricing=ModelPricing(
                input_cost_per_token=0.0015,
                output_cost_per_token=0.002
            )
        )
        
        assert config.model_id == "test-model"
        assert config.name == "Test Model"
        assert config.provider == ModelProvider.OPENAI
        assert config.model_type == ModelType.CHAT
        assert config.status == ModelStatus.ACTIVE
        assert ModelCapability.TEXT_GENERATION in config.capabilities
    
    def test_model_config_validation(self):
        """Test model config validation."""
        # Test invalid model_id
        with pytest.raises(ValueError):
            ModelConfig(
                model_id="",  # Empty model_id should be invalid
                name="Test Model",
                provider=ModelProvider.OPENAI,
                model_type=ModelType.CHAT
            )
    
    def test_model_limits(self):
        """Test model limits."""
        limits = ModelLimits(
            max_tokens=4096,
            max_requests_per_minute=60,
            max_tokens_per_minute=40000,
            context_window=8192
        )
        
        assert limits.max_tokens == 4096
        assert limits.max_requests_per_minute == 60
        assert limits.max_tokens_per_minute == 40000
        assert limits.context_window == 8192
    
    def test_model_pricing(self):
        """Test model pricing."""
        pricing = ModelPricing(
            input_cost_per_token=0.0015,
            output_cost_per_token=0.002,
            currency="USD"
        )
        
        assert pricing.input_cost_per_token == 0.0015
        assert pricing.output_cost_per_token == 0.002
        assert pricing.currency == "USD"
    
    def test_model_metrics(self):
        """Test model metrics."""
        metrics = ModelMetrics(
            total_requests=1000,
            successful_requests=950,
            failed_requests=50,
            average_latency=1.5,
            total_tokens_processed=50000
        )
        
        assert metrics.total_requests == 1000
        assert metrics.successful_requests == 950
        assert metrics.failed_requests == 50
        assert metrics.average_latency == 1.5
        assert metrics.total_tokens_processed == 50000
        
        # Test calculated properties
        assert metrics.success_rate == 0.95
        assert metrics.error_rate == 0.05


class TestModelRegistry:
    """Test ModelRegistry class."""
    
    @pytest.fixture
    def temp_registry_file(self):
        """Create a temporary registry file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = Path(f.name)
        yield temp_path
        if temp_path.exists():
            temp_path.unlink()
    
    @pytest.fixture
    def sample_model_config(self):
        """Create a sample model config."""
        return ModelConfig(
            model_id="gpt-3.5-turbo",
            name="GPT-3.5 Turbo",
            provider=ModelProvider.OPENAI,
            model_type=ModelType.CHAT,
            status=ModelStatus.ACTIVE,
            capabilities=[
                ModelCapability.TEXT_GENERATION,
                ModelCapability.CONVERSATION
            ],
            limits=ModelLimits(
                max_tokens=4096,
                max_requests_per_minute=60,
                max_tokens_per_minute=40000,
                context_window=4096
            ),
            pricing=ModelPricing(
                input_cost_per_token=0.0015,
                output_cost_per_token=0.002
            ),
            description="OpenAI's GPT-3.5 Turbo model",
            version="0613"
        )
    
    @pytest.fixture
    async def registry(self, temp_registry_file):
        """Create a model registry instance."""
        registry = ModelRegistry(registry_file=temp_registry_file)
        await registry.initialize()
        yield registry
        await registry.cleanup()
    
    @pytest.mark.asyncio
    async def test_registry_initialization(self, temp_registry_file):
        """Test registry initialization."""
        registry = ModelRegistry(registry_file=temp_registry_file)
        await registry.initialize()
        
        assert registry._models == {}
        assert registry._aliases == {}
        assert registry._metrics == {}
        assert registry._initialized is True
        
        await registry.cleanup()
    
    @pytest.mark.asyncio
    async def test_register_model(self, registry, sample_model_config):
        """Test registering a model."""
        await registry.register_model(sample_model_config)
        
        # Check that model is registered
        assert "gpt-3.5-turbo" in registry._models
        assert registry._models["gpt-3.5-turbo"] == sample_model_config
        
        # Check that metrics are initialized
        assert "gpt-3.5-turbo" in registry._metrics
        metrics = registry._metrics["gpt-3.5-turbo"]
        assert metrics.total_requests == 0
        assert metrics.successful_requests == 0
        assert metrics.failed_requests == 0
    
    @pytest.mark.asyncio
    async def test_register_duplicate_model(self, registry, sample_model_config):
        """Test registering a duplicate model."""
        await registry.register_model(sample_model_config)
        
        # Try to register the same model again
        with pytest.raises(ValueError, match="Model .* is already registered"):
            await registry.register_model(sample_model_config)
    
    @pytest.mark.asyncio
    async def test_unregister_model(self, registry, sample_model_config):
        """Test unregistering a model."""
        await registry.register_model(sample_model_config)
        
        # Add an alias
        await registry.add_alias("gpt35", "gpt-3.5-turbo")
        
        # Unregister the model
        await registry.unregister_model("gpt-3.5-turbo")
        
        # Check that model and related data are removed
        assert "gpt-3.5-turbo" not in registry._models
        assert "gpt-3.5-turbo" not in registry._metrics
        assert "gpt35" not in registry._aliases
    
    @pytest.mark.asyncio
    async def test_unregister_nonexistent_model(self, registry):
        """Test unregistering a non-existent model."""
        with pytest.raises(ValueError, match="Model .* not found"):
            await registry.unregister_model("nonexistent-model")
    
    @pytest.mark.asyncio
    async def test_get_model(self, registry, sample_model_config):
        """Test getting a model."""
        await registry.register_model(sample_model_config)
        
        # Get model by ID
        model = await registry.get_model("gpt-3.5-turbo")
        assert model == sample_model_config
        
        # Get non-existent model
        model = await registry.get_model("nonexistent")
        assert model is None
    
    @pytest.mark.asyncio
    async def test_list_models(self, registry, sample_model_config):
        """Test listing models."""
        await registry.register_model(sample_model_config)
        
        # List all models
        models = await registry.list_models()
        assert len(models) == 1
        assert models[0] == sample_model_config
        
        # List models by provider
        models = await registry.list_models(provider=ModelProvider.OPENAI)
        assert len(models) == 1
        
        models = await registry.list_models(provider=ModelProvider.ANTHROPIC)
        assert len(models) == 0
        
        # List models by type
        models = await registry.list_models(model_type=ModelType.CHAT)
        assert len(models) == 1
        
        models = await registry.list_models(model_type=ModelType.EMBEDDING)
        assert len(models) == 0
        
        # List models by status
        models = await registry.list_models(status=ModelStatus.ACTIVE)
        assert len(models) == 1
        
        models = await registry.list_models(status=ModelStatus.DEPRECATED)
        assert len(models) == 0
    
    @pytest.mark.asyncio
    async def test_search_models(self, registry, sample_model_config):
        """Test searching models."""
        await registry.register_model(sample_model_config)
        
        # Search by name
        models = await registry.search_models("GPT")
        assert len(models) == 1
        assert models[0] == sample_model_config
        
        # Search by description
        models = await registry.search_models("OpenAI")
        assert len(models) == 1
        
        # Search with no matches
        models = await registry.search_models("Claude")
        assert len(models) == 0
    
    @pytest.mark.asyncio
    async def test_add_alias(self, registry, sample_model_config):
        """Test adding model aliases."""
        await registry.register_model(sample_model_config)
        
        # Add alias
        await registry.add_alias("gpt35", "gpt-3.5-turbo")
        assert registry._aliases["gpt35"] == "gpt-3.5-turbo"
        
        # Get model by alias
        model = await registry.get_model("gpt35")
        assert model == sample_model_config
    
    @pytest.mark.asyncio
    async def test_add_alias_for_nonexistent_model(self, registry):
        """Test adding alias for non-existent model."""
        with pytest.raises(ValueError, match="Model .* not found"):
            await registry.add_alias("alias", "nonexistent-model")
    
    @pytest.mark.asyncio
    async def test_remove_alias(self, registry, sample_model_config):
        """Test removing model aliases."""
        await registry.register_model(sample_model_config)
        await registry.add_alias("gpt35", "gpt-3.5-turbo")
        
        # Remove alias
        await registry.remove_alias("gpt35")
        assert "gpt35" not in registry._aliases
        
        # Try to get model by removed alias
        model = await registry.get_model("gpt35")
        assert model is None
    
    @pytest.mark.asyncio
    async def test_remove_nonexistent_alias(self, registry):
        """Test removing non-existent alias."""
        with pytest.raises(ValueError, match="Alias .* not found"):
            await registry.remove_alias("nonexistent-alias")
    
    @pytest.mark.asyncio
    async def test_update_metrics(self, registry, sample_model_config):
        """Test updating model metrics."""
        await registry.register_model(sample_model_config)
        
        # Update metrics
        await registry.update_metrics(
            "gpt-3.5-turbo",
            requests=10,
            successful=9,
            failed=1,
            latency=1.5,
            tokens=1000
        )
        
        metrics = registry._metrics["gpt-3.5-turbo"]
        assert metrics.total_requests == 10
        assert metrics.successful_requests == 9
        assert metrics.failed_requests == 1
        assert metrics.average_latency == 1.5
        assert metrics.total_tokens_processed == 1000
    
    @pytest.mark.asyncio
    async def test_get_metrics(self, registry, sample_model_config):
        """Test getting model metrics."""
        await registry.register_model(sample_model_config)
        
        # Get initial metrics
        metrics = await registry.get_metrics("gpt-3.5-turbo")
        assert metrics.total_requests == 0
        
        # Update and get metrics
        await registry.update_metrics("gpt-3.5-turbo", requests=5)
        metrics = await registry.get_metrics("gpt-3.5-turbo")
        assert metrics.total_requests == 5
    
    @pytest.mark.asyncio
    async def test_get_model_recommendations(self, registry, sample_model_config):
        """Test getting model recommendations."""
        await registry.register_model(sample_model_config)
        
        # Get recommendations for text generation
        recommendations = await registry.get_model_recommendations(
            task_type="text_generation",
            max_tokens=2000
        )
        
        assert len(recommendations) == 1
        assert recommendations[0] == sample_model_config
        
        # Get recommendations with constraints that don't match
        recommendations = await registry.get_model_recommendations(
            task_type="text_generation",
            max_tokens=10000  # Exceeds model's max_tokens
        )
        
        assert len(recommendations) == 0
    
    @pytest.mark.asyncio
    async def test_health_check(self, registry, sample_model_config):
        """Test model health check."""
        await registry.register_model(sample_model_config)
        
        with patch('backend.core.llm.model_registry.ModelRegistry._check_model_health') as mock_health:
            mock_health.return_value = True
            
            # Check healthy model
            is_healthy = await registry.health_check("gpt-3.5-turbo")
            assert is_healthy is True
            
            # Check unhealthy model
            mock_health.return_value = False
            is_healthy = await registry.health_check("gpt-3.5-turbo")
            assert is_healthy is False
    
    @pytest.mark.asyncio
    async def test_export_registry(self, registry, sample_model_config, temp_registry_file):
        """Test exporting registry."""
        await registry.register_model(sample_model_config)
        await registry.add_alias("gpt35", "gpt-3.5-turbo")
        
        # Export to file
        export_file = temp_registry_file.parent / "export.json"
        await registry.export_registry(export_file)
        
        # Check that file exists and contains data
        assert export_file.exists()
        
        with open(export_file, 'r') as f:
            data = json.load(f)
        
        assert "models" in data
        assert "aliases" in data
        assert "metrics" in data
        assert "gpt-3.5-turbo" in data["models"]
        assert "gpt35" in data["aliases"]
        
        # Clean up
        export_file.unlink()
    
    @pytest.mark.asyncio
    async def test_import_registry(self, registry, temp_registry_file):
        """Test importing registry."""
        # Create test data
        test_data = {
            "models": {
                "test-model": {
                    "model_id": "test-model",
                    "name": "Test Model",
                    "provider": "openai",
                    "model_type": "chat",
                    "status": "active",
                    "capabilities": ["text_generation"],
                    "limits": {
                        "max_tokens": 1000,
                        "max_requests_per_minute": 60,
                        "max_tokens_per_minute": 40000
                    },
                    "pricing": {
                        "input_cost_per_token": 0.001,
                        "output_cost_per_token": 0.002
                    }
                }
            },
            "aliases": {
                "test": "test-model"
            },
            "metrics": {
                "test-model": {
                    "total_requests": 100,
                    "successful_requests": 95,
                    "failed_requests": 5,
                    "average_latency": 1.0,
                    "total_tokens_processed": 10000,
                    "last_updated": datetime.now().isoformat()
                }
            }
        }
        
        # Write test data to file
        import_file = temp_registry_file.parent / "import.json"
        with open(import_file, 'w') as f:
            json.dump(test_data, f)
        
        # Import registry
        await registry.import_registry(import_file)
        
        # Check that data was imported
        assert "test-model" in registry._models
        assert "test" in registry._aliases
        assert "test-model" in registry._metrics
        
        model = await registry.get_model("test-model")
        assert model.model_id == "test-model"
        assert model.name == "Test Model"
        
        # Clean up
        import_file.unlink()
    
    @pytest.mark.asyncio
    async def test_start_health_monitoring(self, registry, sample_model_config):
        """Test starting health monitoring."""
        await registry.register_model(sample_model_config)
        
        with patch('asyncio.create_task') as mock_create_task:
            await registry.start_health_monitoring(interval=60)
            
            # Check that monitoring task was created
            mock_create_task.assert_called_once()
            assert registry._monitoring_task is not None
    
    @pytest.mark.asyncio
    async def test_stop_health_monitoring(self, registry):
        """Test stopping health monitoring."""
        # Create a mock task
        mock_task = Mock()
        mock_task.cancel = Mock()
        registry._monitoring_task = mock_task
        
        await registry.stop_health_monitoring()
        
        # Check that task was cancelled
        mock_task.cancel.assert_called_once()
        assert registry._monitoring_task is None
    
    @pytest.mark.asyncio
    async def test_cleanup(self, registry, sample_model_config):
        """Test registry cleanup."""
        await registry.register_model(sample_model_config)
        
        # Start monitoring
        mock_task = Mock()
        mock_task.cancel = Mock()
        registry._monitoring_task = mock_task
        
        # Cleanup
        await registry.cleanup()
        
        # Check that monitoring was stopped and data was saved
        mock_task.cancel.assert_called_once()
        assert registry._monitoring_task is None


class TestModelRegistryIntegration:
    """Integration tests for ModelRegistry."""
    
    @pytest.mark.asyncio
    async def test_full_workflow(self, temp_registry_file):
        """Test a complete workflow with the registry."""
        registry = ModelRegistry(registry_file=temp_registry_file)
        await registry.initialize()
        
        try:
            # Register multiple models
            gpt_config = ModelConfig(
                model_id="gpt-3.5-turbo",
                name="GPT-3.5 Turbo",
                provider=ModelProvider.OPENAI,
                model_type=ModelType.CHAT,
                status=ModelStatus.ACTIVE,
                capabilities=[ModelCapability.TEXT_GENERATION]
            )
            
            claude_config = ModelConfig(
                model_id="claude-3-sonnet",
                name="Claude 3 Sonnet",
                provider=ModelProvider.ANTHROPIC,
                model_type=ModelType.CHAT,
                status=ModelStatus.ACTIVE,
                capabilities=[ModelCapability.TEXT_GENERATION]
            )
            
            await registry.register_model(gpt_config)
            await registry.register_model(claude_config)
            
            # Add aliases
            await registry.add_alias("gpt35", "gpt-3.5-turbo")
            await registry.add_alias("claude", "claude-3-sonnet")
            
            # Update metrics
            await registry.update_metrics("gpt-3.5-turbo", requests=100, successful=95)
            await registry.update_metrics("claude-3-sonnet", requests=50, successful=48)
            
            # Test various queries
            all_models = await registry.list_models()
            assert len(all_models) == 2
            
            openai_models = await registry.list_models(provider=ModelProvider.OPENAI)
            assert len(openai_models) == 1
            
            search_results = await registry.search_models("GPT")
            assert len(search_results) == 1
            
            # Test recommendations
            recommendations = await registry.get_model_recommendations(
                task_type="text_generation"
            )
            assert len(recommendations) == 2
            
            # Test alias resolution
            model_by_alias = await registry.get_model("gpt35")
            assert model_by_alias.model_id == "gpt-3.5-turbo"
            
            # Test metrics
            gpt_metrics = await registry.get_metrics("gpt-3.5-turbo")
            assert gpt_metrics.total_requests == 100
            assert gpt_metrics.successful_requests == 95
            
        finally:
            await registry.cleanup()


@pytest.mark.asyncio
async def test_concurrent_operations():
    """Test concurrent registry operations."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        temp_path = Path(f.name)
    
    try:
        registry = ModelRegistry(registry_file=temp_path)
        await registry.initialize()
        
        # Create multiple model configs
        configs = []
        for i in range(10):
            config = ModelConfig(
                model_id=f"model-{i}",
                name=f"Model {i}",
                provider=ModelProvider.OPENAI,
                model_type=ModelType.CHAT,
                status=ModelStatus.ACTIVE,
                capabilities=[ModelCapability.TEXT_GENERATION]
            )
            configs.append(config)
        
        # Register models concurrently
        tasks = [registry.register_model(config) for config in configs]
        await asyncio.gather(*tasks)
        
        # Verify all models were registered
        all_models = await registry.list_models()
        assert len(all_models) == 10
        
        # Update metrics concurrently
        update_tasks = [
            registry.update_metrics(f"model-{i}", requests=10, successful=9)
            for i in range(10)
        ]
        await asyncio.gather(*update_tasks)
        
        # Verify metrics were updated
        for i in range(10):
            metrics = await registry.get_metrics(f"model-{i}")
            assert metrics.total_requests == 10
            assert metrics.successful_requests == 9
        
        await registry.cleanup()
        
    finally:
        if temp_path.exists():
            temp_path.unlink()