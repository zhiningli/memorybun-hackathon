# Transcription Service Dockerfile
# Uses faster-whisper with CTranslate2 backend (no PyTorch needed)
FROM python:3.12-slim

# Labels for image metadata
LABEL org.opencontainers.image.source="https://github.com/zhiningli/MemoryBun"
LABEL org.opencontainers.image.title="MemoryBun Transcription Service"
LABEL org.opencontainers.image.description="Audio transcription with Whisper"

WORKDIR /app

# Install system dependencies including ffmpeg for audio processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for caching
COPY requirements.txt .

# Install Python dependencies (faster-whisper bundles CTranslate2)
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create data directories
RUN mkdir -p data/screenshots data/audio_chunks

# Expose port
EXPOSE 8001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8001/health')" || exit 1

# Run the application
# Note: Running as root due to Docker volume permission requirements
# The volumes mounted in docker-compose are created with root ownership
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]

