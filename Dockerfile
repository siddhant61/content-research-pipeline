# Multi-stage Dockerfile for Content Research Pipeline
# Stage 1: Builder - Install dependencies and download models
FROM python:3.11-slim as builder

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Download spaCy model
RUN python -m spacy download en_core_web_sm

# Stage 2: Runtime - Create minimal production image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install runtime system dependencies (tesseract for OCR if needed)
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

# Copy Python packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY setup.py .
COPY README.md .
COPY src/ ./src/

# Install the application in development mode
RUN pip install --no-cache-dir -e .

# Create directories for data persistence
RUN mkdir -p /app/chroma_db /app/reports /app/cache

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    API_HOST=0.0.0.0 \
    API_PORT=8000

# Expose API port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')" || exit 1

# Run the FastAPI application with uvicorn
CMD ["uvicorn", "content_research_pipeline.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
