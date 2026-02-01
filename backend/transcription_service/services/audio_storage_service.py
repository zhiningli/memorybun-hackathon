"""
Audio Storage Service - Business logic for storing audio files to S3.

This service handles:
- Storing audio files to S3 for future evaluation/training
- Skipping storage in FILESYSTEM mode (local development)
- Generating S3 URLs for audio files
"""

import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class AudioStorageService:
    """
    Service for managing audio file storage in S3.
    
    In S3 mode: Stores audio files to s3://bucket/audio/{session_id}_{chunk_index}.webm
    In FILESYSTEM mode: Skips storage entirely (returns None)
    """
    
    # Audio is always WebM format from Chrome MediaRecorder
    AUDIO_CONTENT_TYPE = "video/webm"
    AUDIO_EXTENSION = ".webm"
    
    def __init__(self, storage_backend=None, storage_type: str = None):
        """
        Initialize audio storage service.
        
        Args:
            storage_backend: Optional storage backend (for testing)
            storage_type: Storage type override (for testing)
        """
        from config import settings
        
        self._storage_type = storage_type or settings.storage_type
        
        # Only initialize S3 storage if using S3
        if self._storage_type.upper() == "S3":
            if storage_backend:
                self.storage = storage_backend
                logger.info("Audio storage service initialized with injected S3 backend")
            else:
                from services.storage.factory import get_storage_provider
                
                self.storage = get_storage_provider(
                    storage_type="S3",
                    s3_bucket=settings.s3_bucket,
                    s3_region=settings.s3_region,
                    s3_prefix=settings.s3_audio_prefix  # Uses audio prefix
                )
                logger.info(f"Audio storage service initialized with S3 (prefix: {settings.s3_audio_prefix})")
        else:
            # FILESYSTEM mode - no storage, just skip
            self.storage = None
            logger.info("Audio storage service initialized in FILESYSTEM mode (storage disabled)")
    
    @property
    def is_enabled(self) -> bool:
        """Check if audio storage is enabled (True for S3, False for FILESYSTEM)."""
        return self.storage is not None
    
    async def store_audio(
        self,
        session_id: str,
        chunk_index: int,
        audio_data: bytes
    ) -> Optional[str]:
        """
        Store audio file to S3 and return the public URL.
        
        Args:
            session_id: Session identifier
            chunk_index: Audio chunk index
            audio_data: Raw audio bytes (WebM format)
            
        Returns:
            S3 URL for the audio file, or None if storage is disabled (FILESYSTEM mode)
        """
        if not self.is_enabled:
            logger.debug(f"Audio storage disabled (FILESYSTEM mode), skipping storage for {session_id}")
            return None
        
        # Sanitize session_id
        if ".." in session_id or "/" in session_id or "\\" in session_id:
            raise ValueError("Invalid session_id: contains invalid characters or path traversal attempts")
        
        # Generate filename: {session_id}_{chunk_index}.webm
        filename = f"{session_id}_chunk_{chunk_index}{self.AUDIO_EXTENSION}"
        
        try:
            stored_key = await self.storage.save(filename, audio_data, self.AUDIO_CONTENT_TYPE)
            audio_url = self.storage.get_public_url(stored_key)
            logger.info(f"Stored audio for session {session_id} chunk {chunk_index} at {audio_url}")
            return audio_url
        except Exception as e:
            logger.error(f"Failed to store audio for session {session_id} chunk {chunk_index}: {e}")
            raise IOError(f"Failed to store audio: {str(e)}")
    
    async def store_session_audio(
        self,
        session_id: str,
        audio_data: bytes
    ) -> Optional[str]:
        """
        Store the final combined audio for a session.
        
        This is used when finalizing a session to store the complete audio file.
        
        Args:
            session_id: Session identifier
            audio_data: Combined audio bytes (WebM format)
            
        Returns:
            S3 URL for the audio file, or None if storage is disabled
        """
        if not self.is_enabled:
            logger.debug(f"Audio storage disabled, skipping session audio for {session_id}")
            return None
        
        # Sanitize session_id
        if ".." in session_id or "/" in session_id or "\\" in session_id:
            raise ValueError("Invalid session_id: contains invalid characters")
        
        # Generate filename: {session_id}.webm (final combined audio)
        filename = f"{session_id}{self.AUDIO_EXTENSION}"
        
        try:
            stored_key = await self.storage.save(filename, audio_data, self.AUDIO_CONTENT_TYPE)
            audio_url = self.storage.get_public_url(stored_key)
            logger.info(f"Stored session audio for {session_id} at {audio_url}")
            return audio_url
        except Exception as e:
            logger.error(f"Failed to store session audio for {session_id}: {e}")
            raise IOError(f"Failed to store session audio: {str(e)}")
    
    def get_audio_url(self, session_id: str) -> Optional[str]:
        """
        Get public URL for a session's audio file.
        
        Args:
            session_id: Session identifier
            
        Returns:
            S3 URL or None if storage is disabled
        """
        if not self.is_enabled:
            return None
        
        filename = f"{session_id}{self.AUDIO_EXTENSION}"
        return self.storage.get_public_url(filename)


# Global service instance
audio_storage_service = AudioStorageService()
