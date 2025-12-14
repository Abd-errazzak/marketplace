"""
Application configuration settings
"""

from pydantic_settings import BaseSettings
from typing import List, Optional
import os


class Settings(BaseSettings):
    """Application settings"""
    
    # App settings
    APP_NAME: str = "Online Marketplace"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"
    
    # Database
    DATABASE_URL: str = "mysql+pymysql://root:password@mysql:3306/marketplace"
    DB_HOST: str = "mysql"
    DB_PORT: int = 3306
    DB_NAME: str = "marketplace"
    DB_USER: str = "root"
    DB_PASSWORD: str = "password"
    
    # JWT
    JWT_SECRET_KEY: str = "your-super-secret-jwt-key-here"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Stripe
    STRIPE_PUBLISHABLE_KEY: str = ""
    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    
    # PayPal
    PAYPAL_CLIENT_ID: str = ""
    PAYPAL_CLIENT_SECRET: str = ""
    PAYPAL_MODE: str = "sandbox"
    
    # Email
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    EMAIL_FROM: str = ""
    
    # File Storage
    STORAGE_TYPE: str = "local"  # local, s3
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_BUCKET_NAME: str = ""
    AWS_REGION: str = "us-east-1"
    UPLOAD_DIR: str = "uploads"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379"
    
    # AI Service
    AI_SERVICE_URL: str = "http://localhost:8001"
    AI_API_KEY: str = ""
    
    # Security
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:3001"]
    RATE_LIMIT_PER_MINUTE: int = 60
    
    # Platform Settings
    PLATFORM_COMMISSION_RATE: float = 0.05
    MINIMUM_PAYOUT_AMOUNT: float = 10.00
    DEFAULT_CURRENCY: str = "USD"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Create settings instance
settings = Settings()

