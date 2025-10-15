from pydantic_settings import BaseSettings
from typing import Optional
import os

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql://forexai:forexai123@localhost:5432/forexai_dev"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # Security
    JWT_SECRET: str = "your-secret-key-here"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    ENCRYPTION_KEY: str = "your-encryption-key-here"
    
    # OpenRouter AI
    OPENROUTER_API_KEY: Optional[str] = None
    DEFAULT_AI_MODEL: str = "claude-3-opus"
    
    # WebSocket Configuration
    WEBSOCKET_SERVER_PORT: int = 8765
    CLIENT_HEARTBEAT_INTERVAL: int = 30
    CONNECTION_TIMEOUT: int = 60
    
    # User EA Configuration
    EA_DOWNLOAD_URL: str = "https://your-platform.com/downloads/ea/{user_id}"
    SETUP_GUIDE_URL: str = "https://your-platform.com/setup/{user_token}"
    
    # Trading Config
    MAX_OPEN_TRADES: int = 10
    RISK_PER_TRADE: float = 0.01
    DEFAULT_TIMEFRAME: str = "1h"
    COMMISSION_RATE: float = 0.001
    PROFIT_COMMISSION_RATE: float = 0.10
    
    # External Services
    SENTRY_DSN: Optional[str] = None
    STRIPE_API_KEY: Optional[str] = None
    SENDGRID_API_KEY: Optional[str] = None
    
    # Development
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"
    CORS_ORIGINS: list = ["http://localhost:3000"]
    
    # Freqtrade Configuration
    FREQTRADE_API_URL: str = "http://localhost:8080"
    FREQTRADE_WS_URL: str = "ws://localhost:8080"
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
