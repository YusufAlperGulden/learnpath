"""FastAPI application entry point with CORS and centralized timestamped logging."""

import os
import time
from collections.abc import AsyncGenerator, Awaitable, Callable
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.logging_config import configure_logging, get_logger
from app.routers import (
    admin_catalog,
    assessments,
    auth,
    profile,
    progress,
    recommendations,
)

logger = get_logger("main")


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None, None]:
    configure_logging(debug=settings.DEBUG)
    logger.info("Starting %s v%s", settings.APP_NAME, settings.APP_VERSION)
    if settings.JWT_SECRET_KEY.startswith("change-this"):
        logger.warning(
            "JWT_SECRET_KEY is still the insecure development default; set a strong secret "
            "in the environment before exposing this server publicly."
        )
    yield
    logger.info("Shutting down %s", settings.APP_NAME)


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "Personalized Python Learning Path & Explainable Resource Recommendation System "
        "(COME 491 — Revised RAD v2.0)"
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_origin_regex=settings.CORS_ORIGIN_REGEX,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    started = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        logger.exception(
            "Unhandled error method=%s path=%s duration_ms=%.2f",
            request.method,
            request.url.path,
            elapsed_ms,
        )
        raise

    elapsed_ms = (time.perf_counter() - started) * 1000.0
    logger.info(
        "method=%s path=%s status=%d duration_ms=%.2f",
        request.method,
        request.url.path,
        response.status_code,
        elapsed_ms,
    )
    return response


@app.get(f"{settings.API_V1_PREFIX}/health", tags=["Health"])
def health_check() -> dict[str, str]:
    return {"status": "ok", "version": settings.APP_VERSION}


app.include_router(auth.router, prefix=settings.API_V1_PREFIX)
app.include_router(profile.router, prefix=settings.API_V1_PREFIX)
app.include_router(admin_catalog.router, prefix=settings.API_V1_PREFIX)
app.include_router(assessments.router, prefix=settings.API_V1_PREFIX)
app.include_router(progress.router, prefix=settings.API_V1_PREFIX)
app.include_router(recommendations.router, prefix=settings.API_V1_PREFIX)

# Optional unified SPA serving for single-URL cloud deployments (e.g., Render Blueprint)
_static_dist = Path(os.getenv("STATIC_DIST_DIR", "/app/static_dist"))
if _static_dist.is_dir() and (_static_dist / "index.html").is_file():
    _assets_dir = _static_dist / "assets"
    if _assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=str(_assets_dir)), name="spa-assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def serve_spa(full_path: str) -> FileResponse:
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="API route not found.")
        candidate = (_static_dist / full_path).resolve()
        if candidate.is_relative_to(_static_dist.resolve()) and candidate.is_file():
            return FileResponse(str(candidate))
        return FileResponse(str(_static_dist / "index.html"))
