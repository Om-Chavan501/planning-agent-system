"""
Configuration settings for the Planning Agent System.
"""
import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Settings:
    """Application configuration settings."""
    
    # CouchDB Configuration
    COUCH_URL: str = os.getenv("COUCH_URL", "http://couchdb.genai-dev.kpit.com")
    COUCH_USER: str = os.getenv("COUCH_USER", "admin")
    COUCH_PASS: str = os.getenv("COUCH_PASS", "your_password_here")
    COUCH_DATABASE: str = os.getenv("COUCH_DATABASE", "plans")
    
    # Application Configuration
    APP_TITLE: str = "Planning Agent System"
    APP_VERSION: str = "1.0.0"
    APP_DESCRIPTION: str = "FastAPI application for managing planning and execution workflows"
    
    # CORS Configuration
    CORS_ORIGINS: list = ["*"]
    CORS_CREDENTIALS: bool = True
    CORS_METHODS: list = ["*"]
    CORS_HEADERS: list = ["*"]
    
    # Logging Configuration
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    class Config:
        case_sensitive = True

# Global settings instance
settings = Settings()
