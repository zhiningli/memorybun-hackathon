"""
Tests for SummaryValidateStage.
"""

import pytest
import json
from unittest.mock import patch

from schemas.summary_state import SummaryPipelineStage
from schemas.summary_result import SUMMARY_DIMENSIONS
from pipeline.summary.summary_validate_stage import (
    SummaryValidateStage,
    SummaryValidationError,
    create_summary_validate_stage
)


class TestSummaryValidateStage:
    """Tests for SummaryValidateStage."""
    
    @pytest.mark.asyncio
    async def test_validates_valid_response(
        self, sample_state_with_prompts, valid_summary_llm_response
    ):
        """Test that valid LLM response is validated."""
        sample_state_with_prompts.llm_response = valid_summary_llm_response
        
        stage = SummaryValidateStage()
        result = await stage.run(sample_state_with_prompts)
        
        # Verify result is populated
        assert result.result is not None
        assert len(result.result["dimension_scores"]) == 5
        assert result.stage == SummaryPipelineStage.VALIDATE
    

    
    @pytest.mark.asyncio
    async def test_adds_missing_dimensions(self, sample_state_with_prompts):
        """Test that missing dimensions are filled with defaults."""
        response = json.dumps({
            "dimension_scores": [
                {"dimension": "Problem Framing", "feedback": "Good"}
                # Missing other 4 dimensions
            ],
            "analytics_summary": ["Test"],
            "overall_feedback": "Test feedback",
            "key_strengths": ["Test"],
            "areas_for_improvement": ["Test"]
        })
        sample_state_with_prompts.llm_response = response
        
        stage = SummaryValidateStage()
        result = await stage.run(sample_state_with_prompts)
        
        # All 5 dimensions should be present
        assert len(result.result["dimension_scores"]) == 5
    
    @pytest.mark.asyncio
    async def test_raises_on_invalid_json(self, sample_state_with_prompts):
        """Test that invalid JSON raises SummaryValidationError."""
        sample_state_with_prompts.llm_response = "not valid json"
        
        stage = SummaryValidateStage()
        
        with pytest.raises(SummaryValidationError, match="Invalid JSON"):
            await stage.run(sample_state_with_prompts)
    
    
    @pytest.mark.asyncio
    async def test_raises_without_llm_response(self, sample_summary_state):
        """Test that stage raises without llm_response."""
        stage = SummaryValidateStage()
        
        with pytest.raises(SummaryValidationError, match="LLM response is missing"):
            await stage.run(sample_summary_state)
    
    @pytest.mark.asyncio
    async def test_include_metadata(
        self, sample_state_with_prompts, valid_summary_llm_response
    ):
        """Test that result includes metadata."""
        sample_state_with_prompts.llm_response = valid_summary_llm_response
        
        stage = SummaryValidateStage()
        result = await stage.run(sample_state_with_prompts)
        
        # Verify metadata
        assert result.result["summary_id"] == sample_state_with_prompts.summary_id
        assert result.result["session_ids"] == sample_state_with_prompts.session_ids
        assert "model_info" in result.result
        assert "processing_time" in result.result
    
    @pytest.mark.asyncio
    async def test_stage_name(self):
        """Test stage name property."""
        stage = SummaryValidateStage()
        assert stage.name == "SummaryValidateStage"
    
    def test_factory_function(self):
        """Test factory function creates stage."""
        stage = create_summary_validate_stage()
        assert isinstance(stage, SummaryValidateStage)
