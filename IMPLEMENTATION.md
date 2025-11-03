# Content Research Pipeline Implementation

This document describes the implementation of the core Content Research Pipeline components as specified in the requirements.

## Overview

The Content Research Pipeline is a comprehensive, AI-powered content research and analysis system that implements the following flow:

**Search → Scrape → Analyze → Store → Visualize**

## Implementation Summary

### Phase 1: Core Pipeline Orchestration and Web Scraping

#### 1.1 Pipeline Core (`src/content_research_pipeline/core/pipeline.py`)
- **ContentResearchPipeline** class with async `run()` method
- Orchestrates all pipeline phases sequentially
- Integrates search, scraping, storage, analysis, and visualization
- Implements comprehensive error handling and state management
- Tracks processing time and updates pipeline state

#### 1.2 Scraper Service (`src/content_research_pipeline/services/scraper.py`)
- **ScraperService** class for web content extraction
- Uses `trafilatura` for text extraction and `requests` for HTTP
- Implements `scrape_url()` for single URL scraping
- Implements `scrape_urls()` for concurrent multi-URL scraping
- Includes caching with 2-hour expiration
- Returns **ScrapedContent** models with proper error handling

#### 1.3 Scraping Integration
- Pipeline automatically processes all search results
- Scrapes web and news result URLs asynchronously
- Stores scraped content in `PipelineState.scraped_content`
- Limits concurrent requests to prevent overload (max 5)

### Phase 2: Storage, Analysis, and LLM Interaction

#### 2.1 Vector Store Service (`src/content_research_pipeline/services/vector_store.py`)
- **VectorStoreService** using ChromaDB for persistent storage
- Implements `add_documents()` for storing scraped content
- Implements `retrieve_documents()` for semantic search
- Supports collection management and statistics
- Async operations using thread pools

#### 2.2 LLM Service (`src/content_research_pipeline/services/llm.py`)
- **LLMService** using langchain-openai (ChatOpenAI)
- `generate_summary()` - Creates concise summaries
- `extract_entities()` - Named entity recognition
- `analyze_sentiment()` - Sentiment analysis with polarity
- `extract_topics()` - Topic modeling
- `generate_queries()` - Related query generation
- Configured with `llm_model` and `llm_temperature` from settings

#### 2.3 Analysis Core (`src/content_research_pipeline/core/analysis.py`)
- **AnalysisProcessor** class for comprehensive analysis
- Integrates LLM service and spaCy for NLP
- Extracts entities using both LLM and spaCy
- Performs sentiment analysis with TextBlob fallback
- Identifies topics and themes
- Extracts timeline events using regex patterns
- Generates entity relationships
- Returns complete **AnalysisResult** model

### Phase 3: Visualization and Finalization

#### 3.1 Visualization/Charts (`src/content_research_pipeline/visualization/charts.py`)
- **ChartGenerator** class for visualization data preparation
- Generates entity relationship graph (nodes and edges)
- Creates timeline data structures
- Generates word clouds using matplotlib and wordcloud
- Creates topic treemap data
- Returns **VisualizationData** model

#### 3.2 HTML Report Generation (`src/content_research_pipeline/visualization/html_generator.py`)
- **ReportGenerator** using Jinja2 templates
- Generates comprehensive HTML reports with:
  - Executive summary
  - Statistics overview
  - Sentiment analysis
  - Entity visualization
  - Topic breakdown
  - Word cloud display
  - Timeline of events
  - Related queries
  - Source links
- Fully styled with modern CSS
- Responsive design

#### 3.3 Complete Pipeline
- All phases integrated and functional
- Processing time tracked from start to finish
- Proper error handling with fallback to partial results
- Status updates throughout execution
- Returns **PipelineResult** with all data

## Architecture

### Data Flow

```
1. User Query
   ↓
2. Search Phase (search_service)
   - Web search
   - News search
   - Image search
   - Video search
   ↓
3. Scraping Phase (scraper_service)
   - Extract content from URLs
   - Parse with trafilatura
   ↓
4. Storage Phase (vector_store_service)
   - Store in ChromaDB
   - Enable semantic search
   ↓
5. Analysis Phase (analysis_processor + llm_service)
   - Generate summary
   - Extract entities
   - Analyze sentiment
   - Identify topics
   - Extract timeline
   ↓
6. Visualization Phase (chart_generator)
   - Create graph data
   - Generate word cloud
   - Prepare charts
   ↓
7. Report Generation (report_generator)
   - Compile HTML report
   - Include all visualizations
   ↓
8. PipelineResult
   - Complete state
   - Visualizations
   - HTML report
   - Processing metrics
```

### Key Features

1. **Asynchronous Architecture**
   - All I/O operations use async/await
   - Concurrent processing where possible
   - Thread pool for blocking operations (requests, ChromaDB, etc.)

2. **Caching**
   - Search results cached via `@cache_result` decorator
   - Scraped content cached for 2 hours
   - Configurable expiration times

3. **Error Handling**
   - Graceful degradation on failures
   - Partial results returned when possible
   - Comprehensive logging

4. **Configuration**
   - Environment variable based (via pydantic-settings)
   - Settings for all services
   - Configurable limits and thresholds

5. **Modularity**
   - Clear separation of concerns
   - Each service is independently testable
   - Easy to extend or replace components

## Testing

### Test Coverage

1. **Unit Tests**
   - `test_scraper.py` - Scraper service tests
   - `test_pipeline.py` - Pipeline orchestration tests
   - `test_analysis.py` - Analysis processor tests
   - `test_visualization.py` - Visualization module tests
   - `test_config.py` - Configuration tests (existing)

2. **Integration Tests**
   - `test_integration.py` - End-to-end pipeline tests
   - Tests complete workflow with mocked services
   - Verifies state transitions and data flow

### Running Tests

```bash
# Run all tests
pytest tests/

# Run with coverage
pytest tests/ --cov=src

# Run specific test file
pytest tests/test_pipeline.py -v

# Run integration tests only
pytest tests/test_integration.py -v -m integration
```

## Usage

### Programmatic Usage

```python
from content_research_pipeline import ContentResearchPipeline

async def main():
    pipeline = ContentResearchPipeline()
    result = await pipeline.run("artificial intelligence")
    
    # Access results
    print(result.state.analysis.summary)
    print(f"Found {len(result.state.analysis.entities)} entities")
    
    # Save HTML report
    with open("report.html", "w") as f:
        f.write(result.html_report)

import asyncio
asyncio.run(main())
```

### CLI Usage

```bash
# Run research command
python -m content_research_pipeline.cli research "climate change" \
  --output results/ \
  --format html \
  --verbose

# Quick search
python -m content_research_pipeline.cli search "machine learning" \
  --type web \
  --num-results 10
```

## Dependencies

### Core Dependencies
- **pydantic** - Data validation and settings
- **click** - CLI framework
- **tenacity** - Retry logic
- **asyncio** - Async operations

### AI/ML Dependencies
- **langchain** - LLM orchestration
- **langchain-openai** - OpenAI integration
- **openai** - OpenAI API client
- **spacy** - NLP processing

### Data Processing
- **trafilatura** - Web content extraction
- **requests** - HTTP client
- **chromadb** - Vector database
- **textblob** - Sentiment analysis

### Visualization
- **matplotlib** - Plotting
- **wordcloud** - Word cloud generation
- **jinja2** - Template engine

## Configuration

Required environment variables:

```bash
OPENAI_API_KEY=your_openai_key
GOOGLE_API_KEY=your_google_key
GOOGLE_CSE_ID=your_cse_id
```

Optional configuration:

```bash
LOG_LEVEL=INFO
CHROMA_PERSIST_DIRECTORY=./chroma_db
CACHE_EXPIRE_SECONDS=3600
MAX_SEARCH_RESULTS=5
MAX_TOPICS=5
LLM_MODEL=gpt-4o-mini
LLM_TEMPERATURE=0.0
```

## Files Created

### Core Modules
- `src/content_research_pipeline/core/pipeline.py` - Main orchestration
- `src/content_research_pipeline/core/analysis.py` - Analysis processing

### Services
- `src/content_research_pipeline/services/scraper.py` - Web scraping
- `src/content_research_pipeline/services/vector_store.py` - Vector DB
- `src/content_research_pipeline/services/llm.py` - LLM interactions

### Visualization
- `src/content_research_pipeline/visualization/charts.py` - Chart generation
- `src/content_research_pipeline/visualization/html_generator.py` - HTML reports

### Tests
- `tests/test_scraper.py` - Scraper tests
- `tests/test_pipeline.py` - Pipeline tests
- `tests/test_analysis.py` - Analysis tests
- `tests/test_visualization.py` - Visualization tests
- `tests/test_integration.py` - Integration tests

## Next Steps

The core pipeline is now complete and functional. Potential enhancements:

1. **Additional Analysis**
   - Citation extraction
   - Fact checking
   - Source credibility scoring

2. **Enhanced Visualizations**
   - Interactive charts using Plotly
   - Network graphs for entity relationships
   - Sentiment over time charts

3. **API Development**
   - FastAPI endpoints (structure already exists)
   - WebSocket support for real-time updates
   - Job queue for background processing

4. **Performance Optimization**
   - Implement proper connection pooling
   - Add request rate limiting
   - Optimize ChromaDB queries

5. **Additional Sources**
   - Academic paper databases
   - Social media integration
   - Podcast and video transcription

## License

MIT License - See LICENSE file for details
