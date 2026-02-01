"""
Base Storage Provider Interface
"""
from abc import ABC, abstractmethod
from typing import Optional

class StorageProvider(ABC):
    """
    Abstract base class for file storage providers (Local, S3, etc.)
    """
    
    @abstractmethod
    async def save(self, filename: str, data: bytes, content_type: Optional[str] = None) -> str:
        """
        Save file to storage.
        
        Args:
            filename: Name/Key of the file to save
            data: Raw bytes
            content_type: MIME type
            
        Returns:
            The stored key/filename (may differ from input if collisions handled)
        """
        pass

    @abstractmethod
    async def get(self, key: str) -> bytes:
        """
        Retrieve file from storage.
        
        Args:
            key: File key/path
            
        Returns:
            Raw bytes
        """
        pass
    
    @abstractmethod
    async def delete(self, key: str) -> bool:
        """
        Delete file from storage.
        
        Args:
            key: File key/path
            
        Returns:
            True if deleted, False if not found
        """
        pass
        
    @abstractmethod
    def get_public_url(self, key: str) -> str:
        """
        Get public (or accessible) URL for the file.
        
        Args:
            key: File key/path
            
        Returns:
            Absolute URL string
        """
        pass

# Backward compatibility alias for existing implementations
StorageBackend = StorageProvider

