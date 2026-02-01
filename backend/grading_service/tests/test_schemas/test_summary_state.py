"""
Tests for Summary State Schema.

Tests validation, state transitions, and factory methods.
"""

import pytest
from datetime import datetime, timezone
from schemas.summary_state import SummaryState, SummaryPipelineStage


class TestSummaryPipelineStage:
    """Tests for SummaryPipelineStage enum."""
    
    def test_all_stages_defined(self):
        """Test all expected stages are defined."""
        expected_stages = [
            "task_decode",
            "context_fetch",
            "prompt_build",
            "llm_summarize",
            "validate",
            "persist",
            "completed",
            "failed"
        ]
        actual_stages = [stage.value for stage in SummaryPipelineStage]
        assert set(actual_stages) == set(expected_stages)
    
    def test_stage_string_values(self):
        """Test that stages are string enums."""
        assert SummaryPipelineStage.TASK_DECODE == "task_decode"
        assert SummaryPipelineStage.COMPLETED == "completed"
        assert SummaryPipelineStage.FAILED == "failed"


class TestSummaryState:
    """Tests for SummaryState schema."""
    
    def test_valid_summary_state(self):
        """Test creating a valid summary state."""
        state = SummaryState(
            summary_id="summ_abc123",
            session_ids=["sess_1", "sess_2", "sess_3"]
        )
        assert state.summary_id == "summ_abc123"
        assert len(state.session_ids) == 3
        assert state.stage == SummaryPipelineStage.TASK_DECODE
        assert state.started_at is not None
    
    def test_from_task_factory(self):
        """Test creating state from task dict."""
        task_dict = {
            "summary_id": "summ_test",
            "session_ids": ["sess_1", "sess_2"],
            "session_results": [
                {"session_id": "sess_1", "score": 0.8},
                {"session_id": "sess_2", "score": 0.75}
            ]
        }
        
        state = SummaryState.from_task(task_dict)
        
        assert state.summary_id == "summ_test"
        assert len(state.session_ids) == 2
        assert len(state.session_results) == 2
        assert state.stage == SummaryPipelineStage.TASK_DECODE
    
    def test_from_task_without_results(self):
        """Test creating state from task without pre-fetched results."""
        task_dict = {
            "summary_id": "summ_test",
            "session_ids": ["sess_1"]
        }
        
        state = SummaryState.from_task(task_dict)
        
        assert state.summary_id == "summ_test"
        assert state.session_results is None
    
    def test_advance_to_stage(self):
        """Test advancing through pipeline stages."""
        state = SummaryState(
            summary_id="summ_test",
            session_ids=["sess_1"]
        )
        
        assert state.stage == SummaryPipelineStage.TASK_DECODE
        
        state.advance_to(SummaryPipelineStage.CONTEXT_FETCH)
        assert state.stage == SummaryPipelineStage.CONTEXT_FETCH
        
        state.advance_to(SummaryPipelineStage.PROMPT_BUILD)
        assert state.stage == SummaryPipelineStage.PROMPT_BUILD
        
        state.advance_to(SummaryPipelineStage.COMPLETED)
        assert state.stage == SummaryPipelineStage.COMPLETED
    
    def test_fail_state(self):
        """Test marking state as failed."""
        state = SummaryState(
            summary_id="summ_test",
            session_ids=["sess_1"]
        )
        
        state.fail("LLM API error")
        
        assert state.stage == SummaryPipelineStage.FAILED
        assert state.error == "LLM API error"
    
    def test_state_with_prompts(self):
        """Test state with prompts populated."""
        state = SummaryState(
            summary_id="summ_test",
            session_ids=["sess_1"],
            system_prompt="You are a grading assistant...",
            user_prompt="Summarize these sessions..."
        )
        
        assert state.system_prompt == "You are a grading assistant..."
        assert state.user_prompt == "Summarize these sessions..."
    
    def test_state_with_result(self):
        """Test state with parsed result."""
        state = SummaryState(
            summary_id="summ_test",
            session_ids=["sess_1"],
            result={
                "overall_score": 75,
                "key_strengths": ["Good understanding"]
            }
        )
        
        assert state.result["overall_score"] == 75
        assert "Good understanding" in state.result["key_strengths"]
    
    def test_method_chaining(self):
        """Test that methods return self for chaining."""
        state = SummaryState(
            summary_id="summ_test",
            session_ids=["sess_1"]
        )
        
        # advance_to returns self
        result = state.advance_to(SummaryPipelineStage.CONTEXT_FETCH)
        assert result is state
        
        # fail returns self
        result = state.fail("Error")
        assert result is state
