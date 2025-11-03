"""
Job store service for managing research job states using Redis.
"""

import json
import redis
from typing import Dict, Any, Optional, List
from datetime import datetime

from ..config.settings import settings
from ..config.logging import get_logger

logger = get_logger(__name__)


class JobStoreService:
    """Service for managing job storage with Redis backend."""
    
    def __init__(self):
        """Initialize the job store service with Redis connection."""
        self.redis_client: Optional[redis.Redis] = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize Redis client connection."""
        try:
            logger.info(f"Connecting to Redis at {settings.redis_host}:{settings.redis_port}")
            
            self.redis_client = redis.Redis(
                host=settings.redis_host,
                port=settings.redis_port,
                db=settings.redis_db,
                password=settings.redis_password,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
            
            # Test connection
            self.redis_client.ping()
            logger.info("Redis connection established successfully")
            
        except redis.ConnectionError as e:
            logger.error(f"Failed to connect to Redis: {e}")
            logger.warning("Falling back to in-memory job storage")
            self.redis_client = None
        except Exception as e:
            logger.error(f"Unexpected error initializing Redis client: {e}")
            self.redis_client = None
    
    def _get_job_key(self, job_id: str) -> str:
        """Generate Redis key for a job."""
        return f"job:{job_id}"
    
    def _get_jobs_list_key(self) -> str:
        """Generate Redis key for jobs list."""
        return "jobs:list"
    
    def create_job(self, job_id: str, job_data: Dict[str, Any]) -> bool:
        """
        Create a new job entry.
        
        Args:
            job_id: Unique job identifier
            job_data: Job data dictionary
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.redis_client:
                logger.warning("Redis client not available")
                return False
            
            job_key = self._get_job_key(job_id)
            
            # Serialize job data to JSON
            job_json = json.dumps(job_data, default=str)
            
            # Store job data
            self.redis_client.set(job_key, job_json)
            
            # Add job_id to jobs list with timestamp as score
            timestamp = datetime.now().timestamp()
            self.redis_client.zadd(self._get_jobs_list_key(), {job_id: timestamp})
            
            logger.debug(f"Created job {job_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create job {job_id}: {e}")
            return False
    
    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get job data by job_id.
        
        Args:
            job_id: Unique job identifier
            
        Returns:
            Job data dictionary or None if not found
        """
        try:
            if not self.redis_client:
                logger.warning("Redis client not available")
                return None
            
            job_key = self._get_job_key(job_id)
            job_json = self.redis_client.get(job_key)
            
            if job_json:
                job_data = json.loads(job_json)
                return job_data
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get job {job_id}: {e}")
            return None
    
    def update_job(self, job_id: str, updates: Dict[str, Any]) -> bool:
        """
        Update job data.
        
        Args:
            job_id: Unique job identifier
            updates: Dictionary of fields to update
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.redis_client:
                logger.warning("Redis client not available")
                return False
            
            # Get current job data
            job_data = self.get_job(job_id)
            if not job_data:
                logger.warning(f"Job {job_id} not found for update")
                return False
            
            # Update fields
            job_data.update(updates)
            
            # Save updated data
            job_key = self._get_job_key(job_id)
            job_json = json.dumps(job_data, default=str)
            self.redis_client.set(job_key, job_json)
            
            logger.debug(f"Updated job {job_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update job {job_id}: {e}")
            return False
    
    def delete_job(self, job_id: str) -> bool:
        """
        Delete a job.
        
        Args:
            job_id: Unique job identifier
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.redis_client:
                logger.warning("Redis client not available")
                return False
            
            job_key = self._get_job_key(job_id)
            
            # Delete job data
            self.redis_client.delete(job_key)
            
            # Remove from jobs list
            self.redis_client.zrem(self._get_jobs_list_key(), job_id)
            
            logger.debug(f"Deleted job {job_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete job {job_id}: {e}")
            return False
    
    def list_jobs(
        self, 
        limit: int = 10, 
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        List all jobs with optional filtering.
        
        Args:
            limit: Maximum number of jobs to return
            status: Optional status filter
            
        Returns:
            List of job data dictionaries
        """
        try:
            if not self.redis_client:
                logger.warning("Redis client not available")
                return []
            
            # Get all job IDs sorted by timestamp (most recent first)
            job_ids = self.redis_client.zrevrange(self._get_jobs_list_key(), 0, -1)
            
            jobs = []
            for job_id in job_ids:
                job_data = self.get_job(job_id)
                if job_data:
                    # Filter by status if provided
                    if status and job_data.get("status") != status:
                        continue
                    jobs.append(job_data)
            
            # Apply limit
            return jobs[:limit]
            
        except Exception as e:
            logger.error(f"Failed to list jobs: {e}")
            return []
    
    def get_job_count(self, status: Optional[str] = None) -> int:
        """
        Get total count of jobs.
        
        Args:
            status: Optional status filter
            
        Returns:
            Number of jobs
        """
        try:
            if not self.redis_client:
                logger.warning("Redis client not available")
                return 0
            
            if status:
                # Count jobs with specific status
                job_ids = self.redis_client.zrange(self._get_jobs_list_key(), 0, -1)
                count = 0
                for job_id in job_ids:
                    job_data = self.get_job(job_id)
                    if job_data and job_data.get("status") == status:
                        count += 1
                return count
            else:
                # Total count
                return self.redis_client.zcard(self._get_jobs_list_key())
            
        except Exception as e:
            logger.error(f"Failed to get job count: {e}")
            return 0
    
    def job_exists(self, job_id: str) -> bool:
        """
        Check if a job exists.
        
        Args:
            job_id: Unique job identifier
            
        Returns:
            True if job exists, False otherwise
        """
        try:
            if not self.redis_client:
                logger.warning("Redis client not available")
                return False
            
            job_key = self._get_job_key(job_id)
            return self.redis_client.exists(job_key) > 0
            
        except Exception as e:
            logger.error(f"Failed to check job existence: {e}")
            return False
    
    def close(self):
        """Close the Redis connection."""
        try:
            if self.redis_client:
                self.redis_client.close()
                logger.info("Redis connection closed")
        except Exception as e:
            logger.error(f"Error closing Redis connection: {e}")


# Global job store service instance
job_store_service = JobStoreService()
