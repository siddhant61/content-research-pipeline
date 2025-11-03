"""
Tests for analysis module.
"""

import pytest
from unittest.mock import patch, AsyncMock
from src.content_research_pipeline.core.analysis import AnalysisProcessor
from src.content_research_pipeline.data.models import (
    ScrapedContent,
    ContentType,
    AnalysisResult,
    Entity,
    EntityType
)


class TestAnalysisProcessor:
    """Test analysis processor functionality."""
    
    @pytest.fixture
    def processor(self):
        """Create an analysis processor instance."""
        return AnalysisProcessor()
    
    @pytest.mark.asyncio
    async def test_analyze_with_content(self, processor):
        """Test analysis with valid content."""
        query = "test query"
        scraped_contents = [
            ScrapedContent(
                type=ContentType.TEXT,
                url="https://example.com",
                raw_text="Test content with meaningful information about climate change.",
                text_content="Test content with meaningful information about climate change."
            )
        ]
        
        # Mock LLM service methods
        with patch('src.content_research_pipeline.services.llm.llm_service.generate_summary',
                   new_callable=AsyncMock, return_value="Test summary"):
            with patch('src.content_research_pipeline.services.llm.llm_service.extract_entities',
                       new_callable=AsyncMock, return_value=[]):
                with patch('src.content_research_pipeline.services.llm.llm_service.analyze_sentiment',
                           new_callable=AsyncMock, return_value={'polarity': 0.5, 'subjectivity': 0.5, 'classification': 'positive', 'confidence': 0.8}):
                    with patch('src.content_research_pipeline.services.llm.llm_service.extract_topics',
                               new_callable=AsyncMock, return_value=[]):
                        with patch('src.content_research_pipeline.services.llm.llm_service.generate_queries',
                                   new_callable=AsyncMock, return_value=[]):
                            result = await processor.analyze(query, scraped_contents)
        
        assert isinstance(result, AnalysisResult)
        assert result.query == query
        assert result.summary == "Test summary"
        assert result.sentiment is not None
    
    @pytest.mark.asyncio
    async def test_analyze_empty_content(self, processor):
        """Test analysis with empty content."""
        query = "test query"
        scraped_contents = []
        
        result = await processor.analyze(query, scraped_contents)
        
        assert isinstance(result, AnalysisResult)
        assert result.query == query
        assert "could not be completed" in result.summary.lower()
    
    @pytest.mark.asyncio
    async def test_extract_entities(self, processor):
        """Test entity extraction."""
        text = "Apple Inc. is located in California. Tim Cook is the CEO."
        
        # Mock LLM service
        mock_entities = [
            {'text': 'Apple Inc.', 'label': 'ORG', 'confidence': 0.9},
            {'text': 'California', 'label': 'GPE', 'confidence': 0.9},
            {'text': 'Tim Cook', 'label': 'PERSON', 'confidence': 0.9}
        ]
        
        with patch('src.content_research_pipeline.services.llm.llm_service.extract_entities',
                   new_callable=AsyncMock, return_value=mock_entities):
            entities = await processor._extract_entities(text)
        
        assert len(entities) > 0
        assert all(isinstance(e, Entity) for e in entities)
    
    @pytest.mark.asyncio
    async def test_analyze_sentiment(self, processor):
        """Test sentiment analysis."""
        text = "This is a wonderful and amazing product!"
        
        mock_sentiment = {
            'polarity': 0.8,
            'subjectivity': 0.9,
            'classification': 'positive',
            'confidence': 0.9
        }
        
        with patch('src.content_research_pipeline.services.llm.llm_service.analyze_sentiment',
                   new_callable=AsyncMock, return_value=mock_sentiment):
            sentiment = await processor._analyze_sentiment(text)
        
        assert sentiment['classification'] == 'positive'
        assert sentiment['polarity'] > 0
    
    @pytest.mark.asyncio
    async def test_extract_topics(self, processor):
        """Test topic extraction."""
        text = "Climate change is affecting global temperatures and weather patterns."
        
        mock_topics = [
            {'id': 0, 'label': 'Climate Change', 'words': ['climate', 'change'], 'weight': 1.0}
        ]
        
        with patch('src.content_research_pipeline.services.llm.llm_service.extract_topics',
                   new_callable=AsyncMock, return_value=mock_topics):
            topics = await processor._extract_topics(text)
        
        assert len(topics) > 0
    
    def test_combine_texts(self, processor):
        """Test text combination."""
        scraped_contents = [
            ScrapedContent(
                type=ContentType.TEXT,
                url="https://example1.com",
                raw_text="Text 1",
                text_content="Text content 1 with sufficient length for processing."
            ),
            ScrapedContent(
                type=ContentType.TEXT,
                url="https://example2.com",
                raw_text="Text 2",
                text_content="Text content 2 with sufficient length for processing."
            )
        ]
        
        combined = processor._combine_texts(scraped_contents)
        
        assert "Text content 1" in combined
        assert "Text content 2" in combined
