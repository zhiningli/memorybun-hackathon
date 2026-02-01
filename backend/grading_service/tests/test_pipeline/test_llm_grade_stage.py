"""
Tests for LLMGradeStage.
"""

import pytest
from unittest.mock import AsyncMock

from schemas.grading_state import PipelineStage
from pipeline.llm_grade_stage import LLMGradeStage, create_llm_grade_stage


class TestLLMGradeStage:
    """Tests for LLMGradeStage (mock-only mode)."""
    
    @pytest.mark.asyncio
    async def test_returns_mock_response(self, sample_state, valid_llm_response):
        """Test that mock response is returned."""
        sample_state.system_prompt = "Test system prompt"
        sample_state.user_prompt = "Test user prompt"
        
        # Use the default mock by providing a mock response
        stage = LLMGradeStage(mock_response=valid_llm_response)
        result = await stage.run(sample_state)
        
        # Verify response is set
        assert result.llm_response is not None
        assert result.llm_response == valid_llm_response
        
        # Verify stage advanced
        assert result.stage == PipelineStage.LLM_GRADE
    
    @pytest.mark.asyncio
    async def test_custom_mock_response(self, sample_state, valid_llm_response):
        """Test that custom mock response can be injected."""
        sample_state.system_prompt = "Test system prompt"
        sample_state.user_prompt = "Test user prompt"
        
        stage = LLMGradeStage(mock_response=valid_llm_response)
        result = await stage.run(sample_state)
        
        # Verify custom response used
        assert result.llm_response == valid_llm_response
        assert "0.92" in result.llm_response
    
    @pytest.mark.asyncio
    async def test_raises_error_without_prompts(self, sample_state):
        """Test that error is raised if prompts not set."""
        stage = LLMGradeStage()
        
        with pytest.raises(ValueError, match="Prompts must be set"):
            await stage.run(sample_state)
    
    @pytest.mark.asyncio
    async def test_stage_name(self):
        """Test stage name property."""
        stage = LLMGradeStage()
        assert stage.name == "LLMGradeStage"
    
    def test_factory_function(self):
        """Test the factory function creates stage correctly."""
        stage = create_llm_grade_stage()
        assert isinstance(stage, LLMGradeStage)
    
    def test_factory_with_custom_response(self, valid_llm_response):
        """Test factory with custom mock response."""
        stage = create_llm_grade_stage(mock_response=valid_llm_response)
        assert stage._mock_response == valid_llm_response
