from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.exceptions import DuplicatePmidError, PaperNotFoundError
from src.papers.schemas import AuthorSchema, PaperCreate, PaperSearchParams
from src.papers.service import PaperService


def _make_mock_paper(pmid="12345678", title="Test Paper"):
    paper = MagicMock()
    paper.id = uuid4()
    paper.pmid = pmid
    paper.title = title
    paper.authors = []
    paper.abstract = None
    paper.journal = None
    paper.publication_date = None
    paper.doi = None
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
def service(paper_repo, tag_repo, pubmed_client):
    return PaperService(
        paper_repo=paper_repo,
        tag_repo=tag_repo,
        pubmed_client=pubmed_client,
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
