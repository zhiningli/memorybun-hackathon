"""
Audio Transcription API Routes

Handles streaming transcription from Chrome MediaRecorder API:
1. Create session
2. Upload WebM/Opus chunks sequentially (queued for async processing)
3. Check chunk status
4. Get accumulated results
5. Finalize session

Audio Format: WebM with Opus codec (Chrome MediaRecorder API native output)

Note: Chunks are processed asynchronously by background workers.
The upload endpoint returns immediately with a task_id.
Use the status endpoint to check processing status.
"""

from fastapi import APIRouter, HTTPException, Depends, Request, Response
from schemas.transcription import (
    CreateAudioTranscriptionSessionRequest,
    TranscriptionSession,
)
from schemas.viewer_context import ViewerContext
from services.audio_transcription_service import AudioTranscriptionService
from api.dependencies import get_viewer_context, get_audio_transcription_service
from api.audio import router as audio_router
from api.screenshot import router as screenshot_router
from middleware.rate_limiter import limiter

router = APIRouter(prefix="/api/v1/transcribe", tags=["Audio Transcription"])

# Include sub-routers
router.include_router(audio_router)
router.include_router(screenshot_router)


@router.post("/session", response_model=TranscriptionSession)
@limiter.limit("20/minute")
async def create_transcription_session(
    request: Request,
    response: Response,
    body: CreateAudioTranscriptionSessionRequest,
    viewer_context: ViewerContext = Depends(get_viewer_context),
    audio_transcription_service: AudioTranscriptionService = Depends(get_audio_transcription_service)
):
    """
    Create a new transcription session.
    Call this before sending audio chunks.
    
    Returns session_id to use for subsequent chunk uploads.
    """
    # TODO: Add authorization check if needed
    # For now, allow all authenticated users
    
    session = await audio_transcription_service.gen_create_session(body)
    return session





@router.delete("/session/{session_id}")
@limiter.limit("20/minute")
async def delete_session(
    request: Request,
    response: Response,
    session_id: str,
    viewer_context: ViewerContext = Depends(get_viewer_context),
    audio_transcription_service: AudioTranscriptionService = Depends(get_audio_transcription_service)
):
    """
    Delete a transcription session and free up resources.
    Call this after retrieving final results.
    """
    deleted = await audio_transcription_service.gen_delete_session(session_id)
    
    if not deleted:
        raise HTTPException(
            status_code=404,
            detail=f"Session {session_id} not found"
        )
    
    return {"message": f"Session {session_id} deleted successfully"}


@router.get("/debug/queue-status")
@limiter.limit("30/minute")
async def get_queue_status(
    request: Request,
    response: Response,
    viewer_context: ViewerContext = Depends(get_viewer_context)
):
    """
    Debug endpoint to check queue and worker status.
    """
    from services.transcription_queue import transcription_queue
    from services.transcription_worker import transcription_worker
    
    # Get queue size
    queue_size = transcription_queue._queue.qsize()
    
    # Get worker status
    worker_status = {
        "running": transcription_worker._running,
        "num_workers": transcription_worker.num_workers,
        "active_workers": len([w for w in transcription_worker._workers if not w.done()]) if transcription_worker._workers else 0
    }
    
    # Get pending tasks
    pending_tasks = [
        {
            "task_id": task_id,
            "session_id": task.session_id,
            "chunk_index": task.chunk_index,
            "status": task.status.value,
            "created_at": task.created_at.isoformat() if task.created_at else None
        }
        for task_id, task in transcription_queue._tasks.items()
        if task.status.value in ["pending", "processing"]
    ]
    
    return {
        "queue_size": queue_size,
        "worker_status": worker_status,
        "pending_tasks": pending_tasks,
        "total_tasks": len(transcription_queue._tasks)
    }


@router.get("/device-info")
@limiter.limit("30/minute")
async def get_device_info(
    request: Request,
    response: Response,
    viewer_context: ViewerContext = Depends(get_viewer_context),
    audio_transcription_service: AudioTranscriptionService = Depends(get_audio_transcription_service)
):
    """
    Get information about the compute device being used (CPU/GPU).
    Useful for debugging and monitoring.
    """
    # TODO: Restrict to admin users only
    return audio_transcription_service.get_device_info()

