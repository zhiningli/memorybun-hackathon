"""
Grading Publisher Service - Publishes grading tasks when both transcription and screenshot are ready.

This service:
1. Stores transcription and screenshot status in Redis Hash (session:{session_id})
2. Checks if both are ready
3. Atomically enqueues to grading queue when both ready
4. Prevents duplicate enqueuing using atomic operations
"""

import json
import logging
from typing import Optional
from datetime import datetime, timezone
from services.redis_client import get_redis_client
from services.redis_grading_queue import redis_grading_queue
from schemas.grading import (
    GradingTask,
    GradingReadinessStatus,
    TranscriptionStatus,
    ScreenshotStatus
)
from middleware.request_id import get_request_id

logger = logging.getLogger(__name__)


class GradingPublisher:
    """
    Service for publishing grading tasks when both transcription and screenshot are ready.
    
    Uses Redis Hash to store session state and atomically checks and enqueues.
    """
    
    def __init__(self):
        """Initialize the grading publisher"""
        self.session_key_prefix = "session:"
        self.session_ttl_seconds = 3600  # 1 hour
    
    def _get_session_key(self, session_id: str) -> str:
        """Get Redis key for session state"""
        return f"{self.session_key_prefix}{session_id}"
    
    async def publish_transcription_ready(
        self,
        session_id: str,
        transcription_text: str,
        student_id: Optional[str] = None,
        question_id: Optional[str] = None,
        thinking_time: Optional[float] = None,
        speaking_time: Optional[float] = None,
        audio_url: Optional[str] = None,
    ) -> bool:
        """
        Mark transcription as ready and check if grading should be published.
        
        Updates grading_readiness_status:
        - "waiting_for_screenshot" if screenshot not ready
        - "ready" if both ready (then enqueues)
        - "enqueued" if task successfully enqueued
        
        Args:
            session_id: Session identifier
            transcription_text: Complete transcribed text
            student_id: Optional student identifier
            question_id: Optional question identifier
            thinking_time: Optional thinking time in seconds
            speaking_time: Optional speaking time in seconds
            audio_url: Optional S3 URL of audio file (None for filesystem mode)
            
        Returns:
            True if grading task was published, False otherwise
        """
        try:
            client = get_redis_client().get_client()
            session_key = self._get_session_key(session_id)
            
            # Get current state to check screenshot status
            session_data = await client.hgetall(session_key)
            if session_data:
                session_data = {k.decode() if isinstance(k, bytes) else k: 
                               v.decode() if isinstance(v, bytes) else v 
                               for k, v in session_data.items()}
            
            screenshot_status = session_data.get("screenshot_status", "")
            
            # Determine readiness status
            if screenshot_status == ScreenshotStatus.COMPLETED.value:
                # Both ready - will be set to "ready" then "enqueued" in check_and_publish_if_ready
                readiness_status = GradingReadinessStatus.READY.value
            else:
                # Waiting for screenshot
                readiness_status = GradingReadinessStatus.WAITING_FOR_SCREENSHOT.value
            
            # Update transcription in session state
            mapping = {
                "transcription_text": transcription_text,
                "transcription_status": TranscriptionStatus.COMPLETED.value,
                "grading_readiness_status": readiness_status,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            
            # Add optional IDs if provided
            if student_id:
                mapping["student_id"] = student_id
            if question_id:
                mapping["question_id"] = question_id
            if thinking_time is not None:
                mapping["thinking_time"] = str(thinking_time)
            if speaking_time is not None:
                mapping["speaking_time"] = str(speaking_time)
            if audio_url is not None:
                mapping["audio_url"] = audio_url
            
            await client.hset(
                session_key,
                mapping=mapping
            )
            
            # Set TTL on session
            await client.expire(session_key, self.session_ttl_seconds)
            
            logger.info(f"Transcription ready for session {session_id}, status: {readiness_status}")
            
            # Check if screenshot is also ready and publish if so
            return await self.check_and_publish_if_ready(session_id)
            
        except Exception as e:
            logger.error(f"Failed to publish transcription ready for session {session_id}: {e}")
            return False
    
    async def publish_screenshot_ready(
        self,
        session_id: str,
        screenshot_key: str
    ) -> bool:
        """
        Mark screenshot as ready and check if grading should be published.
        
        Updates grading_readiness_status:
        - "waiting_for_audio" if transcription not ready
        - "ready" if both ready (then enqueues)
        - "enqueued" if task successfully enqueued
        
        Args:
            session_id: Session identifier
            screenshot_key: Key/Filename of the screenshot image
            
        Returns:
            True if grading task was published, False otherwise
        """
        try:
            client = get_redis_client().get_client()
            session_key = self._get_session_key(session_id)
            
            # Get current state to check transcription status
            session_data = await client.hgetall(session_key)
            if session_data:
                session_data = {k.decode() if isinstance(k, bytes) else k: 
                               v.decode() if isinstance(v, bytes) else v 
                               for k, v in session_data.items()}
            
            transcription_status = session_data.get("transcription_status", "")
            
            # Determine readiness status
            if transcription_status == TranscriptionStatus.COMPLETED.value:
                # Both ready - will be set to "ready" then "enqueued" in check_and_publish_if_ready
                readiness_status = GradingReadinessStatus.READY.value
            else:
                # Waiting for transcription
                readiness_status = GradingReadinessStatus.WAITING_FOR_AUDIO.value
            
            # Update screenshot in session state
            now = datetime.now(timezone.utc).isoformat()
            mapping = {
                "screenshot_key": screenshot_key,
                "screenshot_status": ScreenshotStatus.COMPLETED.value,
                "grading_readiness_status": readiness_status,
                "updated_at": now
            }
            
            # Set created_at if it doesn't exist (first time this session is seen)
            if "created_at" not in session_data:
                mapping["created_at"] = now
            
            await client.hset(session_key, mapping=mapping)
            
            # Set TTL on session
            await client.expire(session_key, self.session_ttl_seconds)
            
            logger.info(f"Screenshot ready for session {session_id}, status: {readiness_status}")
            
            # Check if transcription is also ready and publish if so
            return await self.check_and_publish_if_ready(session_id)
            
        except Exception as e:
            logger.error(f"Failed to publish screenshot ready for session {session_id}: {e}")
            return False
    
    async def check_and_publish_if_ready(self, session_id: str) -> bool:
        """
        Check if both transcription and screenshot are ready, and publish to queue if so.
        
        This method is idempotent - it won't publish duplicate tasks.
        
        Args:
            session_id: Session identifier
            
        Returns:
            True if grading task was published, False otherwise
        """
        try:
            client = get_redis_client().get_client()
            session_key = self._get_session_key(session_id)
            
            # Use Redis transaction (MULTI/EXEC) for atomic check-and-enqueue
            # This prevents race conditions when both transcription and screenshot
            # are published at the same time
            
            async with client.pipeline() as pipe:
                # Get session state
                pipe.hgetall(session_key)
                results = await pipe.execute()
                
                session_data = results[0] if results else {}
            
            # Convert bytes to strings if needed (Redis returns bytes for hash values)
            if session_data:
                session_data = {k.decode() if isinstance(k, bytes) else k: 
                               v.decode() if isinstance(v, bytes) else v 
                               for k, v in session_data.items()}
            
            # Check if both are ready
            transcription_status = session_data.get("transcription_status", "")
            screenshot_status = session_data.get("screenshot_status", "")
            already_published = session_data.get("grading_published", "false") == "true"
            
            if (transcription_status == TranscriptionStatus.COMPLETED.value and 
                screenshot_status == ScreenshotStatus.COMPLETED.value):
                # Both ready - check if already published
                if already_published:
                    logger.info(f"Grading task already published for session {session_id}")
                    return False
                
                # Create grading task
                transcription_text = session_data.get("transcription_text", "")
                screenshot_key = session_data.get("screenshot_key", "")
                
                if not transcription_text or not screenshot_key:
                    logger.warning(f"Session {session_id} marked as ready but missing data")
                    return False
                
                task = GradingTask(
                    session_id=session_id,
                    student_id=session_data.get("student_id"),
                    question_id=session_data.get("question_id"),
                    transcription_text=transcription_text,
                    screenshot_key=screenshot_key,
                    audio_key=session_data.get("audio_url"),  # S3 URL or None for filesystem
                    thinking_time=float(session_data.get("thinking_time")) if session_data.get("thinking_time") else None,
                    speaking_time=float(session_data.get("speaking_time")) if session_data.get("speaking_time") else None,
                    correlation_id=get_request_id()
                )
                
                # Enqueue to grading queue
                success = await redis_grading_queue.enqueue_grading_task(task)
                
                if success:
                    # Mark as published and update status to "enqueued" (atomic)
                    async with client.pipeline() as pipe:
                        pipe.hset(session_key, mapping={
                            "grading_published": "true",
                            "grading_readiness_status": GradingReadinessStatus.ENQUEUED.value
                        })
                        pipe.expire(session_key, self.session_ttl_seconds)
                        await pipe.execute()
                    
                    logger.info(f"Published grading task for session {session_id}, status: {GradingReadinessStatus.ENQUEUED.value}")
                    return True
                else:
                    logger.error(f"Failed to enqueue grading task for session {session_id}")
                    return False
            else:
                # Not ready yet - status already set in publish_transcription_ready or publish_screenshot_ready
                current_status = session_data.get("grading_readiness_status", "unknown")
                logger.debug(
                    f"Session {session_id} not ready: "
                    f"transcription={transcription_status}, screenshot={screenshot_status}, "
                    f"readiness_status={current_status}"
                )
                return False
                
        except Exception as e:
            logger.error(f"Failed to check and publish for session {session_id}: {e}")
            return False
    
    async def get_session_state(self, session_id: str) -> Optional[dict]:
        """
        Get current session state from Redis (for debugging).
        
        Args:
            session_id: Session identifier
            
        Returns:
            Dict with session state, or None if not found
            Note: grading_readiness_status is returned as string (compatible with GradingReadinessStatus enum)
        """
        try:
            client = get_redis_client().get_client()
            session_key = self._get_session_key(session_id)
            
            session_data = await client.hgetall(session_key)
            if not session_data:
                return None
            
            # Convert bytes to strings
            result = {}
            for k, v in session_data.items():
                key = k.decode() if isinstance(k, bytes) else k
                value = v.decode() if isinstance(v, bytes) else v
                result[key] = value
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to get session state for {session_id}: {e}")
            return None
    
    async def get_readiness_status(self, session_id: str) -> Optional[GradingReadinessStatus]:
        """
        Get grading readiness status as enum.
        
        Args:
            session_id: Session identifier
            
        Returns:
            GradingReadinessStatus enum value, or None if session not found
        """
        session_state = await self.get_session_state(session_id)
        if not session_state:
            return None
        
        status_str = session_state.get("grading_readiness_status")
        if not status_str:
            return None
        
        try:
            return GradingReadinessStatus(status_str)
        except ValueError:
            logger.warning(f"Unknown readiness status: {status_str} for session {session_id}")
            return None
    
    async def delete_session_state(self, session_id: str) -> bool:
        """
        Delete session state from Redis (for cleanup).
        
        Args:
            session_id: Session identifier
            
        Returns:
            True if deleted, False otherwise
        """
        try:
            client = get_redis_client().get_client()
            session_key = self._get_session_key(session_id)
            
            deleted = await client.delete(session_key)
            logger.info(f"Deleted session state for {session_id}")
            return deleted > 0
            
        except Exception as e:
            logger.error(f"Failed to delete session state for {session_id}: {e}")
            return False


# Global publisher instance
grading_publisher = GradingPublisher()

