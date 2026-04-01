"""Application configuration via pydantic-settings."""

from pydantic_settings import BaseSettings
from typing import List
import os


class Settings(BaseSettings):
    APP_NAME: str = "Multi-Disease Prediction System"
    APP_ENV: str = "development"
    DEBUG: bool = True

    # Security
    SECRET_KEY: str = "change-this-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://mdps_user:mdps_pass@localhost:5432/mdps_db"
    SYNC_DATABASE_URL: str = "postgresql://mdps_user:mdps_pass@localhost:5432/mdps_db"

    # Paths
    MODEL_SAVE_PATH: str = "./ml/saved_models"
    REPORT_SAVE_PATH: str = "./reports"
    DATA_PATH: str = "./ml/data"

    # CORS
    ALLOWED_ORIGINS: List[str] = ["http://localhost:5173", "http://localhost:3000"]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
