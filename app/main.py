import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api import api_router
from app.config.settings import settings

logging.basicConfig(level=settings.log_level)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting %s (env=%s)", settings.app_name, settings.app_env)
    yield
    logger.info("Shutting down %s", settings.app_name)


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        description="Automated lead search and qualification pipeline",
        version="0.1.0",
        lifespan=lifespan,
        debug=settings.debug,
    )
    app.include_router(api_router, prefix="/api/v1")
    return app


app = create_app()
