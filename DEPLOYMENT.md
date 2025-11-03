# Deployment Guide

This guide explains how to deploy the Content Research Pipeline using Docker and docker-compose.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Configuration](#configuration)
3. [Deployment with Docker Compose](#deployment-with-docker-compose)
4. [Accessing the API](#accessing-the-api)
5. [Service Architecture](#service-architecture)
6. [Troubleshooting](#troubleshooting)
7. [Production Considerations](#production-considerations)

## Prerequisites

Before deploying the application, ensure you have the following installed:

- **Docker** (version 20.10 or higher)
- **Docker Compose** (version 2.0 or higher)

To verify your installation:

```bash
docker --version
docker-compose --version
```

## Configuration

### 1. Create Environment File

Copy the example environment file and configure it with your credentials:

```bash
cp env.example .env
```

### 2. Configure Required Variables

Edit the `.env` file and set the following **required** variables:

```env
# OpenAI API Configuration (Required)
OPENAI_API_KEY=your_openai_api_key_here

# Google Search API Configuration (Required)
GOOGLE_API_KEY=your_google_api_key_here
GOOGLE_CSE_ID=your_google_cse_id_here
```

### 3. Configure Optional Variables

The following optional variables can be customized (defaults are set in the application):

```env
# Application Configuration
LOG_LEVEL=INFO
CACHE_EXPIRE_SECONDS=3600

# API Configuration
API_KEY=your_secure_api_key_here  # Leave empty to disable authentication

# Analysis Configuration
MAX_SEARCH_RESULTS=5
MAX_TOPICS=5
SENTIMENT_THRESHOLD=0.5

# Media Processing
DOWNLOAD_IMAGES=true
DOWNLOAD_VIDEOS=false
MAX_CONTENT_LENGTH=10000000
```

**Note:** Redis and ChromaDB connection settings are automatically configured in `docker-compose.yml` and do not need to be set in `.env`.

## Deployment with Docker Compose

### Quick Start

To launch the entire application stack (API, Redis, and ChromaDB):

```bash
docker-compose up -d
```

This command will:
1. Build the API container from the Dockerfile
2. Pull the Redis (alpine) and ChromaDB images
3. Create a shared network for inter-service communication
4. Start all services in detached mode

### View Logs

To view logs from all services:

```bash
docker-compose logs -f
```

To view logs from a specific service:

```bash
docker-compose logs -f api
docker-compose logs -f redis
docker-compose logs -f chromadb
```

### Check Service Status

```bash
docker-compose ps
```

### Stop the Application

```bash
docker-compose down
```

To stop and remove volumes (⚠️ this will delete all data):

```bash
docker-compose down -v
```

## Accessing the API

Once the services are running:

### Interactive API Documentation

Open your browser and navigate to:

- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

### API Endpoints

The following endpoints are available:

#### Health Check
```bash
curl http://localhost:8000/health
```

#### Start a Research Job
```bash
curl -X POST "http://localhost:8000/research" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your_api_key_here" \
  -d '{
    "query": "artificial intelligence impact on healthcare",
    "include_images": true,
    "include_videos": true,
    "include_news": true
  }'
```

Response:
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  "message": "Research job created successfully. Use /status/{job_id} to check progress."
}
```

#### Check Job Status
```bash
curl -H "X-API-Key: your_api_key_here" \
  http://localhost:8000/status/550e8400-e29b-41d4-a716-446655440000
```

#### List All Jobs
```bash
curl -H "X-API-Key: your_api_key_here" \
  "http://localhost:8000/jobs?limit=10&status=completed"
```

#### View Generated Report

Once a job is completed, access the HTML report at:
```
http://localhost:8000/reports/{job_id}.html
```

## Service Architecture

The application consists of three main services:

### 1. API Service (`api`)
- **Image**: Built from local Dockerfile
- **Port**: 8000
- **Purpose**: FastAPI application for content research
- **Dependencies**: Redis, ChromaDB

### 2. Redis Service (`redis`)
- **Image**: redis:alpine
- **Port**: 6379
- **Purpose**: Job state persistence and caching
- **Data**: Stored in `redis_data` volume

### 3. ChromaDB Service (`chromadb`)
- **Image**: chromadb/chroma:latest
- **Port**: 8001 (mapped from container's 8000)
- **Purpose**: Vector database for content embeddings
- **Data**: Stored in `chromadb_data` volume

All services communicate through a dedicated Docker network (`content-research-network`).

## Troubleshooting

### Services Not Starting

**Check logs for errors:**
```bash
docker-compose logs
```

**Ensure ports are not in use:**
```bash
# Check if ports 8000, 6379, or 8001 are already in use
netstat -tuln | grep -E '8000|6379|8001'
```

**Stop conflicting services:**
```bash
# On Linux/Mac
sudo lsof -ti:8000 | xargs kill -9
sudo lsof -ti:6379 | xargs kill -9
sudo lsof -ti:8001 | xargs kill -9
```

### API Health Check Failing

**Verify API key configuration:**
- If `API_KEY` is set in `.env`, include it in all requests via the `X-API-Key` header
- To disable authentication, remove or comment out the `API_KEY` variable

**Check service dependencies:**
```bash
# Verify Redis is running
docker-compose exec redis redis-cli ping
# Expected output: PONG

# Verify ChromaDB is running
curl http://localhost:8001/api/v1/heartbeat
# Expected output: {"nanosecond heartbeat": <timestamp>}
```

### spaCy Model Missing

If you see errors about missing spaCy model:

```bash
# Rebuild the API container
docker-compose build api
docker-compose up -d api
```

### Permission Issues with Volumes

If you encounter permission errors with mounted volumes:

```bash
# Create directories with appropriate permissions
mkdir -p reports chroma_db cache
chmod 755 reports chroma_db cache
```

### Rebuilding After Code Changes

To rebuild the API after making code changes:

```bash
docker-compose build api
docker-compose up -d api
```

Or rebuild all services:

```bash
docker-compose build
docker-compose up -d
```

## Production Considerations

### Security

1. **API Key Authentication**: Always set a strong `API_KEY` in production
2. **HTTPS**: Use a reverse proxy (nginx, traefik) for SSL/TLS termination
3. **Secrets Management**: Consider using Docker secrets or a vault service for sensitive data
4. **Network Isolation**: Restrict external access to Redis and ChromaDB

### Scaling

For production workloads:

1. **Multiple API Workers**: Scale the API service
   ```bash
   docker-compose up -d --scale api=3
   ```

2. **External Services**: Use managed Redis and vector database services

3. **Load Balancing**: Add a load balancer in front of API instances

### Monitoring

1. **Health Checks**: Monitor the `/health` endpoint
2. **Logs**: Aggregate logs using ELK stack or similar
3. **Metrics**: Implement Prometheus/Grafana for monitoring

### Backup

Regularly backup Docker volumes:

```bash
# Backup Redis data
docker run --rm \
  -v content-research-pipeline_redis_data:/data \
  -v $(pwd)/backups:/backup \
  busybox tar czf /backup/redis-$(date +%Y%m%d).tar.gz -C /data .

# Backup ChromaDB data
docker run --rm \
  -v content-research-pipeline_chromadb_data:/data \
  -v $(pwd)/backups:/backup \
  busybox tar czf /backup/chromadb-$(date +%Y%m%d).tar.gz -C /data .
```

### Resource Limits

Add resource limits to `docker-compose.yml`:

```yaml
services:
  api:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G
        reservations:
          cpus: '1'
          memory: 2G
```

## Additional Resources

- [Project README](README.md)
- [Production Deployment Guide](PRODUCTION_DEPLOYMENT.md)
- [API Documentation](http://localhost:8000/docs) (when running)
- [Contributing Guide](CONTRIBUTING.md)

For issues and feature requests, visit the [GitHub repository](https://github.com/siddhant61/content-research-pipeline).
