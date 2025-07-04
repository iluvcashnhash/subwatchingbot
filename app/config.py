from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")
    
    # Bot configuration
    BOT_TOKEN: str
    ADMIN_IDS: list[int]
    
    # MongoDB configuration
    MONGODB_URL: str = "mongodb://mongo:27017"
    DB_NAME: str = "subwatch_bot"
    
    # GigaChat API
    GIGACHAT_CREDENTIALS: Optional[str] = None
    
    # Webhook settings (if using webhooks)
    WEBHOOK_URL: Optional[str] = None
    WEBHOOK_PATH: Optional[str] = None
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
