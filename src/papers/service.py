import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.exceptions import DuplicatePmidError, PaperNotFoundError
from src.llm.embedder import Embedder
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
        embedder: Embedder | None = None,
    ) -> None:
        self._paper_repo = paper_repo
        self._tag_repo = tag_repo
        self._pubmed_client = pubmed_client
        self._embedder = embedder

    async def _embed_paper(self, session: AsyncSession, paper: Paper) -> None:
        """Embed a paper's abstract and store the vector.

        Design choice: simple `if self._embedder is None` guard here rather than
        a NoOpEmbedder pattern. All embedding paths funnel through this single
        private method, so there's no logic duplication. Save the NoOp pattern
        for Oros where more providers and call sites justify the abstraction.

        Log levels:
          - DEBUG: embedder not configured (expected behavior, not a problem)
          - WARNING: embedder exists but call failed (something went wrong)
        """
        if self._embedder is None:
            logger.debug("Skipping embedding for paper %s, no embedder configured", paper.pmid)
            return

        if paper.abstract is None:
            logger.debug("Skipping embedding for paper %s, no abstract", paper.pmid)
            return

        try:
            embedding = await self._embedder.embed(paper.abstract)
            paper.embedding = embedding
            await session.flush()
        except Exception:
            logger.warning("Failed to embed paper %s", paper.pmid, exc_info=True)

    async def create_paper(self, session: AsyncSession, data: PaperCreate) -> Paper:
        paper = await self._paper_repo.create(session, data)
        await self._embed_paper(session, paper)
        return paper

    async def fetch_and_save(self, session: AsyncSession, pmid: str) -> Paper:
        paper_data = await self._pubmed_client.fetch_paper(pmid)

        existing = await self._paper_repo.find_by_pmid(session, pmid)
        if existing is not None:
            raise DuplicatePmidError(pmid)

        paper = await self._paper_repo.create(session, paper_data)
        await self._embed_paper(session, paper)
        return paper

    async def embed_all(self, session: AsyncSession, batch_size: int = 50) -> int:
        """Backfill embeddings for papers that have abstracts but no embedding.

        Processes in batches to stay within OpenAI's per-request token limits.
        Returns the total number of papers embedded.
        """
        if self._embedder is None:
            logger.info("Skipping embed-all, no embedder configured")
            return 0

        total = 0
        while True:
            papers = await self._paper_repo.find_unembedded(session, limit=batch_size)
            if not papers:
                break

            abstracts = [p.abstract for p in papers]
            embeddings = await self._embedder.embed_batch(abstracts)

            for paper, embedding in zip(papers, embeddings, strict=True):
                paper.embedding = embedding

            await session.flush()
            total += len(papers)

        return total

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
