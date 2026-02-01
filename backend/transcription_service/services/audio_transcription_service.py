"""
Audio Transcription Service - Manages streaming audio transcription with Whisper.

Business Logic:
- Frontend sends 30-second audio chunks sequentially
- Each chunk is processed immediately with Whisper
- Results are concatenated in order
- Sessions maintain state in Redis for horizontal scaling

Note: Uses faster-whisper (CTranslate2 backend) for 4x memory reduction and 4x speed improvement.
"""

from faster_whisper import WhisperModel
import uuid
import time
import asyncio
import logging
from pathlib import Path
from typing import Optional, Dict
from datetime import datetime, timezone

logger = logging.getLogger(__name__)
from schemas.transcription import (
    WhisperModelEnum,
    TranscriptionSessionStatus,
    TranscriptionSession,
    AudioTranscriptionSessionState,
    AudioTranscriptionChunkResult,
    AudioTranscriptionSessionResult,
    CreateAudioTranscriptionSessionRequest
)
from schemas.grading import GradingReadinessStatus


class AudioTranscriptionService:
    """Service for managing streaming audio transcription"""
    
    def __init__(self):
        """Initialize service with faster-whisper (CTranslate2 backend)"""
        from config import settings
        
        # Check for CUDA availability using ctranslate2
        try:
            import ctranslate2
            cuda_available = ctranslate2.get_cuda_device_count() > 0
        except Exception:
            cuda_available = False
        
        self.device = "cuda" if cuda_available else "cpu"
        # Use config setting, or auto-detect based on device
        # int8 = lowest memory (CPU), float16 = GPU optimal, float32 = CPU accuracy
        if settings.whisper_compute_type:
            self.compute_type = settings.whisper_compute_type
        else:
            self.compute_type = "float16" if cuda_available else "int8"
        logger.info(f"AudioTranscriptionService initialized with device: {self.device}, compute_type: {self.compute_type}")
        
        # Store loaded models to avoid reloading
        self._loaded_models: Dict[WhisperModelEnum, WhisperModel] = {}
        
        # Session store handles persistence (Redis-backed for horizontal scaling)
        # Import here to avoid circular import
        from services.session_store import session_store
        self._session_store = session_store
        
        # Lock for model access - faster-whisper is NOT thread-safe
        # Multiple workers can queue tasks, but only one can transcribe at a time
        self._model_lock: Optional[asyncio.Lock] = None
        
        # Models will be pre-loaded in initialize()

    
    async def initialize(self):
        """
        Initialize the service.
        Should be called during app startup (lifespan).
        NOTE: Model preloading is NON-BLOCKING - startup completes immediately.
        """
        from config import settings
        
        preload_model = settings.whisper_preload_model
        if preload_model:
            try:
                model_enum = WhisperModelEnum(preload_model)
                # Fire-and-forget: Don't block startup on model loading
                asyncio.create_task(self._startup_model_load(model_enum))
                logger.info(f"Whisper model {model_enum.value} loading started in background")
            except ValueError:
                valid_models = [m.value for m in WhisperModelEnum]
                logger.warning(f"Invalid WHISPER_PRELOAD_MODEL '{preload_model}'. Valid: {valid_models}")
        
        logger.info("AudioTranscriptionService initialized (model loading may be in progress)")
    
    async def _startup_model_load(self, model_name: WhisperModelEnum):
        """Background task for startup model preloading."""
        try:
            await self.ensure_model_loaded(model_name)
            logger.info(f"Startup preload complete: Whisper model {model_name.value} ready")
        except Exception as e:
            logger.error(f"Startup model preload failed: {e}")

    def _get_model_lock(self) -> asyncio.Lock:
        """Get or create the model lock (lazy initialization for correct event loop)"""
        if self._model_lock is None:
            self._model_lock = asyncio.Lock()
        return self._model_lock
    
    
    def _load_model(self, model_name: WhisperModelEnum) -> WhisperModel:
        """
        Load Whisper model using faster-whisper (with caching to avoid reloading).
        Models are loaded on-demand and cached.
        WARNING: This is a blocking/CPU-intensive operation. Call from executor.
        """
        if model_name not in self._loaded_models:
            logger.info(f"Loading faster-whisper model: {model_name.value} (device={self.device}, compute_type={self.compute_type})")
            self._loaded_models[model_name] = WhisperModel(
                model_name.value,
                device=self.device,
                compute_type=self.compute_type
            )
            logger.info(f"Model {model_name.value} loaded successfully on {self.device}")
        
        return self._loaded_models[model_name]
    
    async def ensure_model_loaded(self, model_name: WhisperModelEnum) -> WhisperModel:
        """
        Ensure Whisper model is loaded, loading it asynchronously if needed.
        Uses double-check locking to avoid redundant loads.
        This method is safe to call from the event loop.
        
        Args:
            model_name: The Whisper model to load
            
        Returns:
            The loaded WhisperModel (faster-whisper)
        """
        # Fast path: model already loaded
        if model_name in self._loaded_models:
            return self._loaded_models[model_name]
        
        # Slow path: acquire lock and load
        async with self._get_model_lock():
            # Double-check after acquiring lock
            if model_name in self._loaded_models:
                return self._loaded_models[model_name]
            
            # Load model in executor to avoid blocking event loop
            loop = asyncio.get_event_loop()
            model = await loop.run_in_executor(
                None,
                lambda: self._load_model(model_name)
            )
            return model

    
    # Note: Session expiry is now handled by Redis TTL in session_store
    # No need for manual cleanup
    
    async def gen_create_session(
        self,
        request: CreateAudioTranscriptionSessionRequest
    ) -> TranscriptionSession:
        """
        Create a new transcription session.
        Frontend calls this before sending chunks.
        """
        # Generate unique session ID
        session_id = f"sess_{uuid.uuid4().hex[:12]}"
        
        # Create session state
        now = datetime.now(timezone.utc)
        session_state = AudioTranscriptionSessionState(
            session_id=session_id,
            model=request.model,
            status=TranscriptionSessionStatus.ACTIVE,
            created_at=now,
            last_activity_at=now,
            student_id=request.student_id,
            question_id=request.question_id
        )
        
        # Store session in Redis
        await self._session_store.create_session(session_state)
        
        # Trigger model loading in background (non-blocking)
        # This gives us a head start while user prepares to record
        asyncio.create_task(self._background_model_load(request.model, session_id))
        
        logger.info(f"Created transcription session: {session_id} with model {request.model}")
        
        return TranscriptionSession(
            session_id=session_id,
            model=request.model,
            status=TranscriptionSessionStatus.ACTIVE,
            created_at=now,
            student_id=request.student_id,
            question_id=request.question_id
        )
    
    async def _background_model_load(self, model_name: WhisperModelEnum, session_id: str):
        """
        Background task to pre-load model for a session.
        Errors are logged but don't affect session creation.
        """
        try:
            await self.ensure_model_loaded(model_name)
            logger.debug(f"Model {model_name.value} ready for session {session_id}")
        except Exception as e:
            logger.error(f"Background model load failed for session {session_id}: {e}")
    
    async def gen_get_session_result(
        self,
        session_id: str
    ) -> Optional[AudioTranscriptionSessionResult]:
        """
        Get the current result for a session.
        Can be called at any time to get accumulated transcription.
        """
        session = await self._session_store.get_session(session_id)
        if session is None:
            return None
        
        return AudioTranscriptionSessionResult(
            session_id=session.session_id,
            status=session.status,
            full_text=session.accumulated_audio_transcription_text,
            chunks_processed=session.chunks_processed,
            total_duration=None,  # Could be calculated from chunks if needed
            total_processing_time=session.total_processing_time,
            whisper_model=session.model,
            created_at=session.created_at,
            completed_at=session.completed_at
        )
    
    async def gen_finalize_session(
        self,
        session_id: str,
        thinking_time: Optional[float] = None
    ) -> Optional[AudioTranscriptionSessionResult]:
        """
        Finalize a session (called when frontend has sent all chunks).
        Marks session as completed and returns final result.
        
        After finalization, checks if screenshot is ready and publishes to grading queue if both ready.
        """
        # Finalize session in Redis (marks as completed)
        session = await self._session_store.finalize_session(session_id)
        if session is None:
            return None
        
        # Calculate total speaking time
        speaking_time = sum(session.chunk_durations.values())
        
        logger.info(f"Finalized session {session_id}: {session.chunks_processed} chunks, {session.total_processing_time:.2f}s total processing, {speaking_time:.2f}s speaking time")
        
        # Get final result
        result = await self.gen_get_session_result(session_id)
        # Manually update total_duration in result since gen_get_session_result sets it to None
        result.total_duration = speaking_time
        
        # Publish transcription ready to grading queue (non-blocking, don't fail if this fails)
        try:
            from services.grading_publisher import grading_publisher
            
            transcription_text = session.accumulated_audio_transcription_text                        
            # Handle edge case: no audio detected (speaking_time = 0)
            # Use fallback message to ensure grading pipeline can proceed
            if not transcription_text and speaking_time == 0:
                transcription_text = "[No voice detected]"
                logger.info(f"No voice detected for session {session_id}, using fallback message")
            
            if transcription_text:
                # Get audio URL from Redis session state (stored by worker during S3 upload)
                audio_url = None
                try:
                    session_state = await grading_publisher.get_session_state(session_id)
                    if session_state:
                        audio_url = session_state.get("audio_url")  # Will be None for FILESYSTEM mode
                except Exception:
                    pass  # audio_url remains None if Redis is unavailable
                
                published = await grading_publisher.publish_transcription_ready(
                    session_id=session_id,
                    transcription_text=transcription_text,
                    student_id=session.student_id,
                    question_id=session.question_id,
                    thinking_time=thinking_time,
                    speaking_time=speaking_time,
                    audio_url=audio_url
                )
                
                # Get status for better logging (if Redis is available)
                try:
                    session_state = await grading_publisher.get_session_state(session_id)
                    readiness_status = session_state.get("grading_readiness_status", "unknown") if session_state else "unknown"
                except Exception:
                    readiness_status = "unknown"
                
                if published:
                    logger.info(f"Published grading task for session {session_id} (both transcription and screenshot ready, status: enqueued)")
                elif readiness_status == GradingReadinessStatus.WAITING_FOR_SCREENSHOT.value:
                    logger.info(f"Transcription ready for session {session_id}, waiting for screenshot (status: {readiness_status})")
                else:
                    logger.info(f"Transcription ready for session {session_id}, status: {readiness_status}")
        except Exception as e:
            # Don't fail transcription if grading publish fails - log error only
            logger.warning(f"Warning: Failed to publish transcription to grading queue for session {session_id}: {e}")
            import traceback
            logger.error(traceback.format_exc())
        
        # Always return result, even if Redis publishing failed
        return result
    
    async def gen_delete_session(self, session_id: str) -> bool:
        """
        Delete a session and free up resources.
        Frontend can call this after retrieving final results.
        """
        from services.transcription_queue import transcription_queue
        
        # Clean up tasks for this session (local queue)
        transcription_queue.cleanup_tasks_for_session(session_id)
        
        # Delete from Redis
        deleted = await self._session_store.delete_session(session_id)
        if deleted:
            logger.info(f"Deleted session {session_id}")
        return deleted
    
    async def gen_enqueue_chunk(
        self,
        session_id: str,
        chunk_index: int,
        audio_file_path: Path
    ) -> str:
        """
        Enqueue chunk for async processing.
        Returns immediately with task_id.
        
        Args:
            session_id: Session identifier
            chunk_index: Index of this chunk (0-based)
            audio_file_path: Path to temporary audio file
            
        Returns:
            task_id: Unique identifier for this task
            
        Raises:
            ValueError: If session not found or not active
        """
        from services.transcription_queue import transcription_queue, TranscriptionTask
        
        # Validate session exists in Redis
        session = await self._session_store.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        if session.status != TranscriptionSessionStatus.ACTIVE:
            raise ValueError(f"Session {session_id} is not active (status: {session.status})")
        
        # Create task
        task = TranscriptionTask(
            session_id=session_id,
            chunk_index=chunk_index,
            audio_file_path=str(audio_file_path)
        )
        
        # Enqueue
        task_id = transcription_queue.enqueue(task)
        return task_id
    
    async def gen_process_chunk_async(
        self,
        session_id: str,
        chunk_index: int,
        audio_file_path: Path
    ) -> Optional[AudioTranscriptionChunkResult]:
        """
        Process chunk asynchronously (called by worker).
        This is the actual processing logic that runs in background.
        
        Args:
            session_id: Session identifier
            chunk_index: Index of this chunk (0-based)
            audio_file_path: Path to temporary audio file
            
        Returns:
            ChunkTranscriptionResult with accumulated text, or None if session not found
        """
        # Get session from Redis
        session = await self._session_store.get_session(session_id)
        if not session:
            logger.warning(f"Session not found: {session_id}")
            return None
        
        if session.status != TranscriptionSessionStatus.ACTIVE:
            logger.warning(f"Session {session_id} is not active (status: {session.status})")
            return None
        
        # Ensure model is loaded FIRST (may wait if loading is in progress)
        # This handles the race condition where chunk arrives before model is ready
        # ensure_model_loaded has its own lock for loading, so call it before transcription lock
        model = await self.ensure_model_loaded(session.model)
        
        # Acquire lock before transcribing - Whisper is NOT thread-safe
        # This ensures only one transcription runs at a time
        async with self._get_model_lock():
            # Process audio chunk with Whisper
            start_time = time.time()
            
            try:
                # Run faster-whisper in thread pool (it's CPU-bound, blocking operation)
                def _transcribe_sync():
                    """Synchronous transcription wrapper for faster-whisper."""
                    segments, info = model.transcribe(
                        str(audio_file_path),
                        language='en',  # Force English transcription
                        beam_size=5,  # Default, good balance of speed/accuracy
                        vad_filter=False  # Disabled - was removing all audio as silence
                    )
                    # Convert generator to list (faster-whisper returns generator)
                    return list(segments), info
                
                loop = asyncio.get_event_loop()
                segment_list, transcription_info = await loop.run_in_executor(
                    None,
                    _transcribe_sync
                )
                
                # Combine segment texts
                chunk_text = " ".join(seg.text.strip() for seg in segment_list if seg.text.strip())
                
                # Calculate duration from last segment
                # faster-whisper segment objects have .end attribute
                chunk_duration = 0.0
                if segment_list:
                    chunk_duration = segment_list[-1].end
                
                processing_time = time.time() - start_time
                
                # Store chunk result in Redis
                await self._session_store.append_chunk_result(
                    session_id=session_id,
                    chunk_index=chunk_index,
                    chunk_text=chunk_text,
                    chunk_duration=chunk_duration,
                    processing_time=processing_time
                )
                
                # Fetch updated session to get accumulated text
                updated_session = await self._session_store.get_session(session_id)
                
                logger.debug(f"Processed chunk {chunk_index} for session {session_id} in {processing_time:.2f}s (speech duration: {chunk_duration:.2f}s)")
                
                return AudioTranscriptionChunkResult(
                    session_id=session_id,
                    chunk_index=chunk_index,
                    chunk_text=chunk_text,
                    accumulated_text=updated_session.accumulated_audio_transcription_text if updated_session else chunk_text,
                    chunks_processed=updated_session.chunks_processed if updated_session else 1,
                    processing_time=processing_time
                )
                
            except Exception as e:
                logger.error(f"Error processing chunk {chunk_index} for session {session_id}: {str(e)}")
                raise
    
    async def gen_get_chunk_status(
        self,
        session_id: str,
        chunk_index: int
    ) -> Optional[Dict]:
        """
        Get status of a chunk processing task.
        
        Args:
            session_id: Session identifier
            chunk_index: Index of chunk
            
        Returns:
            Dict with task status information, or None if task not found
        """
        from services.transcription_queue import transcription_queue
        
        task_id = f"{session_id}_chunk_{chunk_index}"
        task = transcription_queue.get_task(task_id)
        
        if not task:
            return None
        
        return {
            "task_id": task_id,
            "session_id": session_id,
            "chunk_index": chunk_index,
            "status": task.status.value,
            "created_at": task.created_at.isoformat() if task.created_at else None,
            "started_at": task.started_at.isoformat() if task.started_at else None,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
            "result": task.result,
            "error": task.error
        }
    
    def get_device_info(self) -> Dict[str, str]:
        """Get information about compute device being used (faster-whisper)"""
        try:
            import ctranslate2
            cuda_available = ctranslate2.get_cuda_device_count() > 0
            cuda_device_count = ctranslate2.get_cuda_device_count()
        except Exception:
            cuda_available = False
            cuda_device_count = 0
        
        info = {
            "device": self.device,
            "compute_type": self.compute_type,
            "cuda_available": str(cuda_available),
            "backend": "faster-whisper (CTranslate2)"
        }
        
        if cuda_available:
            info["cuda_device_count"] = str(cuda_device_count)
        
        return info

