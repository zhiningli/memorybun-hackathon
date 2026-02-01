"""
Redis-backed Session Store for transcription sessions.

Enables horizontal scaling by storing session state in Redis instead of in-memory.
Follows the same pattern as grading_service/services/result_store.py.
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime, timezone
from services.redis_client import get_redis_client
from config import settings
from schemas.transcription import (
    AudioTranscriptionSessionState,
    TranscriptionSessionStatus,
    WhisperModelEnum,
)

logger = logging.getLogger(__name__)


class RedisSessionStore:
    """
    Redis-backed storage for transcription session state.
    
    Uses Redis hashes for session data:
    - transcription:session:{session_id} → Hash with session fields
    
    Session TTL is set to auto-expire stale sessions.
    """
    
    def __init__(self):
        """Initialize the session store."""
        self.session_key_prefix = "transcription:session:"
        # Session TTL: 1 hour (should be longer than max session duration)
        self.ttl_seconds = getattr(settings, 'session_ttl_seconds', 3600)
    
    def _get_session_key(self, session_id: str) -> str:
        """Get Redis key for session storage."""
        return f"{self.session_key_prefix}{session_id}"
    
    async def create_session(self, session: AudioTranscriptionSessionState) -> bool:
        """
        Create a new session in Redis.
        
        Args:
            session: Session state to store
            
        Returns:
            True if successful, False otherwise
        """
        try:
            client = get_redis_client().get_client()
            session_key = self._get_session_key(session.session_id)
            
            # Serialize session to JSON
            json_data = session.model_dump_json()
            
            # Store as string with TTL
            await client.setex(session_key, self.ttl_seconds, json_data)
            
            logger.debug(f"Created session {session.session_id} in Redis")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create session {session.session_id}: {e}")
            return False
    
    async def get_session(self, session_id: str) -> Optional[AudioTranscriptionSessionState]:
        """
        Get session state from Redis.
        
        Args:
            session_id: Session identifier
            
        Returns:
            AudioTranscriptionSessionState if found, None otherwise
        """
        try:
            client = get_redis_client().get_client()
            session_key = self._get_session_key(session_id)
            
            session_json = await client.get(session_key)
            if not session_json:
                return None
            
            # Deserialize using Pydantic
            return AudioTranscriptionSessionState.model_validate_json(session_json)
            
        except Exception as e:
            logger.error(f"Failed to get session {session_id}: {e}")
            return None
    
    async def update_session(self, session: AudioTranscriptionSessionState) -> bool:
        """
        Update an existing session in Redis.
        
        Args:
            session: Updated session state
            
        Returns:
            True if successful, False otherwise
        """
        try:
            client = get_redis_client().get_client()
            session_key = self._get_session_key(session.session_id)
            
            # Check if session exists
            exists = await client.exists(session_key)
            if not exists:
                logger.warning(f"Session {session.session_id} not found for update")
                return False
            
            # Serialize and update with refreshed TTL
            json_data = session.model_dump_json()
            await client.setex(session_key, self.ttl_seconds, json_data)
            
            logger.debug(f"Updated session {session.session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update session {session.session_id}: {e}")
            return False
    
    async def append_chunk_result(
        self,
        session_id: str,
        chunk_index: int,
        chunk_text: str,
        chunk_duration: float,
        processing_time: float
    ) -> bool:
        """
        Append a processed chunk result to a session.
        
        This is an atomic read-modify-write operation.
        
        Args:
            session_id: Session identifier
            chunk_index: Index of the processed chunk
            chunk_text: Transcribed text from the chunk
            chunk_duration: Duration of the audio chunk in seconds
            processing_time: Time taken to process the chunk
            
        Returns:
            True if successful, False otherwise
        """
        try:
            session = await self.get_session(session_id)
            if not session:
                logger.warning(f"Session {session_id} not found for chunk append")
                return False
            
            # Update session with chunk result
            session.chunks[chunk_index] = chunk_text
            session.chunk_durations[chunk_index] = chunk_duration
            session.total_processing_time += processing_time
            session.last_activity_at = datetime.now(timezone.utc)
            
            # Save updated session
            return await self.update_session(session)
            
        except Exception as e:
            logger.error(f"Failed to append chunk to session {session_id}: {e}")
            return False
    
    async def finalize_session(self, session_id: str) -> Optional[AudioTranscriptionSessionState]:
        """
        Mark session as completed and return final state.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Final session state if found, None otherwise
        """
        try:
            session = await self.get_session(session_id)
            if not session:
                return None
            
            # Mark as completed
            session.status = TranscriptionSessionStatus.COMPLETED
            session.completed_at = datetime.now(timezone.utc)
            
            # Save updated session
            await self.update_session(session)
            
            return session
            
        except Exception as e:
            logger.error(f"Failed to finalize session {session_id}: {e}")
            return None
    
    async def delete_session(self, session_id: str) -> bool:
        """
        Delete a session from Redis.
        
        Args:
            session_id: Session identifier
            
        Returns:
            True if deleted, False otherwise
        """
        try:
            client = get_redis_client().get_client()
            session_key = self._get_session_key(session_id)
            
            deleted = await client.delete(session_key)
            if deleted:
                logger.info(f"Deleted session {session_id}")
            return deleted > 0
            
        except Exception as e:
            logger.error(f"Failed to delete session {session_id}: {e}")
            return False
    
    async def session_exists(self, session_id: str) -> bool:
        """
        Check if a session exists in Redis.
        
        Args:
            session_id: Session identifier
            
        Returns:
            True if session exists, False otherwise
        """
        try:
            client = get_redis_client().get_client()
            session_key = self._get_session_key(session_id)
            return await client.exists(session_key) > 0
            
        except Exception as e:
            logger.error(f"Failed to check session {session_id}: {e}")
            return False


# Global session store instance
session_store = RedisSessionStore()
