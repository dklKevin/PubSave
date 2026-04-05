import logging
import time
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.exceptions import DuplicatePmidError, PaperNotFoundError, RagUnavailableError
from src.llm.embedder import Embedder
from src.llm.llm_client import LLMClient
from src.papers.models import Paper
from src.papers.pubmed_client import PubMedClient
from src.papers.repository import PaperRepository, TagRepository
from src.papers.schemas import AskResponse, Citation, PaperCreate, PaperSearchParams, PaperUpdate

logger = logging.getLogger(__name__)

RAG_SYSTEM_PROMPT = (
    "Answer the question using only the provided paper abstracts. "
    "Cite papers by their PMID in brackets like [PMID:12345678]. "
    "If the papers don't contain enough information to answer, say so."
)


class PaperService:
    def __init__(
        self,
        paper_repo: PaperRepository,
        tag_repo: TagRepository,
        pubmed_client: PubMedClient,
        embedder: Embedder | None = None,
        llm_client: LLMClient | None = None,
    ) -> None:
        self._paper_repo = paper_repo
        self._tag_repo = tag_repo
        self._pubmed_client = pubmed_client
        self._embedder = embedder
        self._llm_client = llm_client

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
        Returns the total number of papers successfully embedded. If a batch
        fails, the error is logged and the loop terminates — already-flushed
        batches are preserved, but remaining batches are not attempted.
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
            try:
                embeddings = await self._embedder.embed_batch(abstracts)
            except Exception:
                pmids = [p.pmid for p in papers]
                logger.warning("Failed to embed batch (PMIDs: %s), skipping", pmids, exc_info=True)
                break

            for paper, embedding in zip(papers, embeddings, strict=True):
                paper.embedding = embedding

            await session.flush()
            total += len(papers)

        return total

    async def search_semantic(
        self, session: AsyncSession, query: str, limit: int = 5
    ) -> list[tuple[Paper, float]]:
        """Embed the query and find papers by cosine similarity."""
        if self._embedder is None:
            raise RagUnavailableError()
        query_embedding = await self._embedder.embed(query)
        return await self._paper_repo.search_semantic(session, query_embedding, limit)

    async def ask(self, session: AsyncSession, question: str, top_k: int = 5) -> AskResponse:
        """Retrieve relevant papers and generate an answer using the LLM.

        The system prompt lives here (not in the LLM client) because prompt
        construction is business logic. The LLM client is pure transport.
        """
        if self._embedder is None or self._llm_client is None:
            raise RagUnavailableError()

        start = time.monotonic()

        query_embedding = await self._embedder.embed(question)
        results = await self._paper_repo.search_semantic(session, query_embedding, top_k)

        context_parts = []
        citations = []
        for paper, score in results:
            context_parts.append(f"[PMID:{paper.pmid}] {paper.title}\n{paper.abstract or ''}")
            citations.append(
                Citation(
                    paper_id=paper.id,
                    pmid=paper.pmid,
                    title=paper.title,
                    score=round(score, 4),
                )
            )

        user_message = f"Question: {question}\n\nPapers:\n" + "\n\n".join(context_parts)
        answer = await self._llm_client.generate(system=RAG_SYSTEM_PROMPT, user=user_message)

        elapsed_ms = int((time.monotonic() - start) * 1000)

        return AskResponse(
            answer=answer,
            citations=citations,
            model=self._llm_client.model,
            took_ms=elapsed_ms,
        )

    async def get_paper(self, session: AsyncSession, paper_id: UUID) -> Paper:
        paper = await self._paper_repo.find_by_id(session, paper_id)
        if paper is None:
            raise PaperNotFoundError(paper_id)
        return paper

    async def list_papers(
        self, session: AsyncSession, page: int = 1, limit: int = 20, id_prefix: str | None = None
    ) -> tuple[list[Paper], int]:
        return await self._paper_repo.find_all(session, page=page, limit=limit, id_prefix=id_prefix)

    async def update_paper(self, session: AsyncSession, paper_id: UUID, data: PaperUpdate) -> Paper:
        return await self._paper_repo.update(session, paper_id, data)

    async def delete_paper(self, session: AsyncSession, paper_id: UUID) -> None:
        await self._paper_repo.delete(session, paper_id)

    async def search_papers(
        self, session: AsyncSession, params: PaperSearchParams
    ) -> tuple[list[Paper], int]:
        return await self._paper_repo.search(session, params)

    async def add_tags(self, session: AsyncSession, paper_id: UUID, tag_names: list[str]) -> Paper:
        return await self._tag_repo.add_tags(session, paper_id, tag_names)

    async def remove_tag(self, session: AsyncSession, paper_id: UUID, tag_name: str) -> Paper:
        return await self._tag_repo.remove_tag(session, paper_id, tag_name)

    async def list_tags(
        self, session: AsyncSession, page: int = 1, limit: int = 20
    ) -> tuple[list, int]:
        return await self._tag_repo.find_all(session, page=page, limit=limit)
