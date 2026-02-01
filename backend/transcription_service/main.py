import logging
import sys
from contextlib import asynccontextmanager
import asyncio
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi.errors import RateLimitExceeded
from api.routes import router as transcription_router
from services.transcription_worker import transcription_worker
from services.redis_client import initialize_redis, close_redis
from middleware.rate_limiter import limiter, rate_limit_exceeded_handler
from middleware.log_filter import CorrelationIdFilter
from middleware.correlation import CorrelationIdMiddleware

# Configure logging
# Create handler with filter
handler = logging.StreamHandler(sys.stdout)
handler.addFilter(CorrelationIdFilter())

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - [%(correlation_id)s] - %(levelname)s - %(message)s',
    handlers=[handler],
    force=True
)
logger = logging.getLogger(__name__)


from services.audio_transcription_service import AudioTranscriptionService

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan event handler for FastAPI app.
    Handles startup and shutdown events.
    """
    logger.info("Initializing Transcription Service...")
    
    # Instantiate and initialize AudioTranscriptionService
    service = AudioTranscriptionService()
    await service.initialize()
    app.state.audio_transcription_service = service

    # Startup: Initialize Redis connection
    try:
        await initialize_redis()
    except Exception as e:
        logger.warning(f"Failed to connect to Redis: {e}")
        logger.warning("Service will continue but Redis features will be unavailable")
    
    # Startup: Start background workers
    await transcription_worker.start(audio_transcription_service=service)
    
    try:
        yield
    finally:
        # Shutdown: Stop background workers
        # Use try/except to handle cancellation gracefully during reloads
        try:
            await transcription_worker.stop()
        except asyncio.CancelledError:
            # Expected during uvicorn reload, ignore
            pass
        except Exception as e:
            # Log other errors but don't crash
            logger.error(f"Error stopping workers during shutdown: {e}")
        
        # Shutdown: Close Redis connection
        try:
            await close_redis()
        except Exception as e:
            logger.error(f"Error closing Redis connection during shutdown: {e}")


app = FastAPI(
    title="Transcription Service API",
    description="Microservice for audio transcription with Whisper - MemoryBun",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Add Correlation ID middleware
app.add_middleware(CorrelationIdMiddleware)

# Configure CORS - origins are configurable via CORS_ORIGINS env var
from config import settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure Rate Limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

# Include routers
app.include_router(transcription_router)

# Prometheus metrics instrumentation (exclude health checks)
from prometheus_fastapi_instrumentator import Instrumentator
Instrumentator(
    excluded_handlers=["/health", "/metrics", "/"]
).instrument(app).expose(app, endpoint="/metrics")

# Mount static files for screenshots
# Screenshots are stored in /app/data/screenshots/ (inside container)
# Using parent.parent was incorrect - it resolved to /data which non-root can't write
screenshots_path = Path(__file__).parent / "data" / "screenshots"
screenshots_path.mkdir(parents=True, exist_ok=True)
app.mount(
    "/api/v1/transcribe/screenshots",
    StaticFiles(directory=str(screenshots_path)),
    name="screenshots"
)


@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "Welcome to Transcription Service API", "service": "transcription_service"}


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    from services.redis_client import get_redis_client
    
    redis_status = "unknown"
    try:
        client = get_redis_client()
        redis_healthy = await client.health_check()
        redis_status = "healthy" if redis_healthy else "unhealthy"
    except Exception as e:
        redis_status = f"error: {str(e)}"
    
    return {
        "status": "healthy",
        "service": "transcription_service",
        "redis": redis_status
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)

