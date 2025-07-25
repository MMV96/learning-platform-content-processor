from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List
import os

class Settings(BaseSettings):
    """Application configuration"""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding='utf-8',
        case_sensitive=True,
        extra='ignore'
    )
    
    # Server Configuration
    PORT: int = 8001
    DEBUG: bool = False
    
    # Database Configuration
    MONGODB_URL: str = "mongodb://admin:password123@localhost:27017/learning_platform?authSource=admin"
    DATABASE_NAME: str = "learning_platform"
    
    # Security
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8000"]
    
    # File Processing Configuration - NO COMMENTS!
    MAX_FILE_SIZE: int = 52428800
    ALLOWED_FILE_TYPES: List[str] = [
        "application/pdf",
        "application/epub+zip", 
        "text/plain",
        "text/markdown",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    ]
    ALLOWED_FILE_EXTENSIONS: List[str] = [".pdf", ".epub", ".txt", ".md", ".docx"]
    
    # Text Processing Configuration
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 100
    MIN_CHUNK_SIZE: int = 100
    
    # AI Configuration
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    
    # Logging Configuration
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# Global settings instance
settings = Settings()

# Validate critical settings
def validate_settings():
    """Validate critical configuration settings"""
    if not settings.MONGODB_URL:
        raise ValueError("MONGODB_URL is required")
    
    if settings.MAX_FILE_SIZE < 1048576:
        raise ValueError("MAX_FILE_SIZE should be at least 1MB")
    
    if settings.CHUNK_SIZE < 100:
        raise ValueError("CHUNK_SIZE should be at least 100 characters")

# Run validation on import
validate_settings()