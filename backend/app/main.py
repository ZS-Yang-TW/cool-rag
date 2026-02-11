import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api import admin_router, assistant_router, documents_router
from app.core import DomainError, settings

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.console_log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan events for FastAPI app"""
    # Startup
    logger.info("Starting Canvas RAG Assistant API...")
    logger.info("✓ Application started (database migrations managed by Alembic)")

    yield

    # Shutdown
    logger.info("Shutting down Canvas RAG Assistant API...")


# Create FastAPI app
app = FastAPI(
    title="Canvas RAG Assistant API",
    description="RAG-based Q&A system for Canvas LMS documentation",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    contact={
        "name": "Canvas RAG Team",
    },
)

# Configure CORS
# TODO: Restrict origins in production deployments for better security
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for serving uploaded images
# TODO: Use object storage (e.g., S3) for production deployments
app.mount(
    "/images",
    StaticFiles(directory="uploaded_images"),
    name="images",
)


# Global exception handler for domain errors
@app.exception_handler(DomainError)
async def domain_error_handler(request: Request, exc: DomainError):
    """Handle domain-level business logic errors"""
    logger.warning(
        f"Domain error: {str(exc)}",
        extra={
            "error_code": exc.error_code,
            "status_code": exc.status_code,
            "path": request.url.path,
        },
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error_code": exc.error_code,
            "message": str(exc),
            "details": exc.details,
            "path": request.url.path,
        },
    )


# Include routers
app.include_router(assistant_router)
app.include_router(admin_router)
app.include_router(documents_router, prefix="/api")


@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "Canvas RAG Assistant API", "version": "1.0.0", "docs": "/docs"}


@app.get("/api")
async def api_info():
    """API information"""
    return {
        "name": "Canvas RAG Assistant API",
        "version": "1.0.0",
        "endpoints": {
            "chat": "/api/chat",
            "health": "/api/health",
            "stats": "/api/stats",
            "reindex": "/api/reindex",
        },
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.environment == "development",
        timeout_keep_alive=75,
        access_log=True,
    )
