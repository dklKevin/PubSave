from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.exceptions import DuplicatePmidError, PaperNotFoundError
from src.papers.schemas import AuthorSchema, PaperCreate, PaperSearchParams
from src.papers.service import PaperService

EMBEDDING_DIM = 1536


def _make_mock_paper(pmid="12345678", title="Test Paper", abstract=None):
    paper = MagicMock()
    paper.id = uuid4()
    paper.pmid = pmid
    paper.title = title
    paper.authors = []
    paper.abstract = abstract
    paper.journal = None
    paper.publication_date = None
    paper.doi = None
    paper.embedding = None
    paper.tags = []
    paper.created_at = "2025-01-01T00:00:00Z"
    paper.updated_at = "2025-01-01T00:00:00Z"
    return paper


@pytest.fixture
def paper_repo():
    return AsyncMock()


@pytest.fixture
def tag_repo():
    return AsyncMock()


@pytest.fixture
def pubmed_client():
    return AsyncMock()


@pytest.fixture
def embedder():
    mock = AsyncMock()
    mock.embed.return_value = [0.1] * EMBEDDING_DIM
    mock.embed_batch.return_value = [[0.1] * EMBEDDING_DIM]
    return mock


@pytest.fixture
def service(paper_repo, tag_repo, pubmed_client):
    return PaperService(
        paper_repo=paper_repo,
        tag_repo=tag_repo,
        pubmed_client=pubmed_client,
    )


@pytest.fixture
def service_with_embedder(paper_repo, tag_repo, pubmed_client, embedder):
    return PaperService(
        paper_repo=paper_repo,
        tag_repo=tag_repo,
        pubmed_client=pubmed_client,
        embedder=embedder,
    )


class TestCreatePaper:
    async def test_create_paper(self, service, paper_repo):
        expected = _make_mock_paper()
        paper_repo.create.return_value = expected

        data = PaperCreate(pmid="12345678", title="Test Paper", authors=[])
        result = await service.create_paper(None, data)

        assert result.pmid == "12345678"
        paper_repo.create.assert_called_once()

    async def test_create_duplicate_raises(self, service, paper_repo):
        paper_repo.create.side_effect = DuplicatePmidError("12345678")

        data = PaperCreate(pmid="12345678", title="Test Paper", authors=[])
        with pytest.raises(DuplicatePmidError):
            await service.create_paper(None, data)


class TestFetchFromPubMed:
    async def test_fetch_and_save(self, service, paper_repo, pubmed_client):
        fetch_data = PaperCreate(
            pmid="12345678",
            title="Fetched Paper",
            authors=[AuthorSchema(last_name="Smith", first_name="John")],
        )
        pubmed_client.fetch_paper.return_value = fetch_data

        expected = _make_mock_paper(pmid="12345678", title="Fetched Paper")
        paper_repo.find_by_pmid.return_value = None
        paper_repo.create.return_value = expected

        result = await service.fetch_and_save(None, "12345678")

        assert result.pmid == "12345678"
        pubmed_client.fetch_paper.assert_called_once_with("12345678")
        paper_repo.create.assert_called_once()

    async def test_fetch_duplicate_raises(self, service, paper_repo, pubmed_client):
        fetch_data = PaperCreate(pmid="12345678", title="Fetched", authors=[])
        pubmed_client.fetch_paper.return_value = fetch_data

        paper_repo.find_by_pmid.return_value = _make_mock_paper()

        with pytest.raises(DuplicatePmidError):
            await service.fetch_and_save(None, "12345678")


class TestGetPaper:
    async def test_get_existing(self, service, paper_repo):
        expected = _make_mock_paper()
        paper_repo.find_by_id.return_value = expected

        result = await service.get_paper(None, expected.id)
        assert result.pmid == "12345678"

    async def test_get_not_found(self, service, paper_repo):
        paper_id = uuid4()
        paper_repo.find_by_id.return_value = None

        with pytest.raises(PaperNotFoundError):
            await service.get_paper(None, paper_id)


class TestSearchPapers:
    async def test_search_returns_results(self, service, paper_repo):
        papers = [_make_mock_paper(), _make_mock_paper(pmid="99999999")]
        paper_repo.search.return_value = (papers, 2)

        params = PaperSearchParams(q="test")
        results, total = await service.search_papers(None, params)

        assert total == 2
        assert len(results) == 2


class TestEmbedPaper:
    async def test_create_embeds_paper_with_abstract(
        self, service_with_embedder, paper_repo, embedder
    ):
        paper = _make_mock_paper(abstract="Gene therapy uses viral vectors.")
        paper_repo.create.return_value = paper

        data = PaperCreate(
            pmid="12345678", title="Test", authors=[], abstract="Gene therapy uses viral vectors."
        )
        session = AsyncMock()
        await service_with_embedder.create_paper(session, data)

        embedder.embed.assert_called_once_with("Gene therapy uses viral vectors.")

    async def test_create_skips_embed_without_abstract(
        self, service_with_embedder, paper_repo, embedder
    ):
        paper = _make_mock_paper(abstract=None)
        paper_repo.create.return_value = paper

        data = PaperCreate(pmid="12345678", title="Test", authors=[])
        session = AsyncMock()
        await service_with_embedder.create_paper(session, data)

        embedder.embed.assert_not_called()

    async def test_create_skips_embed_without_embedder(self, service, paper_repo):
        paper = _make_mock_paper(abstract="Some abstract text")
        paper_repo.create.return_value = paper

        data = PaperCreate(
            pmid="12345678", title="Test", authors=[], abstract="Some abstract text"
        )
        result = await service.create_paper(None, data)

        assert result.pmid == "12345678"

    async def test_fetch_embeds_paper_with_abstract(
        self, service_with_embedder, paper_repo, pubmed_client, embedder
    ):
        fetch_data = PaperCreate(
            pmid="12345678", title="Fetched", authors=[], abstract="CRISPR delivery."
        )
        pubmed_client.fetch_paper.return_value = fetch_data

        paper = _make_mock_paper(abstract="CRISPR delivery.")
        paper_repo.find_by_pmid.return_value = None
        paper_repo.create.return_value = paper

        session = AsyncMock()
        await service_with_embedder.fetch_and_save(session, "12345678")

        embedder.embed.assert_called_once_with("CRISPR delivery.")

    async def test_embed_failure_does_not_crash_save(
        self, service_with_embedder, paper_repo, embedder
    ):
        embedder.embed.side_effect = Exception("API timeout")
        paper = _make_mock_paper(abstract="Some abstract")
        paper_repo.create.return_value = paper

        data = PaperCreate(
            pmid="12345678", title="Test", authors=[], abstract="Some abstract"
        )
        session = AsyncMock()
        result = await service_with_embedder.create_paper(session, data)

        assert result.pmid == "12345678"


class TestEmbedAll:
    async def test_embed_all_with_papers(
        self, service_with_embedder, paper_repo, embedder
    ):
        papers = [
            _make_mock_paper(pmid="111", abstract="Abstract one"),
            _make_mock_paper(pmid="222", abstract="Abstract two"),
        ]
        paper_repo.find_unembedded.side_effect = [papers, []]
        embedder.embed_batch.return_value = [
            [0.1] * EMBEDDING_DIM,
            [0.2] * EMBEDDING_DIM,
        ]

        session = AsyncMock()
        count = await service_with_embedder.embed_all(session)

        assert count == 2
        embedder.embed_batch.assert_called_once_with(
            ["Abstract one", "Abstract two"]
        )

    async def test_embed_all_processes_in_batches(
        self, service_with_embedder, paper_repo, embedder
    ):
        batch1 = [_make_mock_paper(pmid="111", abstract="First")]
        batch2 = [_make_mock_paper(pmid="222", abstract="Second")]
        paper_repo.find_unembedded.side_effect = [batch1, batch2, []]
        embedder.embed_batch.side_effect = [
            [[0.1] * EMBEDDING_DIM],
            [[0.2] * EMBEDDING_DIM],
        ]

        session = AsyncMock()
        count = await service_with_embedder.embed_all(session, batch_size=1)

        assert count == 2
        assert embedder.embed_batch.call_count == 2

    async def test_embed_all_no_papers(
        self, service_with_embedder, paper_repo, embedder
    ):
        paper_repo.find_unembedded.return_value = []

        session = AsyncMock()
        count = await service_with_embedder.embed_all(session)

        assert count == 0
        embedder.embed_batch.assert_not_called()

    async def test_embed_all_without_embedder(self, service, paper_repo):
        session = AsyncMock()
        count = await service.embed_all(session)

        assert count == 0
        paper_repo.find_unembedded.assert_not_called()


class TestSemanticSearch:
    async def test_search_semantic_embeds_query_and_returns_results(
        self, service_with_embedder, paper_repo, embedder
    ):
        paper = _make_mock_paper(pmid="111", abstract="Gene therapy")
        paper_repo.search_semantic.return_value = [(paper, 0.9234)]

        session = AsyncMock()
        results = await service_with_embedder.search_semantic(session, "gene therapy")

        embedder.embed.assert_called_once_with("gene therapy")
        paper_repo.search_semantic.assert_called_once()
        assert len(results) == 1
        assert results[0][1] == 0.9234

    async def test_search_semantic_returns_empty_when_no_matches(
        self, service_with_embedder, paper_repo, embedder
    ):
        paper_repo.search_semantic.return_value = []

        session = AsyncMock()
        results = await service_with_embedder.search_semantic(session, "obscure topic")

        assert results == []
