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
    GIGACHAT_CLIENT_ID: str
    GIGACHAT_SCOPE: str
    GIGACHAT_SECRET_KEY: str
    MONGODB_URI: str
    
    # Optional settings with defaults
    DB_NAME: str = "subwatch"
    TZ: str = "Asia/Jerusalem"
    
    # Convenience property to gather GigaChat credentials as dict
    @property
    def GIGACHAT_CREDENTIALS(self) -> dict[str, str]:
        """Return GigaChat credentials as a dictionary for easy use."""
        return {
            "client_id": self.GIGACHAT_CLIENT_ID,
            "scope": self.GIGACHAT_SCOPE,
            "secret_key": self.GIGACHAT_SECRET_KEY,
        }
    
    @property
    def MONGODB_URL(self) -> str:
        return self.MONGODB_URI

# Global settings instance
settings = Settings()
