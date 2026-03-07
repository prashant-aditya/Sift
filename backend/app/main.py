import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.health import router as health_router
from app.config import get_settings
from app.sources.duckduckgo import DuckDuckGoAdapter
from app.sources.hackernews import HackerNewsAdapter
from app.sources.registry import SourceRegistry
from app.sources.wikipedia import WikipediaAdapter

logger = logging.getLogger(__name__)

source_registry = SourceRegistry()


def _register_sources() -> None:
    source_registry.register(DuckDuckGoAdapter())
    source_registry.register(WikipediaAdapter())
    source_registry.register(HackerNewsAdapter())


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    _register_sources()
    logger.info(
        "Starting Sift backend — chroma_dir=%s, llm=%s, sources=%s",
        settings.chroma_persist_dir,
        settings.llm_model,
        [s.name for s in source_registry.get_available()],
    )
    yield
    logger.info("Shutting down Sift backend")


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="Sift Research Engine",
        description="AI-powered multi-source research engine",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health_router)

    return app


app = create_app()
