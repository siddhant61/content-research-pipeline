"""
Tests for pipeline orchestration.
"""

import pytest
from unittest.mock import patch, AsyncMock, Mock
from src.content_research_pipeline.core.pipeline import ContentResearchPipeline
from src.content_research_pipeline.data.models import (
    PipelineResult,
    PipelineState,
    SearchResult,
    ScrapedContent,
    ContentType,
    AnalysisResult,
    SentimentAnalysis
)


class TestContentResearchPipeline:
    """Test pipeline orchestration."""
    
    @pytest.fixture
    def pipeline(self):
        """Create a pipeline instance."""
        return ContentResearchPipeline()
    
    @pytest.mark.asyncio
    async def test_pipeline_initialization(self, pipeline):
        """Test pipeline initialization."""
        assert pipeline is not None
        assert pipeline.logger is not None
    
    @pytest.mark.asyncio
    async def test_search_phase(self, pipeline):
        """Test search phase execution."""
        state = PipelineState(query="test query")
        
        # Mock search results
        mock_results = [
            SearchResult(
                title="Test Result",
                snippet="Test snippet",
                link="https://example.com",
                source="example.com"
            )
        ]
        
        with patch('src.content_research_pipeline.services.search.search_service.search_web',
                   new_callable=AsyncMock, return_value=mock_results):
            with patch('src.content_research_pipeline.services.search.search_service.search_news',
                       new_callable=AsyncMock, return_value=[]):
                with patch('src.content_research_pipeline.services.search.search_service.search_images',
                           new_callable=AsyncMock, return_value=[]):
                    with patch('src.content_research_pipeline.services.search.search_service.search_videos',
                               new_callable=AsyncMock, return_value=[]):
                        await pipeline._search_phase(state, True, True, True)
        
        assert len(state.search_results) > 0
    
    @pytest.mark.asyncio
    async def test_scraping_phase(self, pipeline):
        """Test scraping phase execution."""
        state = PipelineState(query="test query")
        state.search_results = [
            SearchResult(
                title="Test",
                snippet="Test",
                link="https://example.com",
                source="example.com"
            )
        ]
        
        mock_scraped = ScrapedContent(
            type=ContentType.TEXT,
            url="https://example.com",
            raw_text="Test content",
            text_content="Test content"
        )
        
        with patch('src.content_research_pipeline.services.scraper.scraper_service.scrape_urls',
                   new_callable=AsyncMock, return_value=[mock_scraped]):
            await pipeline._scraping_phase(state)
        
        assert len(state.scraped_content) > 0
    
    @pytest.mark.asyncio
    async def test_storage_phase(self, pipeline):
        """Test storage phase execution."""
        state = PipelineState(query="test query")
        state.scraped_content = [
            ScrapedContent(
                type=ContentType.TEXT,
                url="https://example.com",
                raw_text="Test",
                text_content="Test"
            )
        ]
        
        with patch('src.content_research_pipeline.services.vector_store.vector_store_service.add_documents',
                   new_callable=AsyncMock, return_value=True):
            await pipeline._storage_phase(state)
        
        # No assertion needed - just checking it doesn't raise
    
    @pytest.mark.asyncio
    async def test_analysis_phase(self, pipeline):
        """Test analysis phase execution."""
        state = PipelineState(query="test query")
        state.scraped_content = [
            ScrapedContent(
                type=ContentType.TEXT,
                url="https://example.com",
                raw_text="Test content",
                text_content="Test content"
            )
        ]
        
        mock_analysis = AnalysisResult(
            query="test query",
            summary="Test summary",
            entities=[],
            relationships=[],
            topics=[],
            sentiment=SentimentAnalysis(
                polarity=0.5,
                subjectivity=0.5,
                classification="positive"
            ),
            timeline=[],
            related_queries=[]
        )
        
        with patch('src.content_research_pipeline.core.analysis.analysis_processor.analyze',
                   new_callable=AsyncMock, return_value=mock_analysis):
            await pipeline._analysis_phase(state)
        
        assert state.analysis is not None
    
    @pytest.mark.asyncio
    async def test_pipeline_run_complete(self, pipeline):
        """Test complete pipeline run."""
        query = "test query"
        
        # Mock all services
        with patch('src.content_research_pipeline.services.search.search_service.search_web',
                   new_callable=AsyncMock, return_value=[]):
            with patch('src.content_research_pipeline.services.search.search_service.search_news',
                       new_callable=AsyncMock, return_value=[]):
                with patch('src.content_research_pipeline.services.search.search_service.search_images',
                           new_callable=AsyncMock, return_value=[]):
                    with patch('src.content_research_pipeline.services.search.search_service.search_videos',
                               new_callable=AsyncMock, return_value=[]):
                        with patch('src.content_research_pipeline.services.scraper.scraper_service.scrape_urls',
                                   new_callable=AsyncMock, return_value=[]):
                            with patch('src.content_research_pipeline.services.vector_store.vector_store_service.add_documents',
                                       new_callable=AsyncMock, return_value=True):
                                with patch('src.content_research_pipeline.core.analysis.analysis_processor.analyze',
                                           new_callable=AsyncMock):
                                    with patch('src.content_research_pipeline.visualization.charts.chart_generator.generate_visualization_data',
                                               new_callable=AsyncMock):
                                        with patch('src.content_research_pipeline.visualization.html_generator.report_generator.generate_report',
                                                   new_callable=AsyncMock, return_value="<html></html>"):
                                            result = await pipeline.run(query)
        
        assert isinstance(result, PipelineResult)
        assert result.state.query == query
        assert result.processing_time is not None
