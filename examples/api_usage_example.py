"""
Example script demonstrating API usage with authentication.

This script shows how to:
1. Start a research job
2. Check job status
3. Retrieve the report
4. List all jobs
5. Delete a completed job
"""

import requests
import time
import os
from typing import Dict, Optional


class ContentResearchClient:
    """Client for interacting with the Content Research Pipeline API."""
    
    def __init__(self, base_url: str = "http://localhost:8000", api_key: Optional[str] = None):
        """
        Initialize the client.
        
        Args:
            base_url: Base URL of the API
            api_key: API key for authentication (optional)
        """
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.headers = {"Content-Type": "application/json"}
        
        if api_key:
            self.headers["X-API-Key"] = api_key
    
    def start_research(
        self,
        query: str,
        include_images: bool = True,
        include_videos: bool = True,
        include_news: bool = True,
        max_results: Optional[int] = None
    ) -> Dict:
        """
        Start a new research job.
        
        Args:
            query: Research query
            include_images: Whether to include image search
            include_videos: Whether to include video search
            include_news: Whether to include news search
            max_results: Maximum number of search results
            
        Returns:
            Job creation response
        """
        payload = {
            "query": query,
            "include_images": include_images,
            "include_videos": include_videos,
            "include_news": include_news
        }
        
        if max_results:
            payload["max_results"] = max_results
        
        response = requests.post(
            f"{self.base_url}/research",
            json=payload,
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()
    
    def get_job_status(self, job_id: str) -> Dict:
        """
        Get the status of a job.
        
        Args:
            job_id: Job identifier
            
        Returns:
            Job status response
        """
        response = requests.get(
            f"{self.base_url}/status/{job_id}",
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()
    
    def list_jobs(self, limit: int = 10, status: Optional[str] = None) -> Dict:
        """
        List all jobs.
        
        Args:
            limit: Maximum number of jobs to return
            status: Filter by status (pending, running, completed, failed)
            
        Returns:
            List of jobs
        """
        params = {"limit": limit}
        if status:
            params["status"] = status
        
        response = requests.get(
            f"{self.base_url}/jobs",
            params=params,
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()
    
    def delete_job(self, job_id: str) -> Dict:
        """
        Delete a job.
        
        Args:
            job_id: Job identifier
            
        Returns:
            Deletion response
        """
        response = requests.delete(
            f"{self.base_url}/jobs/{job_id}",
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()
    
    def get_report_url(self, job_id: str) -> Optional[str]:
        """
        Get the report URL for a completed job.
        
        Args:
            job_id: Job identifier
            
        Returns:
            Report URL or None if not available
        """
        status = self.get_job_status(job_id)
        
        if status["status"] == "completed":
            report_url = status.get("report_url")
            if report_url:
                return f"{self.base_url}{report_url}"
        
        return None
    
    def wait_for_completion(self, job_id: str, poll_interval: int = 5, timeout: int = 300) -> Dict:
        """
        Wait for a job to complete.
        
        Args:
            job_id: Job identifier
            poll_interval: Seconds between status checks
            timeout: Maximum seconds to wait
            
        Returns:
            Final job status
            
        Raises:
            TimeoutError: If job doesn't complete within timeout
        """
        start_time = time.time()
        
        while True:
            status = self.get_job_status(job_id)
            
            if status["status"] in ["completed", "failed"]:
                return status
            
            if time.time() - start_time > timeout:
                raise TimeoutError(f"Job {job_id} did not complete within {timeout} seconds")
            
            print(f"Job status: {status['status']}... waiting {poll_interval}s")
            time.sleep(poll_interval)


def main():
    """Main example function."""
    
    # Get API key from environment variable
    api_key = os.getenv("API_KEY")
    
    # Create client
    client = ContentResearchClient(
        base_url="http://localhost:8000",
        api_key=api_key
    )
    
    print("Content Research Pipeline API Example")
    print("=" * 50)
    
    # Example 1: Start a research job
    print("\n1. Starting a research job...")
    job_response = client.start_research(
        query="artificial intelligence trends 2024",
        include_images=True,
        include_videos=False,
        include_news=True
    )
    
    job_id = job_response["job_id"]
    print(f"   Job created: {job_id}")
    print(f"   Status: {job_response['status']}")
    
    # Example 2: Check job status
    print("\n2. Checking job status...")
    status = client.get_job_status(job_id)
    print(f"   Current status: {status['status']}")
    print(f"   Query: {status['query']}")
    
    # Example 3: Wait for completion
    print("\n3. Waiting for job to complete...")
    try:
        final_status = client.wait_for_completion(job_id, poll_interval=5, timeout=600)
        print(f"   Job completed with status: {final_status['status']}")
        
        if final_status['status'] == 'completed':
            # Get report URL
            report_url = client.get_report_url(job_id)
            if report_url:
                print(f"   Report available at: {report_url}")
            
            # Print summary from results
            result = final_status.get('result')
            if result:
                state = result.get('state', {})
                analysis = state.get('analysis')
                if analysis:
                    summary = analysis.get('summary', '')
                    if summary:
                        print(f"\n   Summary: {summary[:200]}...")
        
        elif final_status['status'] == 'failed':
            print(f"   Error: {final_status.get('error', 'Unknown error')}")
    
    except TimeoutError as e:
        print(f"   Timeout: {e}")
    
    # Example 4: List all jobs
    print("\n4. Listing recent jobs...")
    jobs = client.list_jobs(limit=5)
    print(f"   Total jobs: {jobs['total']}")
    print(f"   Recent jobs:")
    for job in jobs['jobs']:
        print(f"     - {job['job_id']}: {job['status']} ({job['query'][:50]}...)")
    
    # Example 5: List completed jobs only
    print("\n5. Listing completed jobs...")
    completed_jobs = client.list_jobs(limit=10, status="completed")
    print(f"   Completed jobs: {completed_jobs['filtered']}")
    
    # Example 6: Delete a job (if it's not running)
    if final_status['status'] in ['completed', 'failed']:
        print(f"\n6. Deleting job {job_id}...")
        try:
            delete_response = client.delete_job(job_id)
            print(f"   {delete_response['message']}")
        except requests.exceptions.HTTPError as e:
            print(f"   Failed to delete: {e}")
    
    print("\n" + "=" * 50)
    print("Example completed!")


if __name__ == "__main__":
    main()
