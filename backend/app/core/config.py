"""Core configuration module for MEDREA."""
import os
from pydantic import BaseModel

class Settings(BaseModel):
    PROJECT_NAME: str = "MEDREA"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api"
    WS_PAGER_PATH: str = "/ws/pager"
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./medrea.db")
    
    # Security / JWT
    SECRET_KEY: str = os.getenv("SECRET_KEY", "medrea_clinical_secret_key_development_change_in_production")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

settings = Settings()
