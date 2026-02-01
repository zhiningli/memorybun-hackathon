"""
Pydantic schemas for Streaming Audio Transcription.

Business Logic:
- Frontend chunks audio into 30-second segments
- Sends chunks sequentially to backend
- Backend processes each chunk immediately with Whisper
- Results are concatenated in order
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict
from datetime import datetime
from enum import Enum


class WhisperModelEnum(str, Enum):
    """Available Whisper models"""
    TINY = "tiny"
    TINY_EN = "tiny.en"
    BASE = "base"
    BASE_EN = "base.en"
    SMALL = "small"
    SMALL_EN = "small.en"
    MEDIUM = "medium"
    MEDIUM_EN = "medium.en"


class TranscriptionSessionStatus(str, Enum):
    """Status of a transcription session"""
    ACTIVE = "active"           # Receiving chunks
    COMPLETED = "completed"     # All chunks processed
    EXPIRED = "expired"         # Session timed out


class CreateAudioTranscriptionSessionRequest(BaseModel):
    """Request to create a new transcription session"""
    model: WhisperModelEnum = Field(
        default=WhisperModelEnum.TINY,
        description="Whisper model to use for this session"
    )
    expected_duration: Optional[float] = Field(
        None,
        description="Expected total audio duration in seconds (for progress tracking)"
    )
    student_id: Optional[str] = Field(None, description="Student identifier")
    question_id: Optional[str] = Field(None, description="Question identifier")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "model": "tiny",
                "expected_duration": 180.0
            }
        }
    )


class TranscriptionSession(BaseModel):
    """Response when creating a session"""
    session_id: str = Field(..., description="Unique session identifier")
    model: WhisperModelEnum = Field(..., description="Model that will be used")
    status: TranscriptionSessionStatus = Field(..., description="Session status")
    created_at: datetime = Field(..., description="When session was created")
    student_id: Optional[str] = Field(None, description="Student identifier")
    question_id: Optional[str] = Field(None, description="Question identifier")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "session_id": "sess_abc123xyz",
                "model": "base",
                "status": "active",
                "created_at": "2025-11-18T14:00:00Z"
            }
        }
    )


class AudioTranscriptionChunkResult(BaseModel):
    """Result after processing a single chunk"""
    session_id: str = Field(..., description="Session identifier")
    chunk_index: int = Field(..., description="Index of this chunk (0-based)")
    chunk_text: str = Field(..., description="Transcribed text from this chunk")
    accumulated_text: str = Field(..., description="All transcribed text so far (concatenated)")
    chunks_processed: int = Field(..., description="Total number of chunks processed")
    processing_time: float = Field(..., description="Time taken to process this chunk (seconds)")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "session_id": "sess_abc123xyz",
                "chunk_index": 2,
                "chunk_text": "This is the third chunk of audio.",
                "accumulated_text": "Hello world. This is a test. This is the third chunk of audio.",
                "chunks_processed": 3,
                "processing_time": 0.8
            }
        }
    )


class AudioTranscriptionSessionResult(BaseModel):
    """Complete result for a transcription session"""
    session_id: str = Field(..., description="Session identifier")
    status: TranscriptionSessionStatus = Field(..., description="Session status")
    full_text: str = Field(..., description="Complete concatenated transcription")
    chunks_processed: int = Field(..., description="Total number of chunks processed")
    total_duration: Optional[float] = Field(None, description="Total audio duration in seconds")
    total_processing_time: float = Field(..., description="Total processing time in seconds")
    whisper_model: WhisperModelEnum = Field(..., description="Whisper model used for transcription")
    created_at: datetime = Field(..., description="When session was created")
    completed_at: Optional[datetime] = Field(None, description="When session was completed")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "session_id": "sess_abc123xyz",
                "status": "completed",
                "full_text": "Hello world. This is a test. This is the third chunk of audio.",
                "chunks_processed": 3,
                "total_duration": 30.0,
                "total_processing_time": 2.4,
                "whisper_model": "base",
                "created_at": "2025-11-18T14:00:00Z",
                "completed_at": "2025-11-18T14:00:03Z"
            }
        }
    )


# Internal data structure (not exposed via API)
class AudioTranscriptionSessionState(BaseModel):
    """
    Internal state for a transcription session.
    Stored in memory or Redis, not exposed to clients.
    """
    session_id: str
    model: WhisperModelEnum
    status: TranscriptionSessionStatus
    chunks: Dict[int, str] = Field(default_factory=dict)  # chunk_index -> chunk_audio_transcription_text
    chunk_durations: Dict[int, float] = Field(default_factory=dict)  # chunk_index -> duration_in_seconds
    created_at: datetime
    completed_at: Optional[datetime] = None
    last_activity_at: datetime
    total_processing_time: float = 0.0
    student_id: Optional[str] = None
    question_id: Optional[str] = None
    
    @property
    def accumulated_audio_transcription_text(self) -> str:
        """Get full concatenated chunk_audio_transcription_text in order"""
        # Sort by chunk index and join
        sorted_chunks = sorted(self.chunks.items())
        return " ".join(text for _, text in sorted_chunks)
    
    @property
    def chunks_processed(self) -> int:
        """Get number of chunks processed"""
        return len(self.chunks)

