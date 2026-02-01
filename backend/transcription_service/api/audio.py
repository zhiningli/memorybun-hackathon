"""
Audio Transcription API Routes

Handles streaming transcription from Chrome MediaRecorder API:
1. Upload WebM/Opus chunks sequentially (queued for async processing)
2. Check chunk status

Audio Format: WebM with Opus codec (Chrome MediaRecorder API native output)
"""

import os
import tempfile
from pathlib import Path
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends, Body, Request, Response
from schemas.viewer_context import ViewerContext
from services.audio_transcription_service import AudioTranscriptionService
from api.dependencies import get_viewer_context, get_audio_transcription_service
from schemas.transcription import AudioTranscriptionSessionResult
from pydantic import BaseModel, Field
from typing import Optional
from middleware.rate_limiter import limiter

# The route prefix will be handled when including this router in the main router
# Expected paths:
# POST /session/{session_id}/audio/chunk
# GET /session/{session_id}/audio/chunk/{chunk_index}/status

router = APIRouter()

# Supported audio formats - Chrome MediaRecorder API output
ALLOWED_AUDIO_FORMATS = {
    "audio/webm",  # WebM with Opus (Chrome MediaRecorder default)
    "video/webm",  # WebM container is often identified as video even if audio-only
    "audio/webm;codecs=opus",  # WebM with Opus codec
}

ALLOWED_EXTENSIONS = {".webm"}

MAX_AUDIO_SIZE = 10 * 1024 * 1024  # 10 MB limit


def validate_audio_file(file: UploadFile) -> None:
    """
    Validate uploaded audio file.
    Only accepts WebM with Opus format (Chrome MediaRecorder API output).
    """
    # Check content type
    if file.content_type not in ALLOWED_AUDIO_FORMATS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported audio format: {file.content_type}. "
                   f"Only WebM with Opus (audio/webm) is supported. "
                   f"This format is the native output from Chrome's MediaRecorder API."
        )
    
    # Check file extension
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file extension: {file_ext}. "
                   f"Only .webm files are supported (Chrome MediaRecorder API output)."
        )


@router.post("/session/{session_id}/audio/chunk")
@limiter.limit("100/minute")
async def upload_audio_chunk(
    request: Request,
    response: Response,
    session_id: str,
    chunk_index: int = Form(..., description="0-based index of this chunk"),
    audio_file: UploadFile = File(..., description="Audio chunk file (30 seconds, WebM/Opus format)"),
    viewer_context: ViewerContext = Depends(get_viewer_context),
    audio_transcription_service: AudioTranscriptionService = Depends(get_audio_transcription_service)
):
    """
    Upload audio chunk and enqueue for async processing.
    Returns immediately with task_id (non-blocking).
    
    Process flow:
    1. Frontend chunks audio into 30-second segments using Chrome MediaRecorder API
    2. Sends each chunk with sequential chunk_index (0, 1, 2, ...) as WebM/Opus
    3. Backend enqueues chunk for async processing by background workers
    4. Returns task_id immediately
    5. Use GET /session/{session_id}/audio/chunk/{chunk_index}/status to check status
    6. Use GET /session/{session_id} to get accumulated transcription
    
    Audio Format:
    - Only WebM with Opus codec is supported (Chrome MediaRecorder API default output)
    - Content-Type must be "audio/webm"
    - File extension must be ".webm"
    
    Response:
    - task_id: Use this to check processing status
    - status: "queued" (chunk is in queue waiting for processing)
    """
    # Validate audio file
    validate_audio_file(audio_file)
    
    # Save uploaded file to temp location
    # Note: We don't delete this immediately - the worker will delete it after processing
    with tempfile.NamedTemporaryFile(
        delete=False,
        suffix=Path(audio_file.filename).suffix
    ) as temp_file:
        # Write uploaded content to temp file
        size = 0
        while True:
            chunk = await audio_file.read(1024 * 1024)  # Read 1MB chunks
            if not chunk:
                break
            size += len(chunk)
            if size > MAX_AUDIO_SIZE:
                raise HTTPException(
                    status_code=413,
                    detail=f"Audio file too large. Maximum size is {MAX_AUDIO_SIZE // (1024 * 1024)}MB."
                )
            temp_file.write(chunk)
        temp_file_path = Path(temp_file.name)
    
    try:
        # Enqueue for processing (non-blocking)
        task_id = await audio_transcription_service.gen_enqueue_chunk(
            session_id=session_id,
            chunk_index=chunk_index,
            audio_file_path=temp_file_path
        )
        
        return {
            "task_id": task_id,
            "session_id": session_id,
            "chunk_index": chunk_index,
            "status": "queued",
            "message": "Chunk queued for processing. Use GET /session/{session_id}/audio/chunk/{chunk_index}/status to check status."
        }
        
    except ValueError as e:
        # Clean up temp file if session validation failed
        try:
            os.unlink(temp_file_path)
        except Exception:
            pass
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        # Clean up temp file on any other error
        try:
            os.unlink(temp_file_path)
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=f"Error enqueueing chunk: {str(e)}")


@router.get("/session/{session_id}/audio/chunk/{chunk_index}/status")
@limiter.limit("60/minute")
async def get_chunk_status(
    request: Request,
    response: Response,
    session_id: str,
    chunk_index: int,
    viewer_context: ViewerContext = Depends(get_viewer_context),
    audio_transcription_service: AudioTranscriptionService = Depends(get_audio_transcription_service)
):
    """
    Get processing status of a chunk.
    
    Returns:
    - status: "pending", "processing", "completed", or "failed"
    - result: Transcribed text (if completed)
    - error: Error message (if failed)
    - timestamps: created_at, started_at, completed_at
    """
    status = await audio_transcription_service.gen_get_chunk_status(
        session_id, chunk_index
    )
    
    if not status:
        raise HTTPException(
            status_code=404,
            detail=f"Chunk {chunk_index} not found for session {session_id}"
        )
    
    return status


@router.get("/session/{session_id}/audio", response_model=AudioTranscriptionSessionResult)
@limiter.limit("60/minute")
async def get_session_result(
    request: Request,
    response: Response,
    session_id: str,
    viewer_context: ViewerContext = Depends(get_viewer_context),
    audio_transcription_service: AudioTranscriptionService = Depends(get_audio_transcription_service)
):
    """
    Get current transcription result for a session.
    Can be called at any time to retrieve accumulated text.
    """
    result = await audio_transcription_service.gen_get_session_result(session_id)
    
    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"Session {session_id} not found"
        )
    
    return result


class FinalizeSessionRequest(BaseModel):
    """Request body for finalizing a session"""
    thinking_time: Optional[float] = Field(None, description="Time spent thinking in seconds")


@router.post("/session/{session_id}/audio/finalize", response_model=AudioTranscriptionSessionResult)
@limiter.limit("20/minute")
async def finalize_session(
    request: Request,
    response: Response,
    session_id: str,
    body: FinalizeSessionRequest = Body(default_factory=FinalizeSessionRequest),
    viewer_context: ViewerContext = Depends(get_viewer_context),
    audio_transcription_service: AudioTranscriptionService = Depends(get_audio_transcription_service)
):
    """
    Finalize a transcription session.
    Call this after all chunks have been uploaded.
    
    Marks session as completed and returns final result.
    """
    result = await audio_transcription_service.gen_finalize_session(
        session_id,
        thinking_time=body.thinking_time
    )
    
    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"Session {session_id} not found"
        )
    
    return result
