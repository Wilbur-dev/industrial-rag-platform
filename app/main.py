"""FastAPI application entrypoint — Week 1 + Week 2."""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.error_handlers import register_exception_handlers
from app.api.routes import router
from app.config import get_settings
from app.logging_config import get_logger, setup_logging

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    settings = get_settings()
    logger.info("app_starting", app=settings.app_name, env=settings.app_env)
    yield
    logger.info("app_shutdown")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        description="Week 2 — Retrieval Quality & Evaluation",
        version="0.2.0",
        lifespan=lifespan,
    )
    register_exception_handlers(app)
    app.include_router(router, prefix="/api/v1")
    return app


app = create_app()
