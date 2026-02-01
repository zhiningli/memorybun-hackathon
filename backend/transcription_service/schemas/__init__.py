"""
Schemas package - Pydantic models for validation

This package contains all Pydantic schemas used for:
- Request validation
- Response serialization
- Data contracts
"""
from schemas.transcription import (
    WhisperModelEnum,
    TranscriptionSessionStatus,
    CreateAudioTranscriptionSessionRequest,
    TranscriptionSession,
    AudioTranscriptionChunkResult,
    AudioTranscriptionSessionResult,
    AudioTranscriptionSessionState
)
from schemas.viewer_context import ViewerContext
from schemas.grading import (
    GradingTask,
    GradingResult,
    GradingStatus,
    GradingReadinessStatus,
    TranscriptionStatus,
    ScreenshotStatus
)
from schemas.screenshot import (
    ScreenshotUploadStatus,
    ScreenshotUploadResponse
)

__all__ = [
    "WhisperModelEnum",
    "TranscriptionSessionStatus",
    "CreateAudioTranscriptionSessionRequest",
    "TranscriptionSession",
    "AudioTranscriptionChunkResult",
    "AudioTranscriptionSessionResult",
    "AudioTranscriptionSessionState",
    "ViewerContext",
    "GradingTask",
    "GradingResult",
    "GradingStatus",
    "GradingReadinessStatus",
    "TranscriptionStatus",
    "ScreenshotStatus",
    "ScreenshotUploadStatus",
    "ScreenshotUploadResponse",
]

