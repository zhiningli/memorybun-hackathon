# Question Service Dockerfile
FROM python:3.12-slim

# Labels for image metadata
LABEL org.opencontainers.image.source="https://github.com/zhiningli/MemoryBun"
LABEL org.opencontainers.image.title="MemoryBun Question Service"
LABEL org.opencontainers.image.description="Questions, answers, and rubrics API"

WORKDIR /app
ENV DATA_DIR=data

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash --uid 1000 appuser

# Copy requirements first for caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code with correct ownership
COPY --chown=appuser:appuser . .

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
