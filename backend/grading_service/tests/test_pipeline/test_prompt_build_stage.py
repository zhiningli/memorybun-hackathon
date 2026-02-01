"""
Tests for PromptBuildStage.
"""

import pytest
from unittest.mock import AsyncMock

from schemas.grading_state import PipelineStage
from pipeline.prompt_build_stage import PromptBuildStage


class TestPromptBuildStage:
    """Tests for PromptBuildStage."""
    
    @pytest.mark.asyncio
    async def test_builds_prompts_with_context(self, sample_state, sample_context):
        """Test prompt building with full context."""
        sample_state.context = sample_context
        stage = PromptBuildStage()
        
        result = await stage.run(sample_state)
        
        # Verify prompts are set
        assert result.system_prompt is not None
        assert result.user_prompt is not None
        
        # Verify user prompt contains rubric info (from context.to_prompt())
        assert "Understanding" in result.user_prompt  # Dimension name
        assert "GRADING RUBRIC" in result.user_prompt  # Rubric header
        
        # Verify user prompt contains student answer
        assert "2x" in result.user_prompt
        assert "power rule" in result.user_prompt
        
        # Verify stage advanced
        assert result.stage == PipelineStage.PROMPT_BUILD
    
    @pytest.mark.asyncio
    async def test_builds_prompts_without_context(self, sample_state):
        """Test prompt building without context (uses defaults)."""
        sample_state.context = None
        stage = PromptBuildStage()
        
        result = await stage.run(sample_state)
        
        # Prompts should still be generated
        assert result.system_prompt is not None
        assert result.user_prompt is not None
        
        # Should contain JSON format instructions
        assert "JSON" in result.system_prompt
        assert "score" in result.system_prompt
    
    @pytest.mark.asyncio
    async def test_includes_screenshot_key(self, sample_state, sample_context):
        """Test that screenshot key is included in prompt."""
        sample_state.context = sample_context
        stage = PromptBuildStage()
        
        result = await stage.run(sample_state)
        
        assert sample_state.screenshot_key in result.user_prompt
    
    @pytest.mark.asyncio
    async def test_includes_reference_answer_when_present(self, sample_state, sample_context):
        """Test that reference answer is included when present."""
        sample_state.context = sample_context
        stage = PromptBuildStage()
        
        result = await stage.run(sample_state)
        
        # Reference answer is now included via context.to_prompt()
        assert "REFERENCE ANSWER" in result.user_prompt
        assert "power rule" in result.user_prompt
    
    @pytest.mark.asyncio
    async def test_stage_name(self):
        """Test stage name property."""
        stage = PromptBuildStage()
        assert stage.name == "PromptBuildStage"
