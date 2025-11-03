"""
Tests for prompts module.
"""

import pytest
from src.content_research_pipeline.config import prompts


class TestPrompts:
    """Test prompt templates."""
    
    def test_summary_prompts_exist(self):
        """Test that summary prompts are defined."""
        assert hasattr(prompts, 'SUMMARY_SYSTEM_PROMPT')
        assert hasattr(prompts, 'SUMMARY_USER_PROMPT_TEMPLATE')
        assert isinstance(prompts.SUMMARY_SYSTEM_PROMPT, str)
        assert isinstance(prompts.SUMMARY_USER_PROMPT_TEMPLATE, str)
    
    def test_entity_extraction_prompts_exist(self):
        """Test that entity extraction prompts are defined."""
        assert hasattr(prompts, 'ENTITY_EXTRACTION_SYSTEM_PROMPT')
        assert hasattr(prompts, 'ENTITY_EXTRACTION_USER_PROMPT_TEMPLATE')
        assert isinstance(prompts.ENTITY_EXTRACTION_SYSTEM_PROMPT, str)
        assert isinstance(prompts.ENTITY_EXTRACTION_USER_PROMPT_TEMPLATE, str)
    
    def test_sentiment_analysis_prompts_exist(self):
        """Test that sentiment analysis prompts are defined."""
        assert hasattr(prompts, 'SENTIMENT_ANALYSIS_SYSTEM_PROMPT')
        assert hasattr(prompts, 'SENTIMENT_ANALYSIS_USER_PROMPT_TEMPLATE')
        assert isinstance(prompts.SENTIMENT_ANALYSIS_SYSTEM_PROMPT, str)
        assert isinstance(prompts.SENTIMENT_ANALYSIS_USER_PROMPT_TEMPLATE, str)
    
    def test_topic_extraction_prompts_exist(self):
        """Test that topic extraction prompts are defined."""
        assert hasattr(prompts, 'TOPIC_EXTRACTION_SYSTEM_PROMPT')
        assert hasattr(prompts, 'TOPIC_EXTRACTION_USER_PROMPT_TEMPLATE')
        assert isinstance(prompts.TOPIC_EXTRACTION_SYSTEM_PROMPT, str)
        assert isinstance(prompts.TOPIC_EXTRACTION_USER_PROMPT_TEMPLATE, str)
    
    def test_query_generation_prompts_exist(self):
        """Test that query generation prompts are defined."""
        assert hasattr(prompts, 'QUERY_GENERATION_SYSTEM_PROMPT')
        assert hasattr(prompts, 'QUERY_GENERATION_USER_PROMPT_TEMPLATE')
        assert isinstance(prompts.QUERY_GENERATION_SYSTEM_PROMPT, str)
        assert isinstance(prompts.QUERY_GENERATION_USER_PROMPT_TEMPLATE, str)
    
    def test_credibility_assessment_prompts_exist(self):
        """Test that credibility assessment prompts are defined."""
        assert hasattr(prompts, 'CREDIBILITY_ASSESSMENT_SYSTEM_PROMPT')
        assert hasattr(prompts, 'CREDIBILITY_ASSESSMENT_USER_PROMPT_TEMPLATE')
        assert isinstance(prompts.CREDIBILITY_ASSESSMENT_SYSTEM_PROMPT, str)
        assert isinstance(prompts.CREDIBILITY_ASSESSMENT_USER_PROMPT_TEMPLATE, str)
    
    def test_summary_user_prompt_template_formatting(self):
        """Test that summary user prompt template can be formatted."""
        formatted = prompts.SUMMARY_USER_PROMPT_TEMPLATE.format(
            max_length=500,
            text="test text"
        )
        assert "500" in formatted
        assert "test text" in formatted
    
    def test_entity_extraction_user_prompt_formatting(self):
        """Test that entity extraction user prompt template can be formatted."""
        formatted = prompts.ENTITY_EXTRACTION_USER_PROMPT_TEMPLATE.format(
            text="test text"
        )
        assert "test text" in formatted
    
    def test_sentiment_analysis_user_prompt_formatting(self):
        """Test that sentiment analysis user prompt template can be formatted."""
        formatted = prompts.SENTIMENT_ANALYSIS_USER_PROMPT_TEMPLATE.format(
            text="test text"
        )
        assert "test text" in formatted
        assert "SENTIMENT" in formatted
        assert "POLARITY" in formatted
    
    def test_topic_extraction_user_prompt_formatting(self):
        """Test that topic extraction user prompt template can be formatted."""
        formatted = prompts.TOPIC_EXTRACTION_USER_PROMPT_TEMPLATE.format(
            num_topics=5,
            text="test text"
        )
        assert "5" in formatted
        assert "test text" in formatted
    
    def test_query_generation_user_prompt_formatting(self):
        """Test that query generation user prompt template can be formatted."""
        formatted = prompts.QUERY_GENERATION_USER_PROMPT_TEMPLATE.format(
            num_queries=5,
            text="test text"
        )
        assert "5" in formatted
        assert "test text" in formatted
    
    def test_credibility_assessment_user_prompt_formatting(self):
        """Test that credibility assessment user prompt template can be formatted."""
        formatted = prompts.CREDIBILITY_ASSESSMENT_USER_PROMPT_TEMPLATE.format(
            title="Test Title",
            snippet="Test snippet",
            source="example.com",
            url="https://example.com/page"
        )
        assert "Test Title" in formatted
        assert "Test snippet" in formatted
        assert "example.com" in formatted
        assert "https://example.com/page" in formatted
    
    def test_prompts_not_empty(self):
        """Test that all prompts are not empty."""
        assert len(prompts.SUMMARY_SYSTEM_PROMPT) > 0
        assert len(prompts.SUMMARY_USER_PROMPT_TEMPLATE) > 0
        assert len(prompts.ENTITY_EXTRACTION_SYSTEM_PROMPT) > 0
        assert len(prompts.ENTITY_EXTRACTION_USER_PROMPT_TEMPLATE) > 0
        assert len(prompts.SENTIMENT_ANALYSIS_SYSTEM_PROMPT) > 0
        assert len(prompts.SENTIMENT_ANALYSIS_USER_PROMPT_TEMPLATE) > 0
        assert len(prompts.TOPIC_EXTRACTION_SYSTEM_PROMPT) > 0
        assert len(prompts.TOPIC_EXTRACTION_USER_PROMPT_TEMPLATE) > 0
        assert len(prompts.QUERY_GENERATION_SYSTEM_PROMPT) > 0
        assert len(prompts.QUERY_GENERATION_USER_PROMPT_TEMPLATE) > 0
        assert len(prompts.CREDIBILITY_ASSESSMENT_SYSTEM_PROMPT) > 0
        assert len(prompts.CREDIBILITY_ASSESSMENT_USER_PROMPT_TEMPLATE) > 0
