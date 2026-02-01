"""
Storage Provider Factory
"""
from pathlib import Path
from .base import StorageProvider
from .local import LocalStorageProvider
from .s3 import S3StorageProvider

def get_storage_provider(
    storage_type: str,
    # Local config
    base_path: Path = None,
    base_url: str = None,
    # S3 config
    s3_bucket: str = None,
    s3_region: str = None,
    s3_prefix: str = ""
) -> StorageProvider:
    """
    Factory function to create a storage provider instance.
    """
    storage_type = storage_type.upper()
    
    if storage_type == "S3":
        if not s3_bucket or not s3_region:
            raise ValueError("S3 storage requires s3_bucket and s3_region")
        return S3StorageProvider(
            bucket_name=s3_bucket, 
            region_name=s3_region,
            prefix=s3_prefix
        )
        
    elif storage_type == "FILESYSTEM":
        if not base_path or not base_url:
            raise ValueError("Local storage requires base_path and base_url")
        return LocalStorageProvider(base_path=base_path, base_url=base_url)
        
    else:
        raise ValueError(f"Unknown storage type: {storage_type}")
