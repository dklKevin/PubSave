import pytest

from src.papers.repository import PaperRepository, TagRepository
from src.papers.schemas import PaperCreate
from tests.factories import make_paper_data_unique


@pytest.fixture
def paper_repo():
    return PaperRepository()


@pytest.fixture
def tag_repo():
    return TagRepository()


class TestTagOperations:
    async def test_add_tags_to_paper(self, paper_repo, tag_repo, session):
        paper = await paper_repo.create(session, PaperCreate(**make_paper_data_unique()))
        updated = await tag_repo.add_tags(session, paper.id, ["ml", "genomics"])

        tag_names = [t.name for t in updated.tags]
        assert "ml" in tag_names
        assert "genomics" in tag_names

    async def test_add_duplicate_tag_is_idempotent(self, paper_repo, tag_repo, session):
        paper = await paper_repo.create(session, PaperCreate(**make_paper_data_unique()))
        await tag_repo.add_tags(session, paper.id, ["ml"])
        updated = await tag_repo.add_tags(session, paper.id, ["ml"])

        ml_count = sum(1 for t in updated.tags if t.name == "ml")
        assert ml_count == 1

    async def test_remove_tag_from_paper(self, paper_repo, tag_repo, session):
        paper = await paper_repo.create(session, PaperCreate(**make_paper_data_unique()))
        await tag_repo.add_tags(session, paper.id, ["ml", "genomics"])

        updated = await tag_repo.remove_tag(session, paper.id, "ml")
        tag_names = [t.name for t in updated.tags]
        assert "ml" not in tag_names
        assert "genomics" in tag_names

    async def test_list_all_tags(self, paper_repo, tag_repo, session):
        paper = await paper_repo.create(session, PaperCreate(**make_paper_data_unique()))
        await tag_repo.add_tags(session, paper.id, ["unique-tag-list"])

        tags, total = await tag_repo.find_all(session)
        tag_names = [t.name for t in tags]
        assert "unique-tag-list" in tag_names
        assert total >= 1

    async def test_list_tags_pagination(self, paper_repo, tag_repo, session):
        paper = await paper_repo.create(session, PaperCreate(**make_paper_data_unique()))
        await tag_repo.add_tags(session, paper.id, ["page-a", "page-b", "page-c"])

        tags_page1, total = await tag_repo.find_all(session, page=1, limit=2)
        assert len(tags_page1) <= 2
        assert total >= 3
