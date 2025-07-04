from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional, List

class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )
    
    # Required settings (no defaults)
    BOT_TOKEN: str
    GIGACHAT_TOKEN: str
    MONGODB_URI: str
    
    # Optional settings with defaults
    DB_NAME: str = "subwatch"
    TZ: str = "Asia/Jerusalem"
    
    # For backward compatibility
    @property
    def GIGACHAT_CREDENTIALS(self) -> str:
        return self.GIGACHAT_TOKEN
    
    @property
    def MONGODB_URL(self) -> str:
        return self.MONGODB_URI

# Global settings instance
settings = Settings()
