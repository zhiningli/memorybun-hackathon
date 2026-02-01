"""
Context Fetch Stage - Fetches rubric and reference answer from ContextProvider.

Wraps the ContextProvider service to fit the pipeline pattern.
Populates state.context with rubric and reference answer.
Also fetches screenshot data if screenshot_url is provided.
"""

import logging
import httpx
from pipeline.base import PipelineStageBase
from schemas.grading_state import GradingState, PipelineStage
from services.context_provider import context_provider, ContextProvider
from config import settings

logger = logging.getLogger(__name__)


class ContextFetchStage(PipelineStageBase):
    """
    Fetches context (rubric, reference answer) and screenshot for grading.
    
    Uses:
    - state.question_id (optional, for fetching specific question context)
    - state.question_id (optional, for fetching specific question context)
    - state.screenshot_key (for fetching screenshot data)
    
    Produces:
    - state.context (dict with rubric, reference_answer, question_id)
    - state.screenshot_data (raw screenshot bytes if URL provided)
    
    Note: This stage wraps ContextProvider service.
    MVP uses mock data; future will fetch from question_service via HTTP.
    """
    
    def __init__(self, provider: ContextProvider = None):
        """
        Initialize Context Fetch Stage.
        
        Args:
            provider: Optional ContextProvider instance (for testing)
        """
        self._provider = provider or context_provider
    
    @property
    def name(self) -> str:
        return "ContextFetchStage"
    
    async def _fetch_screenshot(self, screenshot_key: str) -> bytes:
        """
        Download screenshot from transcription service or external URL.
        
        Args:
            screenshot_key: Key/Filename (e.g. "sess_123.png") or Full URL (e.g. "https://s3...")
            
        Returns:
            Raw screenshot bytes
        """
        import time
        start_time = time.perf_counter()
        
        target_url = ""
        is_external = False
        
        # Check if key is a full URL
        if screenshot_key.startswith("http://") or screenshot_key.startswith("https://"):
            target_url = screenshot_key
            is_external = True
            logger.info(f"Downloading screenshot from external URL: {target_url}")
        else:
            # Legacy/Local mode: Construct internal URL
            if not settings.transcription_service_url:
                raise ValueError("Transcription service URL not configured via settings.transcription_service_url")

            # Validate key (prevent path traversal for local mode)
            if ".." in screenshot_key or screenshot_key.startswith("/") or "\\" in screenshot_key:
                raise ValueError(f"Invalid screenshot key detected: {screenshot_key}")

            base_url = settings.transcription_service_url.rstrip("/")
            target_url = f"{base_url}/api/v1/transcribe/screenshots/{screenshot_key}"
            logger.info(f"Downloading screenshot from internal URL: {target_url}")

        from middleware.request_id import get_request_id
        from services.circuit_breaker import transcription_service_breaker
        headers = {"X-Correlation-ID": get_request_id()}

        # For external URLs (S3), we might not want to send internal headers or use the same circuit breaker?
        # Typically, S3 is high availability. 
        # But for simplicity, we use a plain httpx client for external, and the breaker for internal.
        
        async def _download_external():
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(target_url)  # No internal headers for external S3
                response.raise_for_status()
                return response.content

        @transcription_service_breaker
        async def _download_internal():
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(target_url, headers=headers)
                response.raise_for_status()
                return response.content
        
        try:
            if is_external:
                content = await _download_external()
            else:
                content = await _download_internal()
            
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            logger.info(
                f"[SCREENSHOT_DOWNLOAD] key={screenshot_key} | "
                f"size_bytes={len(content)} | "
                f"duration_ms={elapsed_ms:.2f} | "
                f"source={'external' if is_external else 'internal'}"
            )
            return content
            
        except Exception as e:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            logger.error(
                f"[SCREENSHOT_DOWNLOAD_FAILED] key={screenshot_key} | "
                f"duration_ms={elapsed_ms:.2f} | "
                f"error={e}"
            )
            raise

    
    async def run(self, state: GradingState) -> GradingState:
        """
        Fetch context and screenshot from providers.
        
        Args:
            state: Current grading state
            
        Returns:
            Updated state with context and screenshot_data populated
        """
        logger.debug(f"Fetching context for session {state.session_id}")
        
        # Fetch context using provider
        # Convert question_id to int (comes as string from GradingTask)
        question_id_int = int(state.question_id) if state.question_id else None
        context = await self._provider.gen_question_context(
            question_id=question_id_int
        )
        
        # Store QuestionContext object directly (supports to_prompt() in next stage)
        state.context = context

        
        # Fetch screenshot if Key provided
        if state.screenshot_key:
            try:
                state.screenshot_data = await self._fetch_screenshot(state.screenshot_key)
                logger.info(f"Screenshot fetched: {len(state.screenshot_data)} bytes")
            except Exception as e:
                logger.warning(f"Failed to fetch screenshot: {e}")
                state.screenshot_data = None
        
        # Advance stage
        state.advance_to(PipelineStage.CONTEXT_FETCH)
        
        # Log rubric info
        rubric = context.rubric if context else {}
        logger.info(
            f"Context fetched for session {state.session_id}: "
            f"rubric_dimensions={len(rubric.get('dimensions', []))}"
        )
        return state


def create_context_fetch_stage(provider: ContextProvider = None) -> ContextFetchStage:
    """
    Factory function for ContextFetchStage.
    
    Args:
        provider: Optional ContextProvider for testing
        
    Returns:
        Configured ContextFetchStage instance
    """
    return ContextFetchStage(provider=provider)
