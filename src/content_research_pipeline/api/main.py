"""
FastAPI application for the Content Research Pipeline.
"""

import asyncio
import uuid
from typing import Dict, Optional
from datetime import datetime
from pathlib import Path
from fastapi import FastAPI, HTTPException, BackgroundTasks, Security, Depends
from fastapi.responses import JSONResponse
from fastapi.security import APIKeyHeader
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from ..config.settings import settings
from ..config.logging import get_logger
from ..core.pipeline import ContentResearchPipeline
from ..data.models import PipelineResult
from ..services.job_store import job_store_service

logger = get_logger(__name__)

# Initialize FastAPI app with OpenAPI tags
app = FastAPI(
    title="Content Research Pipeline API",
    description="A comprehensive, AI-powered content research and analysis system",
    version="1.0.0",
    openapi_tags=[
        {
            "name": "health",
            "description": "Health check and status endpoints"
        },
        {
            "name": "research",
            "description": "Research job management operations"
        },
        {
            "name": "jobs",
            "description": "Job listing and management operations"
        }
    ]
)

# Configure static file serving for reports
reports_dir = Path("reports")
reports_dir.mkdir(parents=True, exist_ok=True)
app.mount("/reports", StaticFiles(directory=str(reports_dir)), name="reports")

# API Key security
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def verify_api_key(api_key: str = Security(api_key_header)) -> str:
    """
    Verify API key authentication.
    
    Args:
        api_key: API key from request header
        
    Returns:
        API key if valid
        
    Raises:
        HTTPException: If API key is invalid or missing
    """
    # If no API key is configured, skip authentication
    if not settings.api_key:
        return None
    
    if not api_key or api_key != settings.api_key:
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing API key"
        )
    return api_key


# Backward compatibility: in-memory fallback
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
    report_url: Optional[str] = Field(None, description="URL to the generated HTML report")
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
        
        # Update job status in Redis or fallback
        if job_store_service.redis_client:
            job_store_service.update_job(job_id, {"status": "running"})
        else:
            jobs[job_id]["status"] = "running"
        
        # Initialize and run pipeline
        pipeline = ContentResearchPipeline()
        result = await pipeline.run(
            query=request.query,
            include_images=request.include_images,
            include_videos=request.include_videos,
            include_news=request.include_news,
            max_results=request.max_results or settings.max_search_results,
            job_id=job_id
        )
        
        # Update job with result
        completed_at = datetime.now().isoformat()
        if job_store_service.redis_client:
            job_store_service.update_job(job_id, {
                "status": "completed",
                "completed_at": completed_at,
                "result": result.dict()
            })
        else:
            jobs[job_id]["status"] = "completed"
            jobs[job_id]["completed_at"] = completed_at
            jobs[job_id]["result"] = result
        
        logger.info(f"Research job {job_id} completed successfully")
        
    except Exception as e:
        logger.error(f"Research job {job_id} failed: {e}")
        completed_at = datetime.now().isoformat()
        if job_store_service.redis_client:
            job_store_service.update_job(job_id, {
                "status": "failed",
                "completed_at": completed_at,
                "error": str(e)
            })
        else:
            jobs[job_id]["status"] = "failed"
            jobs[job_id]["completed_at"] = completed_at
            jobs[job_id]["error"] = str(e)


@app.get("/", tags=["health"])
async def root():
    """Root endpoint - API information."""
    return {
        "name": "Content Research Pipeline API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health", tags=["health"])
async def health():
    """Health check endpoint - verify API and services are operational."""
    redis_status = "connected" if job_store_service.redis_client else "disconnected"
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "redis": redis_status
    }


@app.post(
    "/research",
    response_model=JobResponse,
    tags=["research"],
    summary="Start a new research job",
    description="Submit a research query to start an asynchronous content research and analysis job."
)
async def research(
    request: ResearchRequest,
    background_tasks: BackgroundTasks,
    api_key: str = Depends(verify_api_key)
):
    """
    Start a new research job.
    
    Args:
        request: Research request parameters
        background_tasks: FastAPI background tasks manager
        api_key: API key for authentication
        
    Returns:
        JobResponse with job_id and initial status
    """
    try:
        # Generate unique job ID
        job_id = str(uuid.uuid4())
        
        # Create job entry
        job_data = {
            "job_id": job_id,
            "status": "pending",
            "query": request.query,
            "created_at": datetime.now().isoformat(),
            "completed_at": None,
            "result": None,
            "error": None
        }
        
        # Store in Redis or fallback to memory
        if job_store_service.redis_client:
            job_store_service.create_job(job_id, job_data)
        else:
            jobs[job_id] = job_data
        
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


@app.get(
    "/status/{job_id}",
    response_model=JobStatusResponse,
    tags=["research"],
    summary="Get job status",
    description="Retrieve the current status and results of a research job by its ID."
)
async def get_status(
    job_id: str,
    api_key: str = Depends(verify_api_key)
):
    """
    Get the status of a research job.
    
    Args:
        job_id: Unique job identifier
        api_key: API key for authentication
        
    Returns:
        JobStatusResponse with job status and result (if completed)
    """
    try:
        # Get job from Redis or fallback
        if job_store_service.redis_client:
            job = job_store_service.get_job(job_id)
            if not job:
                raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
        else:
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
            "error": job.get("error"),
            "report_url": None
        }
        
        # Include result if completed (excluding HTML report)
        if job["status"] == "completed" and job.get("result"):
            result = job["result"]
            # Handle both PipelineResult objects and dicts
            if isinstance(result, PipelineResult):
                result_dict = result.dict()
            else:
                result_dict = result.copy() if isinstance(result, dict) else {}
            result_dict.pop("html_report", None)  # Exclude HTML report from JSON response
            response_data["result"] = result_dict
            
            # Add report URL if report file exists
            report_path = Path("reports") / f"{job_id}.html"
            if report_path.exists():
                response_data["report_url"] = f"/reports/{job_id}.html"
        
        return JobStatusResponse(**response_data)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get job status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get(
    "/jobs",
    tags=["jobs"],
    summary="List all jobs",
    description="Retrieve a list of all research jobs with optional filtering by status."
)
async def list_jobs(
    limit: int = 10,
    status: Optional[str] = None,
    api_key: str = Depends(verify_api_key)
):
    """
    List all jobs.
    
    Args:
        limit: Maximum number of jobs to return
        status: Filter by status (pending, running, completed, failed)
        api_key: API key for authentication
        
    Returns:
        List of job summaries
    """
    try:
        # Use Redis or fallback
        if job_store_service.redis_client:
            job_list = job_store_service.list_jobs(limit=limit, status=status)
            total = job_store_service.get_job_count()
            filtered = job_store_service.get_job_count(status=status) if status else total
        else:
            # Filter jobs by status if provided
            filtered_jobs = list(jobs.values())
            if status:
                filtered_jobs = [j for j in filtered_jobs if j["status"] == status]
            
            # Sort by creation time (most recent first)
            sorted_jobs = sorted(
                filtered_jobs,
                key=lambda j: j["created_at"],
                reverse=True
            )
            
            # Limit results
            job_list = sorted_jobs[:limit]
            total = len(jobs)
            filtered = len(filtered_jobs)
        
        # Return summary without full results
        return {
            "total": total,
            "filtered": filtered,
            "jobs": [
                {
                    "job_id": j["job_id"],
                    "status": j["status"],
                    "query": j["query"],
                    "created_at": j["created_at"],
                    "completed_at": j.get("completed_at")
                }
                for j in job_list
            ]
        }
        
    except Exception as e:
        logger.error(f"Failed to list jobs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete(
    "/jobs/{job_id}",
    tags=["jobs"],
    summary="Delete a job",
    description="Delete a completed or failed research job. Running jobs cannot be deleted."
)
async def delete_job(
    job_id: str,
    api_key: str = Depends(verify_api_key)
):
    """
    Delete a job.
    
    Args:
        job_id: Unique job identifier
        api_key: API key for authentication
        
    Returns:
        Success message
    """
    try:
        # Use Redis or fallback
        if job_store_service.redis_client:
            job = job_store_service.get_job(job_id)
            if not job:
                raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
            
            # Check if job is still running
            if job["status"] in ["pending", "running"]:
                raise HTTPException(
                    status_code=400,
                    detail="Cannot delete a job that is still running"
                )
            
            # Delete job
            job_store_service.delete_job(job_id)
        else:
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
