"""
Application configuration
"""
from pydantic_settings import BaseSettings
from typing import List
import os


class Settings(BaseSettings):
    # API
    SECRET_KEY: str = "change-this-secret-key-in-production"
    ENVIRONMENT: str = "development"
    API_PORT: int = 8000
    
    # Database
    DATABASE_URL: str = "postgresql://receipts_user:receipts_pass@localhost:5432/receipts_db"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # Storage
    STORAGE_TYPE: str = "local"  # local, minio, or s3
    UPLOAD_DIR: str = "C:/Users/USER/Desktop/WhatsApp_Invoice/uploads"  # For local storage
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_BUCKET: str = "receipts"
    MINIO_SECURE: bool = False
    
    # AWS S3 (alternative)
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_REGION: str = "us-east-1"
    S3_BUCKET: str = ""
    
    # Google Gemini
    GOOGLE_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.0-flash"
    
    # OCR
    OCR_ENGINE: str = "tesseract"  # tesseract or easyocr
    TESSERACT_CMD: str = "tesseract"
    POPPLER_PATH: str = ""  # Path to Poppler bin directory for PDF support
    
    # Email
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    EMAIL_FROM: str = "noreply@receipts.app"
    
    # Security
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8000"]
    MAX_UPLOAD_SIZE: int = 10485760  # 10MB
    ALLOWED_EXTENSIONS: List[str] = ["jpg", "jpeg", "png", "pdf"]
    
    # Rate limiting
    RATE_LIMIT_PER_MINUTE: int = 60
    
    # JWT
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 day
    ALGORITHM: str = "HS256"
    
    # Monitoring
    SENTRY_DSN: str = ""
    SENTRY_ENVIRONMENT: str = "development"
    
    # Logging
    LOG_LEVEL: str = "INFO"
    
    class Config:
        env_file = "../.env"
        case_sensitive = True


settings = Settings()
