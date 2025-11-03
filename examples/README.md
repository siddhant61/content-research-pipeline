# API Usage Examples

This directory contains example scripts demonstrating how to use the Content Research Pipeline API.

## Prerequisites

1. Install the `requests` library:
   ```bash
   pip install requests
   ```

2. Start the API server:
   ```bash
   # Without Redis (in-memory mode)
   uvicorn src.content_research_pipeline.api.main:app --host 0.0.0.0 --port 8000
   
   # With Redis (production mode)
   redis-server &
   uvicorn src.content_research_pipeline.api.main:app --host 0.0.0.0 --port 8000
   ```

3. Set up API key (optional):
   ```bash
   export API_KEY=your-secure-api-key
   ```

## Running the Examples

### Basic API Usage

Run the complete example:

```bash
cd examples
python api_usage_example.py
```

This script demonstrates:
- Starting a research job
- Checking job status
- Waiting for completion
- Retrieving the HTML report URL
- Listing jobs
- Deleting jobs

### Using the Client Library

You can import and use the `ContentResearchClient` class in your own scripts:

```python
from api_usage_example import ContentResearchClient
import os

# Initialize client
client = ContentResearchClient(
    base_url="http://localhost:8000",
    api_key=os.getenv("API_KEY")
)

# Start a research job
response = client.start_research(
    query="quantum computing applications",
    include_images=True,
    include_videos=False,
    include_news=True
)

job_id = response["job_id"]
print(f"Job created: {job_id}")

# Wait for completion
final_status = client.wait_for_completion(job_id)

# Get report URL
if final_status["status"] == "completed":
    report_url = client.get_report_url(job_id)
    print(f"Report: {report_url}")
```

## Example Output

```
Content Research Pipeline API Example
==================================================

1. Starting a research job...
   Job created: 550e8400-e29b-41d4-a716-446655440000
   Status: pending

2. Checking job status...
   Current status: pending
   Query: artificial intelligence trends 2024

3. Waiting for job to complete...
Job status: running... waiting 5s
Job status: running... waiting 5s
   Job completed with status: completed
   Report available at: http://localhost:8000/reports/550e8400-e29b-41d4-a716-446655440000.html

   Summary: This comprehensive analysis examines the current trends in artificial intelligence...

4. Listing recent jobs...
   Total jobs: 5
   Recent jobs:
     - 550e8400-e29b-41d4-a716-446655440000: completed (artificial intelligence trends 2024...)
     - 123e4567-e89b-12d3-a456-426614174000: completed (machine learning best practices...)
     - 987fcdeb-51a2-43f1-b7c9-12345678abcd: failed (invalid query test...)

5. Listing completed jobs...
   Completed jobs: 4

6. Deleting job 550e8400-e29b-41d4-a716-446655440000...
   Job 550e8400-e29b-41d4-a716-446655440000 deleted successfully

==================================================
Example completed!
```

## API Endpoints Used

### POST /research
Start a new research job.

**Request:**
```json
{
  "query": "research topic",
  "include_images": true,
  "include_videos": true,
  "include_news": true,
  "max_results": 10
}
```

**Response:**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  "message": "Research job created successfully..."
}
```

### GET /status/{job_id}
Get job status and results.

**Response:**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "query": "research topic",
  "created_at": "2024-01-01T00:00:00",
  "completed_at": "2024-01-01T00:05:30",
  "report_url": "/reports/550e8400-e29b-41d4-a716-446655440000.html",
  "result": {
    "state": {...},
    "visualization": {...},
    "processing_time": 330.5
  }
}
```

### GET /jobs
List all jobs with optional filtering.

**Query Parameters:**
- `limit`: Maximum number of jobs to return (default: 10)
- `status`: Filter by status (pending, running, completed, failed)

**Response:**
```json
{
  "total": 25,
  "filtered": 10,
  "jobs": [
    {
      "job_id": "550e8400-e29b-41d4-a716-446655440000",
      "status": "completed",
      "query": "research topic",
      "created_at": "2024-01-01T00:00:00",
      "completed_at": "2024-01-01T00:05:30"
    }
  ]
}
```

### DELETE /jobs/{job_id}
Delete a completed or failed job.

**Response:**
```json
{
  "message": "Job 550e8400-e29b-41d4-a716-446655440000 deleted successfully"
}
```

## Authentication

If API key authentication is enabled, include the key in the `X-API-Key` header:

```python
headers = {
    "X-API-Key": "your-api-key",
    "Content-Type": "application/json"
}

response = requests.post(
    "http://localhost:8000/research",
    json={"query": "research topic"},
    headers=headers
)
```

## Error Handling

The client handles common HTTP errors:

```python
try:
    response = client.start_research(query="test")
except requests.exceptions.HTTPError as e:
    if e.response.status_code == 401:
        print("Authentication failed - check API key")
    elif e.response.status_code == 422:
        print("Invalid request - check parameters")
    else:
        print(f"Error: {e}")
```

## Advanced Usage

### Custom Timeout

```python
# Wait up to 10 minutes with 10-second poll interval
status = client.wait_for_completion(
    job_id,
    poll_interval=10,
    timeout=600
)
```

### List Only Failed Jobs

```python
failed_jobs = client.list_jobs(limit=20, status="failed")
for job in failed_jobs["jobs"]:
    print(f"Failed job: {job['job_id']}")
```

### Download Report

```python
import requests

report_url = client.get_report_url(job_id)
if report_url:
    response = requests.get(report_url)
    with open("report.html", "w") as f:
        f.write(response.text)
```

## Troubleshooting

### Connection Refused

If you get "Connection refused" errors:
1. Ensure the API server is running
2. Check the correct port (default: 8000)
3. Verify firewall settings

### Authentication Errors

If you get 401 Unauthorized:
1. Check that API_KEY is set correctly
2. Verify the key matches the server configuration
3. Ensure the `X-API-Key` header is included

### Timeout Errors

If jobs timeout:
1. Increase the timeout parameter
2. Check API server logs for errors
3. Verify required services (OpenAI, Google Search) are accessible

## Additional Resources

- [API Documentation](http://localhost:8000/docs) - Interactive Swagger UI
- [Production Deployment Guide](../PRODUCTION_DEPLOYMENT.md) - Deployment instructions
- [Main README](../README.md) - Project overview
