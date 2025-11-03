"""
FastAPI application for the Content Research Pipeline.
"""

import asyncio
import uuid
from typing import Dict, Optional
from datetime import datetime
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from ..config.settings import settings
from ..config.logging import get_logger
from ..core.pipeline import ContentResearchPipeline
from ..data.models import PipelineResult

logger = get_logger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Content Research Pipeline API",
    description="A comprehensive, AI-powered content research and analysis system",
    version="1.0.0"
)

# In-memory job storage (in production, use Redis or a database)
jobs: Dict[str, Dict] = {}


class ResearchRequest(BaseModel):
    """Request model for research endpoint."""
    query: str = Field(..., description="The research query", min_length=1)
    include_images: bool = Field(True, description="Whether to include image search")
    include_videos: bool = Field(True, description="Whether to include video search")
    include_news: bool = Field(True, description="Whether to include news search")
    max_results: Optional[int] = Field(None, description="Maximum number of search results")


class JobResponse(BaseModel):
    """Response model for job creation."""
    job_id: str = Field(..., description="Unique job identifier")
    status: str = Field(..., description="Current job status")
    message: str = Field(..., description="Status message")


class JobStatusResponse(BaseModel):
    """Response model for job status."""
    job_id: str = Field(..., description="Job identifier")
    status: str = Field(..., description="Current job status")
    query: str = Field(..., description="Research query")
    created_at: str = Field(..., description="Job creation timestamp")
    completed_at: Optional[str] = Field(None, description="Job completion timestamp")
    result: Optional[Dict] = Field(None, description="Pipeline result (when completed)")
    error: Optional[str] = Field(None, description="Error message (if failed)")


async def run_research_pipeline(job_id: str, request: ResearchRequest):
    """
    Run the research pipeline in the background.
    
    Args:
        job_id: Unique job identifier
        request: Research request parameters
    """
    try:
        logger.info(f"Starting research job {job_id} for query: {request.query}")
        
        # Update job status
        jobs[job_id]["status"] = "running"
        
        # Initialize and run pipeline
        pipeline = ContentResearchPipeline()
        result = await pipeline.run(
            query=request.query,
            include_images=request.include_images,
            include_videos=request.include_videos,
            include_news=request.include_news,
            max_results=request.max_results or settings.max_search_results
        )
        
        # Update job with result
        jobs[job_id]["status"] = "completed"
        jobs[job_id]["completed_at"] = datetime.now().isoformat()
        jobs[job_id]["result"] = result
        
        logger.info(f"Research job {job_id} completed successfully")
        
    except Exception as e:
        logger.error(f"Research job {job_id} failed: {e}")
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["completed_at"] = datetime.now().isoformat()
        jobs[job_id]["error"] = str(e)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "Content Research Pipeline API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }


@app.post("/research", response_model=JobResponse)
async def research(
    request: ResearchRequest,
    background_tasks: BackgroundTasks
):
    """
    Start a new research job.
    
    Args:
        request: Research request parameters
        background_tasks: FastAPI background tasks manager
        
    Returns:
        JobResponse with job_id and initial status
    """
    try:
        # Generate unique job ID
        job_id = str(uuid.uuid4())
        
        # Create job entry
        jobs[job_id] = {
            "job_id": job_id,
            "status": "pending",
            "query": request.query,
            "created_at": datetime.now().isoformat(),
            "completed_at": None,
            "result": None,
            "error": None
        }
        
        # Start background task using asyncio
        asyncio.create_task(run_research_pipeline(job_id, request))
        
        logger.info(f"Created research job {job_id} for query: {request.query}")
        
        return JobResponse(
            job_id=job_id,
            status="pending",
            message=f"Research job created successfully. Use /status/{job_id} to check progress."
        )
        
    except Exception as e:
        logger.error(f"Failed to create research job: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/status/{job_id}", response_model=JobStatusResponse)
async def get_status(job_id: str):
    """
    Get the status of a research job.
    
    Args:
        job_id: Unique job identifier
        
    Returns:
        JobStatusResponse with job status and result (if completed)
    """
    try:
        # Check if job exists
        if job_id not in jobs:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
        
        job = jobs[job_id]
        
        # Prepare response
        response_data = {
            "job_id": job["job_id"],
            "status": job["status"],
            "query": job["query"],
            "created_at": job["created_at"],
            "completed_at": job["completed_at"],
            "error": job.get("error")
        }
        
        # Include result if completed (excluding HTML report)
        if job["status"] == "completed" and job["result"]:
            result: PipelineResult = job["result"]
            # Convert to dict, excluding html_report
            result_dict = result.dict()
            result_dict.pop("html_report", None)  # Exclude HTML report from JSON response
            response_data["result"] = result_dict
        
        return JobStatusResponse(**response_data)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get job status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/jobs")
async def list_jobs(limit: int = 10, status: Optional[str] = None):
    """
    List all jobs.
    
    Args:
        limit: Maximum number of jobs to return
        status: Filter by status (pending, running, completed, failed)
        
    Returns:
        List of job summaries
    """
    try:
        # Filter jobs by status if provided
        filtered_jobs = jobs.values()
        if status:
            filtered_jobs = [j for j in filtered_jobs if j["status"] == status]
        
        # Sort by creation time (most recent first)
        sorted_jobs = sorted(
            filtered_jobs,
            key=lambda j: j["created_at"],
            reverse=True
        )
        
        # Limit results
        limited_jobs = sorted_jobs[:limit]
        
        # Return summary without full results
        return {
            "total": len(jobs),
            "filtered": len(filtered_jobs),
            "jobs": [
                {
                    "job_id": j["job_id"],
                    "status": j["status"],
                    "query": j["query"],
                    "created_at": j["created_at"],
                    "completed_at": j["completed_at"]
                }
                for j in limited_jobs
            ]
        }
        
    except Exception as e:
        logger.error(f"Failed to list jobs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/jobs/{job_id}")
async def delete_job(job_id: str):
    """
    Delete a job.
    
    Args:
        job_id: Unique job identifier
        
    Returns:
        Success message
    """
    try:
        if job_id not in jobs:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
        
        # Check if job is still running
        if jobs[job_id]["status"] in ["pending", "running"]:
            raise HTTPException(
                status_code=400,
                detail="Cannot delete a job that is still running"
            )
        
        # Delete job
        del jobs[job_id]
        
        logger.info(f"Deleted job {job_id}")
        
        return {"message": f"Job {job_id} deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete job: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.on_event("startup")
async def startup_event():
    """Run on application startup."""
    logger.info("Content Research Pipeline API starting up")


@app.on_event("shutdown")
async def shutdown_event():
    """Run on application shutdown."""
    logger.info("Content Research Pipeline API shutting down")
