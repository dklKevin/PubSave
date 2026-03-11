import pytest

from src.exceptions import DuplicatePmidError, PaperNotFoundError
from src.papers.repository import PaperRepository
from src.papers.schemas import PaperCreate, PaperSearchParams, PaperUpdate
from tests.factories import make_paper_data, make_paper_data_unique


@pytest.fixture
def repo():
    return PaperRepository()


class TestPaperCreate:
    async def test_create_paper(self, repo, session):
        data = PaperCreate(**make_paper_data())
        paper = await repo.create(session, data)

        assert paper.pmid == "12345678"
        assert paper.title == "A Test Paper"
        assert paper.id is not None

    async def test_create_duplicate_pmid_raises(self, repo, session):
        data = PaperCreate(**make_paper_data(pmid="99999999"))
        await repo.create(session, data)

        with pytest.raises(DuplicatePmidError):
            await repo.create(session, PaperCreate(**make_paper_data(pmid="99999999")))


class TestPaperFind:
    async def test_find_by_id(self, repo, session):
        data = PaperCreate(**make_paper_data_unique())
        created = await repo.create(session, data)

        found = await repo.find_by_id(session, created.id)
        assert found is not None
        assert found.pmid == created.pmid

    async def test_find_by_id_not_found(self, repo, session):
        import uuid

        result = await repo.find_by_id(session, uuid.uuid4())
        assert result is None

    async def test_find_by_pmid(self, repo, session):
        data = PaperCreate(**make_paper_data_unique(pmid="55555555"))
        await repo.create(session, data)

        found = await repo.find_by_pmid(session, "55555555")
        assert found is not None
        assert found.pmid == "55555555"

    async def test_find_all(self, repo, session):
        await repo.create(session, PaperCreate(**make_paper_data_unique()))
        await repo.create(session, PaperCreate(**make_paper_data_unique()))

        papers, total = await repo.find_all(session, page=1, limit=10)
        assert total >= 2
        assert len(papers) >= 2


class TestPaperUpdate:
    async def test_update_paper(self, repo, session):
        data = PaperCreate(**make_paper_data_unique())
        created = await repo.create(session, data)

        update = PaperUpdate(title="Updated Title")
        updated = await repo.update(session, created.id, update)

        assert updated.title == "Updated Title"
        assert updated.pmid == created.pmid

    async def test_update_not_found_raises(self, repo, session):
        import uuid

        with pytest.raises(PaperNotFoundError):
            await repo.update(session, uuid.uuid4(), PaperUpdate(title="X"))


class TestPaperDelete:
    async def test_delete_paper(self, repo, session):
        data = PaperCreate(**make_paper_data_unique())
        created = await repo.create(session, data)

        await repo.delete(session, created.id)
        found = await repo.find_by_id(session, created.id)
        assert found is None

    async def test_delete_not_found_raises(self, repo, session):
        import uuid

        with pytest.raises(PaperNotFoundError):
            await repo.delete(session, uuid.uuid4())


class TestPaperSearch:
    async def test_search_by_title(self, repo, session):
        await repo.create(session, PaperCreate(**make_paper_data_unique(title="Genomics Study Alpha")))

        params = PaperSearchParams(q="Genomics")
        papers, total = await repo.search(session, params)
        assert total >= 1
        assert any("Genomics" in p.title for p in papers)

    async def test_search_by_pmid(self, repo, session):
        await repo.create(session, PaperCreate(**make_paper_data_unique(pmid="77777777")))

        params = PaperSearchParams(pmid="77777777")
        papers, total = await repo.search(session, params)
        assert total >= 1
        assert papers[0].pmid == "77777777"
