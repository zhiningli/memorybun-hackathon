"""
Summary State Schema - Pipeline state for summary orchestrator.

Tracks state as summary task moves through pipeline stages.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from enum import Enum


class SummaryPipelineStage(str, Enum):
    """Stages in the summary pipeline."""
    TASK_DECODE = "task_decode"
    CONTEXT_FETCH = "context_fetch"      # Fetch all session results
    PROMPT_BUILD = "prompt_build"
    LLM_SUMMARIZE = "llm_summarize"
    VALIDATE = "validate"
    PERSIST = "persist"
    COMPLETED = "completed"
    FAILED = "failed"


class SummaryState(BaseModel):
    """
    State object for summary pipeline.
    
    Passed through each stage of the summary orchestrator.
    Each stage reads/writes to this state.
    """
    # Input task data (from queue)
    summary_id: str = Field(..., description="Summary identifier")
    session_ids: List[str] = Field(..., description="Session IDs to summarize")
    
    # Context (populated by SummaryContextFetchStage)
    session_results: Optional[List[Dict[str, Any]]] = Field(
        None,
        description="Grading results for each session (fetched from Redis)"
    )
    
    # Prompt (populated by SummaryPromptBuildStage)
    system_prompt: Optional[str] = Field(
        None,
        description="Assembled system prompt for LLM"
    )
    user_prompt: Optional[str] = Field(
        None,
        description="Assembled user prompt for LLM"
    )
    
    # LLM response (populated by LLMSummarizeStage)
    llm_response: Optional[str] = Field(
        None,
        description="Raw LLM response text"
    )
    
    # Parsed result (populated by SummaryValidateStage)
    result: Optional[Dict[str, Any]] = Field(
        None,
        description="Parsed and validated summary result"
    )
    
    # State tracking
    stage: SummaryPipelineStage = Field(
        default=SummaryPipelineStage.TASK_DECODE,
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
    def from_task(cls, task_dict: Dict[str, Any]) -> "SummaryState":
        """
        Create SummaryState from a SummaryTask dict.
        
        Args:
            task_dict: Dict with SummaryTask fields
            
        Returns:
            New SummaryState instance
        """
        return cls(
            summary_id=task_dict["summary_id"],
            session_ids=task_dict["session_ids"],
            # Pre-fetched session results (optional - can be fetched in pipeline)
            session_results=task_dict.get("session_results"),
            stage=SummaryPipelineStage.TASK_DECODE
        )
    
    def fail(self, error: str) -> "SummaryState":
        """
        Mark state as failed with error message.
        
        Args:
            error: Error message
            
        Returns:
            Self for chaining
        """
        self.stage = SummaryPipelineStage.FAILED
        self.error = error
        return self
    
    def advance_to(self, stage: SummaryPipelineStage) -> "SummaryState":
        """
        Advance to next pipeline stage.
        
        Args:
            stage: Next stage
            
        Returns:
            Self for chaining
        """
        self.stage = stage
        return self
