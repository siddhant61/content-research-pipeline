"""
Tests for API module.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient

from src.content_research_pipeline.api.main import app, jobs, ResearchRequest
from src.content_research_pipeline.data.models import (
    PipelineResult,
    PipelineState,
    VisualizationData
)


class TestAPI:
    """Test FastAPI endpoints."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Clear jobs before each test
        jobs.clear()
        self.client = TestClient(app)
        
        # Mock Redis client to None to use in-memory fallback
        with patch('src.content_research_pipeline.services.job_store.redis.Redis') as mock_redis:
            mock_redis.side_effect = Exception("Redis not available")
        
        # Ensure API key is not set for tests (optional authentication)
        with patch('src.content_research_pipeline.config.settings.settings') as mock_settings:
            mock_settings.api_key = None
    
    def test_root_endpoint(self):
        """Test root endpoint returns correct response."""
        response = self.client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Content Research Pipeline API"
        assert data["version"] == "1.0.0"
        assert data["status"] == "running"
    
    def test_health_endpoint(self):
        """Test health check endpoint."""
        response = self.client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
    
    def test_research_endpoint_creates_job(self):
        """Test that research endpoint creates a job."""
        request_data = {
            "query": "test query",
            "include_images": True,
            "include_videos": True,
            "include_news": True
        }
        
        response = self.client.post("/research", json=request_data)
        assert response.status_code == 200
        
        data = response.json()
        assert "job_id" in data
        assert data["status"] == "pending"
        assert "message" in data
        
        # Verify job was created
        job_id = data["job_id"]
        assert job_id in jobs
        assert jobs[job_id]["query"] == "test query"
        assert jobs[job_id]["status"] == "pending"
    
    def test_research_endpoint_validation(self):
        """Test that research endpoint validates input."""
        # Missing required query field
        response = self.client.post("/research", json={})
        assert response.status_code == 422  # Unprocessable Entity
    
    def test_status_endpoint_job_not_found(self):
        """Test status endpoint returns 404 for non-existent job."""
        response = self.client.get("/status/non-existent-id")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
    
    def test_status_endpoint_pending_job(self):
        """Test status endpoint returns correct status for pending job."""
        # Create a pending job manually
        job_id = "test-job-id"
        jobs[job_id] = {
            "job_id": job_id,
            "status": "pending",
            "query": "test query",
            "created_at": "2024-01-01T00:00:00",
            "completed_at": None,
            "result": None,
            "error": None
        }
        
        response = self.client.get(f"/status/{job_id}")
        assert response.status_code == 200
        
        data = response.json()
        assert data["job_id"] == job_id
        assert data["status"] == "pending"
        assert data["query"] == "test query"
        assert data["result"] is None
    
    def test_status_endpoint_completed_job(self):
        """Test status endpoint returns result for completed job."""
        # Create a completed job with mock result
        job_id = "test-completed-job"
        mock_state = PipelineState(query="test query")
        mock_result = PipelineResult(
            state=mock_state,
            visualization=VisualizationData(),
            html_report="<html>test</html>",
            processing_time=1.5
        )
        
        jobs[job_id] = {
            "job_id": job_id,
            "status": "completed",
            "query": "test query",
            "created_at": "2024-01-01T00:00:00",
            "completed_at": "2024-01-01T00:00:05",
            "result": mock_result,
            "error": None
        }
        
        response = self.client.get(f"/status/{job_id}")
        assert response.status_code == 200
        
        data = response.json()
        assert data["job_id"] == job_id
        assert data["status"] == "completed"
        assert data["result"] is not None
        assert "html_report" not in data["result"]  # HTML should be excluded
    
    def test_status_endpoint_failed_job(self):
        """Test status endpoint returns error for failed job."""
        job_id = "test-failed-job"
        jobs[job_id] = {
            "job_id": job_id,
            "status": "failed",
            "query": "test query",
            "created_at": "2024-01-01T00:00:00",
            "completed_at": "2024-01-01T00:00:05",
            "result": None,
            "error": "Test error message"
        }
        
        response = self.client.get(f"/status/{job_id}")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "failed"
        assert data["error"] == "Test error message"
    
    def test_list_jobs_endpoint(self):
        """Test list jobs endpoint."""
        # Create multiple test jobs
        for i in range(3):
            job_id = f"test-job-{i}"
            jobs[job_id] = {
                "job_id": job_id,
                "status": "completed" if i % 2 == 0 else "pending",
                "query": f"test query {i}",
                "created_at": f"2024-01-01T00:00:0{i}",
                "completed_at": None
            }
        
        response = self.client.get("/jobs")
        assert response.status_code == 200
        
        data = response.json()
        assert data["total"] == 3
        assert len(data["jobs"]) == 3
    
    def test_list_jobs_with_status_filter(self):
        """Test list jobs endpoint with status filter."""
        # Create jobs with different statuses
        jobs["job1"] = {
            "job_id": "job1",
            "status": "completed",
            "query": "query1",
            "created_at": "2024-01-01T00:00:00",
            "completed_at": None
        }
        jobs["job2"] = {
            "job_id": "job2",
            "status": "pending",
            "query": "query2",
            "created_at": "2024-01-01T00:00:01",
            "completed_at": None
        }
        
        response = self.client.get("/jobs?status=completed")
        assert response.status_code == 200
        
        data = response.json()
        assert data["filtered"] == 1
        assert data["jobs"][0]["status"] == "completed"
    
    def test_list_jobs_with_limit(self):
        """Test list jobs endpoint with limit parameter."""
        # Create multiple jobs
        for i in range(5):
            jobs[f"job{i}"] = {
                "job_id": f"job{i}",
                "status": "completed",
                "query": f"query{i}",
                "created_at": f"2024-01-01T00:00:0{i}",
                "completed_at": None
            }
        
        response = self.client.get("/jobs?limit=3")
        assert response.status_code == 200
        
        data = response.json()
        assert len(data["jobs"]) == 3
    
    def test_delete_job_endpoint(self):
        """Test delete job endpoint."""
        job_id = "test-delete-job"
        jobs[job_id] = {
            "job_id": job_id,
            "status": "completed",
            "query": "test query",
            "created_at": "2024-01-01T00:00:00",
            "completed_at": "2024-01-01T00:00:05"
        }
        
        response = self.client.delete(f"/jobs/{job_id}")
        assert response.status_code == 200
        assert job_id not in jobs
    
    def test_delete_job_not_found(self):
        """Test delete job returns 404 for non-existent job."""
        response = self.client.delete("/jobs/non-existent-id")
        assert response.status_code == 404
    
    def test_delete_running_job_fails(self):
        """Test that deleting a running job fails."""
        job_id = "test-running-job"
        jobs[job_id] = {
            "job_id": job_id,
            "status": "running",
            "query": "test query",
            "created_at": "2024-01-01T00:00:00",
            "completed_at": None
        }
        
        response = self.client.delete(f"/jobs/{job_id}")
        assert response.status_code == 400
        assert "still running" in response.json()["detail"].lower()


class TestAPIAuthentication:
    """Test API authentication."""
    
    def setup_method(self):
        """Set up test fixtures."""
        jobs.clear()
        self.client = TestClient(app)
    
    @patch('src.content_research_pipeline.api.main.settings')
    def test_api_key_required(self, mock_settings):
        """Test that API key is required when configured."""
        # Set API key in settings
        mock_settings.api_key = "test-api-key-123"
        mock_settings.max_search_results = 5
        
        # Try to access protected endpoint without API key
        request_data = {
            "query": "test query",
            "include_images": True,
            "include_videos": True,
            "include_news": True
        }
        
        response = self.client.post("/research", json=request_data)
        
        # Should return 401 Unauthorized
        assert response.status_code == 401
    
    @patch('src.content_research_pipeline.api.main.settings')
    def test_api_key_valid(self, mock_settings):
        """Test that valid API key allows access."""
        # Set API key in settings
        mock_settings.api_key = "test-api-key-123"
        mock_settings.max_search_results = 5
        
        request_data = {
            "query": "test query",
            "include_images": True,
            "include_videos": True,
            "include_news": True
        }
        
        # Access endpoint with valid API key
        response = self.client.post(
            "/research",
            json=request_data,
            headers={"X-API-Key": "test-api-key-123"}
        )
        
        # Should return 200 OK
        assert response.status_code == 200
    
    @patch('src.content_research_pipeline.api.main.settings')
    def test_api_key_invalid(self, mock_settings):
        """Test that invalid API key denies access."""
        # Set API key in settings
        mock_settings.api_key = "test-api-key-123"
        mock_settings.max_search_results = 5
        
        request_data = {
            "query": "test query",
            "include_images": True,
            "include_videos": True,
            "include_news": True
        }
        
        # Access endpoint with invalid API key
        response = self.client.post(
            "/research",
            json=request_data,
            headers={"X-API-Key": "wrong-key"}
        )
        
        # Should return 401 Unauthorized
        assert response.status_code == 401
    
    @patch('src.content_research_pipeline.api.main.settings')
    def test_api_key_optional(self, mock_settings):
        """Test that API key is optional when not configured."""
        # No API key configured
        mock_settings.api_key = None
        mock_settings.max_search_results = 5
        
        request_data = {
            "query": "test query",
            "include_images": True,
            "include_videos": True,
            "include_news": True
        }
        
        # Access endpoint without API key
        response = self.client.post("/research", json=request_data)
        
        # Should return 200 OK (authentication skipped)
        assert response.status_code == 200


class TestAPIOpenAPITags:
    """Test OpenAPI documentation enhancements."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.client = TestClient(app)
    
    def test_openapi_schema_has_tags(self):
        """Test that OpenAPI schema includes tags."""
        response = self.client.get("/openapi.json")
        assert response.status_code == 200
        
        schema = response.json()
        
        # Check that tags are defined
        assert "tags" in schema
        assert len(schema["tags"]) > 0
        
        # Check for expected tags
        tag_names = [tag["name"] for tag in schema["tags"]]
        assert "health" in tag_names
        assert "research" in tag_names
        assert "jobs" in tag_names
    
    def test_endpoints_have_tags(self):
        """Test that endpoints are tagged."""
        response = self.client.get("/openapi.json")
        assert response.status_code == 200
        
        schema = response.json()
        paths = schema["paths"]
        
        # Check that /research endpoint has tags
        assert "tags" in paths["/research"]["post"]
        assert "research" in paths["/research"]["post"]["tags"]
        
        # Check that /jobs endpoint has tags
        assert "tags" in paths["/jobs"]["get"]
        assert "jobs" in paths["/jobs"]["get"]["tags"]
