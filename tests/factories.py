import uuid


def make_paper_data(
    *,
    pmid: str = "12345678",
    title: str = "A Test Paper",
    authors: list | None = None,
    abstract: str = "Test abstract content.",
    journal: str = "Test Journal",
    publication_date: str = "2025-01-15",
    doi: str = "10.1000/test.123",
) -> dict:
    return {
        "pmid": pmid,
        "title": title,
        "authors": authors or [{"last_name": "Smith", "first_name": "John"}],
        "abstract": abstract,
        "journal": journal,
        "publication_date": publication_date,
        "doi": doi,
    }


def make_paper_data_unique(**overrides) -> dict:
    defaults = make_paper_data(pmid=str(uuid.uuid4().int)[:8])
    return {**defaults, **overrides}
