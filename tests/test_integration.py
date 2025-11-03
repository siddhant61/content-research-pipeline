"""
Integration tests for the content research pipeline.
"""

import pytest
from unittest.mock import patch, AsyncMock
from src.content_research_pipeline import ContentResearchPipeline
from src.content_research_pipeline.data.models import (
    PipelineResult,
    SearchResult,
    ScrapedContent,
    ContentType,
    AnalysisResult,
    SentimentAnalysis,
    VisualizationData
)


@pytest.mark.integration
class TestPipelineIntegration:
    """Integration tests for the complete pipeline."""
    
    @pytest.mark.asyncio
    async def test_end_to_end_pipeline(self):
        """Test complete end-to-end pipeline execution."""
        pipeline = ContentResearchPipeline()
        query = "artificial intelligence"
        
        # Mock search results
        mock_search_results = [
            SearchResult(
                title="AI Overview",
                snippet="Introduction to AI",
                link="https://example.com/ai",
                source="example.com"
            )
        ]
        
        # Mock scraped content
        mock_scraped = ScrapedContent(
            type=ContentType.TEXT,
            url="https://example.com/ai",
            raw_text="Artificial intelligence is transforming technology. Machine learning enables computers to learn.",
            text_content="Artificial intelligence is transforming technology. Machine learning enables computers to learn."
        )
        
        # Mock analysis result
        mock_analysis = AnalysisResult(
            query=query,
            summary="AI is transforming technology through machine learning.",
            entities=[],
            relationships=[],
            topics=[],
            sentiment=SentimentAnalysis(
                polarity=0.6,
                subjectivity=0.5,
                classification="positive"
            ),
            timeline=[],
            related_queries=[]
        )
        
        # Mock visualization
        mock_viz = VisualizationData()
        
        # Mock all service calls
        with patch('src.content_research_pipeline.services.search.search_service.search_web',
                   new_callable=AsyncMock, return_value=mock_search_results):
            with patch('src.content_research_pipeline.services.search.search_service.search_news',
                       new_callable=AsyncMock, return_value=[]):
                with patch('src.content_research_pipeline.services.search.search_service.search_images',
                           new_callable=AsyncMock, return_value=[]):
                    with patch('src.content_research_pipeline.services.search.search_service.search_videos',
                               new_callable=AsyncMock, return_value=[]):
                        with patch('src.content_research_pipeline.services.scraper.scraper_service.scrape_urls',
                                   new_callable=AsyncMock, return_value=[mock_scraped]):
                            with patch('src.content_research_pipeline.services.vector_store.vector_store_service.add_documents',
                                       new_callable=AsyncMock, return_value=True):
                                with patch('src.content_research_pipeline.core.analysis.analysis_processor.analyze',
                                           new_callable=AsyncMock, return_value=mock_analysis):
                                    with patch('src.content_research_pipeline.visualization.charts.chart_generator.generate_visualization_data',
                                               new_callable=AsyncMock, return_value=mock_viz):
                                        with patch('src.content_research_pipeline.visualization.html_generator.report_generator.generate_report',
                                                   new_callable=AsyncMock, return_value="<html><body>Test Report</body></html>"):
                                            result = await pipeline.run(query)
        
        # Verify result
        assert isinstance(result, PipelineResult)
        assert result.state.query == query
        assert result.state.status == "completed"
        assert len(result.state.search_results) > 0
        assert len(result.state.scraped_content) > 0
        assert result.state.analysis is not None
        assert result.html_report is not None
        assert result.processing_time is not None
        assert result.processing_time > 0
    
    @pytest.mark.asyncio
    async def test_pipeline_with_minimal_options(self):
        """Test pipeline with minimal options (no images/videos)."""
        pipeline = ContentResearchPipeline()
        query = "test query"
        
        mock_search_results = [
            SearchResult(
                title="Test",
                snippet="Test",
                link="https://example.com",
                source="example.com"
            )
        ]
        
        with patch('src.content_research_pipeline.services.search.search_service.search_web',
                   new_callable=AsyncMock, return_value=mock_search_results):
            with patch('src.content_research_pipeline.services.scraper.scraper_service.scrape_urls',
                       new_callable=AsyncMock, return_value=[]):
                with patch('src.content_research_pipeline.services.vector_store.vector_store_service.add_documents',
                           new_callable=AsyncMock, return_value=True):
                    with patch('src.content_research_pipeline.core.analysis.analysis_processor.analyze',
                               new_callable=AsyncMock):
                        with patch('src.content_research_pipeline.visualization.charts.chart_generator.generate_visualization_data',
                                   new_callable=AsyncMock, return_value=VisualizationData()):
                            with patch('src.content_research_pipeline.visualization.html_generator.report_generator.generate_report',
                                       new_callable=AsyncMock, return_value="<html></html>"):
                                result = await pipeline.run(
                                    query,
                                    include_images=False,
                                    include_videos=False,
                                    include_news=False
                                )
        
        assert isinstance(result, PipelineResult)
        assert result.state.query == query
        assert len(result.state.images) == 0
        assert len(result.state.videos) == 0
    
    @pytest.mark.asyncio
    async def test_pipeline_error_handling(self):
        """Test pipeline error handling."""
        pipeline = ContentResearchPipeline()
        query = "test query"
        
        # Mock a failure in search
        with patch('src.content_research_pipeline.services.search.search_service.search_web',
                   new_callable=AsyncMock, side_effect=Exception("Search failed")):
            result = await pipeline.run(query)
        
        # Pipeline should still return a result, even on failure
        assert isinstance(result, PipelineResult)
        assert result.state.status == "failed"
    
    @pytest.mark.asyncio
    async def test_pipeline_state_transitions(self):
        """Test pipeline state transitions during execution."""
        pipeline = ContentResearchPipeline()
        query = "test query"
        
        states_encountered = []
        
        # Create a function to capture state changes
        original_update_status = None
        
        def capture_status(new_status):
            states_encountered.append(new_status)
            if original_update_status:
                original_update_status(new_status)
        
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
                                               new_callable=AsyncMock, return_value=VisualizationData()):
                                        with patch('src.content_research_pipeline.visualization.html_generator.report_generator.generate_report',
                                                   new_callable=AsyncMock, return_value="<html></html>"):
                                            result = await pipeline.run(query)
        
        assert result.state.status == "completed"
