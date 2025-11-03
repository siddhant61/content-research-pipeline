"""
Tests for visualization modules.
"""

import pytest
from unittest.mock import patch, AsyncMock
from src.content_research_pipeline.visualization.charts import ChartGenerator
from src.content_research_pipeline.visualization.html_generator import ReportGenerator
from src.content_research_pipeline.data.models import (
    AnalysisResult,
    Entity,
    EntityType,
    Relationship,
    Topic,
    TimelineEvent,
    SentimentAnalysis,
    PipelineState,
    VisualizationData
)


class TestChartGenerator:
    """Test chart generator functionality."""
    
    @pytest.fixture
    def generator(self):
        """Create a chart generator instance."""
        return ChartGenerator()
    
    @pytest.fixture
    def sample_analysis(self):
        """Create sample analysis data."""
        return AnalysisResult(
            query="test query",
            summary="Test summary",
            entities=[
                Entity(text="Entity1", label=EntityType.PERSON, confidence=0.9),
                Entity(text="Entity2", label=EntityType.ORG, confidence=0.8)
            ],
            relationships=[
                Relationship(
                    from_entity="Entity1",
                    to_entity="Entity2",
                    relationship_type="works_at",
                    confidence=0.7
                )
            ],
            topics=[
                Topic(id=0, label="Topic1", words=["word1", "word2"], weight=0.8)
            ],
            sentiment=SentimentAnalysis(
                polarity=0.5,
                subjectivity=0.5,
                classification="positive"
            ),
            timeline=[
                TimelineEvent(
                    date="2024-01-01",
                    event="Test event",
                    source="https://example.com"
                )
            ],
            related_queries=[]
        )
    
    @pytest.mark.asyncio
    async def test_generate_visualization_data(self, generator, sample_analysis):
        """Test visualization data generation."""
        result = await generator.generate_visualization_data(sample_analysis)
        
        assert isinstance(result, VisualizationData)
        assert len(result.nodes) > 0
        assert len(result.edges) >= 0
    
    @pytest.mark.asyncio
    async def test_generate_entity_graph(self, generator, sample_analysis):
        """Test entity graph generation."""
        nodes, edges = await generator._generate_entity_graph(
            sample_analysis.entities,
            sample_analysis.relationships
        )
        
        assert len(nodes) == 2
        assert all('id' in node for node in nodes)
        assert all('label' in node for node in nodes)
    
    @pytest.mark.asyncio
    async def test_generate_timeline_data(self, generator, sample_analysis):
        """Test timeline data generation."""
        dates, events = await generator._generate_timeline_data(sample_analysis.timeline)
        
        assert len(dates) == 1
        assert len(events) == 1
        assert dates[0] == "2024-01-01"
    
    @pytest.mark.asyncio
    async def test_generate_topic_treemap(self, generator, sample_analysis):
        """Test topic treemap generation."""
        labels, parents, values = await generator._generate_topic_treemap(sample_analysis.topics)
        
        assert len(labels) > 0
        assert len(parents) == len(labels)
        assert len(values) == len(labels)


class TestReportGenerator:
    """Test report generator functionality."""
    
    @pytest.fixture
    def generator(self):
        """Create a report generator instance."""
        return ReportGenerator()
    
    @pytest.fixture
    def sample_state(self):
        """Create sample pipeline state."""
        return PipelineState(
            query="test query",
            search_results=[],
            images=[],
            videos=[],
            scraped_content=[],
            analysis=AnalysisResult(
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
        )
    
    @pytest.mark.asyncio
    async def test_generate_report(self, generator, sample_state):
        """Test HTML report generation."""
        visualization = VisualizationData()
        
        result = await generator.generate_report(
            state=sample_state,
            visualization=visualization,
            processing_time=1.5
        )
        
        assert isinstance(result, str)
        assert "<html" in result.lower()
        assert "test query" in result.lower()
    
    @pytest.mark.asyncio
    async def test_generate_report_with_analysis(self, generator, sample_state):
        """Test report generation with analysis data."""
        visualization = VisualizationData()
        
        result = await generator.generate_report(
            state=sample_state,
            visualization=visualization,
            processing_time=2.0
        )
        
        assert "Test summary" in result
        assert "positive" in result.lower()
    
    def test_get_template(self, generator):
        """Test template retrieval."""
        template = generator._get_template()
        
        assert template is not None
        assert hasattr(template, 'render')
    
    def test_generate_error_report(self, generator):
        """Test error report generation."""
        result = generator._generate_error_report("test query", "Test error")
        
        assert isinstance(result, str)
        assert "<html" in result.lower()
        assert "test query" in result
        assert "Test error" in result
