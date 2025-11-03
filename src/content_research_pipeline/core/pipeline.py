"""
Main pipeline orchestration for the Content Research Pipeline.
"""

import asyncio
import time
from typing import Optional, Dict, Any

from ..config.settings import settings
from ..config.logging import get_logger
from ..data.models import (
    PipelineState,
    PipelineResult,
    VisualizationData,
    ContentType,
)
from ..services.search import search_service
from ..services.scraper import scraper_service
from ..services.vector_store import vector_store_service
from .analysis import analysis_processor
from ..visualization.charts import chart_generator
from ..visualization.html_generator import report_generator

logger = get_logger(__name__)


class ContentResearchPipeline:
    """Main pipeline orchestrator for content research."""
    
    def __init__(self):
        """Initialize the pipeline."""
        self.logger = logger
        
    async def run(
        self, 
        query: str,
        include_images: bool = True,
        include_videos: bool = True,
        include_news: bool = True,
        max_results: Optional[int] = None,
        job_id: Optional[str] = None,
        **kwargs
    ) -> PipelineResult:
        """
        Run the complete content research pipeline.
        
        Args:
            query: The research query
            include_images: Whether to include image search
            include_videos: Whether to include video search
            include_news: Whether to include news search
            max_results: Maximum number of search results per source
            **kwargs: Additional pipeline configuration
            
        Returns:
            PipelineResult containing complete analysis and visualizations
        """
        start_time = time.time()
        self.logger.info(f"Starting pipeline for query: {query}")
        
        # Initialize pipeline state
        state = PipelineState(query=query)
        state.update_status("searching")
        
        try:
            # Phase 1: Search
            await self._search_phase(state, include_images, include_videos, include_news)
            
            # Phase 2: Scrape
            state.update_status("scraping")
            await self._scraping_phase(state)
            
            # Phase 3: Store
            state.update_status("storing")
            await self._storage_phase(state)
            
            # Phase 4: Analyze
            state.update_status("analyzing")
            await self._analysis_phase(state)
            
            # Phase 5: Visualize
            state.update_status("visualizing")
            visualization = await self._visualization_phase(state)
            
            # Phase 6: Generate Report
            state.update_status("generating_report")
            html_report = await self._report_generation_phase(state, visualization, job_id)
            
            # Complete
            state.update_status("completed")
            processing_time = time.time() - start_time
            
            self.logger.info(f"Pipeline completed in {processing_time:.2f} seconds")
            
            return PipelineResult(
                state=state,
                visualization=visualization,
                html_report=html_report,
                processing_time=processing_time
            )
            
        except Exception as e:
            self.logger.error(f"Pipeline failed: {e}")
            state.update_status("failed")
            processing_time = time.time() - start_time
            
            # Return partial results
            return PipelineResult(
                state=state,
                visualization=VisualizationData(),
                html_report=None,
                processing_time=processing_time
            )
    
    async def _search_phase(
        self, 
        state: PipelineState,
        include_images: bool,
        include_videos: bool,
        include_news: bool
    ) -> None:
        """
        Execute the search phase.
        
        Args:
            state: Current pipeline state
            include_images: Whether to include image search
            include_videos: Whether to include video search
            include_news: Whether to include news search
        """
        self.logger.info("Executing search phase")
        
        # Perform web search
        search_results = await search_service.search_web(state.query)
        state.search_results = search_results
        
        # Perform additional searches in parallel
        tasks = []
        
        if include_news:
            tasks.append(search_service.search_news(state.query))
        
        if include_images:
            tasks.append(search_service.search_images(state.query))
        
        if include_videos:
            tasks.append(search_service.search_videos(state.query))
        
        # Gather results
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            idx = 0
            if include_news:
                news_results = results[idx] if not isinstance(results[idx], Exception) else []
                state.search_results.extend(news_results)
                idx += 1
            
            if include_images:
                state.images = results[idx] if not isinstance(results[idx], Exception) else []
                idx += 1
            
            if include_videos:
                state.videos = results[idx] if not isinstance(results[idx], Exception) else []
        
        self.logger.info(
            f"Search phase completed: {len(state.search_results)} web results, "
            f"{len(state.images)} images, {len(state.videos)} videos"
        )
    
    async def _scraping_phase(self, state: PipelineState) -> None:
        """
        Execute the scraping phase.
        
        Args:
            state: Current pipeline state
        """
        self.logger.info("Executing scraping phase")
        
        # Collect all URLs to scrape from search results
        urls_to_scrape = []
        
        # Add web and news results
        for result in state.search_results:
            urls_to_scrape.append(str(result.link))
        
        if not urls_to_scrape:
            self.logger.warning("No URLs to scrape")
            return
        
        # Limit the number of URLs to scrape based on settings
        max_urls = min(len(urls_to_scrape), settings.max_search_results * 2)
        urls_to_scrape = urls_to_scrape[:max_urls]
        
        self.logger.info(f"Scraping {len(urls_to_scrape)} URLs")
        
        # Scrape all URLs concurrently
        scraped_contents = await scraper_service.scrape_urls(urls_to_scrape)
        
        # Store scraped content in state
        state.scraped_content = scraped_contents
        
        # Log statistics
        successful = sum(1 for s in scraped_contents if s.type != ContentType.ERROR)
        self.logger.info(
            f"Scraping phase completed: {successful}/{len(scraped_contents)} successful"
        )
    
    async def _storage_phase(self, state: PipelineState) -> None:
        """
        Execute the storage phase.
        
        Args:
            state: Current pipeline state
        """
        self.logger.info("Executing storage phase")
        
        # Store scraped content in vector store
        if state.scraped_content:
            success = await vector_store_service.add_documents(state.scraped_content)
            if success:
                self.logger.info("Content stored in vector database")
            else:
                self.logger.warning("Failed to store content in vector database")
    
    async def _analysis_phase(self, state: PipelineState) -> None:
        """
        Execute the analysis phase.
        
        Args:
            state: Current pipeline state
        """
        self.logger.info("Executing analysis phase")
        
        # Calculate credibility for search results
        await analysis_processor.calculate_credibility(state)
        
        # Perform comprehensive analysis
        if state.scraped_content:
            analysis_result = await analysis_processor.analyze(
                query=state.query,
                scraped_contents=state.scraped_content
            )
            state.analysis = analysis_result
            self.logger.info("Analysis phase completed")
        else:
            self.logger.warning("No scraped content available for analysis")
    
    async def _visualization_phase(self, state: PipelineState) -> VisualizationData:
        """
        Execute the visualization phase.
        
        Args:
            state: Current pipeline state
            
        Returns:
            VisualizationData containing chart data
        """
        self.logger.info("Executing visualization phase")
        
        # Generate visualization data from analysis
        if state.analysis:
            visualization = await chart_generator.generate_visualization_data(state.analysis)
            self.logger.info("Visualization phase completed")
            return visualization
        else:
            self.logger.warning("No analysis available for visualization")
            return VisualizationData()
    
    async def _report_generation_phase(
        self, 
        state: PipelineState,
        visualization: VisualizationData,
        job_id: Optional[str] = None
    ) -> Optional[str]:
        """
        Execute the report generation phase.
        
        Args:
            state: Current pipeline state
            visualization: Visualization data
            job_id: Optional job ID for saving report to file
            
        Returns:
            HTML report string or None
        """
        self.logger.info("Executing report generation phase")
        
        # Generate HTML report
        processing_time = time.time() - state.created_at.timestamp()
        html_report = await report_generator.generate_report(
            state=state,
            visualization=visualization,
            processing_time=processing_time
        )
        
        # Save report to static file if job_id is provided
        if job_id and html_report:
            try:
                from pathlib import Path
                reports_dir = Path("reports")
                reports_dir.mkdir(parents=True, exist_ok=True)
                
                report_path = reports_dir / f"{job_id}.html"
                report_path.write_text(html_report, encoding="utf-8")
                self.logger.info(f"Saved report to {report_path}")
            except Exception as e:
                self.logger.error(f"Failed to save report to file: {e}")
        
        self.logger.info("Report generation phase completed")
        return html_report
