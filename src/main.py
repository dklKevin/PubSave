import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.config import get_settings
from src.database import create_engine, create_session_factory
from src.health.router import router as health_router
from src.llm.openai_embedder import OpenAIEmbedder
from src.llm.openai_llm import OpenAILLM
from src.logging_config import setup_logging
from src.middleware.error_handler import register_error_handlers
from src.papers.ask_router import router as ask_router
from src.papers.pubmed_client import PubMedClient
from src.papers.router import router as papers_router
from src.papers.tag_router import router as tags_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    setup_logging(settings.log_level)

    engine = create_engine(settings.database_url)
    app.state.session_factory = create_session_factory(engine)
    app.state.pubmed_client = PubMedClient(base_url=settings.pubmed_base_url)

    if settings.openai_api_key:
        app.state.embedder = OpenAIEmbedder(api_key=settings.openai_api_key)
        app.state.llm_client = OpenAILLM(api_key=settings.openai_api_key)
        logger.info("RAG features enabled")
    else:
        app.state.embedder = None
        app.state.llm_client = None
        logger.info("RAG features disabled, no OPENAI_API_KEY configured")

    logger.info("PubSave API started")
    yield

    await app.state.pubmed_client.close()
    await engine.dispose()
    logger.info("PubSave API shutdown")


def create_app() -> FastAPI:
    app = FastAPI(title="PubSave", version="0.1.0", lifespan=lifespan)

    register_error_handlers(app)
    app.include_router(health_router)
    app.include_router(papers_router)
    app.include_router(tags_router)
    app.include_router(ask_router)

    return app
