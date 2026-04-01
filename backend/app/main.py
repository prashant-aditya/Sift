import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.health import router as health_router
from app.api.routes.research import router as research_router
from app.api.routes.sessions import router as sessions_router
from app.cache.embedding_cache import EmbeddingCache
from app.cache.redis_cache import ResearchCache
from app.config import get_settings
from app.core.logging_config import setup_logging
from app.core.query_analyzer import QueryAnalyzer
from app.core.synthesizer import Synthesizer
from app.db.session import create_engine, create_sessionmaker
from app.db.vector_store import VectorStore
from app.ingestion.embedder import EmbeddingGenerator
from app.ingestion.pipeline import IngestionPipeline
from app.middleware.request_context import RequestContextMiddleware
from app.sources.arxiv import ArxivAdapter
from app.sources.duckduckgo import DuckDuckGoAdapter
from app.sources.hackernews import HackerNewsAdapter
from app.sources.reddit import RedditAdapter
from app.sources.registry import SourceRegistry
from app.sources.wikipedia import WikipediaAdapter
from workers.celery_app import celery_app

logger = logging.getLogger(__name__)

source_registry = SourceRegistry()


def _register_sources() -> None:
    source_registry.register(DuckDuckGoAdapter())
    source_registry.register(WikipediaAdapter())
    source_registry.register(HackerNewsAdapter())
    source_registry.register(ArxivAdapter())
    source_registry.register(RedditAdapter())


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    _register_sources()

    embedding_cache = EmbeddingCache(max_entries=10_000)
    embedder = EmbeddingGenerator(
        hf_api_token=settings.hf_api_token,
        model_name=settings.embedding_model,
        embedding_cache=embedding_cache,
    )

    app.state.source_registry = source_registry
    app.state.query_analyzer = QueryAnalyzer()
    app.state.vector_store = VectorStore()
    app.state.embedder = embedder
    app.state.ingestion_pipeline = IngestionPipeline(embedder=embedder)
    app.state.synthesizer = Synthesizer()
    app.state.celery_app = celery_app
    app.state.research_cache = ResearchCache.from_url(settings.redis_url)

    db_engine = create_engine(settings)
    app.state.db_engine = db_engine
    app.state.db_sessionmaker = create_sessionmaker(db_engine)

    logger.info(
        "Starting Sift backend — chroma_dir=%s, llm=%s, sources=%s",
        settings.chroma_persist_dir,
        settings.llm_model,
        [s.name for s in source_registry.get_available()],
    )
    yield
    try:
        await db_engine.dispose()
    except Exception:
        logger.exception("Failed to dispose DB engine")
    logger.info("Shutting down Sift backend")


def create_app() -> FastAPI:
    setup_logging()

    app = FastAPI(
        title="Sift Research Engine",
        description="AI-powered multi-source research engine",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health_router)
    app.include_router(research_router)
    app.include_router(sessions_router)

    return app


app = create_app()
