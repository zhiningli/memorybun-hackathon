"""
Summary Result Schema - Rich result model for summary output.

Combines multiple session grading results into a unified interview summary.
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime, timezone


class DimensionScore(BaseModel):
    """Feedback for a single rubric dimension in the summary."""
    dimension: str = Field(..., description="Dimension name (e.g., Problem Framing)")
    feedback: str = Field(..., description="Dimension-specific feedback")


class ModelInfo(BaseModel):
    """Information about the LLM used for summarization."""
    provider: str = Field(..., description="LLM provider (gemini, openai, etc.)")
    model: str = Field(..., description="Model name/version")
    prompt_version: Optional[str] = Field(None, description="Version of summary prompt used")
    temperature: Optional[float] = Field(None, description="Temperature setting used")


class SummaryLLMResponse(BaseModel):
    """
    Schema for the Structured Output from the LLM.
    Enforces the exact structure we expect the LLM to generate for summaries.
    """
    
    dimension_scores: List[DimensionScore] = Field(
        ..., 
        description="Score breakdown per dimension",
        min_length=5,
        max_length=5
    )
    
    analytics_summary: List[str] = Field(
        ...,
        description="Bullet points for analytics overview",
        min_length=3,
        max_length=7
    )
    
    overall_feedback: str = Field(
        ...,
        description="Paragraph-form overall feedback"
    )
    
    key_strengths: List[str] = Field(
        ...,
        description="Key strengths identified (one per dimension)",
        min_length=1
    )
    
    areas_for_improvement: List[str] = Field(
        ...,
        description="Areas for improvement (one per dimension)",
        min_length=1
    )


class SummaryResult(BaseModel):
    """
    Complete summary result from LLM processing.
    
    This schema is designed for:
    - Frontend display (scores, feedback, radar chart data)
    - Auditing (model_info)
    - Analytics (dimension_scores)
    """
    # Identification
    summary_id: str = Field(..., description="Summary identifier")
    session_ids: List[str] = Field(..., description="Session IDs included in summary")
    
    # Scores
    dimension_scores: List[DimensionScore] = Field(
        ...,
        description="Scores for each of the 5 fixed dimensions"
    )
    
    # Feedback sections
    analytics_summary: List[str] = Field(
        ...,
        description="Bullet points for the Analytics tab"
    )
    
    overall_feedback: str = Field(
        ...,
        description="Paragraph feedback for the Feedback tab"
    )
    
    key_strengths: List[str] = Field(
        ...,
        description="Key strengths list"
    )
    
    areas_for_improvement: List[str] = Field(
        ...,
        description="Areas for improvement list"
    )
    
    # Audit trail
    model_info: Optional[ModelInfo] = Field(
        None,
        description="Information about LLM used for summarization"
    )
    
    # Timestamps
    completed_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When summary was completed"
    )
    processing_time: Optional[float] = Field(
        None,
        description="Time taken to process (seconds)"
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "summary_id": "summ_abc123",
                "session_ids": ["sess_1", "sess_2", "sess_3"],
                "dimension_scores": [
                    {"dimension": "Problem Framing", "feedback": "Strong ability to identify core principles."},
                    {"dimension": "Solution Execution", "feedback": "Good approach with minor errors."},
                    {"dimension": "Technical Correctness", "feedback": "Solid understanding shown."},
                    {"dimension": "Communication & Whiteboard Use", "feedback": "Clear explanations with good visuals."},
                    {"dimension": "Time Management", "feedback": "Efficient pacing."}
                ],
                "analytics_summary": [
                    "Overall score: 71/100, placing in Top 15%",
                    "Highest scoring: Correctness",
                    "Lowest scoring: Time Management"
                ],
                "overall_feedback": "Solid technical performance with room for time management improvement.",
                "key_strengths": ["Strong theoretical understanding", "Clear communication"],
                "areas_for_improvement": ["Time management", "Axis scaling consistency"]
            }
        }
    )


# Fixed dimensions for the summary
SUMMARY_DIMENSIONS = [
    "Problem Framing",
    "Solution Execution",
    "Technical Correctness",
    "Communication & Whiteboard Use",
    "Time Management"
]
