from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path
from typing import Optional, List


class Settings(BaseSettings):
    """Application settings for Transcription Service"""
    app_name: str = "Transcription Service"
    debug: bool = False  # Default to False for production safety
    host: str = "0.0.0.0"
    port: int = 8001
    
    # CORS Configuration
    # In production, set CORS_ORIGINS to your actual frontend domain(s)
    cors_origins: List[str] = ["*"]  # Override in production!
    
    # Base URL for this service
    base_url: str = "http://localhost:8001"
    
    # Storage Configuration
    storage_type: str = "FILESYSTEM"  # Options: FILESYSTEM, S3
    screenshots_path: Path = Path("data/screenshots")
    storage_ttl_seconds: int = 3600
    
    # S3 Configuration
    s3_bucket: Optional[str] = None
    s3_region: str = "us-east-1"
    s3_prefix: str = "screenshots"  # Prefix for S3 screenshot keys
    s3_audio_prefix: str = "audio"  # Prefix for S3 audio keys

    
    # Whisper Configuration
    whisper_preload_model: Optional[str] = None
    whisper_compute_type: str = "int8"  # Options: int8 (lowest memory), float16 (GPU), float32 (CPU accuracy)
    
    # Redis Configuration
    # REDIS_URL is set by docker-compose to redis://redis:6379/0
    # We parse host/port from it, or use localhost defaults for local development
    redis_url: str = "redis://localhost:6379/0"
    redis_host: str = "redis"  # Default to Docker container name; overridden from REDIS_URL if set
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: Optional[str] = None
    redis_socket_timeout: int = 5
    redis_socket_connect_timeout: int = 5
    
    def model_post_init(self, __context) -> None:
        """Parse redis_host from redis_url if not explicitly set."""
        # Extract host from redis_url (format: redis://[password@]host:port/db)
        if self.redis_url:
            from urllib.parse import urlparse
            parsed = urlparse(self.redis_url)
            if parsed.hostname:
                object.__setattr__(self, 'redis_host', parsed.hostname)
            if parsed.port:
                object.__setattr__(self, 'redis_port', parsed.port)
            if parsed.path and parsed.path.startswith('/'):
                try:
                    db = int(parsed.path[1:])
                    object.__setattr__(self, 'redis_db', db)
                except ValueError:
                    pass
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

settings = Settings()

