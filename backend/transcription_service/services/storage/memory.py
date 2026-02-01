from typing import Dict, Optional, Tuple
import logging
from .base import StorageBackend

logger = logging.getLogger(__name__)

class MemoryStorage(StorageBackend):
    """
    In-memory storage backend using a simple dictionary.
    Data is lost when the application stops/restarts.
    Suitable for development or single-instance deployments with ephemeral data.
    """
    
    def __init__(self, ttl_seconds: int = 3600, base_url: str = "http://localhost:8001"):
        # Store as Dict[file_id, Tuple[bytes, float]] -> data, timestamp
        self._store: Dict[str, Tuple[bytes, float]] = {}
        self.ttl_seconds = ttl_seconds
        self.base_url = base_url.rstrip("/")
        logger.info(f"Initialized MemoryStorage backend with TTL: {ttl_seconds}s")
    
    def _cleanup_expired(self):
        """Remove items older than TTL"""
        import time
        now = time.time()
        expired_keys = []
        
        for file_id, (_, timestamp) in self._store.items():
            if now - timestamp > self.ttl_seconds:
                expired_keys.append(file_id)
        
        for key in expired_keys:
            del self._store[key]
            
        if expired_keys:
            logger.info(f"Cleaned up {len(expired_keys)} expired items from memory storage")

    async def save(self, file_id: str, data: bytes, content_type: str) -> str:
        # Perform cleanup periodically (on every write for simplicity)
        self._cleanup_expired()
        
        import time
        self._store[file_id] = (data, time.time())
        logger.debug(f"Saved {len(data)} bytes to memory for {file_id}")
        return file_id
        
    async def get(self, file_id: str) -> bytes:
        if file_id not in self._store:
            raise FileNotFoundError(f"File {file_id} not found in memory storage")
        return self._store[file_id][0]
        
    async def delete(self, file_id: str) -> bool:
        if file_id in self._store:
            del self._store[file_id]
            logger.debug(f"Deleted {file_id} from memory storage")
            return True
        return False
        
    def get_public_url(self, file_id: str) -> Optional[str]:
        # Return URL for internal API serving
        return f"{self.base_url}/api/v1/transcribe/screenshots/{file_id}"

