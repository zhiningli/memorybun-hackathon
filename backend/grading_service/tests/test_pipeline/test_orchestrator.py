"""
Tests for Orchestrator and end-to-end pipeline flow.
"""

import pytest
import json
from unittest.mock import AsyncMock

from schemas.grading_state import PipelineStage
from pipeline.orchestrator import Orchestrator, create_orchestrator
from pipeline.context_fetch_stage import ContextFetchStage
from pipeline.prompt_build_stage import PromptBuildStage
from pipeline.llm_grade_stage import LLMGradeStage
from pipeline.validate_stage import ValidateStage
from pipeline.persist_stage import PersistStage


class TestOrchestrator:
    """Tests for Orchestrator."""
    
    @pytest.mark.asyncio
    async def test_run_pipeline_from_dict(self, sample_context, valid_llm_response):
        """Test running full pipeline from task dict."""
        # Mock store for persist stage
        mock_store = AsyncMock()
        mock_store.store_result = AsyncMock(return_value=True)
        
        # Mock provider for context stage
        mock_provider = AsyncMock()
        mock_provider.gen_question_context = AsyncMock(return_value=sample_context)
        
        # Create orchestrator with custom stages
        stages = [
            ContextFetchStage(provider=mock_provider),
            PromptBuildStage(),
            LLMGradeStage(mock_response=valid_llm_response),
            ValidateStage(),
            PersistStage(store=mock_store),
        ]
        orchestrator = Orchestrator(stages=stages)
        
        # Task data
        task_dict = {
            "session_id": "test_sess_123",
            "student_id": "student_456",
            "question_id": "789",  # String type
            "transcription_text": "The answer is 2x by power rule.",
            "screenshot_key": "test.png"
        }
        
        # Run pipeline
        final_state = await orchestrator.run_pipeline(task_dict)
        
        # Verify completed
        assert final_state.stage == PipelineStage.COMPLETED
        assert final_state.result is not None
        assert "Good understanding" in final_state.result["feedback"]
    
    @pytest.mark.asyncio
    async def test_run_pipeline_from_json(self, sample_context, valid_llm_response):
        """Test running pipeline from JSON string."""
        mock_store = AsyncMock()
        mock_store.store_result = AsyncMock(return_value=True)
        
        mock_provider = AsyncMock()
        mock_provider.gen_question_context = AsyncMock(return_value=sample_context)
        
        stages = [
            ContextFetchStage(provider=mock_provider),
            PromptBuildStage(),
            LLMGradeStage(mock_response=valid_llm_response),
            ValidateStage(),
            PersistStage(store=mock_store),
        ]
        orchestrator = Orchestrator(stages=stages)
        
        task_json = json.dumps({
            "session_id": "test_sess_json",
            "transcription_text": "Test answer",
            "screenshot_key": "test.png"
        })
        
        final_state = await orchestrator.run_pipeline(task_json)
        
        assert final_state.stage == PipelineStage.COMPLETED
    
    @pytest.mark.asyncio
    async def test_run_from_state(self, sample_state, sample_context, valid_llm_response):
        """Test running pipeline from existing state."""
        mock_store = AsyncMock()
        mock_store.store_result = AsyncMock(return_value=True)
        
        mock_provider = AsyncMock()
        mock_provider.gen_question_context = AsyncMock(return_value=sample_context)
        
        stages = [
            ContextFetchStage(provider=mock_provider),
            PromptBuildStage(),
            LLMGradeStage(mock_response=valid_llm_response),
            ValidateStage(),
            PersistStage(store=mock_store),
        ]
        orchestrator = Orchestrator(stages=stages)
        
        final_state = await orchestrator.run_from_state(sample_state)
        
        assert final_state.stage == PipelineStage.COMPLETED
        assert "Good understanding" in final_state.result["feedback"]
    
    def test_default_stages(self):
        """Test that default stages are created."""
        orchestrator = Orchestrator()
        
        assert len(orchestrator.stages) == 5
        stage_names = [s.name for s in orchestrator.stages]
        assert "ContextFetchStage" in stage_names
        assert "PromptBuildStage" in stage_names
        assert "LLMGradeStage" in stage_names
        assert "ValidateStage" in stage_names
        assert "PersistStage" in stage_names
    
    def test_factory_function(self):
        """Test factory function creates orchestrator."""
        orchestrator = create_orchestrator()
        assert isinstance(orchestrator, Orchestrator)


class TestPipelineIntegration:
    """Integration tests for manual pipeline stages flow."""
    
    @pytest.mark.asyncio
    async def test_manual_pipeline_flow(self, sample_state, sample_context, valid_llm_response):
        """Test running stages manually in sequence."""
        # Stage 1: Context Fetch
        mock_provider = AsyncMock()
        mock_provider.gen_question_context = AsyncMock(return_value=sample_context)
        context_stage = ContextFetchStage(provider=mock_provider)
        sample_state = await context_stage.run(sample_state)
        assert sample_state.stage == PipelineStage.CONTEXT_FETCH
        
        # Stage 2: Prompt Build
        prompt_stage = PromptBuildStage()
        sample_state = await prompt_stage.run(sample_state)
        assert sample_state.stage == PipelineStage.PROMPT_BUILD
        
        # Stage 3: LLM Grade
        llm_stage = LLMGradeStage(mock_response=valid_llm_response)
        sample_state = await llm_stage.run(sample_state)
        assert sample_state.stage == PipelineStage.LLM_GRADE
        
        # Stage 4: Validate
        validate_stage = ValidateStage()
        sample_state = await validate_stage.run(sample_state)
        assert sample_state.stage == PipelineStage.VALIDATE
        
        # Final verification
        assert sample_state.result is not None
        assert "Good understanding" in sample_state.result["feedback"]
