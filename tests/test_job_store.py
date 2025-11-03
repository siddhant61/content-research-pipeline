"""
Tests for job store service.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from src.content_research_pipeline.services.job_store import JobStoreService


class TestJobStoreService:
    """Test JobStoreService functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Create a mock Redis client
        self.mock_redis = MagicMock()
        self.mock_redis.ping.return_value = True
        
    @patch('src.content_research_pipeline.services.job_store.redis.Redis')
    def test_initialize_client_success(self, mock_redis_class):
        """Test successful Redis client initialization."""
        mock_redis_class.return_value = self.mock_redis
        
        service = JobStoreService()
        
        assert service.redis_client is not None
        self.mock_redis.ping.assert_called_once()
    
    @patch('src.content_research_pipeline.services.job_store.redis.Redis')
    def test_initialize_client_failure(self, mock_redis_class):
        """Test Redis client initialization failure falls back gracefully."""
        mock_redis_class.side_effect = Exception("Connection failed")
        
        service = JobStoreService()
        
        assert service.redis_client is None
    
    def test_create_job(self):
        """Test creating a new job."""
        service = JobStoreService()
        service.redis_client = self.mock_redis
        
        job_id = "test-job-123"
        job_data = {
            "job_id": job_id,
            "status": "pending",
            "query": "test query",
            "created_at": datetime.now().isoformat()
        }
        
        result = service.create_job(job_id, job_data)
        
        assert result is True
        self.mock_redis.set.assert_called_once()
        self.mock_redis.zadd.assert_called_once()
    
    def test_create_job_without_redis(self):
        """Test creating a job when Redis is not available."""
        service = JobStoreService()
        service.redis_client = None
        
        job_id = "test-job-123"
        job_data = {"job_id": job_id, "status": "pending"}
        
        result = service.create_job(job_id, job_data)
        
        assert result is False
    
    def test_get_job(self):
        """Test getting a job by ID."""
        service = JobStoreService()
        service.redis_client = self.mock_redis
        
        job_id = "test-job-123"
        job_data = {"job_id": job_id, "status": "completed"}
        
        import json
        self.mock_redis.get.return_value = json.dumps(job_data)
        
        result = service.get_job(job_id)
        
        assert result is not None
        assert result["job_id"] == job_id
        assert result["status"] == "completed"
    
    def test_get_job_not_found(self):
        """Test getting a non-existent job."""
        service = JobStoreService()
        service.redis_client = self.mock_redis
        
        self.mock_redis.get.return_value = None
        
        result = service.get_job("non-existent")
        
        assert result is None
    
    def test_update_job(self):
        """Test updating a job."""
        service = JobStoreService()
        service.redis_client = self.mock_redis
        
        job_id = "test-job-123"
        existing_data = {"job_id": job_id, "status": "pending"}
        updates = {"status": "running"}
        
        import json
        self.mock_redis.get.return_value = json.dumps(existing_data)
        
        result = service.update_job(job_id, updates)
        
        assert result is True
        self.mock_redis.set.assert_called_once()
    
    def test_update_job_not_found(self):
        """Test updating a non-existent job."""
        service = JobStoreService()
        service.redis_client = self.mock_redis
        
        self.mock_redis.get.return_value = None
        
        result = service.update_job("non-existent", {"status": "running"})
        
        assert result is False
    
    def test_delete_job(self):
        """Test deleting a job."""
        service = JobStoreService()
        service.redis_client = self.mock_redis
        
        job_id = "test-job-123"
        
        result = service.delete_job(job_id)
        
        assert result is True
        self.mock_redis.delete.assert_called_once()
        self.mock_redis.zrem.assert_called_once()
    
    def test_list_jobs(self):
        """Test listing jobs."""
        service = JobStoreService()
        service.redis_client = self.mock_redis
        
        job_ids = [b"job1", b"job2", b"job3"]
        self.mock_redis.zrevrange.return_value = job_ids
        
        import json
        self.mock_redis.get.side_effect = [
            json.dumps({"job_id": "job1", "status": "completed"}),
            json.dumps({"job_id": "job2", "status": "pending"}),
            json.dumps({"job_id": "job3", "status": "running"})
        ]
        
        result = service.list_jobs(limit=10)
        
        assert len(result) == 3
        assert result[0]["job_id"] == "job1"
    
    def test_list_jobs_with_status_filter(self):
        """Test listing jobs with status filter."""
        service = JobStoreService()
        service.redis_client = self.mock_redis
        
        job_ids = [b"job1", b"job2"]
        self.mock_redis.zrevrange.return_value = job_ids
        
        import json
        self.mock_redis.get.side_effect = [
            json.dumps({"job_id": "job1", "status": "completed"}),
            json.dumps({"job_id": "job2", "status": "pending"})
        ]
        
        result = service.list_jobs(limit=10, status="completed")
        
        assert len(result) == 1
        assert result[0]["status"] == "completed"
    
    def test_job_exists(self):
        """Test checking if a job exists."""
        service = JobStoreService()
        service.redis_client = self.mock_redis
        
        self.mock_redis.exists.return_value = 1
        
        result = service.job_exists("test-job-123")
        
        assert result is True
    
    def test_job_not_exists(self):
        """Test checking if a job doesn't exist."""
        service = JobStoreService()
        service.redis_client = self.mock_redis
        
        self.mock_redis.exists.return_value = 0
        
        result = service.job_exists("non-existent")
        
        assert result is False
    
    def test_get_job_count(self):
        """Test getting total job count."""
        service = JobStoreService()
        service.redis_client = self.mock_redis
        
        self.mock_redis.zcard.return_value = 5
        
        result = service.get_job_count()
        
        assert result == 5
