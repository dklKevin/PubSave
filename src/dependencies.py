from collections.abc import AsyncGenerator

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import Settings, get_settings
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


def get_pubmed_client(settings: Settings = Depends(get_settings)) -> PubMedClient:
    return PubMedClient(base_url=settings.pubmed_base_url)


def get_paper_service(
    paper_repo: PaperRepository = Depends(get_paper_repo),
    tag_repo: TagRepository = Depends(get_tag_repo),
    pubmed_client: PubMedClient = Depends(get_pubmed_client),
) -> PaperService:
    return PaperService(
        paper_repo=paper_repo,
        tag_repo=tag_repo,
        pubmed_client=pubmed_client,
    )
