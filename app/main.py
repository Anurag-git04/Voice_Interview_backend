"""FastAPI application entry point."""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from datetime import datetime
import logging
import sys

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.config import settings
from app.db import connect_to_mongo, close_mongo_connection
from app.routes.sessions import router as sessions_router
from app.routes.auth import router as auth_router
from app.schemas import HealthResponse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events.
    """
    # Startup
    logger.info("Starting up application...")
    try:
        await connect_to_mongo()
        logger.info("Application startup complete")
    except Exception as e:
        logger.error(f"Failed to start application: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down application...")
    await close_mongo_connection()
    logger.info("Application shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="AI Voice Interview Coach API",
    description="Backend API for AI-powered interview practice with voice interaction",
    version="1.0.0",
    lifespan=lifespan
)

# Add rate limiter to app state
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Configure CORS
# Build allowed origins list from environment variables
origins = [
    settings.frontend_origin,  # Primary frontend (e.g., http://localhost:3000)
    "http://localhost:3000",   # Development fallback
    "http://127.0.0.1:3000",   # Development fallback
]

# Add additional origins from ALLOWED_ORIGINS env var (comma-separated)
if settings.allowed_origins:
    additional_origins = [origin.strip() for origin in settings.allowed_origins.split(",") if origin.strip()]
    origins.extend(additional_origins)
    logger.info(f"Added {len(additional_origins)} additional CORS origins from ALLOWED_ORIGINS")

logger.info(f"CORS allowed origins: {origins}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Global exception handler for uncaught exceptions.
    Sanitizes error details in production to prevent information leakage.
    """
    # Log the full error server-side
    logger.error(f"Unhandled exception on {request.url}: {exc}", exc_info=True)
    
    # Return sanitized error to client (no internal details)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "An internal server error occurred",
            "path": str(request.url.path)  # Only path, not full URL with params
        }
    )


# Include routers
app.include_router(sessions_router)
app.include_router(auth_router)


# Health check endpoint
@app.get("/health", response_model=HealthResponse, tags=["health"])
async def health_check():
    """
    Health check endpoint for monitoring and deployment.
    """
    return HealthResponse(
        status="healthy",
        message="API is running",
        timestamp=datetime.utcnow()
    )


# Root endpoint
@app.get("/", tags=["root"])
async def root():
    """
    Root endpoint with API information.
    """
    return {
        "message": "AI Voice Interview Coach API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
