"""
Grading Service API Routes.

Provides endpoints for:
- Grading status polling (frontend)
- Queue monitoring (debug/admin)
- Debug endpoint to manually trigger grading
"""

import json
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Request
from typing import Optional, List
from pydantic import BaseModel, Field

from services.result_store import result_store
from services.redis_client import get_redis_client
from services.grading_worker import grading_worker
from pipeline.orchestrator import Orchestrator
from middleware.rate_limiter import limiter
from middleware.request_id import get_request_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["grading"])


# ==================== Request/Response Models ====================

class GradingStatusResponse(BaseModel):
    """Response for grading status endpoint."""
    session_id: str
    status: str  # pending, processing, completed, failed, not_found
    message: Optional[str] = None
    # Result fields (only present when completed)
    score: Optional[float] = None
    feedback: Optional[str] = None
    confidence: Optional[float] = None
    completed_at: Optional[str] = None


class GradingResultResponse(BaseModel):
    """Full grading result response."""
    session_id: str
    score: float
    feedback: str
    confidence: Optional[float] = None
    score_breakdown: Optional[List[dict]] = None
    model_info: Optional[dict] = None
    processing_time: Optional[float] = None
    completed_at: Optional[str] = None


class QueueMetricsResponse(BaseModel):
    """Response for queue metrics endpoint."""
    queue_name: str = "grading:queue"
    queue_length: int
    worker_status: str
    worker_count: int


class DebugGradeRequest(BaseModel):
    """Request body for debug grade endpoint."""
    session_id: str = Field(..., description="Unique session identifier")
    transcription_text: str = Field(..., description="Student's answer text")
    screenshot_key: str = Field(..., description="Key/Filename of screenshot")
    student_id: Optional[str] = Field(None, description="Student identifier")
    question_id: Optional[str] = Field(None, description="Question identifier")


class DebugGradeResponse(BaseModel):
    """Response for debug grade endpoint."""
    session_id: str
    status: str
    message: str
    result: Optional[dict] = None



# ==================== Summary Request/Response Models ====================

class CreateSummaryRequest(BaseModel):
    """Request to create a summary."""
    session_ids: List[str] = Field(..., min_length=1)


class CreateSummaryResponse(BaseModel):
    """Response for create summary endpoint."""
    summary_id: str
    status: str
    message: str
    session_count: int


class SummaryStatusResponse(BaseModel):
    """Response for summary status endpoint."""
    summary_id: str
    status: str
    message: Optional[str] = None


class SummaryResultResponse(BaseModel):
    """Response for summary result endpoint."""
    summary_id: str
    session_ids: List[str]
    session_ids: List[str]
    dimension_scores: List[dict]
    analytics_summary: List[str]
    overall_feedback: str
    key_strengths: List[str]
    areas_for_improvement: List[str]
    model_info: Optional[dict] = None
    processing_time: Optional[float] = None
    completed_at: Optional[str] = None


# ==================== Status Polling Endpoints ====================

@router.get("/grading/session/{session_id}/status", response_model=GradingStatusResponse)
@limiter.limit("60/minute")
async def get_grading_status(request: Request, session_id: str):
    """
    Get grading status for a session.
    
    Frontend polls this endpoint to check if grading is complete.
    Recommended polling interval: 2-3 seconds.
    
    Args:
        session_id: Session identifier
        
    Returns:
        GradingStatusResponse with status and result (if completed)
    """
    # First check status
    status_data = await result_store.get_status(session_id)
    
    if status_data is None:
        # Check if result exists (status might have expired but result exists)
        result = await result_store.get_result(session_id)
        if result:
            # Result is now a GradingResult object
            return GradingStatusResponse(
                session_id=session_id,
                status="completed",
                score=result.score,
                feedback=result.feedback,
                confidence=result.confidence,
                completed_at=result.completed_at.isoformat() if result.completed_at else None
            )
        # No status or result - return not found
        return GradingStatusResponse(
            session_id=session_id,
            status="not_found",
            message="No grading task found for this session"
        )
    
    status = status_data.get("status", "unknown")
    
    # If completed, include result
    if status == "completed":
        result = await result_store.get_result(session_id)
        return GradingStatusResponse(
            session_id=session_id,
            status=status,
            score=result.score if result else None,
            feedback=result.feedback if result else None,
            confidence=result.confidence if result else None,
            completed_at=result.completed_at.isoformat() if result and result.completed_at else None
        )
    
    return GradingStatusResponse(
        session_id=session_id,
        status=status,
        message=status_data.get("message")
    )


@router.get("/grading/session/{session_id}/result", response_model=GradingResultResponse)
@limiter.limit("30/minute")
async def get_grading_result(request: Request, session_id: str):
    """
    Get full grading result for a session.
    
    Returns detailed result including score breakdown (if available).
    Returns 404 if result not found or grading not complete.
    
    Args:
        session_id: Session identifier
        
    Returns:
        GradingResultResponse with full result details
    """
    result = await result_store.get_result(session_id)
    
    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"Grading result not found for session {session_id}"
        )
    
    # Convert score_breakdown (List[ScoreBreakdown]) to dicts for response model
    score_breakdown_dicts = None
    if result.score_breakdown:
        score_breakdown_dicts = [sb.model_dump() for sb in result.score_breakdown]

    # Convert model_info to dict
    model_info_dict = None
    if result.model_info:
        model_info_dict = result.model_info.model_dump()

    return GradingResultResponse(
        session_id=session_id,
        score=result.score if result.score is not None else 0.0,
        feedback=result.feedback,
        confidence=result.confidence,
        score_breakdown=score_breakdown_dicts,
        model_info=model_info_dict,
        processing_time=result.processing_time,
        completed_at=result.completed_at.isoformat() if result.completed_at else None
    )

# ==================== Queue Monitoring Endpoints ====================

@router.get("/queue/metrics", response_model=QueueMetricsResponse)
@limiter.limit("30/minute")
async def get_queue_metrics(request: Request):
    """
    Get grading queue metrics for monitoring.
    
    Returns:
        QueueMetricsResponse with queue depth and worker status
    """
    try:
        client = get_redis_client().get_client()
        queue_length = await client.llen("grading:queue")
        
        return QueueMetricsResponse(
            queue_length=queue_length,
            worker_status="running" if grading_worker.is_running else "stopped",
            worker_count=grading_worker.num_workers
        )
    except Exception as e:
        logger.error(f"Failed to get queue metrics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get queue metrics: {e}")


# ==================== Debug Endpoints ====================

@router.post("/debug/grade", response_model=DebugGradeResponse)
@limiter.limit("3/minute")
async def debug_grade(request: Request, body: DebugGradeRequest):
    """
    Debug endpoint to manually trigger grading (bypasses queue).
    
    Runs the grading pipeline synchronously and returns result.
    For development/testing only - do not use in production.
    
    Args:
        request: The HTTP request (used for rate limiting)
        body: DebugGradeRequest with task data
        
    Returns:
        DebugGradeResponse with grading result
    """
    logger.info(f"[DEBUG] Manual grading for session {body.session_id}")
    
    try:
        # Create task dict
        task_dict = {
            "session_id": body.session_id,
            "student_id": body.student_id,
            "question_id": body.question_id,
            "transcription_text": body.transcription_text,
            "screenshot_key": body.screenshot_key
        }
        
        # Run orchestrator directly (synchronous, bypasses queue)
        orchestrator = Orchestrator()
        final_state = await orchestrator.run_pipeline(task_dict)
        
        return DebugGradeResponse(
            session_id=body.session_id,
            status="completed",
            message="Grading completed successfully",
            result=final_state.result
        )
        
    except Exception as e:
        logger.error(f"[DEBUG] Grading failed for {body.session_id}: {e}", exc_info=True)
        return DebugGradeResponse(
            session_id=body.session_id,
            status="failed",
            message=f"Grading failed: {str(e)}",
            result=None
        )


@router.get("/debug/queue-status")
@limiter.limit("30/minute")
async def get_queue_status(request: Request):
    """
    Get detailed queue status (for debugging).
    
    Returns:
        Dict with queue details
    """
    try:
        client = get_redis_client().get_client()
        queue_length = await client.llen("grading:queue")
        
        # Peek at next task (without removing it)
        next_task_json = await client.lindex("grading:queue", -1)
        next_task = None
        if next_task_json:
            try:
                next_task = json.loads(next_task_json)
                # Only include non-sensitive fields
                next_task = {
                    "session_id": next_task.get("session_id"),
                    "created_at": next_task.get("created_at")
                }
            except json.JSONDecodeError:
                next_task = {"error": "Invalid JSON in queue"}
        
        return {
            "queue_name": "grading:queue",
            "queue_length": queue_length,
            "next_task": next_task,
            "worker_status": "running" if grading_worker.is_running else "stopped",
            "worker_count": grading_worker.num_workers
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get queue status: {e}")


# ==================== Dead-Letter Queue Admin Endpoints ====================

@router.get("/admin/dlq/tasks")
@limiter.limit("10/minute")
async def get_dlq_tasks(request: Request, limit: int = 10):
    """
    Get tasks from dead-letter queue (admin only).
    
    Args:
        limit: Max number of tasks to return (default 10)
        
    Returns:
        List of failed tasks with error details
    """
    from services.grading_queue import grading_queue
    
    try:
        tasks = await grading_queue.get_dlq_tasks(limit=limit)
        dlq_length = await grading_queue.get_dlq_length()
        
        return {
            "total_count": dlq_length,
            "returned_count": len(tasks),
            "tasks": tasks
        }
    except Exception as e:
        logger.error(f"Failed to get DLQ tasks: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get DLQ tasks: {e}")


@router.post("/admin/dlq/requeue/{session_id}")
@limiter.limit("10/minute")
async def requeue_from_dlq(request: Request, session_id: str):
    """
    Requeue a task from dead-letter queue (admin only).
    
    Resets retry count and moves task back to main queue.
    
    Args:
        session_id: Session ID of task to requeue
        
    Returns:
        Success status
    """
    from services.grading_queue import grading_queue
    
    try:
        success = await grading_queue.requeue_from_dlq(session_id)
        
        if success:
            return {
                "status": "success",
                "message": f"Task {session_id} requeued from DLQ"
            }
        else:
            raise HTTPException(
                status_code=404,
                detail=f"Task {session_id} not found in DLQ"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to requeue from DLQ: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to requeue: {e}")


@router.delete("/admin/dlq/clear")
@limiter.limit("5/minute")
async def clear_dlq(request: Request):
    """
    Clear all tasks from dead-letter queue (admin only).
    
    WARNING: This permanently removes all failed tasks.
    
    Returns:
        Number of tasks cleared
    """
    from services.grading_queue import grading_queue
    
    try:
        count = await grading_queue.clear_dlq()
        return {
            "status": "success",
            "cleared_count": count
        }
    except Exception as e:
        logger.error(f"Failed to clear DLQ: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to clear DLQ: {e}")


@router.get("/admin/dlq/metrics")
@limiter.limit("30/minute")
async def get_dlq_metrics(request: Request):
    """
    Get DLQ metrics for monitoring.
    
    Returns:
        DLQ size and queue health info
    """
    from services.grading_queue import grading_queue
    
    try:
        dlq_length = await grading_queue.get_dlq_length()
        queue_length = await grading_queue.get_queue_length()
        
        return {
            "dlq_length": dlq_length,
            "queue_length": queue_length,
            "worker_status": "running" if grading_worker.is_running else "stopped"
        }
    except Exception as e:
        logger.error(f"Failed to get DLQ metrics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get metrics: {e}")


# ==================== Summary Endpoints ====================


@router.post("/grading/summarize", response_model=CreateSummaryResponse)
@limiter.limit("5/minute")
async def create_summary(request: Request, body: CreateSummaryRequest):
    """
    Create a summary task for multiple grading sessions.
    
    This endpoint:
    1. Validates all sessions have completed results
    2. Generates a summary_id
    3. Enqueues the task for background processing
    4. Returns summary_id for polling
    
    Args:
        request: HTTP request (used for rate limiting)
        body: CreateSummaryRequest with session_ids
        
    Returns:
        CreateSummaryResponse with summary_id to poll
    """
    import uuid
    from services.summary_queue import summary_queue
    
    try:
        # Generate summary ID
        summary_id = f"summ_{uuid.uuid4().hex[:12]}"
        
        # Validate that all sessions have completed results
        missing_sessions = []
        for session_id in body.session_ids:
            result = await result_store.get_result(session_id)
            if result is None:
                missing_sessions.append(session_id)
        
        if missing_sessions:
            raise HTTPException(
                status_code=400,
                detail=f"Missing grading results for sessions: {missing_sessions}"
            )
        
        # Set initial status
        await result_store.set_summary_status(
            summary_id=summary_id,
            status="pending",
            message="Summary task queued"
        )
        
        # Enqueue the summary task
        task = {
            "summary_id": summary_id,
            "session_ids": body.session_ids,
            "correlation_id": get_request_id(),
        }
        
        success = await summary_queue.enqueue(task)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to enqueue summary task")
        
        logger.info(f"Created summary task {summary_id} for {len(body.session_ids)} sessions")
        
        return CreateSummaryResponse(
            summary_id=summary_id,
            status="pending",
            message="Summary task created successfully",
            session_count=len(body.session_ids)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create summary: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create summary: {e}")


@router.get("/grading/summary/{summary_id}/status", response_model=SummaryStatusResponse)
@limiter.limit("60/minute")
async def get_summary_status(request: Request, summary_id: str):
    """
    Get the processing status of a summary.
    
    Args:
        summary_id: Summary identifier
        
    Returns:
        SummaryStatusResponse with current status
    """
    try:
        status_data = await result_store.get_summary_status(summary_id)
        
        if status_data is None:
            return SummaryStatusResponse(
                summary_id=summary_id,
                status="not_found",
                message="Summary not found"
            )
        
        return SummaryStatusResponse(
            summary_id=summary_id,
            status=status_data.get("status", "unknown"),
            message=status_data.get("message")
        )
        
    except Exception as e:
        logger.error(f"Failed to get summary status for {summary_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get status: {e}")


@router.get("/grading/summary/{summary_id}/result", response_model=SummaryResultResponse)
@limiter.limit("30/minute")
async def get_summary_result(request: Request, summary_id: str):
    """
    Get the full summary result.
    
    Args:
        summary_id: Summary identifier
        
    Returns:
        SummaryResultResponse with full summary data
        
    Raises:
        404 if summary not found or not yet complete
    """
    try:
        result = await result_store.get_summary_result(summary_id)
        
        if result is None:
            # Check status to provide better error message
            status_data = await result_store.get_summary_status(summary_id)
            
            if status_data is None:
                raise HTTPException(status_code=404, detail="Summary not found")
            
            status = status_data.get("status", "unknown")
            if status in ["pending", "processing"]:
                raise HTTPException(
                    status_code=202,
                    detail=f"Summary is still {status}. Please poll status endpoint."
                )
            elif status == "failed":
                raise HTTPException(
                    status_code=500,
                    detail=f"Summary failed: {status_data.get('message', 'Unknown error')}"
                )
            else:
                raise HTTPException(status_code=404, detail="Summary result not available")
        
        # Helper to dump list of models to list of dicts
        dimension_scores = [d.model_dump() for d in result.dimension_scores] if result.dimension_scores else []
        model_info = result.model_info.model_dump() if result.model_info else None

        return SummaryResultResponse(
            summary_id=result.summary_id,
            session_ids=result.session_ids,
            dimension_scores=dimension_scores,
            analytics_summary=result.analytics_summary,
            overall_feedback=result.overall_feedback,
            key_strengths=result.key_strengths,
            areas_for_improvement=result.areas_for_improvement,
            model_info=model_info,
            processing_time=result.processing_time,
            completed_at=result.completed_at.isoformat() if result.completed_at else None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get summary result for {summary_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get result: {e}")

