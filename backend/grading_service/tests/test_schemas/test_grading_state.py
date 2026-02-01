"""
Tests for Grading State Schema.

Tests pipeline state transitions and helper methods.
"""

import pytest
from datetime import datetime, timezone
from schemas.grading_state import GradingState, PipelineStage


class TestPipelineStage:
    """Tests for PipelineStage enum."""
    
    def test_stage_values(self):
        """Test that all expected stages exist."""
        assert PipelineStage.TASK_DECODE.value == "task_decode"
        assert PipelineStage.CONTEXT_FETCH.value == "context_fetch"
        assert PipelineStage.PROMPT_BUILD.value == "prompt_build"
        assert PipelineStage.LLM_GRADE.value == "llm_grade"
        assert PipelineStage.VALIDATE.value == "validate"
        assert PipelineStage.PERSIST.value == "persist"
        assert PipelineStage.COMPLETED.value == "completed"
        assert PipelineStage.FAILED.value == "failed"


class TestGradingState:
    """Tests for GradingState schema."""
    
    def test_create_minimal_state(self):
        """Test creating state with minimal required fields."""
        state = GradingState(
            session_id="sess_abc123",
            transcription_text="The answer is 42",
            screenshot_key="test.png"
        )
        assert state.session_id == "sess_abc123"
        assert state.transcription_text == "The answer is 42"
        assert state.stage == PipelineStage.TASK_DECODE
        assert state.error is None
    
    def test_create_full_state(self):
        """Test creating state with all fields."""
        state = GradingState(
            session_id="sess_abc123",
            student_id="student_456",
            question_id="q_789",
            transcription_text="The answer is 42",
            screenshot_key="test.png",
            context={"rubric": {"total_marks": 10}},
            system_prompt="You are a grader",
            user_prompt="Grade this answer",
            llm_response='{"score": 0.85}',
            result={"score": 0.85, "feedback": "Good"}
        )
        assert state.student_id == "student_456"
        assert state.context["rubric"]["total_marks"] == 10
    
    def test_from_task(self):
        """Test creating state from task dict."""
        task_dict = {
            "session_id": "sess_abc123",
            "student_id": "student_456",
            "question_id": "q_789",
            "transcription_text": "The answer is 42",
            "screenshot_key": "test.png"
        }
        
        state = GradingState.from_task(task_dict)
        
        assert state.session_id == "sess_abc123"
        assert state.student_id == "student_456"
        assert state.question_id == "q_789"
        assert state.transcription_text == "The answer is 42"
        assert state.stage == PipelineStage.TASK_DECODE
    
    def test_fail_method(self):
        """Test failing a state."""
        state = GradingState(
            session_id="sess_abc123",
            transcription_text="Test",
            screenshot_key="test.png"
        )
        
        state.fail("LLM call failed")
        
        assert state.stage == PipelineStage.FAILED
        assert state.error == "LLM call failed"
    
    def test_advance_to(self):
        """Test advancing through pipeline stages."""
        state = GradingState(
            session_id="sess_abc123",
            transcription_text="Test",
            screenshot_key="test.png"
        )
        
        assert state.stage == PipelineStage.TASK_DECODE
        
        state.advance_to(PipelineStage.CONTEXT_FETCH)
        assert state.stage == PipelineStage.CONTEXT_FETCH
        
        state.advance_to(PipelineStage.PROMPT_BUILD)
        assert state.stage == PipelineStage.PROMPT_BUILD
        
        state.advance_to(PipelineStage.COMPLETED)
        assert state.stage == PipelineStage.COMPLETED
    
    def test_method_chaining(self):
        """Test that fail and advance_to return self."""
        state = GradingState(
            session_id="sess_abc123",
            transcription_text="Test",
            screenshot_key="test.png"
        )
        
        # advance_to returns self
        result = state.advance_to(PipelineStage.CONTEXT_FETCH)
        assert result is state
        
        # fail returns self
        result = state.fail("Error")
        assert result is state
    
    def test_started_at_auto_set(self):
        """Test that started_at is automatically set."""
        state = GradingState(
            session_id="sess_abc123",
            transcription_text="Test",
            screenshot_key="test.png"
        )
        
        assert state.started_at is not None
        assert isinstance(state.started_at, datetime)
