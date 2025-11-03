"""
Configuration management for the Content Research Pipeline.
"""

from typing import Optional
from pydantic import BaseSettings, Field, validator
from pathlib import Path
import os


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # API Keys
    openai_api_key: str = Field(..., env="OPENAI_API_KEY")
    google_api_key: str = Field(..., env="GOOGLE_API_KEY")
    google_cse_id: str = Field(..., env="GOOGLE_CSE_ID")
    
    # Application Configuration
    log_level: str = Field("INFO", env="LOG_LEVEL")
    chroma_persist_directory: str = Field("./chroma_db", env="CHROMA_PERSIST_DIRECTORY")
    cache_expire_seconds: int = Field(3600, env="CACHE_EXPIRE_SECONDS")
    
    # Vector Database Configuration
    chroma_host: str = Field("localhost", env="CHROMA_HOST")
    chroma_port: int = Field(8000, env="CHROMA_PORT")
    
    # FastAPI Configuration
    api_host: str = Field("0.0.0.0", env="API_HOST")
    api_port: int = Field(8000, env="API_PORT")
    api_reload: bool = Field(True, env="API_RELOAD")
    api_key: Optional[str] = Field(None, env="API_KEY")
    
    # Redis Configuration
    redis_host: str = Field("localhost", env="REDIS_HOST")
    redis_port: int = Field(6379, env="REDIS_PORT")
    redis_db: int = Field(0, env="REDIS_DB")
    redis_password: Optional[str] = Field(None, env="REDIS_PASSWORD")
    
    # Media Processing
    download_images: bool = Field(True, env="DOWNLOAD_IMAGES")
    download_videos: bool = Field(False, env="DOWNLOAD_VIDEOS")
    max_content_length: int = Field(10000000, env="MAX_CONTENT_LENGTH")
    
    # Analysis Configuration
    max_search_results: int = Field(5, env="MAX_SEARCH_RESULTS")
    max_topics: int = Field(5, env="MAX_TOPICS")
    sentiment_threshold: float = Field(0.5, env="SENTIMENT_THRESHOLD")
    
    # LLM Configuration
    llm_temperature: float = Field(0.0, env="LLM_TEMPERATURE")
    llm_model: str = Field("gpt-4o-mini", env="LLM_MODEL")
    max_tokens: int = Field(8000, env="MAX_TOKENS")
    
    # Text Processing
    chunk_size: int = Field(1000, env="CHUNK_SIZE")
    chunk_overlap: int = Field(200, env="CHUNK_OVERLAP")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
    
    @validator("chroma_persist_directory")
    def validate_chroma_directory(cls, v):
        """Ensure chroma directory exists."""
        path = Path(v)
        path.mkdir(parents=True, exist_ok=True)
        return str(path)
    
    @validator("log_level")
    def validate_log_level(cls, v):
        """Validate log level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Log level must be one of: {valid_levels}")
        return v.upper()
    
    @property
    def chroma_settings(self) -> dict:
        """Get Chroma-specific settings."""
        return {
            "persist_directory": self.chroma_persist_directory,
            "host": self.chroma_host,
            "port": self.chroma_port,
        }
    
    @property
    def api_settings(self) -> dict:
        """Get FastAPI-specific settings."""
        return {
            "host": self.api_host,
            "port": self.api_port,
            "reload": self.api_reload,
        }


# Global settings instance
settings = Settings() 