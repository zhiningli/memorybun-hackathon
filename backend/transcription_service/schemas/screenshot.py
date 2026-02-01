"""
Pydantic schemas for Screenshot Upload.

Defines schemas for screenshot upload requests and responses.
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from enum import Enum
from schemas.grading import GradingReadinessStatus


class ScreenshotUploadStatus(str, Enum):
    """Status of screenshot upload"""
    UPLOADED = "uploaded"  # Screenshot uploaded but waiting for transcription
    READY_FOR_GRADING = "ready_for_grading"  # Both screenshot and transcription ready, grading enqueued


class ScreenshotUploadResponse(BaseModel):
    """Response schema for screenshot upload"""
    session_id: str = Field(..., description="Session identifier")
    screenshot_key: str = Field(..., description="Key/Filename of the uploaded screenshot")
    status: ScreenshotUploadStatus = Field(..., description="Upload status")
    message: str = Field(..., description="Human-readable message")
    grading_readiness_status: Optional[GradingReadinessStatus] = Field(
        None,
        description="Current grading readiness status (for debugging/monitoring)"
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "session_id": "sess_abc123xyz",
                "screenshot_key": "sess_abc123xyz.png",
                "status": "ready_for_grading",
                "message": "Screenshot uploaded successfully. Grading task enqueued.",
                "grading_readiness_status": "enqueued"
            }
        }
    )
