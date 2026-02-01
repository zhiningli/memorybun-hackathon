"""
Tests for ValidateStage.
"""

import pytest
import json
from unittest.mock import AsyncMock

from schemas.grading_state import PipelineStage
from pipeline.validate_stage import ValidateStage, ValidationError


class TestValidateStage:
    """Tests for ValidateStage."""
    
    @pytest.mark.asyncio
    async def test_validates_valid_response(self, sample_state, valid_llm_response):
        """Test validation of a valid LLM response."""
        sample_state.llm_response = valid_llm_response
        sample_state.stage = PipelineStage.LLM_GRADE
        
        stage = ValidateStage()
        result = await stage.run(sample_state)
        
        # Verify result is populated
        assert result.result is not None
        assert result.result["session_id"] == "test_sess_123"
        assert "Good understanding" in result.result["feedback"]
        assert result.result["confidence"] == 0.92
        
        # Verify stage advanced
        assert result.stage == PipelineStage.VALIDATE
    
    
    @pytest.mark.asyncio
    async def test_raises_error_for_missing_feedback(self, sample_state):
        """Test that missing feedback raises error."""
        sample_state.llm_response = json.dumps({
            "confidence": 0.9
        })
        
        stage = ValidateStage()
        with pytest.raises(ValidationError, match="Feedback is missing"):
            await stage.run(sample_state)
    
    @pytest.mark.asyncio
    async def test_raises_error_for_short_feedback(self, sample_state):
        """Test that too-short feedback raises error."""
        sample_state.llm_response = json.dumps({
            "feedback": "Short",  # Too short
            "confidence": 0.9
        })
        
        stage = ValidateStage()
        with pytest.raises(ValidationError, match="Feedback too short"):
            await stage.run(sample_state)
    
    @pytest.mark.asyncio
    async def test_raises_error_for_invalid_json(self, sample_state):
        """Test that invalid JSON raises error."""
        sample_state.llm_response = "not valid json"
        
        stage = ValidateStage()
        with pytest.raises(ValidationError, match="Invalid JSON"):
            await stage.run(sample_state)
    
    @pytest.mark.asyncio
    async def test_raises_error_without_llm_response(self, sample_state):
        """Test that missing LLM response raises error."""
        sample_state.llm_response = None
        
        stage = ValidateStage()
        with pytest.raises(ValidationError, match="LLM response is missing"):
            await stage.run(sample_state)
    
    @pytest.mark.asyncio
    async def test_validates_score_breakdown(self, sample_state, valid_llm_response):
        """Test that score breakdown is validated."""
        sample_state.llm_response = valid_llm_response
        
        stage = ValidateStage()
        result = await stage.run(sample_state)
        
        breakdown = result.result.get("score_breakdown")
        assert breakdown is not None
        assert len(breakdown) == 3
        assert breakdown[0]["dimension"] == "Understanding"
    
    @pytest.mark.asyncio
    async def test_includes_model_info(self, sample_state, valid_llm_response):
        """Test that model info is included in result."""
        sample_state.llm_response = valid_llm_response
        
        stage = ValidateStage()
        result = await stage.run(sample_state)
        
        model_info = result.result.get("model_info")
        assert model_info is not None
        assert "provider" in model_info
        assert "model" in model_info
    
    @pytest.mark.asyncio
    async def test_calculates_processing_time(self, sample_state, valid_llm_response):
        """Test that processing time is calculated."""
        sample_state.llm_response = valid_llm_response
        
        stage = ValidateStage()
        result = await stage.run(sample_state)
        
        processing_time = result.result.get("processing_time")
        assert processing_time is not None
        assert processing_time >= 0
    
    @pytest.mark.asyncio
    async def test_stage_name(self):
        """Test stage name property."""
        stage = ValidateStage()
        assert stage.name == "ValidateStage"
