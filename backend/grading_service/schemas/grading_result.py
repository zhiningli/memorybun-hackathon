"""
Grading Result Schema - Rich result model for grading output.

Includes detailed scoring breakdown, confidence, model info, and raw output
for auditing purposes.
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Dict, List
from datetime import datetime, timezone


class ScoreBreakdown(BaseModel):
    """Detailed scoring per rubric dimension."""
    dimension: str = Field(..., description="Name of the rubric dimension (e.g. Understanding, Logic)")
    percentage: float = Field(..., ge=0.0, le=1.0, description="Score percentage (0.0 to 1.0)")
    feedback: Optional[str] = Field(None, description="Specific feedback for this dimension")


class LLMGradingResponse(BaseModel):
    """
    Schema for the Structured Output from the LLM.
    Enforces the exact structure we expect the LLM to generate.
    """
    feedback: str = Field(..., description="Overall constructive feedback for the student")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score (0.0 to 1.0)")
    internal_notes: str = Field(..., description="Internal reasoning notes for the grade")
    score_breakdown: List[ScoreBreakdown] = Field(..., description="List of scores per dimension")


class ModelInfo(BaseModel):
    """Information about the LLM used for grading."""
    provider: str = Field(..., description="LLM provider (openai, anthropic, etc.)")
    model: str = Field(..., description="Model name/version")
    prompt_version: Optional[str] = Field(None, description="Version of grading prompt used")
    temperature: Optional[float] = Field(None, description="Temperature setting used")


class GradingResult(BaseModel):
    """
    Complete grading result from LLM processing.
    
    This schema is designed for:
    - Frontend display (score, feedback)
    - Auditing (model_info, raw_output, confidence)
    - Analytics (score_breakdown, processing_time)
    """
    # Core identification
    session_id: str = Field(..., description="Session identifier for correlation")
    
    score_breakdown: Optional[List[ScoreBreakdown]] = Field(
        None,
        description="Detailed scoring per rubric dimension"
    )
    
    # Feedback
    feedback: str = Field(..., description="Student-facing constructive feedback")
    internal_notes: Optional[str] = Field(
        None, 
        description="AI reasoning notes (not shown to student)"
    )
    
    # Quality metrics
    score: Optional[float] = Field(
        None,
        description="Overall score (0.0 to 1.0 or 0-100)"
    )
    confidence: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Model self-rating of confidence (0.0 to 1.0)"
    )
    
    # Audit trail
    model_info: Optional[ModelInfo] = Field(
        None,
        description="Information about LLM used for grading"
    )
    raw_output: Optional[str] = Field(
        None,
        description="Full raw JSON response from LLM (for debugging)"
    )
    
    # Timestamps
    completed_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When grading was completed"
    )
    processing_time: Optional[float] = Field(
        None,
        description="Time taken to process (seconds)"
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "session_id": "sess_abc123xyz",
                "score_breakdown": [
                    {"dimension": "Understanding", "feedback": "Good grasp"},
                    {"dimension": "Logic", "feedback": "Some gaps"}
                ],
                "feedback": "Good explanation of the concept.",
                "internal_notes": "Student showed understanding but made a sign error.",
                "confidence": 0.92,
                "model_info": {
                    "provider": "gemini",
                    "model": "gemini-2.0-flash"
                }
            }
        }
    )
