from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


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


class PaperResponse(_TimestampMixin):
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

    @field_validator("tags", mode="before")
    @classmethod
    def extract_tag_names(cls, v: list) -> list[str]:
        if not v:
            return []
        first = v[0]
        if isinstance(first, str):
            return v
        if hasattr(first, "name"):
            return [t.name for t in v]
        if isinstance(first, dict) and "name" in first:
            return [t["name"] for t in v]
        return v


class TagResponse(_TimestampMixin):
    model_config = ConfigDict(frozen=True, from_attributes=True)

    id: UUID
    name: str
    created_at: str


class TagRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    tags: list[str] = Field(min_length=1, max_length=50)

    def model_post_init(self, __context) -> None:
        normalized = [t.strip().lower() for t in self.tags]
        for tag in normalized:
            if not tag:
                raise ValueError("Tag name cannot be blank")
            if len(tag) > 100:
                raise ValueError("Tag name must be 100 characters or fewer")
        object.__setattr__(self, "tags", normalized)


class PaperSearchParams(BaseModel):
    model_config = ConfigDict(frozen=True)

    q: str | None = None
    author: str | None = None
    tag: str | None = None
    pmid: str | None = None
    page: int = Field(default=1, ge=1)
    limit: int = Field(default=20, ge=1, le=100)


class PaginationMeta(BaseModel):
    model_config = ConfigDict(frozen=True)

    total: int
    page: int
    limit: int


class ApiResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    success: bool
    data: object | None = None
    error: str | None = None
    meta: PaginationMeta | None = None
