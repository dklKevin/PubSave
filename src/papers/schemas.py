from datetime import datetime
from typing import Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from src.papers.formatters import extract_tag_names, format_authors_short

T = TypeVar("T")


class AuthorSchema(BaseModel):
    model_config = ConfigDict(frozen=True)

    last_name: str
    first_name: str
    affiliation: str | None = None


class PaperCreate(BaseModel):
    model_config = ConfigDict(frozen=True)

    pmid: str = Field(min_length=1, max_length=20)
    title: str = Field(min_length=1)
    authors: list[AuthorSchema] = Field(default_factory=list)
    abstract: str | None = None
    journal: str | None = None
    publication_date: str | None = None
    doi: str | None = None


class PaperUpdate(BaseModel):
    model_config = ConfigDict(frozen=True)

    pmid: str | None = Field(default=None, min_length=1, max_length=20)
    title: str | None = Field(default=None, min_length=1)
    authors: list[AuthorSchema] | None = None
    abstract: str | None = None
    journal: str | None = None
    publication_date: str | None = None
    doi: str | None = None


class _TimestampMixin(BaseModel):
    @field_validator("created_at", "updated_at", mode="before", check_fields=False)
    @classmethod
    def datetime_to_str(cls, v: datetime | str) -> str:
        if isinstance(v, datetime):
            return v.isoformat()
        return str(v)


class _TagMixin(BaseModel):
    @field_validator("tags", mode="before", check_fields=False)
    @classmethod
    def extract_tag_names(cls, v: list) -> list[str]:
        return extract_tag_names(v)


class PaperResponse(_TimestampMixin, _TagMixin):
    model_config = ConfigDict(frozen=True, from_attributes=True)

    id: UUID
    pmid: str
    title: str
    authors: list[AuthorSchema]
    abstract: str | None = None
    journal: str | None = None
    publication_date: str | None = None
    doi: str | None = None
    tags: list[str] = Field(default_factory=list)
    created_at: str
    updated_at: str


class PaperCompactResponse(_TagMixin):
    model_config = ConfigDict(frozen=True, from_attributes=True)

    id: UUID
    pmid: str
    title: str
    authors_short: str = ""
    journal: str | None = None
    tags: list[str] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def compute_authors_short(cls, data):
        if hasattr(data, "__dict__"):
            authors = getattr(data, "authors", []) or []
            obj = {
                "id": data.id,
                "pmid": data.pmid,
                "title": data.title,
                "authors_short": format_authors_short(authors),
                "journal": data.journal,
                "tags": data.tags,
            }
            return obj
        if isinstance(data, dict) and "authors_short" not in data:
            authors = data.get("authors", []) or []
            return {**data, "authors_short": format_authors_short(authors)}
        return data

    @field_validator("title", mode="before")
    @classmethod
    def truncate_title(cls, v: str) -> str:
        if len(v) > 120:
            return v[:117] + "..."
        return v


class TagResponse(_TimestampMixin):
    model_config = ConfigDict(frozen=True, from_attributes=True)

    id: UUID
    name: str
    created_at: str


class TagRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    tags: list[str] = Field(min_length=1, max_length=50)

    @field_validator("tags", mode="before")
    @classmethod
    def normalize_tags(cls, v: list[str]) -> list[str]:
        normalized = [t.strip().lower() for t in v]
        for tag in normalized:
            if not tag:
                raise ValueError("Tag name cannot be blank")
            if len(tag) > 100:
                raise ValueError("Tag name must be 100 characters or fewer")
        return list(dict.fromkeys(normalized))


class PaperSearchParams(BaseModel):
    model_config = ConfigDict(frozen=True)

    q: str | None = Field(default=None, max_length=500)
    author: str | None = Field(default=None, max_length=200)
    tag: str | None = Field(default=None, max_length=100)
    pmid: str | None = None
    page: int = Field(default=1, ge=1)
    limit: int = Field(default=20, ge=1, le=100)


class PaginationMeta(BaseModel):
    model_config = ConfigDict(frozen=True)

    total: int
    page: int
    limit: int


class SemanticSearchResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    paper: PaperCompactResponse
    score: float


class AskRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    question: str = Field(min_length=1, max_length=1000)
    top_k: int = Field(default=5, ge=1, le=20)


class Citation(BaseModel):
    model_config = ConfigDict(frozen=True)

    paper_id: UUID
    pmid: str
    title: str
    score: float


class AskResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    answer: str
    citations: list[Citation]
    model: str
    took_ms: int


class ApiResponse(BaseModel, Generic[T]):  # noqa: UP046 - Pydantic requires Generic[T]
    model_config = ConfigDict(frozen=True)

    success: bool
    data: T | None = None
    error: str | None = None
    meta: PaginationMeta | None = None
