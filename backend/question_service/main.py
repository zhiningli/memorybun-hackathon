import logging
import sys
import mimetypes
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from services.question_service import QuestionService

# Configure logging FIRST
from middleware.log_filter import CorrelationIdFilter
from middleware.correlation import CorrelationIdMiddleware

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - [%(correlation_id)s] - %(levelname)s - %(message)s',
    handlers=[],  # We will add handler manually
    force=True
)

# Create handler with filter
handler = logging.StreamHandler(sys.stdout)
handler.addFilter(CorrelationIdFilter())
logging.getLogger().addHandler(handler)

# Add filter to root logger (optional, but handler filter is more important for formatting)
# logging.getLogger().addFilter(CorrelationIdFilter())

logging.getLogger().setLevel(logging.INFO)

# Import routers
# Import routers
from api.routers import question_lists_router, answers_router, rubrics_router, questions_router
from api.routers.admin import router as admin_router

logger = logging.getLogger(__name__)
logger.info("Starting Question Service - Logging configured")

# Blob storage path
BLOB_PATH = Path(__file__).parent / "data" / "blob"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan event handler for FastAPI app.
    Handles startup and shutdown events.
    """
    logger.info("Initializing Question Service...")
    
    # Import rubric store for FK validation
    from storage import JsonRubricStore
    from config import settings
    
    data_dir = settings.get_data_dir()
    
    # Create rubric store for FK validation in question_store
    rubric_store = JsonRubricStore(data_dir)
    
    # Initialize QuestionService with rubric_store for FK validation
    service = QuestionService(rubric_store=rubric_store)
    try:
        await service.initialize()
        app.state.question_service = service
        logger.info("QuestionService initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize QuestionService: {e}")
        # We might want to raise here if the service is unusable without data
        raise
    
    yield
    
    # Clean up if needed
    logger.info("Shutting down Question Service...")


app = FastAPI(
    title="MemoryBun Question Service",
    description="Microservice for managing questions, answers, and rubrics",
    version="0.1.0",
    lifespan=lifespan
)

# Add Correlation ID middleware
app.add_middleware(CorrelationIdMiddleware)

# CORS setup - origins are configurable via CORS_ORIGINS env var
from config import settings as app_settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=app_settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers with /api/v1 prefix
app.include_router(question_lists_router, prefix="/api/v1")
app.include_router(answers_router, prefix="/api/v1")
app.include_router(rubrics_router, prefix="/api/v1")
app.include_router(questions_router, prefix="/api/v1")
app.include_router(admin_router, prefix="/api/v1")

# Prometheus metrics instrumentation (exclude health checks)
from prometheus_fastapi_instrumentator import Instrumentator
Instrumentator(
    excluded_handlers=["/health", "/metrics", "/"]
).instrument(app).expose(app, endpoint="/metrics")


@app.get("/blob/{file_path:path}")
async def serve_blob_file(file_path: str):
    """
    Serve blob files with proper CORS headers for cross-origin image loading.
    This enables html2canvas to capture the images in screenshots.
    """
    full_path = BLOB_PATH / file_path
    
    # Security: ensure the path doesn't escape the blob directory
    try:
        full_path = full_path.resolve()
        if not str(full_path).startswith(str(BLOB_PATH.resolve())):
            raise HTTPException(status_code=403, detail="Access denied")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid path")
    
    if not full_path.exists() or not full_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    
    # Determine content type
    content_type, _ = mimetypes.guess_type(str(full_path))
    if content_type is None:
        content_type = "application/octet-stream"
    
    # Return file with CORS headers
    response = FileResponse(
        path=full_path,
        media_type=content_type,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, OPTIONS",
            "Access-Control-Allow-Headers": "*",
            "Cache-Control": "public, max-age=3600",
        }
    )
    return response


@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "Welcome to Question Service API", "service": "question_service"}


@app.get("/health")
async def health_check(request: Request):
    """Health check endpoint"""
    service = getattr(request.app.state, "question_service", None)
    if not service:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    if not service.questions:
        raise HTTPException(status_code=503, detail="Data not loaded")
        
    return {
        "status": "healthy", 
        "service": "question_service", 
        "questions_count": len(service.questions)
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True, log_level="debug")

