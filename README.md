# Content Research Pipeline

A comprehensive, AI-powered content research and analysis system that aggregates information from multiple sources, performs intelligent analysis, and generates detailed reports with visualizations.

## Features

- **Multi-Source Content Aggregation**: Search across web, news, images, and videos
- **AI-Powered Analysis**: Sentiment analysis, topic modeling, and entity extraction
- **Source Credibility Assessment**: AI-powered credibility scoring for each source
- **Interactive Visualizations**: Entity relationship graphs with vis.js, enhanced timelines, and word clouds
- **Vector Database Storage**: Persistent storage with Chroma for semantic search
- **Comprehensive Reports**: HTML dashboards and JSON exports
- **Caching System**: Intelligent caching for improved performance
- **CLI Interface**: Command-line tools for easy operation
- **Web API**: RESTful API for background job processing and integration (optional)

## Installation

### Prerequisites

- Python 3.8+
- OpenAI API key
- Google Search API key and Custom Search Engine ID

### Setup

1. **Clone the repository**:
```bash
git clone https://github.com/siddhant61/content-research-pipeline.git
cd content-research-pipeline
```

2. **Install dependencies**:
```bash
pip install -r requirements.txt
```

3. **Download spaCy language model**:
```bash
python -m spacy download en_core_web_sm
```

4. **Set up environment variables**:
```bash
cp env.example .env
# Edit .env with your API keys
```

Required environment variables:
- `OPENAI_API_KEY`: Your OpenAI API key
- `GOOGLE_API_KEY`: Your Google Search API key
- `GOOGLE_CSE_ID`: Your Google Custom Search Engine ID

5. **Validate setup**:
```bash
python -m content_research_pipeline.cli validate
```

## Usage

### Command Line Interface

The CLI provides several commands for different operations:

#### Research Command
Perform comprehensive research on a topic:

```bash
python -m content_research_pipeline.cli research "Impact of climate change on agriculture"
```

Options:
- `--output, -o`: Output directory for results
- `--format, -f`: Output format (html, json, both)
- `--max-results, -m`: Maximum number of search results
- `--no-images`: Skip image search
- `--no-videos`: Skip video search
- `--no-news`: Skip news search
- `--verbose, -v`: Enable verbose logging

#### Quick Search
Perform a quick search without full analysis:

```bash
python -m content_research_pipeline.cli search "artificial intelligence" --type web --num-results 10
```

#### Cache Management
Manage the application cache:

```bash
# Show cache statistics
python -m content_research_pipeline.cli cache --stats

# Clear cache
python -m content_research_pipeline.cli cache --clear
```

#### Configuration
Show current configuration:

```bash
python -m content_research_pipeline.cli config
```

#### Web Server (Optional)
Start the web API server:

```bash
python -m content_research_pipeline.cli serve --host 0.0.0.0 --port 8000
```

Options:
- `--host`: Host to bind to (default: 0.0.0.0)
- `--port`: Port to bind to (default: 8000)
- `--reload`: Enable auto-reload for development

### Programmatic Usage

```python
from content_research_pipeline import ContentResearchPipeline

async def main():
    pipeline = ContentResearchPipeline()
    result = await pipeline.run("climate change impacts")
    
    # Access results
    print(f"Analysis: {result.state.analysis.summary}")
    print(f"Topics: {result.state.analysis.topics}")
    print(f"Sentiment: {result.state.analysis.sentiment}")
    
    # Save HTML report
    with open("report.html", "w") as f:
        f.write(result.html_report)

import asyncio
asyncio.run(main())
```

### API Usage

The FastAPI server provides RESTful endpoints for background job processing:

#### Start a Research Job
```bash
curl -X POST "http://localhost:8000/research" \
  -H "Content-Type: application/json" \
  -d '{"query": "climate change impacts", "include_images": true, "include_videos": true}'
```

Response:
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  "message": "Research job created successfully. Use /status/{job_id} to check progress."
}
```

#### Check Job Status
```bash
curl "http://localhost:8000/status/550e8400-e29b-41d4-a716-446655440000"
```

Response (when completed):
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "query": "climate change impacts",
  "created_at": "2024-01-01T00:00:00",
  "completed_at": "2024-01-01T00:05:30",
  "result": {
    "state": {...},
    "visualization": {...},
    "processing_time": 330.5
  }
}
```

#### List All Jobs
```bash
curl "http://localhost:8000/jobs?limit=10&status=completed"
```

#### Delete a Job
```bash
curl -X DELETE "http://localhost:8000/jobs/550e8400-e29b-41d4-a716-446655440000"
```

### API Endpoints

- `GET /` - API information
- `GET /health` - Health check
- `POST /research` - Start a new research job
- `GET /status/{job_id}` - Get job status and results
- `GET /jobs` - List all jobs with optional filtering
- `DELETE /jobs/{job_id}` - Delete a completed or failed job
```

## Project Structure

```
content_research_pipeline/
├── src/content_research_pipeline/
│   ├── __init__.py                 # Package initialization
│   ├── cli.py                      # Command-line interface
│   ├── config/
│   │   ├── __init__.py
│   │   ├── settings.py             # Configuration management
│   │   ├── logging.py              # Logging configuration
│   │   └── prompts.py              # LLM prompt templates
│   ├── core/
│   │   ├── __init__.py
│   │   ├── pipeline.py             # Main pipeline orchestration
│   │   ├── analysis.py             # Content analysis functions
│   │   └── entities.py             # Entity extraction and graph creation
│   ├── services/
│   │   ├── __init__.py
│   │   ├── search.py               # Google Search API integration
│   │   ├── scraper.py              # Web scraping functionality
│   │   ├── vector_store.py         # Vector database operations
│   │   └── llm.py                  # Language model interactions
│   ├── data/
│   │   ├── __init__.py
│   │   ├── models.py               # Pydantic models
│   │   └── schemas.py              # API response schemas
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── text_processing.py      # Text processing utilities
│   │   ├── media_handlers.py       # Image/video handling
│   │   └── caching.py              # Caching functionality
│   ├── visualization/
│   │   ├── __init__.py
│   │   ├── html_generator.py       # HTML report generation
│   │   └── charts.py               # Chart generation utilities
│   └── api/                        # Optional FastAPI endpoints
│       ├── __init__.py
│       └── main.py                 # FastAPI application
├── tests/                          # Test files
├── docs/                           # Documentation
├── requirements.txt                # Python dependencies
├── env.example                     # Environment variables template
├── .gitignore                      # Git ignore file
└── README.md                       # This file
```

## Configuration

The application uses environment variables for configuration. Copy `env.example` to `.env` and configure:

### Required Settings
- `OPENAI_API_KEY`: OpenAI API key for AI analysis
- `GOOGLE_API_KEY`: Google Search API key
- `GOOGLE_CSE_ID`: Google Custom Search Engine ID

### Optional Settings
- `LOG_LEVEL`: Logging level (DEBUG, INFO, WARNING, ERROR)
- `CHROMA_PERSIST_DIRECTORY`: Vector database directory
- `CACHE_EXPIRE_SECONDS`: Cache expiration time
- `MAX_SEARCH_RESULTS`: Maximum search results per source
- `MAX_TOPICS`: Maximum number of topics to extract
- `LLM_MODEL`: OpenAI model to use

## API Keys Setup

### OpenAI API Key
1. Go to [OpenAI API Keys](https://platform.openai.com/api-keys)
2. Create a new API key
3. Add it to your `.env` file

### Google Search API
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Enable the Custom Search API
4. Create credentials for the API
5. Set up a Custom Search Engine at [Google CSE](https://cse.google.com/)
6. Add both keys to your `.env` file

## Output

The system generates comprehensive reports including:

- **Executive Summary**: AI-generated analysis of the research topic
- **Interactive Entity Relationship Graph**: Zoomable, interactive visualization of key entities and their relationships using vis.js
- **Enhanced Timeline**: Vertical timeline with visual markers, hover effects, and source attribution
- **Sentiment Analysis**: Overall sentiment and emotional tone
- **Topic Modeling**: Key themes and topics identified
- **Word Cloud**: Visual representation of key terms
- **Source Credibility Scores**: AI-assessed credibility scores (0.0-1.0) for each information source
- **Related Queries**: Suggested follow-up research topics

## Architecture

The system is built with a modular architecture:

1. **Search Layer**: Aggregates content from multiple sources
2. **Scraping Layer**: Extracts content from web pages
3. **Analysis Layer**: Performs AI-powered analysis with credibility assessment
4. **Storage Layer**: Manages vector database and caching
5. **Visualization Layer**: Generates interactive reports and visualizations
6. **API Layer**: RESTful API for background job processing (optional)

## Development

### Running Tests
```bash
pytest tests/
```

### Code Quality
```bash
# Format code
black src/

# Lint code
flake8 src/

# Type checking
mypy src/
```

### Contributing
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## Security Notes

- Never commit API keys to version control
- Use environment variables for sensitive configuration
- Regularly rotate API keys
- Monitor API usage to prevent abuse

## Troubleshooting

### Common Issues

1. **spaCy model not found**:
   ```bash
   python -m spacy download en_core_web_sm
   ```

2. **API key errors**:
   - Verify keys are set in `.env`
   - Check API key permissions and quotas

3. **Permission errors**:
   - Ensure write permissions for output directories
   - Check Chroma database directory permissions

4. **Memory issues**:
   - Reduce `MAX_SEARCH_RESULTS` in configuration
   - Clear cache regularly

### Debug Mode
Enable debug logging:
```bash
export LOG_LEVEL=DEBUG
python -m content_research_pipeline.cli research "your query" --verbose
```

## License

This project is licensed under the MIT License. See LICENSE file for details.

## Support

For issues and questions:
1. Check the troubleshooting section
2. Review the logs for error messages
3. Open an issue on GitHub
4. Contact the development team

## Changelog

### Version 1.0.0
- Initial release
- Multi-source content aggregation
- AI-powered analysis
- Interactive visualizations
- CLI and API interfaces
- Vector database integration
- Caching system 