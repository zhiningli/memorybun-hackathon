"""
Tests for SummaryPromptBuildStage.
"""

import pytest
from unittest.mock import patch

from schemas.summary_state import SummaryPipelineStage
from schemas.summary_result import SUMMARY_DIMENSIONS
from pipeline.summary.summary_prompt_build_stage import (
    SummaryPromptBuildStage,
    create_summary_prompt_build_stage
)


class TestSummaryPromptBuildStage:
    """Tests for SummaryPromptBuildStage."""
    
    @pytest.mark.asyncio
    async def test_builds_prompts(self, sample_state_with_results):
        """Test that prompts are built from session results."""
        stage = SummaryPromptBuildStage()
        result = await stage.run(sample_state_with_results)
        
        # Verify prompts are populated
        assert result.system_prompt is not None
        assert result.user_prompt is not None
        assert len(result.system_prompt) > 0
        assert len(result.user_prompt) > 0
        
        # Verify stage advanced
        assert result.stage == SummaryPipelineStage.PROMPT_BUILD
    
    @pytest.mark.asyncio
    async def test_user_prompt_contains_session_ids(self, sample_state_with_results):
        """Test that user prompt contains session IDs."""
        stage = SummaryPromptBuildStage()
        result = await stage.run(sample_state_with_results)
        
        # Verify session IDs appear in prompt
        for session_id in sample_state_with_results.session_ids:
            assert session_id in result.user_prompt
    
    @pytest.mark.asyncio
    async def test_user_prompt_contains_dimensions(self, sample_state_with_results):
        """Test that user prompt contains required dimensions."""
        stage = SummaryPromptBuildStage()
        result = await stage.run(sample_state_with_results)
        
        # Verify dimensions are mentioned
        for dimension in SUMMARY_DIMENSIONS:
            assert dimension in result.user_prompt
    

    
    @pytest.mark.asyncio
    async def test_raises_without_session_results(self, sample_summary_state):
        """Test that stage raises without session results."""
        stage = SummaryPromptBuildStage()
        
        with pytest.raises(ValueError, match="session_results must be populated"):
            await stage.run(sample_summary_state)
    
    @pytest.mark.asyncio
    async def test_stage_name(self):
        """Test stage name property."""
        stage = SummaryPromptBuildStage()
        assert stage.name == "SummaryPromptBuildStage"
    
    def test_factory_function(self):
        """Test factory function creates stage."""
        stage = create_summary_prompt_build_stage()
        assert isinstance(stage, SummaryPromptBuildStage)
