import logging
import shutil
import asyncio
import functools
from pathlib import Path
from typing import Optional
from .base import StorageBackend

logger = logging.getLogger(__name__)

class FileSystemStorage(StorageBackend):
    """
    Filesystem storage backend.
    Persists data to local disk.
    Uses run_in_executor to avoid blocking the event loop during file I/O.
    """
    
    def __init__(self, base_path: Path, base_url: str = "http://localhost:8001"):
        self.base_path = base_path
        self.base_url = base_url.rstrip("/")
        self.base_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Initialized FileSystemStorage backend at {self.base_path}")
    
    async def save(self, file_id: str, data: bytes, content_type: str) -> str:
        # Sanitize file_id to prevent path traversal
        if ".." in file_id or "/" in file_id or "\\" in file_id:
             raise ValueError("Invalid file_id: contains invalid characters")

        file_path = self.base_path / file_id
        loop = asyncio.get_running_loop()
        try:
            await loop.run_in_executor(None, file_path.write_bytes, data)
            logger.debug(f"Saved {len(data)} bytes to disk for {file_id}")
            return file_id
        except Exception as e:
            logger.error(f"Failed to save file {file_id}: {e}")
            raise IOError(f"Failed to save file: {e}")
        
    async def get(self, file_id: str) -> bytes:
        file_path = self.base_path / file_id
        if not file_path.exists():
             raise FileNotFoundError(f"File {file_id} not found on disk")
        
        loop = asyncio.get_running_loop()
        try:
            return await loop.run_in_executor(None, file_path.read_bytes)
        except Exception as e:
            raise IOError(f"Failed to read file: {e}")
        
    async def delete(self, file_id: str) -> bool:
        file_path = self.base_path / file_id
        if not file_path.exists():
            return False
        
        loop = asyncio.get_running_loop()
        try:
            await loop.run_in_executor(None, file_path.unlink)
            return True
        except Exception as e:
            logger.error(f"Failed to delete file {file_id}: {e}")
            return False

    def get_public_url(self, file_id: str) -> Optional[str]:
        # Return URL for internal API serving
        return f"{self.base_url}/api/v1/transcribe/screenshots/{file_id}"

