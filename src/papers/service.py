import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.exceptions import DuplicatePmidError, PaperNotFoundError
from src.papers.models import Paper
from src.papers.pubmed_client import PubMedClient
from src.papers.repository import PaperRepository, TagRepository
from src.papers.schemas import PaperCreate, PaperSearchParams, PaperUpdate

logger = logging.getLogger(__name__)


class PaperService:
    def __init__(
        self,
        paper_repo: PaperRepository,
        tag_repo: TagRepository,
        pubmed_client: PubMedClient,
    ) -> None:
        self._paper_repo = paper_repo
        self._tag_repo = tag_repo
        self._pubmed_client = pubmed_client

    async def create_paper(self, session: AsyncSession, data: PaperCreate) -> Paper:
        return await self._paper_repo.create(session, data)

    async def fetch_and_save(self, session: AsyncSession, pmid: str) -> Paper:
        paper_data = await self._pubmed_client.fetch_paper(pmid)

        existing = await self._paper_repo.find_by_pmid(session, pmid)
        if existing is not None:
            raise DuplicatePmidError(pmid)

        return await self._paper_repo.create(session, paper_data)

    async def get_paper(self, session: AsyncSession, paper_id: UUID) -> Paper:
        paper = await self._paper_repo.find_by_id(session, paper_id)
        if paper is None:
            raise PaperNotFoundError(paper_id)
        return paper

    async def list_papers(
        self, session: AsyncSession, page: int = 1, limit: int = 20, id_prefix: str | None = None
    ) -> tuple[list[Paper], int]:
        return await self._paper_repo.find_all(session, page=page, limit=limit, id_prefix=id_prefix)

    async def update_paper(
        self, session: AsyncSession, paper_id: UUID, data: PaperUpdate
    ) -> Paper:
        return await self._paper_repo.update(session, paper_id, data)

    async def delete_paper(self, session: AsyncSession, paper_id: UUID) -> None:
        await self._paper_repo.delete(session, paper_id)

    async def search_papers(
        self, session: AsyncSession, params: PaperSearchParams
    ) -> tuple[list[Paper], int]:
        return await self._paper_repo.search(session, params)

    async def add_tags(
        self, session: AsyncSession, paper_id: UUID, tag_names: list[str]
    ) -> Paper:
        return await self._tag_repo.add_tags(session, paper_id, tag_names)

    async def remove_tag(
        self, session: AsyncSession, paper_id: UUID, tag_name: str
    ) -> Paper:
        return await self._tag_repo.remove_tag(session, paper_id, tag_name)

    async def list_tags(
        self, session: AsyncSession, page: int = 1, limit: int = 20
    ) -> tuple[list, int]:
        return await self._tag_repo.find_all(session, page=page, limit=limit)
