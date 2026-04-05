import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.papers.repository import PaperRepository


def _make_embedding(seed: float) -> list[float]:
    """Create a 1536-dim unit-ish vector biased by seed for cosine distance variation."""
    return [seed] + [0.0] * 1535


class TestSearchSemantic:
    async def test_returns_closest_match(self, session: AsyncSession):
        repo = PaperRepository()
        ids = []
        for i, (pmid_suffix, embed_seed) in enumerate([("A", 1.0), ("B", 0.5), ("C", 0.1)]):
            paper_id = uuid.uuid4()
            ids.append(paper_id)
            await session.execute(
                text(
                    "INSERT INTO papers (id, pmid, title, authors, abstract, embedding) "
                    "VALUES (:id, :pmid, :title, :authors, :abstract, :embedding)"
                ),
                {
                    "id": str(paper_id),
                    "pmid": f"SEM{i}{pmid_suffix}",
                    "title": f"Semantic Paper {embed_seed}",
                    "authors": "[]",
                    "abstract": "Test abstract",
                    "embedding": str(_make_embedding(embed_seed)),
                },
            )
        await session.flush()

        query_embedding = _make_embedding(1.0)
        results = await repo.search_semantic(session, query_embedding, limit=3)

        assert len(results) >= 3
        papers = [r[0] for r in results]
        scores = [r[1] for r in results]
        assert papers[0].pmid == "SEM0A"
        assert scores[0] >= scores[1] >= scores[2]


class TestFindUnembedded:
    async def test_returns_papers_without_embedding(self, session: AsyncSession):
        repo = PaperRepository()

        embedded_id = uuid.uuid4()
        unembedded_id = uuid.uuid4()

        await session.execute(
            text(
                "INSERT INTO papers (id, pmid, title, authors, abstract, embedding) "
                "VALUES (:id, :pmid, :title, :authors, :abstract, :embedding)"
            ),
            {
                "id": str(embedded_id),
                "pmid": f"EMB{uuid.uuid4().hex[:6]}",
                "title": "Embedded Paper",
                "authors": "[]",
                "abstract": "Has embedding",
                "embedding": str(_make_embedding(0.5)),
            },
        )

        await session.execute(
            text(
                "INSERT INTO papers (id, pmid, title, authors, abstract) "
                "VALUES (:id, :pmid, :title, :authors, :abstract)"
            ),
            {
                "id": str(unembedded_id),
                "pmid": f"UNEMB{uuid.uuid4().hex[:6]}",
                "title": "Unembedded Paper",
                "authors": "[]",
                "abstract": "No embedding",
            },
        )
        await session.flush()

        papers = await repo.find_unembedded(session, limit=100)

        unembedded_ids = {p.id for p in papers}
        assert unembedded_id in unembedded_ids
        assert embedded_id not in unembedded_ids
