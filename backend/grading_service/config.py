"""
Configuration settings for Grading Service.

Uses pydantic-settings for environment variable support.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import SecretStr
from typing import Optional, List


class Settings(BaseSettings):
    """Application settings for Grading Service"""
    app_name: str = "Grading Service"
    debug: bool = False  # Default to False for production safety
    host: str = "0.0.0.0"
    port: int = 8002
    
    # CORS Configuration
    # In production, set CORS_ORIGINS to your actual frontend domain(s)
    # Example: CORS_ORIGINS='["https://memorybun.com","https://www.memorybun.com"]'
    cors_origins: List[str] = ["*"]  # Override in production!
    
    # Redis Configuration
    redis_url: str = "redis://localhost:6379/0"
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: Optional[str] = None
    redis_socket_timeout: int = 5
    redis_socket_connect_timeout: int = 5
    
    # Result Storage Configuration
    result_ttl_seconds: int = 3600
    
    # LLM Configuration
    mock_llm_response: bool = False
    llm_provider: str = "gemini"
    llm_model: str = "gemini-3-flash-preview"
    llm_temperature: float = 0.3
    llm_max_tokens: int = 5000
    
    # Summary LLM Configuration
    summary_llm_provider: str = "gemini"
    summary_llm_model: str = "gemini-3-flash-preview"
    summary_llm_temperature: float = 0.3
    summary_llm_max_tokens: int = 5000
    
    # Provider-specific settings (Secrets - using SecretStr to prevent logging)
    openai_api_key: Optional[SecretStr] = None
    gemini_api_key: Optional[SecretStr] = None
    
    # Service URLs
    question_service_url: Optional[str] = "http://localhost:8000"
    transcription_service_url: Optional[str] = "http://localhost:8001"
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

settings = Settings()
