from uuid import UUID


class PubSaveError(Exception):
    pass


class PaperNotFoundError(PubSaveError):
    def __init__(self, paper_id: UUID) -> None:
        super().__init__(f"Paper not found: {paper_id}")
        self.paper_id = paper_id


class DuplicatePmidError(PubSaveError):
    def __init__(self, pmid: str) -> None:
        super().__init__(f"Paper with PMID {pmid} already exists")
        self.pmid = pmid


class TagNotFoundError(PubSaveError):
    def __init__(self, tag_name: str) -> None:
        super().__init__(f"Tag not found: {tag_name}")
        self.tag_name = tag_name


class PubMedFetchError(PubSaveError):
    def __init__(self, pmid: str, reason: str) -> None:
        super().__init__(f"Failed to fetch PMID {pmid}: {reason}")
        self.pmid = pmid
        self.reason = reason
