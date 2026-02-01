"""
Screenshot API Routes

Handles screenshot uploads and retrieval for transcription sessions.
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Depends, Request, Response
from fastapi.responses import Response as StreamingResponse
from schemas.screenshot import ScreenshotUploadResponse, ScreenshotUploadStatus
from schemas.grading import GradingReadinessStatus
from schemas.viewer_context import ViewerContext
from services.screenshot_service import screenshot_service
from services.grading_publisher import grading_publisher
from api.dependencies import get_viewer_context
from middleware.rate_limiter import limiter

# The route prefix will be handled when including this router in the main router
# Expected paths:
# POST /session/{session_id}/screenshot
# GET /screenshots/{session_id}

router = APIRouter()

MAX_SCREENSHOT_SIZE = 10 * 1024 * 1024  # 10 MB limit


@router.post("/session/{session_id}/screenshot", response_model=ScreenshotUploadResponse)
@limiter.limit("20/minute")
async def upload_screenshot(
    request: Request,
    response: Response,
    session_id: str,
    screenshot: UploadFile = File(..., description="Screenshot image file (PNG, JPEG, or WebP)"),
    viewer_context: ViewerContext = Depends(get_viewer_context)
):
    """
    Upload a screenshot for a transcription session.
    
    This endpoint:
    1. Validates the image format (PNG, JPEG, WebP)
    2. Stores the screenshot to filesystem
    3. Updates Redis session state with screenshot URL
    4. Checks if transcription is ready and enqueues grading task if both ready
    
    Request Format:
    - Content-Type: multipart/form-data
    - Field name: "screenshot"
    - Supported formats: PNG, JPEG, WebP
    
    Response:
    - status: "uploaded" (waiting for transcription) or "ready_for_grading" (grading enqueued)
    - grading_readiness_status: Current readiness status (for debugging)
    
    Note: The screenshot URL can be accessed at:
    GET /api/v1/transcribe/screenshots/{session_id}.{ext}
    """
    # Validate screenshot file
    try:
        content_type = screenshot_service.validate_upload_file(screenshot)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    # Read image data
    try:
        image_data = bytearray()
        while True:
            chunk = await screenshot.read(1024 * 1024)
            if not chunk:
                break
            image_data.extend(chunk)
            if len(image_data) > MAX_SCREENSHOT_SIZE:
                raise HTTPException(
                    status_code=413,
                    detail=f"Screenshot file too large. Maximum size is {MAX_SCREENSHOT_SIZE // (1024 * 1024)}MB."
                )

        if not image_data:
            raise HTTPException(status_code=400, detail="Screenshot file is empty")
        
        image_data = bytes(image_data)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read screenshot: {str(e)}")
    
    # Validate file signature (magic bytes)
    # This is done in store_screenshot, but we can also check here for better error messages
    inferred_type = screenshot_service._validate_file_signature(image_data)
    if not inferred_type:
        raise HTTPException(
            status_code=400,
            detail="Invalid image format. File signature does not match PNG, JPEG, or WebP."
        )
    
    # Store screenshot
    try:
        screenshot_key = await screenshot_service.store_screenshot(
            session_id=session_id,
            image_data=image_data,
            content_type=content_type
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except IOError as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    # Update Redis session state and check if grading should be published
    try:
        grading_published = await grading_publisher.publish_screenshot_ready(
            session_id=session_id,
            screenshot_key=screenshot_key
        )
    except Exception as e:
        # Log error but don't fail the upload
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to publish screenshot ready for session {session_id}: {e}", exc_info=True)
        grading_published = False
    
    # Get readiness status for response
    readiness_status = await grading_publisher.get_readiness_status(session_id)
    
    # Determine response status
    if grading_published:
        status = ScreenshotUploadStatus.READY_FOR_GRADING
        message = "Screenshot uploaded successfully. Grading task enqueued."
    else:
        status = ScreenshotUploadStatus.UPLOADED
        if readiness_status == GradingReadinessStatus.WAITING_FOR_AUDIO:
            message = "Screenshot uploaded successfully. Waiting for transcription to complete."
        else:
            message = "Screenshot uploaded successfully."
    
    return ScreenshotUploadResponse(
        session_id=session_id,
        screenshot_key=screenshot_key,
        status=status,
        message=message,
        grading_readiness_status=readiness_status
    )


@router.get("/screenshots/{session_id:path}")
@limiter.limit("60/minute")
async def get_screenshot(
    request: Request,
    response: Response,
    session_id: str,
    viewer_context: ViewerContext = Depends(get_viewer_context)
):

    """
    Retrieve a screenshot for a transcription session.
    
    Returns the raw image bytes (PNG, JPEG, or WebP) for the screenshot
    associated with the given session_id.
    
    This endpoint is used by the grading service to fetch screenshots
    for multimodal grading with vision models.
    
    Args:
        session_id: The session identifier
        
    Returns:
        Raw image bytes with appropriate Content-Type header
        
    Raises:
        404: If screenshot not found for the session
        500: If there's an error reading the screenshot
    """
    try:
        # Handle session_id with extension (e.g. from absolute URLs)
        # The URL structure is .../screenshots/{session_id}.{ext}
        # But the route is .../screenshots/{session_id}
        # So session_id captures the extension. We need to strip it.
        base_session_id = session_id
        for ext in screenshot_service.SUPPORTED_EXTENSIONS:
            if session_id.lower().endswith(ext):
                base_session_id = session_id[:-len(ext)]
                break
        
        image_data, content_type = await screenshot_service.get_screenshot(base_session_id)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except IOError as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    return StreamingResponse(
        content=image_data,
        media_type=content_type,
        headers={
            "Cache-Control": "public, max-age=31536000",  # Cache for 1 year
            "Content-Disposition": f'inline; filename="{session_id}.{content_type.split("/")[1]}"'
        }
    )
