from collections.abc import AsyncGenerator

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.llm.embedder import Embedder
from src.papers.pubmed_client import PubMedClient
from src.papers.repository import PaperRepository, TagRepository
from src.papers.service import PaperService


async def get_session(request: Request) -> AsyncGenerator[AsyncSession, None]:
    session_factory = request.app.state.session_factory
    async with session_factory() as session:
        yield session


def get_paper_repo() -> PaperRepository:
    return PaperRepository()


def get_tag_repo() -> TagRepository:
    return TagRepository()


def get_pubmed_client(request: Request) -> PubMedClient:
    return request.app.state.pubmed_client


def get_embedder(request: Request) -> Embedder | None:
    return getattr(request.app.state, "embedder", None)


def get_paper_service(
    paper_repo: PaperRepository = Depends(get_paper_repo),
    tag_repo: TagRepository = Depends(get_tag_repo),
    pubmed_client: PubMedClient = Depends(get_pubmed_client),
    embedder: Embedder | None = Depends(get_embedder),
) -> PaperService:
    return PaperService(
        paper_repo=paper_repo,
        tag_repo=tag_repo,
        pubmed_client=pubmed_client,
        embedder=embedder,
    )
