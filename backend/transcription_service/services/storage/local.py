"""
Local Filesystem Storage Provider
"""
import os
import logging
import aiofiles
from pathlib import Path
from typing import Optional
from .base import StorageProvider

logger = logging.getLogger(__name__)

class LocalStorageProvider(StorageProvider):
    """
    Storage provider that uses local filesystem.
    Compatible with original implementation.
    """
    
    def __init__(self, base_path: Path, base_url: str):
        """
        Args:
            base_path: Absolute directory path to store files
            base_url: Base URL for serving files via API
        """
        self.base_path = base_path
        self.base_url = base_url.rstrip("/")
        
        # Ensure directory exists
        self.base_path.mkdir(parents=True, exist_ok=True)
        
    async def save(self, filename: str, data: bytes, content_type: Optional[str] = None) -> str:
        """Save file to local disk."""
        path = self.base_path / filename
        
        try:
            async with aiofiles.open(path, "wb") as f:
                await f.write(data)
            return filename
        except Exception as e:
            logger.error(f"Failed to save {filename} to {path}: {e}")
            raise
    
    async def get(self, key: str) -> bytes:
        """Read file from local disk."""
        path = self.base_path / key
        
        if not path.exists():
            raise FileNotFoundError(f"File not found: {key}")
            
        try:
            async with aiofiles.open(path, "rb") as f:
                return await f.read()
        except Exception as e:
            logger.error(f"Failed to read {key} from {path}: {e}")
            raise
            
    async def delete(self, key: str) -> bool:
        """Delete file from local disk."""
        path = self.base_path / key
        
        if not path.exists():
            return False
            
        try:
            os.remove(path)
            return True
        except Exception as e:
            logger.error(f"Failed to delete {key}: {e}")
            return False
            
    def get_public_url(self, key: str) -> str:
        """
        Get internal API URL for the file.
        Format: {base_url}/api/v1/transcribe/screenshots/{key}
        """
        # Note: This path structure mimics the logic in ScreenshotService using settings.base_url
        return f"{self.base_url}/api/v1/transcribe/screenshots/{key}"
