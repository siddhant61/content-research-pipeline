# Production Deployment Guide

This guide describes the production-ready features implemented in Phase 6 & 7, including Redis-backed persistence, API security, and enhanced documentation.

## Table of Contents

1. [Redis Job Store](#redis-job-store)
2. [Redis-Backed Cache](#redis-backed-cache)
3. [ChromaDB Client/Server Mode](#chromadb-clientserver-mode)
4. [API Key Authentication](#api-key-authentication)
5. [Static File Serving](#static-file-serving)
6. [Enhanced API Documentation](#enhanced-api-documentation)
7. [Configuration](#configuration)
8. [Deployment](#deployment)

## Redis Job Store

The API now uses Redis to persist job state across restarts and share state across multiple API workers.

### Features

- **Persistent Storage**: Job data persists in Redis, surviving API restarts
- **Scalability**: Multiple API workers can share the same Redis instance
- **Graceful Fallback**: Automatically falls back to in-memory storage if Redis is unavailable

### Implementation

The `JobStoreService` in `src/content_research_pipeline/services/job_store.py` provides:

- `create_job(job_id, job_data)`: Create a new job entry
- `get_job(job_id)`: Retrieve job data by ID
- `update_job(job_id, updates)`: Update job fields
- `delete_job(job_id)`: Remove a job
- `list_jobs(limit, status)`: List jobs with filtering
- `job_exists(job_id)`: Check if a job exists

### Usage Example

```python
from src.content_research_pipeline.services.job_store import job_store_service

# Create a job
job_data = {
    "job_id": "123",
    "status": "pending",
    "query": "research query",
    "created_at": datetime.now().isoformat()
}
job_store_service.create_job("123", job_data)

# Retrieve a job
job = job_store_service.get_job("123")

# Update job status
job_store_service.update_job("123", {"status": "completed"})
```

## Redis-Backed Cache

The caching system now uses Redis for shared caching across multiple workers.

### Features

- **Shared Cache**: All API workers share the same cache via Redis
- **Automatic Expiration**: Redis handles TTL automatically
- **Pickle Serialization**: Supports caching complex Python objects
- **Graceful Fallback**: Falls back to in-memory cache if Redis is unavailable

### Implementation

The cache decorators in `src/content_research_pipeline/utils/caching.py`:

- `@cache_result(expire_after)`: Async function caching
- `@cache_sync_result(expire_after)`: Sync function caching
- `CacheManager`: Advanced cache operations

### Usage Example

```python
from src.content_research_pipeline.utils.caching import cache_result, CacheManager

# Decorate async functions
@cache_result(expire_after=3600)
async def expensive_operation(param):
    # ... expensive computation
    return result

# Use CacheManager for manual caching
manager = CacheManager()
manager.set("key", "value", expire_after=1800)
value = manager.get("key")
```

## ChromaDB Client/Server Mode

ChromaDB now supports client/server architecture for better scalability.

### Features

- **Remote Server**: Connect to a ChromaDB server via HTTP
- **Scalability**: ChromaDB can run independently in a container
- **Graceful Fallback**: Falls back to local persistent storage if server is unavailable

### Configuration

Set these environment variables:

```bash
CHROMA_HOST=localhost
CHROMA_PORT=8000
```

### Deployment

Run ChromaDB server in a Docker container:

```bash
docker run -p 8000:8000 chromadb/chroma:latest
```

## API Key Authentication

All API endpoints are now protected with API key authentication.

### Features

- **Header-Based**: Uses `X-API-Key` header
- **Optional**: Authentication is skipped if API_KEY is not configured
- **Backward Compatible**: Existing deployments without API keys continue to work

### Configuration

Set the API key in your `.env` file:

```bash
API_KEY=your-secure-api-key-here
```

### Usage

Include the API key in request headers:

```bash
curl -X POST http://localhost:8000/research \
  -H "X-API-Key: your-secure-api-key-here" \
  -H "Content-Type: application/json" \
  -d '{"query": "research topic"}'
```

### Python Example

```python
import requests

headers = {
    "X-API-Key": "your-secure-api-key-here",
    "Content-Type": "application/json"
}

response = requests.post(
    "http://localhost:8000/research",
    headers=headers,
    json={"query": "research topic"}
)
```

## Static File Serving

HTML reports are now saved to static files instead of being returned in API responses.

### Features

- **Reduced Memory**: Reports are not stored in Redis or memory
- **Direct Access**: Reports accessible via static URLs
- **Automatic Cleanup**: Old reports can be cleaned up independently

### Configuration

Reports are saved to the `reports/` directory, which is automatically created.

### Usage

After a job completes, get the report URL from the status endpoint:

```bash
curl -X GET http://localhost:8000/status/job-id-123 \
  -H "X-API-Key: your-api-key"
```

Response includes `report_url`:

```json
{
  "job_id": "job-id-123",
  "status": "completed",
  "report_url": "/reports/job-id-123.html",
  ...
}
```

Access the report directly:

```
http://localhost:8000/reports/job-id-123.html
```

## Enhanced API Documentation

The API now includes comprehensive OpenAPI (Swagger) documentation.

### Features

- **Tagged Endpoints**: Organized by category (health, research, jobs)
- **Rich Descriptions**: Detailed summaries and descriptions for each endpoint
- **Request/Response Models**: Complete Pydantic models for all endpoints
- **Interactive UI**: Try endpoints directly from Swagger UI

### Access Documentation

Visit these URLs when the API is running:

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`
- **OpenAPI JSON**: `http://localhost:8000/openapi.json`

### Endpoint Tags

- `health`: Health check and status endpoints
- `research`: Research job creation and status
- `jobs`: Job listing and management

## Configuration

### Environment Variables

Update your `.env` file with the following variables:

```bash
# API Configuration
API_KEY=your-secure-api-key-here
API_HOST=0.0.0.0
API_PORT=8000

# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=

# ChromaDB Configuration
CHROMA_HOST=localhost
CHROMA_PORT=8000
CHROMA_PERSIST_DIRECTORY=./chroma_db

# Cache Configuration
CACHE_EXPIRE_SECONDS=3600
```

### Required Services

For production deployment, you need:

1. **Redis**: For job storage and caching
2. **ChromaDB Server** (optional): For scalable vector storage
3. **API Application**: The FastAPI application

## Deployment

### Using Docker Compose

Create a `docker-compose.yml`:

```yaml
version: '3.8'

services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes

  chromadb:
    image: chromadb/chroma:latest
    ports:
      - "8000:8000"
    volumes:
      - chroma_data:/chroma/chroma
    environment:
      - IS_PERSISTENT=TRUE

  api:
    build: .
    ports:
      - "8001:8000"
    environment:
      - REDIS_HOST=redis
      - REDIS_PORT=6379
      - CHROMA_HOST=chromadb
      - CHROMA_PORT=8000
      - API_KEY=${API_KEY}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - GOOGLE_API_KEY=${GOOGLE_API_KEY}
      - GOOGLE_CSE_ID=${GOOGLE_CSE_ID}
    depends_on:
      - redis
      - chromadb
    volumes:
      - ./reports:/app/reports

volumes:
  redis_data:
  chroma_data:
```

### Start Services

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f api

# Stop services
docker-compose down
```

### Manual Deployment

1. **Start Redis**:
   ```bash
   redis-server
   ```

2. **Start ChromaDB** (optional):
   ```bash
   docker run -p 8000:8000 chromadb/chroma:latest
   ```

3. **Start API**:
   ```bash
   uvicorn src.content_research_pipeline.api.main:app --host 0.0.0.0 --port 8001
   ```

## Monitoring

### Health Check

```bash
curl http://localhost:8000/health
```

Response:

```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T00:00:00.000000",
  "redis": "connected"
}
```

### Cache Statistics

Use the `CacheManager` to get cache stats:

```python
from src.content_research_pipeline.utils.caching import cache_manager

stats = cache_manager.cleanup()
print(f"Cleaned up {stats} expired entries")
```

## Security Considerations

1. **API Key Management**: Store API keys securely (e.g., AWS Secrets Manager, HashiCorp Vault)
2. **Redis Security**: Use Redis AUTH and TLS in production
3. **Redis Namespace**: If sharing Redis with other apps, implement key prefixing (e.g., `crp:cache:*`, `crp:job:*`)
4. **Network Isolation**: Run services in a private network
5. **Rate Limiting**: Consider adding rate limiting middleware
6. **CORS**: Configure CORS appropriately for your frontend

### Redis Key Namespacing

When sharing Redis across multiple applications, implement key prefixes to avoid collisions:

```python
# Example: Add prefix to cache keys
CACHE_PREFIX = "crp:cache:"
cache_key = f"{CACHE_PREFIX}{func.__name__}:{args_str}"
```

**Warning**: The `CacheManager.clear()` method currently clears ALL keys in the Redis database. In production with shared Redis, modify this to use pattern matching with your prefix.

## Troubleshooting

### Redis Connection Issues

If Redis is not available, the API will fall back to in-memory storage. Check logs:

```
WARNING: Failed to connect to Redis: [error]
INFO: Falling back to in-memory job storage
```

### ChromaDB Connection Issues

If ChromaDB server is not available, the API will use local persistent storage:

```
WARNING: Failed to connect to ChromaDB server: [error]
INFO: Falling back to local ChromaDB client
```

### API Key Issues

If API key authentication fails:

```
ERROR: Invalid or missing API key
```

Ensure:
- API_KEY is set in .env
- X-API-Key header is included in requests
- API key matches the configured value

## Performance Tuning

1. **Redis Connection Pool**: Configure connection pool size
2. **Cache Expiration**: Adjust CACHE_EXPIRE_SECONDS based on data freshness needs
3. **Worker Processes**: Run multiple API workers behind a load balancer
4. **ChromaDB Batch Size**: Tune batch operations for large datasets

## Backup and Recovery

### Redis Backup

Redis supports automatic persistence (RDB and AOF):

```bash
# In redis.conf
save 900 1
save 300 10
save 60 10000
appendonly yes
```

### Report Backup

Backup the `reports/` directory regularly:

```bash
tar -czf reports-backup-$(date +%Y%m%d).tar.gz reports/
```

### ChromaDB Backup

Backup the ChromaDB data directory:

```bash
tar -czf chromadb-backup-$(date +%Y%m%d).tar.gz chroma_db/
```
