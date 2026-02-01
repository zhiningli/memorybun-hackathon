"""
Pydantic schemas for Grading Queue.

Defines schemas for grading tasks that are enqueued in Redis
and processed by the grading service.
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime, timezone
from enum import Enum


class GradingStatus(str, Enum):
    """Status of a grading task (after it's been enqueued)"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class TranscriptionStatus(str, Enum):
    """Status of transcription processing"""
    PENDING = "pending"
    COMPLETED = "completed"


class ScreenshotStatus(str, Enum):
    """Status of screenshot upload"""
    PENDING = "pending"
    COMPLETED = "completed"


class GradingReadinessStatus(str, Enum):
    """
    Status of grading readiness (before task is enqueued).
    
    Tracks whether transcription and screenshot are ready for grading.
    """
    WAITING_FOR_SCREENSHOT = "waiting_for_screenshot"
    WAITING_FOR_AUDIO = "waiting_for_audio"
    READY = "ready"
    ENQUEUED = "enqueued"


class GradingTask(BaseModel):
    """
    Represents a grading task in the queue.
    
    This task is serialized to JSON and stored in Redis queue.
    """
    session_id: str = Field(..., description="Session identifier")
    student_id: Optional[str] = Field(None, description="Student identifier")
    question_id: Optional[str] = Field(None, description="Question identifier")
    transcription_text: str = Field(..., description="Student's answer text (transcription)")
    screenshot_key: str = Field(..., description="Key/Filename of the screenshot image (e.g. sess_123.png)")
    audio_key: Optional[str] = Field(None, description="S3 URL of the audio file (None for filesystem storage)")
    thinking_time: Optional[float] = Field(None, description="Time spent thinking (seconds)")
    speaking_time: Optional[float] = Field(None, description="Time spent speaking (seconds)")
    correlation_id: Optional[str] = Field(None, description="Correlation ID for distributed tracing")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="When task was created")
    retry_count: int = Field(default=0, description="Number of times this task has been retried")
    max_retries: int = Field(default=3, description="Maximum number of retries allowed")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "session_id": "sess_abc123xyz",
                "student_id": "student_123",
                "question_id": "q_456",
                "transcription_text": "The student explained the concept clearly...",
                "screenshot_key": "sess_abc123xyz.png",
                "created_at": "2025-01-18T14:00:00Z",
                "retry_count": 0,
                "max_retries": 3
            }
        }
    )


class GradingResult(BaseModel):
    """
    Result of a grading task (used by grading service).
    
    This is stored after LLM processing completes.
    """
    session_id: str = Field(..., description="Session identifier")
    grade: float = Field(..., ge=0.0, le=1.0, description="Grade from 0.0 to 1.0")
    feedback: str = Field(..., description="Feedback text from LLM")
    completed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="When grading was completed")
    processing_time: Optional[float] = Field(None, description="Time taken to process (seconds)")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "session_id": "sess_abc123xyz",
                "grade": 0.85,
                "feedback": "Good explanation of the concept. Consider adding more examples.",
                "completed_at": "2025-01-18T14:05:00Z",
                "processing_time": 2.3
            }
        }
    )

