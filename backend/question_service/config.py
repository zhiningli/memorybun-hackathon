from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import SecretStr
from pathlib import Path
from typing import List


class Settings(BaseSettings):
    """Application settings for Question Service"""
    app_name: str = "Question Service"
    debug: bool = False  # Default to False for production safety
    host: str = "0.0.0.0"
    port: int = 8000
    
    # CORS Configuration
    # In production, set CORS_ORIGINS to your actual frontend domain(s)
    cors_origins: List[str] = ["*"]  # Override in production!
    
    # Data directory path
    data_dir: str = "data"
    
    # Admin API Key for protected routes (using SecretStr to prevent logging)
    admin_api_key: SecretStr = SecretStr("secret")
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    def get_data_dir(self) -> Path:
        """
        Get the data directory as a Path object.
        If relative path, resolves relative to question_service directory.
        If absolute path, uses as-is.
        """
        data_path = Path(self.data_dir)
        if data_path.is_absolute():
            return data_path
        # Relative to question_service directory
        service_dir = Path(__file__).parent
        return service_dir / data_path


settings = Settings()

