"""
Command-line interface for the Content Research Pipeline.
"""

import asyncio
import click
from pathlib import Path
from typing import Optional

from .config.settings import settings
from .config.logging import get_logger
from .core.pipeline import ContentResearchPipeline
from .utils.caching import get_cache_stats, clear_cache

logger = get_logger(__name__)


@click.group()
@click.version_option(version="1.0.0")
def cli():
    """Content Research Pipeline - A comprehensive tool for content research and analysis."""
    pass


@cli.command()
@click.argument("query", type=str)
@click.option(
    "--output", "-o", 
    type=click.Path(path_type=Path), 
    default=None,
    help="Output directory for results"
)
@click.option(
    "--format", "-f",
    type=click.Choice(["html", "json", "both"]),
    default="html",
    help="Output format"
)
@click.option(
    "--max-results", "-m",
    type=int,
    default=None,
    help="Maximum number of search results per source"
)
@click.option(
    "--no-images",
    is_flag=True,
    help="Skip image search"
)
@click.option(
    "--no-videos",
    is_flag=True,
    help="Skip video search"
)
@click.option(
    "--no-news",
    is_flag=True,
    help="Skip news search"
)
@click.option(
    "--verbose", "-v",
    is_flag=True,
    help="Enable verbose logging"
)
def research(
    query: str,
    output: Optional[Path],
    format: str,
    max_results: Optional[int],
    no_images: bool,
    no_videos: bool,
    no_news: bool,
    verbose: bool
):
    """
    Research a topic and generate comprehensive analysis.
    
    QUERY: The topic or question to research
    """
    if verbose:
        logger.info("Verbose logging enabled")
    
    # Set up output directory
    if output is None:
        output = Path(f"results/{query.replace(' ', '_')}")
    
    output.mkdir(parents=True, exist_ok=True)
    
    # Configure pipeline options
    pipeline_config = {
        "include_images": not no_images,
        "include_videos": not no_videos,
        "include_news": not no_news,
        "max_results": max_results or settings.max_search_results,
    }
    
    try:
        # Run the research pipeline
        result = asyncio.run(_run_research(query, pipeline_config))
        
        # Save results
        if format in ["html", "both"]:
            html_path = output / f"{query.replace(' ', '_')}.html"
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(result.html_report or "")
            click.echo(f"HTML report saved to: {html_path}")
        
        if format in ["json", "both"]:
            json_path = output / f"{query.replace(' ', '_')}.json"
            with open(json_path, "w", encoding="utf-8") as f:
                f.write(result.json(indent=2))
            click.echo(f"JSON data saved to: {json_path}")
        
        # Print summary
        click.echo(f"\nResearch completed for: {query}")
        click.echo(f"Processing time: {result.processing_time:.2f} seconds")
        click.echo(f"Results saved to: {output}")
        
    except Exception as e:
        logger.error(f"Research failed: {e}")
        click.echo(f"Error: {e}", err=True)
        raise click.Abort()


async def _run_research(query: str, config: dict):
    """Run the research pipeline asynchronously."""
    pipeline = ContentResearchPipeline()
    result = await pipeline.run(query, **config)
    return result


@cli.command()
@click.option(
    "--stats",
    is_flag=True,
    help="Show cache statistics"
)
@click.option(
    "--clear",
    is_flag=True,
    help="Clear cache"
)
def cache(stats: bool, clear: bool):
    """Manage the application cache."""
    
    if clear:
        clear_cache()
        click.echo("Cache cleared successfully")
    
    if stats:
        cache_stats = get_cache_stats()
        click.echo("Cache Statistics:")
        click.echo(f"  Total entries: {cache_stats['total_entries']}")
        click.echo(f"  Active entries: {cache_stats['active_entries']}")
        click.echo(f"  Expired entries: {cache_stats['expired_entries']}")
        click.echo(f"  Estimated size: {cache_stats['estimated_size_bytes']:,} bytes")
        click.echo(f"  Cache expiration: {cache_stats['cache_expire_seconds']} seconds")
    
    if not stats and not clear:
        click.echo("Use --stats to show cache statistics or --clear to clear cache")


@cli.command()
def config():
    """Show current configuration."""
    click.echo("Current Configuration:")
    click.echo(f"  Log level: {settings.log_level}")
    click.echo(f"  Chroma directory: {settings.chroma_persist_directory}")
    click.echo(f"  Cache expiration: {settings.cache_expire_seconds} seconds")
    click.echo(f"  Max search results: {settings.max_search_results}")
    click.echo(f"  Max topics: {settings.max_topics}")
    click.echo(f"  LLM model: {settings.llm_model}")
    click.echo(f"  Download images: {settings.download_images}")
    click.echo(f"  Download videos: {settings.download_videos}")
    
    # API key status (without showing the actual keys)
    click.echo("\nAPI Key Status:")
    click.echo(f"  OpenAI API Key: {'✓ Set' if settings.openai_api_key else '✗ Not set'}")
    click.echo(f"  Google API Key: {'✓ Set' if settings.google_api_key else '✗ Not set'}")
    click.echo(f"  Google CSE ID: {'✓ Set' if settings.google_cse_id else '✗ Not set'}")


@cli.command()
@click.argument("query", type=str)
@click.option(
    "--num-results", "-n",
    type=int,
    default=5,
    help="Number of results to return"
)
@click.option(
    "--type", "-t",
    type=click.Choice(["web", "news", "images", "videos"]),
    default="web",
    help="Type of search to perform"
)
def search(query: str, num_results: int, type: str):
    """
    Perform a quick search without full analysis.
    
    QUERY: The search query
    """
    from .services.search import search_service
    
    try:
        results = asyncio.run(_run_search(query, num_results, type))
        
        click.echo(f"\nSearch results for: {query}")
        click.echo(f"Type: {type}")
        click.echo(f"Results: {len(results)}")
        click.echo("-" * 50)
        
        for i, result in enumerate(results, 1):
            if hasattr(result, 'title') and hasattr(result, 'link'):
                click.echo(f"{i}. {result.title}")
                click.echo(f"   {result.link}")
                if hasattr(result, 'snippet'):
                    click.echo(f"   {result.snippet}")
                click.echo()
        
    except Exception as e:
        logger.error(f"Search failed: {e}")
        click.echo(f"Error: {e}", err=True)
        raise click.Abort()


async def _run_search(query: str, num_results: int, search_type: str):
    """Run a search operation asynchronously."""
    from .services.search import search_service
    
    if search_type == "web":
        return await search_service.search_web(query, num_results)
    elif search_type == "news":
        return await search_service.search_news(query, num_results)
    elif search_type == "images":
        return await search_service.search_images(query, num_results)
    elif search_type == "videos":
        return await search_service.search_videos(query, num_results)
    else:
        raise ValueError(f"Unknown search type: {search_type}")


@cli.command()
@click.option(
    "--host",
    default="0.0.0.0",
    help="Host to bind to"
)
@click.option(
    "--port",
    type=int,
    default=8000,
    help="Port to bind to"
)
@click.option(
    "--reload",
    is_flag=True,
    help="Enable auto-reload"
)
def serve(host: str, port: int, reload: bool):
    """Start the web API server."""
    try:
        import uvicorn
        from .api.main import app
        
        click.echo(f"Starting server at http://{host}:{port}")
        click.echo("Press Ctrl+C to stop")
        
        uvicorn.run(
            "content_research_pipeline.api.main:app",
            host=host,
            port=port,
            reload=reload,
            log_level=settings.log_level.lower()
        )
        
    except ImportError:
        click.echo("FastAPI dependencies not installed. Install with: pip install fastapi uvicorn")
        raise click.Abort()
    except Exception as e:
        logger.error(f"Server failed to start: {e}")
        click.echo(f"Error: {e}", err=True)
        raise click.Abort()


@cli.command()
def validate():
    """Validate the configuration and dependencies."""
    click.echo("Validating configuration...")
    
    # Check API keys
    errors = []
    if not settings.openai_api_key:
        errors.append("OpenAI API key not set")
    if not settings.google_api_key:
        errors.append("Google API key not set")
    if not settings.google_cse_id:
        errors.append("Google CSE ID not set")
    
    # Check dependencies
    try:
        import spacy
        try:
            nlp = spacy.load("en_core_web_sm")
            click.echo("✓ spaCy model loaded successfully")
        except OSError:
            errors.append("spaCy model 'en_core_web_sm' not found. Install with: python -m spacy download en_core_web_sm")
    except ImportError:
        errors.append("spaCy not installed")
    
    # Check directories
    try:
        Path(settings.chroma_persist_directory).mkdir(parents=True, exist_ok=True)
        click.echo("✓ Chroma directory accessible")
    except Exception as e:
        errors.append(f"Cannot access Chroma directory: {e}")
    
    if errors:
        click.echo("\nValidation errors:")
        for error in errors:
            click.echo(f"  ✗ {error}")
        raise click.Abort()
    else:
        click.echo("\n✓ All validations passed")


if __name__ == "__main__":
    cli() 