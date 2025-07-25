# learning-platform-content-processor/src/config.py

from pydantic_settings import BaseSettings
from typing import List
import os

class Settings(BaseSettings):
    """Application configuration"""
    
    # Server Configuration
    PORT: int = 8001
    DEBUG: bool = False
    
    # Database Configuration
    MONGODB_URL: str = "mongodb://admin:password123@localhost:27017/learning_platform?authSource=admin"
    DATABASE_NAME: str = "learning_platform"
    
    # Security
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8000"]
    
    # File Processing Configuration
    MAX_FILE_SIZE: int = 50 * 1024 * 1024  # 50MB
    ALLOWED_FILE_TYPES: List[str] = [
        "application/pdf",
        "application/epub+zip", 
        "text/plain",
        "text/markdown",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"  # DOCX
    ]
    ALLOWED_FILE_EXTENSIONS: List[str] = [".pdf", ".epub", ".txt", ".md", ".docx"]
    
    # Text Processing Configuration
    CHUNK_SIZE: int = 1000  # Characters per chunk
    CHUNK_OVERLAP: int = 100  # Overlap between chunks
    MIN_CHUNK_SIZE: int = 100  # Minimum chunk size
    
    # AI Configuration (for future use)
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    
    # Logging Configuration
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    class Config:
        env_file = ".env"
        env_file_encoding = 'utf-8'
        case_sensitive = True

# Global settings instance
settings = Settings()

# Validate critical settings
def validate_settings():
    """Validate critical configuration settings"""
    if not settings.MONGODB_URL:
        raise ValueError("MONGODB_URL is required")
    
    if settings.MAX_FILE_SIZE < 1024 * 1024:  # At least 1MB
        raise ValueError("MAX_FILE_SIZE should be at least 1MB")
    
    if settings.CHUNK_SIZE < 100:
        raise ValueError("CHUNK_SIZE should be at least 100 characters")

# Run validation on import
validate_settings()