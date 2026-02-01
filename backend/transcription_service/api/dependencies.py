from fastapi import Request
from services.audio_transcription_service import AudioTranscriptionService
from schemas.viewer_context import ViewerContext


# Dependency to extract viewer context from request
async def get_viewer_context() -> ViewerContext:
    # In the future, this will be extracted from the request headers
    # For now, we will just return an anonymous context
    return ViewerContext(
        user_id=None,
        is_authenticated=False,
        role=None,
        permissions=[]
    )


async def get_audio_transcription_service(request: Request) -> AudioTranscriptionService:
    """Get the initialized audio transcription service from app state"""
    return request.app.state.audio_transcription_service

