"""
Data models for the Content Research Pipeline.
"""

from typing import List, Dict, Any, Optional, Union
from pydantic import BaseModel, Field, validator, HttpUrl
from datetime import datetime
from enum import Enum


class ContentType(str, Enum):
    """Content type enumeration."""
    TEXT = "text"
    IMAGE = "image"
    VIDEO = "video"
    PDF = "pdf"
    ERROR = "error"


class EntityType(str, Enum):
    """Entity type enumeration."""
    PERSON = "PERSON"
    ORGANIZATION = "ORG"
    LOCATION = "GPE"
    PRODUCT = "PRODUCT"
    EVENT = "EVENT"
    WORK_OF_ART = "WORK_OF_ART"
    LAW = "LAW"
    FACILITY = "FAC"


class SearchResult(BaseModel):
    """Search result model."""
    title: str = Field(..., description="Title of the search result")
    snippet: str = Field(..., description="Snippet or description")
    link: HttpUrl = Field(..., description="URL of the result")
    source: str = Field(..., description="Source domain")
    credibility: Optional[float] = Field(None, ge=0.0, le=1.0, description="Credibility score")
    
    @validator("credibility")
    def validate_credibility(cls, v):
        """Ensure credibility is between 0 and 1."""
        if v is not None and not (0.0 <= v <= 1.0):
            raise ValueError("Credibility must be between 0.0 and 1.0")
        return v


class ImageResult(BaseModel):
    """Image result model."""
    title: str = Field(..., description="Title of the image")
    link: HttpUrl = Field(..., description="URL of the image")
    thumbnail: Optional[HttpUrl] = Field(None, description="Thumbnail URL")
    source: str = Field(..., description="Source domain")
    alt_text: Optional[str] = Field(None, description="Alternative text")


class VideoResult(BaseModel):
    """Video result model."""
    title: str = Field(..., description="Title of the video")
    link: HttpUrl = Field(..., description="URL of the video")
    thumbnail: Optional[HttpUrl] = Field(None, description="Thumbnail URL")
    snippet: str = Field(..., description="Video description")
    source: str = Field(..., description="Source domain")
    duration: Optional[str] = Field(None, description="Video duration")


class Entity(BaseModel):
    """Entity model."""
    text: str = Field(..., description="Entity text")
    label: EntityType = Field(..., description="Entity type")
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0, description="Confidence score")
    start: Optional[int] = Field(None, description="Start position in text")
    end: Optional[int] = Field(None, description="End position in text")


class Relationship(BaseModel):
    """Relationship model."""
    from_entity: str = Field(..., description="Source entity")
    to_entity: str = Field(..., description="Target entity")
    relationship_type: str = Field(..., description="Type of relationship")
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0, description="Confidence score")


class ScrapedContent(BaseModel):
    """Scraped content model."""
    type: ContentType = Field(..., description="Type of content")
    url: HttpUrl = Field(..., description="Source URL")
    raw_text: str = Field(..., description="Extracted text content")
    file_name: Optional[str] = Field(None, description="Downloaded file name")
    text_content: Optional[str] = Field(None, description="Processed text content")
    error_message: Optional[str] = Field(None, description="Error message if scraping failed")
    scraped_at: datetime = Field(default_factory=datetime.now, description="Scraping timestamp")
    
    @validator("raw_text")
    def validate_raw_text(cls, v):
        """Ensure raw_text is not empty for successful scrapes."""
        if not v and not cls.error_message:
            raise ValueError("raw_text cannot be empty unless there's an error")
        return v


class Topic(BaseModel):
    """Topic model."""
    id: int = Field(..., description="Topic ID")
    label: str = Field(..., description="Topic label")
    words: List[str] = Field(..., description="Top words in topic")
    weight: float = Field(..., ge=0.0, le=1.0, description="Topic weight")


class SentimentAnalysis(BaseModel):
    """Sentiment analysis model."""
    polarity: float = Field(..., ge=-1.0, le=1.0, description="Sentiment polarity")
    subjectivity: float = Field(..., ge=0.0, le=1.0, description="Subjectivity score")
    classification: str = Field(..., description="Sentiment classification")
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0, description="Confidence score")
    
    @validator("classification")
    def validate_classification(cls, v):
        """Validate sentiment classification."""
        valid_classifications = ["positive", "negative", "neutral"]
        if v.lower() not in valid_classifications:
            raise ValueError(f"Classification must be one of: {valid_classifications}")
        return v.lower()


class TimelineEvent(BaseModel):
    """Timeline event model."""
    date: str = Field(..., description="Event date")
    event: str = Field(..., description="Event description")
    source: str = Field(..., description="Source of the event")
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0, description="Confidence score")


class RelatedQuery(BaseModel):
    """Related query model."""
    query: str = Field(..., description="Related query text")
    source: HttpUrl = Field(..., description="Source URL")
    relevance: Optional[float] = Field(None, ge=0.0, le=1.0, description="Relevance score")


class AnalysisResult(BaseModel):
    """Analysis result model."""
    query: str = Field(..., description="Original query")
    summary: str = Field(..., description="Analysis summary")
    entities: List[Entity] = Field(default_factory=list, description="Extracted entities")
    relationships: List[Relationship] = Field(default_factory=list, description="Entity relationships")
    topics: List[Topic] = Field(default_factory=list, description="Identified topics")
    sentiment: SentimentAnalysis = Field(..., description="Sentiment analysis")
    timeline: List[TimelineEvent] = Field(default_factory=list, description="Timeline events")
    related_queries: List[RelatedQuery] = Field(default_factory=list, description="Related queries")
    analyzed_at: datetime = Field(default_factory=datetime.now, description="Analysis timestamp")


class PipelineState(BaseModel):
    """Pipeline state model."""
    query: str = Field(..., description="Search query")
    search_results: List[SearchResult] = Field(default_factory=list, description="Search results")
    images: List[ImageResult] = Field(default_factory=list, description="Image results")
    videos: List[VideoResult] = Field(default_factory=list, description="Video results")
    scraped_content: List[ScrapedContent] = Field(default_factory=list, description="Scraped content")
    analysis: Optional[AnalysisResult] = Field(None, description="Analysis results")
    status: str = Field("initialized", description="Pipeline status")
    created_at: datetime = Field(default_factory=datetime.now, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")
    
    def update_status(self, new_status: str):
        """Update pipeline status and timestamp."""
        self.status = new_status
        self.updated_at = datetime.now()


class VisualizationData(BaseModel):
    """Visualization data model."""
    nodes: List[Dict[str, Any]] = Field(default_factory=list, description="Graph nodes")
    edges: List[Dict[str, Any]] = Field(default_factory=list, description="Graph edges")
    timeline_dates: List[str] = Field(default_factory=list, description="Timeline dates")
    timeline_events: List[str] = Field(default_factory=list, description="Timeline events")
    word_cloud: Optional[str] = Field(None, description="Word cloud base64 data")
    treemap_labels: List[str] = Field(default_factory=list, description="Treemap labels")
    treemap_parents: List[str] = Field(default_factory=list, description="Treemap parents")
    treemap_values: List[float] = Field(default_factory=list, description="Treemap values")


class PipelineResult(BaseModel):
    """Final pipeline result model."""
    state: PipelineState = Field(..., description="Pipeline state")
    visualization: VisualizationData = Field(..., description="Visualization data")
    html_report: Optional[str] = Field(None, description="Generated HTML report")
    processing_time: Optional[float] = Field(None, description="Processing time in seconds")
    
    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            HttpUrl: lambda v: str(v),
        } 