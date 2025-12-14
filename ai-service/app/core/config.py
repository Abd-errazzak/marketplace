"""
AI Service configuration settings
"""

from pydantic_settings import BaseSettings
from typing import List, Optional
import os


class Settings(BaseSettings):
    """AI Service settings"""
    
    # App settings
    APP_NAME: str = "Marketplace AI Service"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"
    
    # Database
    DATABASE_URL: str = "mysql+pymysql://root:password@mysql:3306/marketplace"
    
    # AI Service
    AI_API_KEY: str = "your-ai-service-api-key"
    OPENAI_API_KEY: str = ""
    
    # Model settings
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    RECOMMENDATION_MODEL: str = "collaborative"
    
    # Vector database
    VECTOR_DB_PATH: str = "data/vector_db"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Create settings instance
settings = Settings()



