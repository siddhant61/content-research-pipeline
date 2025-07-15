"""
Tests for configuration module.
"""

import os
import pytest
from unittest.mock import patch
from src.content_research_pipeline.config.settings import Settings


class TestSettings:
    """Test configuration settings."""
    
    def test_settings_default_values(self):
        """Test that default settings are loaded correctly."""
        with patch.dict(os.environ, {
            'OPENAI_API_KEY': 'test_openai_key',
            'GOOGLE_API_KEY': 'test_google_key',
            'GOOGLE_CSE_ID': 'test_cse_id'
        }):
            settings = Settings()
            
            assert settings.openai_api_key == 'test_openai_key'
            assert settings.google_api_key == 'test_google_key'
            assert settings.google_cse_id == 'test_cse_id'
            assert settings.log_level == 'INFO'
            assert settings.max_search_results == 5
            assert settings.max_topics == 5
    
    def test_settings_custom_values(self):
        """Test that custom settings are loaded correctly."""
        with patch.dict(os.environ, {
            'OPENAI_API_KEY': 'test_openai_key',
            'GOOGLE_API_KEY': 'test_google_key',
            'GOOGLE_CSE_ID': 'test_cse_id',
            'LOG_LEVEL': 'DEBUG',
            'MAX_SEARCH_RESULTS': '10',
            'MAX_TOPICS': '8'
        }):
            settings = Settings()
            
            assert settings.log_level == 'DEBUG'
            assert settings.max_search_results == 10
            assert settings.max_topics == 8
    
    def test_settings_validation(self):
        """Test that settings validation works correctly."""
        with patch.dict(os.environ, {
            'OPENAI_API_KEY': 'test_openai_key',
            'GOOGLE_API_KEY': 'test_google_key',
            'GOOGLE_CSE_ID': 'test_cse_id',
            'LOG_LEVEL': 'INVALID'
        }):
            with pytest.raises(ValueError, match="Log level must be one of"):
                Settings()
    
    def test_chroma_settings_property(self):
        """Test that chroma settings property works correctly."""
        with patch.dict(os.environ, {
            'OPENAI_API_KEY': 'test_openai_key',
            'GOOGLE_API_KEY': 'test_google_key',
            'GOOGLE_CSE_ID': 'test_cse_id'
        }):
            settings = Settings()
            chroma_settings = settings.chroma_settings
            
            assert 'persist_directory' in chroma_settings
            assert 'host' in chroma_settings
            assert 'port' in chroma_settings
    
    def test_api_settings_property(self):
        """Test that API settings property works correctly."""
        with patch.dict(os.environ, {
            'OPENAI_API_KEY': 'test_openai_key',
            'GOOGLE_API_KEY': 'test_google_key',
            'GOOGLE_CSE_ID': 'test_cse_id'
        }):
            settings = Settings()
            api_settings = settings.api_settings
            
            assert 'host' in api_settings
            assert 'port' in api_settings
            assert 'reload' in api_settings 