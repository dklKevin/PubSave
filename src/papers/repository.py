import logging
import re
from uuid import UUID

from sqlalchemy import String, cast, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.exceptions import DuplicatePmidError, PaperNotFoundError, TagNotFoundError
from src.papers.models import Paper, Tag, paper_tags
from src.papers.schemas import PaperCreate, PaperSearchParams, PaperUpdate

logger = logging.getLogger(__name__)


def _escape_like(value: str) -> str:
    return re.sub(r"([%_\\])", r"\\\1", value)


async def _paginate(session: AsyncSession, stmt, page: int, limit: int, order_by):
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await session.execute(count_stmt)).scalar_one()

    offset = (page - 1) * limit
    stmt = stmt.order_by(order_by).offset(offset).limit(limit)
    result = await session.execute(stmt)

    return list(result.scalars().all()), total


async def _get_paper_or_raise(session: AsyncSession, paper_id: UUID) -> Paper:
    stmt = select(Paper).where(Paper.id == paper_id)
    paper = (await session.execute(stmt)).scalar_one_or_none()
    if paper is None:
        raise PaperNotFoundError(paper_id)
    return paper


_ALLOWED_UPDATE_FIELDS = frozenset(
    {"pmid", "title", "authors", "abstract", "journal", "publication_date", "doi"}
)


class PaperRepository:
    async def create(self, session: AsyncSession, data: PaperCreate) -> Paper:
        paper = Paper(
            pmid=data.pmid,
            title=data.title,
            authors=[a.model_dump() for a in data.authors],
            abstract=data.abstract,
            journal=data.journal,
            publication_date=data.publication_date,
            doi=data.doi,
        )
        session.add(paper)
        try:
            await session.flush()
        except IntegrityError as exc:
            await session.rollback()
            raise DuplicatePmidError(data.pmid) from exc

        await session.refresh(paper)
        return paper

    async def find_by_id(self, session: AsyncSession, paper_id: UUID) -> Paper | None:
        stmt = select(Paper).where(Paper.id == paper_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def find_by_pmid(self, session: AsyncSession, pmid: str) -> Paper | None:
        stmt = select(Paper).where(Paper.pmid == pmid)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def find_all(
        self, session: AsyncSession, page: int = 1, limit: int = 20,
        id_prefix: str | None = None,
    ) -> tuple[list[Paper], int]:
        stmt = select(Paper)

        if id_prefix:
            escaped = _escape_like(id_prefix)
            stmt = stmt.where(cast(Paper.id, String).ilike(f"{escaped}%"))

        return await _paginate(session, stmt, page, limit, Paper.created_at.desc())

    async def update(self, session: AsyncSession, paper_id: UUID, data: PaperUpdate) -> Paper:
        paper = await self.find_by_id(session, paper_id)
        if paper is None:
            raise PaperNotFoundError(paper_id)

        raw_data = data.model_dump(exclude_unset=True)
        update_data = {k: v for k, v in raw_data.items() if k in _ALLOWED_UPDATE_FIELDS}

        if "authors" in update_data and update_data["authors"] is not None:
            update_data["authors"] = [
                a.model_dump() if hasattr(a, "model_dump") else a
                for a in update_data["authors"]
            ]

        for key, value in update_data.items():
            setattr(paper, key, value)

        await session.flush()
        await session.refresh(paper)
        return paper

    async def delete(self, session: AsyncSession, paper_id: UUID) -> None:
        paper = await self.find_by_id(session, paper_id)
        if paper is None:
            raise PaperNotFoundError(paper_id)

        await session.delete(paper)
        await session.flush()

    async def search(
        self, session: AsyncSession, params: PaperSearchParams
    ) -> tuple[list[Paper], int]:
        stmt = select(Paper)

        if params.q:
            escaped = _escape_like(params.q)
            pattern = f"%{escaped}%"
            stmt = stmt.where(
                Paper.title.ilike(pattern) | Paper.abstract.ilike(pattern)
            )

        if params.pmid:
            stmt = stmt.where(Paper.pmid == params.pmid)

        if params.author:
            escaped = _escape_like(params.author)
            stmt = stmt.where(
                cast(Paper.authors, String).ilike(f"%{escaped}%")
            )

        if params.tag:
            stmt = stmt.join(paper_tags).join(Tag).where(Tag.name == params.tag)

        return await _paginate(
            session, stmt, params.page, params.limit, Paper.created_at.desc()
        )


class TagRepository:
    async def add_tags(
        self, session: AsyncSession, paper_id: UUID, tag_names: list[str],
    ) -> Paper:
        paper = await _get_paper_or_raise(session, paper_id)
        existing_tag_names = {t.name for t in paper.tags}

        for name in tag_names:
            if name in existing_tag_names:
                continue

            tag_stmt = select(Tag).where(Tag.name == name)
            tag = (await session.execute(tag_stmt)).scalar_one_or_none()
            if tag is None:
                tag = Tag(name=name)
                session.add(tag)
                await session.flush()

            paper.tags.append(tag)

        await session.flush()
        await session.refresh(paper)
        return paper

    async def remove_tag(
        self, session: AsyncSession, paper_id: UUID, tag_name: str,
    ) -> Paper:
        paper = await _get_paper_or_raise(session, paper_id)

        tag_stmt = select(Tag).where(Tag.name == tag_name)
        tag = (await session.execute(tag_stmt)).scalar_one_or_none()
        if tag is None:
            raise TagNotFoundError(tag_name)

        paper.tags = [t for t in paper.tags if t.name != tag_name]
        await session.flush()
        await session.refresh(paper)
        return paper

    async def find_all(
        self, session: AsyncSession, page: int = 1, limit: int = 20
    ) -> tuple[list[Tag], int]:
        return await _paginate(session, select(Tag), page, limit, Tag.name)
