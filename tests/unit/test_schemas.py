import pytest
from pydantic import ValidationError

from src.papers.schemas import AuthorSchema, PaperCreate, PaperSearchParams, PaperUpdate, TagRequest


class TestAuthorSchema:
    def test_valid_author(self):
        author = AuthorSchema(last_name="Smith", first_name="John")
        assert author.last_name == "Smith"
        assert author.first_name == "John"

    def test_author_with_affiliation(self):
        author = AuthorSchema(last_name="Doe", first_name="Jane", affiliation="MIT")
        assert author.affiliation == "MIT"

    def test_author_missing_last_name(self):
        with pytest.raises(ValidationError):
            AuthorSchema(first_name="John")

    def test_author_missing_first_name(self):
        with pytest.raises(ValidationError):
            AuthorSchema(last_name="Smith")

    def test_author_is_frozen(self):
        author = AuthorSchema(last_name="Smith", first_name="John")
        with pytest.raises(ValidationError):
            author.last_name = "Jones"


class TestPaperCreate:
    def test_valid_paper(self):
        paper = PaperCreate(
            pmid="12345678",
            title="A Test Paper",
            authors=[{"last_name": "Smith", "first_name": "John"}],
        )
        assert paper.pmid == "12345678"
        assert paper.title == "A Test Paper"
        assert len(paper.authors) == 1

    def test_paper_with_all_fields(self):
        paper = PaperCreate(
            pmid="99999999",
            title="Full Paper",
            authors=[{"last_name": "Doe", "first_name": "Jane"}],
            abstract="An abstract.",
            journal="Nature",
            publication_date="2025-06",
            doi="10.1000/xyz",
        )
        assert paper.journal == "Nature"
        assert paper.doi == "10.1000/xyz"

    def test_paper_missing_pmid(self):
        with pytest.raises(ValidationError):
            PaperCreate(title="No PMID", authors=[])

    def test_paper_missing_title(self):
        with pytest.raises(ValidationError):
            PaperCreate(pmid="12345678", authors=[])

    def test_paper_empty_pmid(self):
        with pytest.raises(ValidationError):
            PaperCreate(pmid="", title="Test", authors=[])

    def test_paper_pmid_too_long(self):
        with pytest.raises(ValidationError):
            PaperCreate(pmid="1" * 21, title="Test", authors=[])

    def test_paper_is_frozen(self):
        paper = PaperCreate(pmid="123", title="Test", authors=[])
        with pytest.raises(ValidationError):
            paper.title = "Modified"


class TestPaperUpdate:
    def test_update_partial(self):
        update = PaperUpdate(title="New Title")
        assert update.title == "New Title"
        assert update.pmid is None
        assert update.abstract is None

    def test_update_empty_is_valid(self):
        update = PaperUpdate()
        assert update.title is None


class TestTagRequest:
    def test_valid_tags(self):
        req = TagRequest(tags=["ml", "genomics"])
        assert req.tags == ["ml", "genomics"]

    def test_empty_tag_list(self):
        with pytest.raises(ValidationError):
            TagRequest(tags=[])

    def test_blank_tag_name(self):
        with pytest.raises(ValidationError):
            TagRequest(tags=[""])

    def test_tags_are_normalized(self):
        req = TagRequest(tags=["  ML ", "Genomics"])
        assert req.tags == ["ml", "genomics"]

    def test_tag_name_too_long(self):
        with pytest.raises(ValidationError):
            TagRequest(tags=["a" * 101])


class TestPaperSearchParams:
    def test_defaults(self):
        params = PaperSearchParams()
        assert params.page == 1
        assert params.limit == 20

    def test_custom_values(self):
        params = PaperSearchParams(q="cancer", author="Smith", tag="oncology", page=2, limit=50)
        assert params.q == "cancer"
        assert params.author == "Smith"

    def test_limit_max(self):
        with pytest.raises(ValidationError):
            PaperSearchParams(limit=101)

    def test_page_min(self):
        with pytest.raises(ValidationError):
            PaperSearchParams(page=0)
