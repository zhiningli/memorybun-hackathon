"""
Screenshot Service - Business logic for storing and managing screenshots.

This service handles:
- Storing screenshots to filesystem
- Generating URLs for screenshots
- Validating image formats (PNG, JPEG, WebP)
- Managing screenshot lifecycle
"""

import logging
from pathlib import Path
from typing import Optional
from fastapi import UploadFile

logger = logging.getLogger(__name__)


class ScreenshotService:
    """
    Service for managing screenshot storage and retrieval.
    
    Storage Location: backend/data/screenshots/{session_id}.{ext}
    URL Pattern: /api/v1/transcribe/screenshots/{session_id}.{ext}
    """
    
    # Supported image formats
    SUPPORTED_CONTENT_TYPES = {
        "image/png",
        "image/jpeg",
        "image/jpg",
        "image/webp"
    }
    
    SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
    
    # Content type to extension mapping
    CONTENT_TYPE_TO_EXT = {
        "image/png": ".png",
        "image/jpeg": ".jpeg",
        "image/jpg": ".jpg",
        "image/webp": ".webp"
    }
    
    
    def __init__(self, storage_backend=None):
        """
        Initialize screenshot service with configured storage backend.
        
        Args:
            storage_backend: Optional StorageBackend instance (dependency injection for testing)
        """
        if storage_backend:
            self.storage = storage_backend
            logger.info("Screenshot service initialized with injected storage backend")
            return

        from config import settings
        from services.storage.factory import get_storage_provider
        
        # Initialize storage backend based on config
        # Use absolute path for screenshots data if using filesystem
        current_file = Path(__file__)
        base_path = settings.screenshots_path
        if not base_path.is_absolute():
            service_root = current_file.parent.parent
            base_path = service_root / base_path

        self.storage = get_storage_provider(
            storage_type=settings.storage_type,
            # Local config
            base_path=base_path,
            base_url=settings.base_url,
            # S3 config
            s3_bucket=settings.s3_bucket,
            s3_region=settings.s3_region,
            s3_prefix=settings.s3_prefix
        )
        logger.info(f"Screenshot service initialized with storage: {settings.storage_type}")
    
    def _validate_content_type(self, content_type: Optional[str]) -> bool:
        """
        Validate content type is supported.
        """
        if not content_type:
            return False
        return content_type.lower() in self.SUPPORTED_CONTENT_TYPES
    
    def _validate_file_signature(self, image_data: bytes) -> Optional[str]:
        """
        Validate file signature (magic bytes) and return content type.
        """
        if len(image_data) < 12:
            return None
        
        # PNG signature: 89 50 4E 47 0D 0A 1A 0A
        if image_data[:8] == b"\x89PNG\r\n\x1a\n":
            return "image/png"
        
        # JPEG signature: FF D8 FF
        if image_data[:3] == b"\xff\xd8\xff":
            return "image/jpeg"
        
        # WebP signature: RIFF ... WEBP
        if image_data[:4] == b"RIFF" and image_data[8:12] == b"WEBP":
            return "image/webp"
        
        return None
    
    def _get_extension_from_content_type(self, content_type: str) -> str:
        """
        Get file extension from content type.
        """
        return self.CONTENT_TYPE_TO_EXT.get(content_type.lower(), ".png")

    
    async def store_screenshot(
        self,
        session_id: str,
        image_data: bytes,
        content_type: Optional[str] = None
    ) -> str:
        """
        Store screenshot and return the filename/key.
        """
        import time
        start_time = time.perf_counter()
        
        # Validate content type if provided
        if content_type and not self._validate_content_type(content_type):
            raise ValueError(f"Unsupported content type: {content_type}. Supported: {self.SUPPORTED_CONTENT_TYPES}")
        
        # Sanitize session_id
        if ".." in session_id or "/" in session_id or "\\" in session_id:
            raise ValueError("Invalid session_id: contains invalid characters or path traversal attempts")
        
        # If content type not provided, infer from file signature
        if not content_type:
            content_type = self._validate_file_signature(image_data)
            if not content_type:
                raise ValueError("Could not determine image format from file signature. Supported: PNG, JPEG, WebP")
        
        # Get extension
        extension = self._get_extension_from_content_type(content_type)
        
        # Generate filename/ID
        filename = f"{session_id}{extension}"
        
        # Store via backend
        try:
            stored_key = await self.storage.save(filename, image_data, content_type)
            
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            logger.info(
                f"[SCREENSHOT_STORE] session_id={session_id} | "
                f"size_bytes={len(image_data)} | "
                f"duration_ms={elapsed_ms:.2f} | "
                f"key={stored_key}"
            )
        except Exception as e:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            logger.error(
                f"[SCREENSHOT_STORE_FAILED] session_id={session_id} | "
                f"duration_ms={elapsed_ms:.2f} | "
                f"error={e}"
            )
            raise IOError(f"Failed to store screenshot: {str(e)}")
        
        # Return only the filename/key
        return stored_key
    
    def get_screenshot_url(self, session_id: str, extension: Optional[str] = None) -> str:
        """
        Generate URL for a screenshot.
        """
        # With abstract storage, we need the stored key.
        # Ideally we know it. If not, we guess standard extension or use session_id if key matches.
        # Assumption: The 'key' passed to get_public_url is the one returned by store_screenshot.
        # But we don't have that key stored here (it's in Redis session).
        
        # Fallback logic: Construct likely key
        if extension is None:
            extension = ".png"
            
        key = f"{session_id}{extension}"
        
        # Delegate URL generation to provider
        return self.storage.get_public_url(key)

    
    async def get_screenshot(self, session_id: str) -> tuple[bytes, str]:
        """
        Retrieve screenshot data and content type.
        Accepts session_id, tries to find the file with supported extensions.
        """
        # Try all supported extensions since we don't know which one it was stored as
        # (This is a bit inefficient for Key-Value stores, but compatible with previous logic)
        
        found_data = None
        found_ext = None
        
        for ext in self.SUPPORTED_EXTENSIONS:
            filename = f"{session_id}{ext}"
            try:
                found_data = await self.storage.get(filename)
                found_ext = ext
                break
            except Exception:
                continue
        
        if found_data is None:
            raise FileNotFoundError(f"Screenshot not found for session {session_id}")
        
        # Determine content type
        content_type_map = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".webp": "image/webp"
        }
        content_type = content_type_map.get(found_ext, "image/png")
        
        return found_data, content_type
    
    async def delete_screenshot(self, session_id: str) -> bool:
        """
        Delete screenshot file.
        """
        deleted_any = False
        
        # Try to delete all possible extensions
        for ext in self.SUPPORTED_EXTENSIONS:
            filename = f"{session_id}{ext}"
            try:
                if await self.storage.delete(filename):
                    deleted_any = True
            except Exception:
                continue
                
        if deleted_any:
            logger.info(f"Deleted screenshot(s) for session {session_id}")
            return True
        else:
            logger.debug(f"No screenshot found to delete for session {session_id}")
            return False
    
    def validate_upload_file(self, file: UploadFile) -> str:
        """
        Validate upload file metadata.
        
        Args:
            file: FastAPI UploadFile
            
        Returns:
            Content type string
            
        Raises:
            ValueError: If file format is invalid
        """
        # Check content type
        content_type = file.content_type
        if not self._validate_content_type(content_type):
            raise ValueError(
                f"Unsupported content type: {content_type}. "
                f"Supported: {', '.join(self.SUPPORTED_CONTENT_TYPES)}"
            )
        
        # Check file extension
        if file.filename:
            file_ext = Path(file.filename).suffix.lower()
            if file_ext not in self.SUPPORTED_EXTENSIONS:
                raise ValueError(
                    f"Unsupported file extension: {file_ext}. "
                    f"Supported: {', '.join(self.SUPPORTED_EXTENSIONS)}"
                )
        
        return content_type


# Global service instance
screenshot_service = ScreenshotService()

