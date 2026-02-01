"""
Tests for SummaryLLMStage.
"""

import pytest
import json
from unittest.mock import AsyncMock, patch

from schemas.summary_state import SummaryPipelineStage
from pipeline.summary.summary_llm_stage import (
    SummaryLLMStage,
    create_summary_llm_stage,
    MOCK_SUMMARY_RESPONSE
)


class TestSummaryLLMStage:
    """Tests for SummaryLLMStage."""
    
    @pytest.mark.asyncio
    async def test_returns_mock_response_when_flag_set(self, sample_state_with_prompts):
        """Test that mock response is returned when mock flag is set."""
        with patch('pipeline.summary.summary_llm_stage.settings') as mock_settings:
            mock_settings.mock_llm_response = True
            
            stage = SummaryLLMStage()
            result = await stage.run(sample_state_with_prompts)
            
            # Verify mock response is used
            assert result.llm_response == MOCK_SUMMARY_RESPONSE
            assert result.stage == SummaryPipelineStage.LLM_SUMMARIZE
    
    @pytest.mark.asyncio
    async def test_uses_custom_mock_response(self, sample_state_with_prompts):
        """Test that custom mock response can be injected."""
        custom_response = json.dumps({
            "overall_score": 90,
            "dimension_scores": [],
            "analytics_summary": ["Test"],
            "overall_feedback": "Custom",
            "key_strengths": ["Test"],
            "areas_for_improvement": ["Test"]
        })
        
        stage = SummaryLLMStage(mock_response=custom_response)
        result = await stage.run(sample_state_with_prompts)
        
        assert result.llm_response == custom_response
        parsed = json.loads(result.llm_response)
        assert parsed["overall_score"] == 90
    
    @pytest.mark.asyncio
    async def test_raises_without_prompts(self, sample_summary_state):
        """Test that stage raises without prompts."""
        stage = SummaryLLMStage()
        
        with pytest.raises(ValueError, match="Prompts must be set"):
            await stage.run(sample_summary_state)
    
    @pytest.mark.asyncio
    async def test_stage_name(self):
        """Test stage name property."""
        stage = SummaryLLMStage()
        assert stage.name == "SummaryLLMStage"
    
    def test_factory_function(self):
        """Test factory function creates stage."""
        stage = create_summary_llm_stage()
        assert isinstance(stage, SummaryLLMStage)
    
    def test_mock_response_is_valid_json(self):
        """Test that default mock response is valid JSON."""
        parsed = json.loads(MOCK_SUMMARY_RESPONSE)
        
        assert "dimension_scores" in parsed
        assert "analytics_summary" in parsed
        assert "overall_feedback" in parsed
        assert "key_strengths" in parsed
        assert "areas_for_improvement" in parsed
        assert len(parsed["dimension_scores"]) == 5
