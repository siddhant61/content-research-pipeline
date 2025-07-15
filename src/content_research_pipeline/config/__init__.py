"""
Configuration package for Content Research Pipeline.
"""

from .settings import settings
from .logging import get_logger, setup_logging

__all__ = ["settings", "get_logger", "setup_logging"] 