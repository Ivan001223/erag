"""Tests for Prompt Manager."""

import asyncio
import pytest
import tempfile
import yaml
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from typing import Dict, Any

from backend.core.llm.prompt_manager import (
    PromptManager,
    PromptType,
    PromptCategory,
    PromptFormat,
    PromptVariable,
    PromptTemplate,
    PromptChain,
    PromptExecution,
    PromptValidator,
    PromptRenderer
)


@pytest.fixture
def temp_dir():
    """Create temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_template():
    """Create sample prompt template."""
    return PromptTemplate(
        template_id="test_template",
        name="Test Template",
        description="A test template",
        template="Hello {{name}}, how are you?",
        variables=[
            PromptVariable(
                name="name",
                type="string",
                description="User's name",
                required=True
            )
        ],
        prompt_type=PromptType.CHAT,
        category=PromptCategory.GENERAL
    )


@pytest.fixture
def sample_chain():
    """Create sample prompt chain."""
    return PromptChain(
        chain_id="test_chain",
        name="Test Chain",
        description="A test chain",
        steps=[
            {
                "template_id": "step1",
                "variables": {"input": "{{user_input}}"},
                "output_variable": "step1_output"
            },
            {
                "template_id": "step2",
                "variables": {"previous": "{{step1_output}}"},
                "output_variable": "final_output"
            }
        ]
    )


@pytest.fixture
def prompt_manager(temp_dir):
    """Create prompt manager with temporary directory."""
    return PromptManager(templates_dir=temp_dir)


class TestPromptManager:
    """Test Prompt Manager functionality."""
    
    @pytest.mark.asyncio
    async def test_add_template(self, prompt_manager, sample_template):
        """Test adding a template."""
        success = await prompt_manager.add_template(sample_template)
        assert success
        
        # Check template was added
        retrieved = prompt_manager.get_template("test_template")
        assert retrieved is not None
        assert retrieved.template_id == "test_template"
        assert retrieved.name == "Test Template"
    
    @pytest.mark.asyncio
    async def test_add_duplicate_template(self, prompt_manager, sample_template):
        """Test adding duplicate template."""
        # Add template first time
        success = await prompt_manager.add_template(sample_template)
        assert success
        
        # Try to add same template again
        success = await prompt_manager.add_template(sample_template)
        assert not success
    
    @pytest.mark.asyncio
    async def test_update_template(self, prompt_manager, sample_template):
        """Test updating a template."""
        # Add template
        await prompt_manager.add_template(sample_template)
        
        # Update template
        updates = {
            "name": "Updated Template",
            "description": "Updated description"
        }
        success = await prompt_manager.update_template("test_template", updates)
        assert success
        
        # Check updates
        retrieved = prompt_manager.get_template("test_template")
        assert retrieved.name == "Updated Template"
        assert retrieved.description == "Updated description"
    
    @pytest.mark.asyncio
    async def test_delete_template(self, prompt_manager, sample_template):
        """Test deleting a template."""
        # Add template
        await prompt_manager.add_template(sample_template)
        
        # Delete template
        success = await prompt_manager.delete_template("test_template")
        assert success
        
        # Check template was deleted
        retrieved = prompt_manager.get_template("test_template")
        assert retrieved is None
    
    def test_list_templates(self, prompt_manager, sample_template):
        """Test listing templates."""
        # Add template
        asyncio.run(prompt_manager.add_template(sample_template))
        
        # List all templates
        templates = prompt_manager.list_templates()
        assert len(templates) == 1
        assert templates[0].template_id == "test_template"
        
        # List by category
        templates = prompt_manager.list_templates(category=PromptCategory.GENERAL)
        assert len(templates) == 1
        
        # List by type
        templates = prompt_manager.list_templates(prompt_type=PromptType.CHAT)
        assert len(templates) == 1
        
        # List by non-matching category
        templates = prompt_manager.list_templates(category=PromptCategory.SYSTEM)
        assert len(templates) == 0
    
    @pytest.mark.asyncio
    async def test_render_template(self, prompt_manager, sample_template):
        """Test rendering a template."""
        # Add template
        await prompt_manager.add_template(sample_template)
        
        # Render template
        result = await prompt_manager.render_template(
            "test_template",
            {"name": "Alice"}
        )
        
        assert result == "Hello Alice, how are you?"
    
    @pytest.mark.asyncio
    async def test_render_template_missing_variable(self, prompt_manager, sample_template):
        """Test rendering template with missing required variable."""
        # Add template
        await prompt_manager.add_template(sample_template)
        
        # Try to render without required variable
        with pytest.raises(ValueError, match="Missing required variable"):
            await prompt_manager.render_template("test_template", {})
    
    @pytest.mark.asyncio
    async def test_render_nonexistent_template(self, prompt_manager):
        """Test rendering non-existent template."""
        with pytest.raises(ValueError, match="Template nonexistent not found"):
            await prompt_manager.render_template("nonexistent", {})
    
    @pytest.mark.asyncio
    async def test_add_chain(self, prompt_manager, sample_chain):
        """Test adding a prompt chain."""
        success = await prompt_manager.add_chain(sample_chain)
        assert success
        
        # Check chain was added
        retrieved = prompt_manager.get_chain("test_chain")
        assert retrieved is not None
        assert retrieved.chain_id == "test_chain"
        assert retrieved.name == "Test Chain"
    
    @pytest.mark.asyncio
    async def test_execute_chain(self, prompt_manager, sample_chain):
        """Test executing a prompt chain."""
        # Create step templates
        step1_template = PromptTemplate(
            template_id="step1",
            name="Step 1",
            template="Process: {{input}}",
            variables=[
                PromptVariable(name="input", type="string", required=True)
            ]
        )
        
        step2_template = PromptTemplate(
            template_id="step2",
            name="Step 2",
            template="Result: {{previous}}",
            variables=[
                PromptVariable(name="previous", type="string", required=True)
            ]
        )
        
        # Add templates and chain
        await prompt_manager.add_template(step1_template)
        await prompt_manager.add_template(step2_template)
        await prompt_manager.add_chain(sample_chain)
        
        # Mock LLM responses
        with patch.object(prompt_manager, '_execute_llm_call') as mock_llm:
            mock_llm.side_effect = [
                "Processed input",
                "Final result"
            ]
            
            # Execute chain
            result = await prompt_manager.execute_chain(
                "test_chain",
                {"user_input": "test input"}
            )
            
            assert result.chain_id == "test_chain"
            assert result.success
            assert "final_output" in result.outputs
            assert result.outputs["final_output"] == "Final result"
    
    @pytest.mark.asyncio
    async def test_get_execution_history(self, prompt_manager, sample_chain):
        """Test getting execution history."""
        # Add chain
        await prompt_manager.add_chain(sample_chain)
        
        # Mock execution
        execution = PromptExecution(
            execution_id="test_exec",
            chain_id="test_chain",
            inputs={"user_input": "test"},
            outputs={"final_output": "result"},
            success=True,
            execution_time=1.0
        )
        
        # Add to history (this would normally be done during execution)
        prompt_manager._execution_history.append(execution)
        
        # Get history
        history = prompt_manager.get_execution_history("test_chain")
        assert len(history) == 1
        assert history[0].execution_id == "test_exec"
    
    @pytest.mark.asyncio
    async def test_get_statistics(self, prompt_manager, sample_template):
        """Test getting statistics."""
        # Add template
        await prompt_manager.add_template(sample_template)
        
        # Get statistics
        stats = await prompt_manager.get_statistics()
        
        assert "total_templates" in stats
        assert "total_chains" in stats
        assert "total_executions" in stats
        assert stats["total_templates"] == 1
        assert stats["total_chains"] == 0
    
    @pytest.mark.asyncio
    async def test_export_templates(self, prompt_manager, sample_template, temp_dir):
        """Test exporting templates."""
        # Add template
        await prompt_manager.add_template(sample_template)
        
        # Export templates
        export_path = temp_dir / "export.yaml"
        success = await prompt_manager.export_templates(export_path)
        assert success
        
        # Check export file exists and contains data
        assert export_path.exists()
        
        with open(export_path, 'r') as f:
            data = yaml.safe_load(f)
        
        assert "templates" in data
        assert "test_template" in data["templates"]
    
    @pytest.mark.asyncio
    async def test_import_templates(self, prompt_manager, temp_dir):
        """Test importing templates."""
        # Create import data
        import_data = {
            "templates": {
                "imported_template": {
                    "template_id": "imported_template",
                    "name": "Imported Template",
                    "template": "Hello {{name}}",
                    "variables": [
                        {
                            "name": "name",
                            "type": "string",
                            "required": True
                        }
                    ],
                    "prompt_type": "chat",
                    "category": "general"
                }
            }
        }
        
        # Write import file
        import_path = temp_dir / "import.yaml"
        with open(import_path, 'w') as f:
            yaml.dump(import_data, f)
        
        # Import templates
        success = await prompt_manager.import_templates(import_path)
        assert success
        
        # Check template was imported
        template = prompt_manager.get_template("imported_template")
        assert template is not None
        assert template.name == "Imported Template"
    
    @pytest.mark.asyncio
    async def test_load_default_templates(self, prompt_manager):
        """Test loading default templates."""
        await prompt_manager.load_default_templates()
        
        # Check that some default templates were loaded
        templates = prompt_manager.list_templates()
        assert len(templates) > 0
        
        # Check for specific default templates
        system_templates = prompt_manager.list_templates(category=PromptCategory.SYSTEM)
        assert len(system_templates) > 0
    
    @pytest.mark.asyncio
    async def test_cleanup(self, prompt_manager):
        """Test cleanup."""
        # Add some data
        sample_template = PromptTemplate(
            template_id="test",
            name="Test",
            template="Test template"
        )
        await prompt_manager.add_template(sample_template)
        
        # Cleanup
        await prompt_manager.cleanup()
        
        # Check that cleanup doesn't raise errors
        assert True


class TestPromptValidator:
    """Test Prompt Validator functionality."""
    
    def test_validate_template_valid(self):
        """Test validating a valid template."""
        template = PromptTemplate(
            template_id="valid",
            name="Valid Template",
            template="Hello {{name}}",
            variables=[
                PromptVariable(name="name", type="string", required=True)
            ]
        )
        
        validator = PromptValidator()
        is_valid, errors = validator.validate_template(template)
        
        assert is_valid
        assert len(errors) == 0
    
    def test_validate_template_missing_variable(self):
        """Test validating template with missing variable definition."""
        template = PromptTemplate(
            template_id="invalid",
            name="Invalid Template",
            template="Hello {{name}} and {{age}}",
            variables=[
                PromptVariable(name="name", type="string", required=True)
                # Missing 'age' variable
            ]
        )
        
        validator = PromptValidator()
        is_valid, errors = validator.validate_template(template)
        
        assert not is_valid
        assert len(errors) > 0
        assert any("age" in error for error in errors)
    
    def test_validate_template_unused_variable(self):
        """Test validating template with unused variable."""
        template = PromptTemplate(
            template_id="unused",
            name="Unused Variable Template",
            template="Hello {{name}}",
            variables=[
                PromptVariable(name="name", type="string", required=True),
                PromptVariable(name="unused", type="string", required=False)
            ]
        )
        
        validator = PromptValidator()
        is_valid, errors = validator.validate_template(template)
        
        # Should still be valid, but might have warnings
        assert is_valid
    
    def test_validate_variables_valid(self):
        """Test validating valid variables."""
        template = PromptTemplate(
            template_id="test",
            name="Test",
            template="Hello {{name}}",
            variables=[
                PromptVariable(name="name", type="string", required=True)
            ]
        )
        
        variables = {"name": "Alice"}
        
        validator = PromptValidator()
        is_valid, errors = validator.validate_variables(template, variables)
        
        assert is_valid
        assert len(errors) == 0
    
    def test_validate_variables_missing_required(self):
        """Test validating variables with missing required variable."""
        template = PromptTemplate(
            template_id="test",
            name="Test",
            template="Hello {{name}}",
            variables=[
                PromptVariable(name="name", type="string", required=True)
            ]
        )
        
        variables = {}  # Missing required 'name'
        
        validator = PromptValidator()
        is_valid, errors = validator.validate_variables(template, variables)
        
        assert not is_valid
        assert len(errors) > 0
        assert any("name" in error for error in errors)


class TestPromptRenderer:
    """Test Prompt Renderer functionality."""
    
    def test_render_simple_template(self):
        """Test rendering simple template."""
        template = "Hello {{name}}, how are you?"
        variables = {"name": "Alice"}
        
        renderer = PromptRenderer()
        result = renderer.render(template, variables)
        
        assert result == "Hello Alice, how are you?"
    
    def test_render_complex_template(self):
        """Test rendering complex template with conditionals."""
        template = """Hello {{name}}!
{% if age %}
You are {{age}} years old.
{% endif %}
{% if items %}
Your items:
{% for item in items %}
- {{item}}
{% endfor %}
{% endif %}"""
        
        variables = {
            "name": "Alice",
            "age": 25,
            "items": ["book", "pen", "notebook"]
        }
        
        renderer = PromptRenderer()
        result = renderer.render(template, variables)
        
        assert "Hello Alice!" in result
        assert "You are 25 years old." in result
        assert "- book" in result
        assert "- pen" in result
        assert "- notebook" in result
    
    def test_render_with_filters(self):
        """Test rendering with Jinja2 filters."""
        template = "Hello {{name|upper}}, today is {{date|strftime('%Y-%m-%d')}}"
        variables = {
            "name": "alice",
            "date": datetime(2023, 12, 25)
        }
        
        renderer = PromptRenderer()
        result = renderer.render(template, variables)
        
        assert "Hello ALICE" in result
        assert "2023-12-25" in result
    
    def test_render_missing_variable(self):
        """Test rendering with missing variable."""
        template = "Hello {{name}}, your age is {{age}}"
        variables = {"name": "Alice"}  # Missing 'age'
        
        renderer = PromptRenderer()
        
        # Should raise an error for undefined variable
        with pytest.raises(Exception):
            renderer.render(template, variables)


class TestPromptDataModels:
    """Test prompt data models."""
    
    def test_prompt_variable_model(self):
        """Test PromptVariable model."""
        variable = PromptVariable(
            name="test_var",
            type="string",
            description="A test variable",
            required=True,
            default_value="default"
        )
        
        assert variable.name == "test_var"
        assert variable.type == "string"
        assert variable.description == "A test variable"
        assert variable.required is True
        assert variable.default_value == "default"
    
    def test_prompt_template_model(self):
        """Test PromptTemplate model."""
        template = PromptTemplate(
            template_id="test",
            name="Test Template",
            description="A test template",
            template="Hello {{name}}",
            variables=[
                PromptVariable(name="name", type="string", required=True)
            ],
            prompt_type=PromptType.CHAT,
            category=PromptCategory.GENERAL,
            tags=["test", "example"]
        )
        
        assert template.template_id == "test"
        assert template.name == "Test Template"
        assert template.prompt_type == PromptType.CHAT
        assert template.category == PromptCategory.GENERAL
        assert "test" in template.tags
        assert len(template.variables) == 1
    
    def test_prompt_chain_model(self):
        """Test PromptChain model."""
        chain = PromptChain(
            chain_id="test_chain",
            name="Test Chain",
            description="A test chain",
            steps=[
                {
                    "template_id": "step1",
                    "variables": {"input": "{{user_input}}"},
                    "output_variable": "step1_output"
                }
            ]
        )
        
        assert chain.chain_id == "test_chain"
        assert chain.name == "Test Chain"
        assert len(chain.steps) == 1
        assert chain.steps[0]["template_id"] == "step1"
    
    def test_prompt_execution_model(self):
        """Test PromptExecution model."""
        execution = PromptExecution(
            execution_id="exec_1",
            chain_id="chain_1",
            inputs={"user_input": "test"},
            outputs={"result": "output"},
            success=True,
            execution_time=1.5,
            error_message=None
        )
        
        assert execution.execution_id == "exec_1"
        assert execution.chain_id == "chain_1"
        assert execution.success is True
        assert execution.execution_time == 1.5
        assert execution.error_message is None


if __name__ == "__main__":
    pytest.main([__file__])