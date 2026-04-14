"""
FastAPI application entry point.

Responsibilities:
  - Create and configure the FastAPI app
  - Register middleware (CORS, rate limiting, logging)
  - Mount API routers
  - Add global exception handlers
"""
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler  # type: ignore
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.logging import get_logger, setup_logging
from app.middleware.logging import RequestLoggingMiddleware

# Logging setup
setup_logging()
logger = get_logger(__name__)

# Rate limiter
limiter = Limiter(key_func=get_remote_address, default_limits=[f"{settings.RATE_LIMIT_PER_MINUTE}/minute"])


# App factory
def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description=(
            "A production-ready FastAPI authentication service with JWT, "
            "Google OAuth2, RBAC, SMS/Email integrations."
        ),
        docs_url="/docs" if not settings.is_production else None,   # Hide Swagger in prod
        redoc_url="/redoc" if not settings.is_production else None,
        openapi_url="/openapi.json" if not settings.is_production else None,
    )

    # App state
    app.state.limiter = limiter

    # Middleware setup

    # 1. CORS — must come before auth middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )

    # 2. Rate limiting
    app.add_middleware(SlowAPIMiddleware)

    # 3. Request/response logging
    app.add_middleware(RequestLoggingMiddleware)

    # Exception handlers
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.error("unhandled_exception", error=str(exc), path=request.url.path, exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": "An unexpected error occurred. Please try again later."},
        )

    # API routers
    app.include_router(api_router)

    # Lifecycle hooks
    @app.on_event("startup")
    async def on_startup() -> None:
        logger.info(
            "application_started",
            app=settings.APP_NAME,
            version=settings.APP_VERSION,
            environment=settings.ENVIRONMENT,
        )

    @app.on_event("shutdown")
    async def on_shutdown() -> None:
        logger.info("application_shutdown")

    # Health check
    @app.get("/health", tags=["Health"], summary="Health check")
    async def health_check():
        return {"status": "ok", "version": settings.APP_VERSION}

    return app


app = create_app()
