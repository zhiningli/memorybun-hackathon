import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from schemas.grading_state import GradingState, PipelineStage
from schemas.context import QuestionContext
from pipeline.prompt_build_stage import PromptBuildStage


@pytest.mark.asyncio
async def test_rubric_injection():
    """Test that rubric from context is correctly injected into the user prompt."""
    
    # Setup state with QuestionContext containing rubric
    context = QuestionContext(
        question_id=123,
        rubric={
            "dimensions": [
                {
                    "name": "Technical Correctness",
                    "weight": 0.5,
                    "description": "Is it correct?",
                    "example_criteria": "Correct approach"
                }
            ]
        },
        reference_answer={"text_answer": "Sample answer"},
        question={"title": "Test Question", "topics": ["Graph Plotting"]}
    )
    
    state = GradingState(
        session_id="test",
        transcription_text="answer",
        screenshot_key="key",
        stage=PipelineStage.CONTEXT_FETCH
    )
    state.context = context
    
    # Run stage
    stage = PromptBuildStage()
    new_state = await stage.run(state)
    
    # Verify rubric content in user prompt (via context.to_prompt())
    assert "Technical Correctness" in new_state.user_prompt
    assert "5.0 marks" in new_state.user_prompt  # 0.5 * 10
    assert "Is it correct?" in new_state.user_prompt


@pytest.mark.asyncio
async def test_no_rubric_when_no_context():
    """Test that prompt is generated even without rubric context."""
    
    state = GradingState(
        session_id="test",
        transcription_text="answer",
        screenshot_key="key",
        stage=PipelineStage.CONTEXT_FETCH
    )
    # No context set
    state.context = None
    
    stage = PromptBuildStage()
    new_state = await stage.run(state)
    
    # Generic prompt should still work
    assert new_state.system_prompt is not None
    assert "expert educational grader" in new_state.system_prompt
