"""
Tests for credibility assessment functionality.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from src.content_research_pipeline.core.analysis import analysis_processor
from src.content_research_pipeline.services.llm import llm_service
from src.content_research_pipeline.data.models import SearchResult, PipelineState


class TestCredibility:
    """Test credibility assessment functionality."""
    
    @pytest.mark.asyncio
    async def test_assess_credibility_returns_valid_score(self):
        """Test that assess_credibility returns a score between 0 and 1."""
        with patch.object(llm_service.llm, 'invoke') as mock_invoke:
            # Mock LLM response
            mock_response = Mock()
            mock_response.content = "0.85"
            mock_invoke.return_value = mock_response
            
            score = await llm_service.assess_credibility(
                title="Test Article",
                snippet="Test snippet",
                source="example.com",
                url="https://example.com/article"
            )
            
            assert 0.0 <= score <= 1.0
            assert score == 0.85
    
    @pytest.mark.asyncio
    async def test_assess_credibility_handles_invalid_response(self):
        """Test that assess_credibility handles invalid LLM responses."""
        with patch.object(llm_service.llm, 'invoke') as mock_invoke:
            # Mock invalid LLM response
            mock_response = Mock()
            mock_response.content = "invalid"
            mock_invoke.return_value = mock_response
            
            score = await llm_service.assess_credibility(
                title="Test Article",
                snippet="Test snippet",
                source="example.com",
                url="https://example.com/article"
            )
            
            # Should return default score of 0.5
            assert score == 0.5
    
    @pytest.mark.asyncio
    async def test_assess_credibility_clamps_out_of_range_scores(self):
        """Test that assess_credibility clamps scores outside valid range."""
        with patch.object(llm_service.llm, 'invoke') as mock_invoke:
            # Mock LLM response with out-of-range score
            mock_response = Mock()
            mock_response.content = "1.5"
            mock_invoke.return_value = mock_response
            
            score = await llm_service.assess_credibility(
                title="Test Article",
                snippet="Test snippet",
                source="example.com",
                url="https://example.com/article"
            )
            
            # Should be clamped to 1.0
            assert score == 1.0
    
    @pytest.mark.asyncio
    async def test_assess_credibility_handles_exceptions(self):
        """Test that assess_credibility handles exceptions gracefully."""
        with patch.object(llm_service.llm, 'invoke') as mock_invoke:
            # Mock exception
            mock_invoke.side_effect = Exception("Test error")
            
            score = await llm_service.assess_credibility(
                title="Test Article",
                snippet="Test snippet",
                source="example.com",
                url="https://example.com/article"
            )
            
            # Should return default score of 0.5 on error
            assert score == 0.5
    
    @pytest.mark.asyncio
    async def test_calculate_credibility_updates_search_results(self):
        """Test that calculate_credibility updates search results."""
        # Create test pipeline state with search results
        state = PipelineState(query="test query")
        state.search_results = [
            SearchResult(
                title="Article 1",
                snippet="Snippet 1",
                link="https://example.com/1",
                source="example.com",
                credibility=None
            ),
            SearchResult(
                title="Article 2",
                snippet="Snippet 2",
                link="https://example.com/2",
                source="example.com",
                credibility=None
            )
        ]
        
        with patch.object(llm_service.llm, 'invoke') as mock_invoke:
            # Mock LLM responses
            mock_response = Mock()
            mock_response.content = "0.8"
            mock_invoke.return_value = mock_response
            
            await analysis_processor.calculate_credibility(state)
            
            # Verify all results have credibility scores
            for result in state.search_results:
                assert result.credibility is not None
                assert 0.0 <= result.credibility <= 1.0
    
    @pytest.mark.asyncio
    async def test_calculate_credibility_skips_existing_scores(self):
        """Test that calculate_credibility skips results with existing scores."""
        # Create test pipeline state with one result already having a score
        state = PipelineState(query="test query")
        state.search_results = [
            SearchResult(
                title="Article 1",
                snippet="Snippet 1",
                link="https://example.com/1",
                source="example.com",
                credibility=0.9  # Already has score
            ),
            SearchResult(
                title="Article 2",
                snippet="Snippet 2",
                link="https://example.com/2",
                source="example.com",
                credibility=None  # Needs score
            )
        ]
        
        with patch.object(llm_service, 'assess_credibility') as mock_assess:
            mock_assess.return_value = 0.7
            
            await analysis_processor.calculate_credibility(state)
            
            # Should only call assess_credibility once (for the second result)
            assert mock_assess.call_count == 1
            
            # First result should keep original score
            assert state.search_results[0].credibility == 0.9
            
            # Second result should have new score
            assert state.search_results[1].credibility == 0.7
    
    @pytest.mark.asyncio
    async def test_calculate_credibility_handles_empty_results(self):
        """Test that calculate_credibility handles empty search results."""
        state = PipelineState(query="test query")
        state.search_results = []
        
        # Should not raise an exception
        await analysis_processor.calculate_credibility(state)
    
    @pytest.mark.asyncio
    async def test_calculate_credibility_sets_default_on_error(self):
        """Test that calculate_credibility sets default score on error."""
        state = PipelineState(query="test query")
        state.search_results = [
            SearchResult(
                title="Article 1",
                snippet="Snippet 1",
                link="https://example.com/1",
                source="example.com",
                credibility=None
            )
        ]
        
        with patch.object(llm_service, 'assess_credibility') as mock_assess:
            # Mock exception during assessment
            mock_assess.side_effect = Exception("Test error")
            
            await analysis_processor.calculate_credibility(state)
            
            # Should have default credibility of 0.5
            assert state.search_results[0].credibility == 0.5
