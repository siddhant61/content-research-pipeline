"""
Logging configuration for the Content Research Pipeline.
"""

import sys
from loguru import logger
from .settings import settings


def setup_logging():
    """Configure logging with loguru."""
    
    # Remove default logger
    logger.remove()
    
    # Add console handler with custom format
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
               "<level>{level: <8}</level> | "
               "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
               "<level>{message}</level>",
        level=settings.log_level,
        colorize=True,
        backtrace=True,
        diagnose=True
    )
    
    # Add file handler for persistent logging
    logger.add(
        "logs/content_research_pipeline.log",
        rotation="10 MB",
        retention="10 days",
        compression="zip",
        level=settings.log_level,
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}",
        backtrace=True,
        diagnose=True
    )
    
    # Add JSON file handler for structured logging
    logger.add(
        "logs/content_research_pipeline.json",
        rotation="10 MB",
        retention="10 days",
        compression="zip",
        level=settings.log_level,
        serialize=True,
        backtrace=True,
        diagnose=True
    )
    
    logger.info("Logging configuration completed")


def get_logger(name: str = None):
    """Get a logger instance with optional name."""
    if name:
        return logger.bind(name=name)
    return logger


# Initialize logging when module is imported
setup_logging() 