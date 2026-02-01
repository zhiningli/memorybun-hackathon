"""
Grading State Schema - Pipeline state for orchestrator.

Tracks state as grading task moves through pipeline stages.
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, Union
from datetime import datetime, timezone
from enum import Enum
from schemas.context import QuestionContext


class PipelineStage(str, Enum):
    """Stages in the grading pipeline."""
    TASK_DECODE = "task_decode"
    CONTEXT_FETCH = "context_fetch"
    PROMPT_BUILD = "prompt_build"
    LLM_GRADE = "llm_grade"
    VALIDATE = "validate"
    PERSIST = "persist"
    COMPLETED = "completed"
    FAILED = "failed"


class GradingState(BaseModel):
    """
    State object for grading pipeline.
    
    Passed through each stage of the orchestrator.
    Each stage reads/writes to this state.
    """
    # Input task data (from queue)
    session_id: str = Field(..., description="Session identifier")
    student_id: Optional[str] = Field(None, description="Student identifier")
    question_id: Optional[str] = Field(None, description="Question identifier")
    transcription_text: str = Field(..., description="Student's answer text")
    screenshot_key: str = Field(..., description="Key for screenshot (e.g. filename)")
    screenshot_data: Optional[bytes] = Field(
        None,
        description="Raw screenshot bytes (fetched by ContextFetchStage)"
    )
    audio_key: Optional[str] = Field(None, description="S3 URL for audio file (None for filesystem)")
    thinking_time: Optional[float] = Field(None, description="Time spent thinking (seconds)")
    speaking_time: Optional[float] = Field(None, description="Time spent speaking (seconds)")
    
    # Context (populated by ContextFetchStage)
    context: Optional[Union[QuestionContext, Dict[str, Any]]] = Field(
        None,
        description="Rubric, reference answer, and other context"
    )
    
    # Prompt (populated by PromptBuildStage)
    system_prompt: Optional[str] = Field(
        None,
        description="Assembled system prompt for LLM"
    )
    user_prompt: Optional[str] = Field(
        None,
        description="Assembled user prompt for LLM"
    )
    
    # LLM response (populated by LLMGradeStage)
    llm_response: Optional[str] = Field(
        None,
        description="Raw LLM response text"
    )
    
    # Parsed result (populated by ValidateStage)
    result: Optional[Dict[str, Any]] = Field(
        None,
        description="Parsed and validated grading result"
    )
    
    # State tracking
    stage: PipelineStage = Field(
        default=PipelineStage.TASK_DECODE,
        description="Current pipeline stage"
    )
    error: Optional[str] = Field(
        None,
        description="Error message if pipeline failed"
    )
    
    # Timing
    started_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When processing started"
    )
    
    @classmethod
    def from_task(cls, task_dict: Dict[str, Any]) -> "GradingState":
        """
        Create GradingState from a GradingTask dict.
        
        Args:
            task_dict: Dict with GradingTask fields
            
        Returns:
            New GradingState instance
        """
        return cls(
            session_id=task_dict["session_id"],
            student_id=task_dict.get("student_id"),
            question_id=task_dict.get("question_id"),
            transcription_text=task_dict["transcription_text"],
            screenshot_key=task_dict["screenshot_key"],
            audio_key=task_dict.get("audio_key"),  # Optional - None for filesystem mode
            thinking_time=task_dict.get("thinking_time"),
            speaking_time=task_dict.get("speaking_time"),
            stage=PipelineStage.TASK_DECODE
        )
    
    def fail(self, error: str) -> "GradingState":
        """
        Mark state as failed with error message.
        
        Args:
            error: Error message
            
        Returns:
            Self for chaining
        """
        self.stage = PipelineStage.FAILED
        self.error = error
        return self
    
    def advance_to(self, stage: PipelineStage) -> "GradingState":
        """
        Advance to next pipeline stage.
        
        Args:
            stage: Next stage
            
        Returns:
            Self for chaining
        """
        self.stage = stage
        return self
