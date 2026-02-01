import logging
import sys
from contextlib import asynccontextmanager
import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded

from api.routes import router as grading_router
from services.redis_client import initialize_redis, close_redis, get_redis_client
from services.grading_worker import start_grading_worker, stop_grading_worker, grading_worker
from services.summary_worker import start_summary_worker, stop_summary_worker, summary_worker
from services.rubric_provider import rubric_provider
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan event handler for FastAPI app.
    Handles startup and shutdown events.
    """
    logger.info("Initializing Grading Service...")

    # Startup: Initialize Redis connection
    try:
        await initialize_redis()
    except Exception as e:
        logger.warning(f"Failed to connect to Redis: {e}")
        logger.warning("Service will continue but Redis features will be unavailable")
    
    # Startup: Load Rubrics
    try:
        await rubric_provider.load_rubrics()
    except Exception as e:
        logger.warning(f"Failed to load rubrics: {e}")

    # Startup: Start grading worker
    try:
        await start_grading_worker()
    except Exception as e:
        logger.error(f"Failed to start grading worker: {e}")
    
    # Startup: Start summary worker
    try:
        await start_summary_worker()
    except Exception as e:
        logger.error(f"Failed to start summary worker: {e}")
    
    try:
        yield
    finally:
        # Shutdown: Stop workers and close connections
        try:
            await stop_grading_worker()
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Error stopping grading worker: {e}")
        
        try:
            await stop_summary_worker()
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Error stopping summary worker: {e}")
        
        # Shutdown: Close Redis connection
        try:
            await close_redis()
        except Exception as e:
            logger.error(f"Error closing Redis connection during shutdown: {e}")


app = FastAPI(
    title="Grading Service API",
    description="Microservice for LLM-based grading of student answers - MemoryBun",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Configure CORS (must be added before other middleware)
# CORS origins are configurable via CORS_ORIGINS env var
from config import settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add Correlation ID middleware
app.add_middleware(CorrelationIdMiddleware)

# Configure Rate Limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

# Include routers
app.include_router(grading_router)

# Prometheus metrics instrumentation (exclude health checks)
from prometheus_fastapi_instrumentator import Instrumentator
Instrumentator(
    excluded_handlers=["/health", "/metrics", "/"]
).instrument(app).expose(app, endpoint="/metrics")


@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "Welcome to Grading Service API", "service": "grading_service"}


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    redis_status = "unknown"
    try:
        client = get_redis_client()
        redis_healthy = await client.health_check()
        redis_status = "healthy" if redis_healthy else "unhealthy"
    except Exception as e:
        redis_status = f"error: {str(e)}"
    
    grading_worker_status = "running" if grading_worker.is_running else "stopped"
    summary_worker_status = "running" if summary_worker.is_running else "stopped"
    
    return {
        "status": "healthy",
        "service": "grading_service",
        "redis": redis_status,
        "grading_worker": grading_worker_status,
        "grading_worker_count": grading_worker.num_workers,
        "summary_worker": summary_worker_status,
        "summary_worker_count": summary_worker.num_workers
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8002, reload=True)
