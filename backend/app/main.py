"""FastAPI application entry point."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse

from backend.app.core.config import settings
from backend.app.core.logging import setup_logging, get_logger, log_request
from backend.app.core.middleware import RequestIDMiddleware, auth_middleware, RateLimitMiddleware, AuditMiddleware
from backend.app.api.v1 import api_v1_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager."""
    setup_logging()
    logger = get_logger("main")
    logger.info("application_starting", version=settings.app_version, environment=settings.environment)
    yield
    logger.info("application_shutting_down")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="CloudDesk Autonomous Customer Support Platform",
    docs_url="/docs" if settings.environment != "production" else None,
    redoc_url="/redoc" if settings.environment != "production" else None,
    lifespan=lifespan,
)

# Request ID middleware (must be first to capture all requests)
app.add_middleware(RequestIDMiddleware)

# Authentication middleware (JWT bearer token)
app.add_middleware(auth_middleware)

# Rate limiting middleware
app.add_middleware(RateLimitMiddleware, redis_url=settings.redis_url)

# Audit middleware (after auth to capture user info)
app.add_middleware(AuditMiddleware)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Trusted host
if settings.trusted_hosts:
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.trusted_hosts)


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    import time
    start_time = time.perf_counter()
    request_id = request.state.request_id

    response = await call_next(request)

    duration_ms = (time.perf_counter() - start_time) * 1000

    logger = get_logger("http")
    log_request(
        logger,
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        duration_ms=duration_ms,
        request_id=request_id,
    )

    # Request ID already added to response headers by RequestIDMiddleware
    return response


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger = get_logger("exceptions")
    logger.error(
        "unhandled_exception",
        path=request.url.path,
        method=request.method,
        error_type=type(exc).__name__,
        error_message=str(exc),
        request_id=request.state.request_id,
        exc_info=True,
    )
    return JSONResponse(
        status_code=500,
        content={
            "type": "https://api.clouddesk.io/errors/internal",
            "title": "Internal Server Error",
            "status": 500,
            "detail": "An unexpected error occurred",
            "instance": str(request.url),
        },
    )


# Include API v1 router
app.include_router(api_v1_router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.app.main:app",
        host=settings.host,
        port=settings.port,
        workers=settings.workers,
        reload=settings.debug,
    )