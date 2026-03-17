import logging
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.dependencies import get_paper_service, get_session
from src.papers.schemas import (
    ApiResponse,
    PaginationMeta,
    PaperCompactResponse,
    PaperCreate,
    PaperResponse,
    PaperSearchParams,
    PaperUpdate,
    TagRequest,
)
from src.papers.service import PaperService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/papers", tags=["papers"])


def _paper_to_response(paper, compact: bool = False):
    if compact:
        return PaperCompactResponse.model_validate(paper)
    return PaperResponse.model_validate(paper)


@router.post("", status_code=201)
async def create_paper(
    data: PaperCreate,
    session: AsyncSession = Depends(get_session),
    service: PaperService = Depends(get_paper_service),
):
    paper = await service.create_paper(session, data)
    await session.commit()
    return ApiResponse(success=True, data=_paper_to_response(paper))


@router.post("/fetch/{pmid}", status_code=201)
async def fetch_from_pubmed(
    pmid: str,
    session: AsyncSession = Depends(get_session),
    service: PaperService = Depends(get_paper_service),
):
    paper = await service.fetch_and_save(session, pmid)
    await session.commit()
    return ApiResponse(success=True, data=_paper_to_response(paper))


@router.get("/search")
async def search_papers(
    q: str | None = None,
    author: str | None = None,
    tag: str | None = None,
    pmid: str | None = None,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    compact: bool = Query(default=False),
    session: AsyncSession = Depends(get_session),
    service: PaperService = Depends(get_paper_service),
):
    params = PaperSearchParams(q=q, author=author, tag=tag, pmid=pmid, page=page, limit=limit)
    papers, total = await service.search_papers(session, params)
    return ApiResponse(
        success=True,
        data=[_paper_to_response(p, compact=compact) for p in papers],
        meta=PaginationMeta(total=total, page=page, limit=limit),
    )


@router.get("/{paper_id}")
async def get_paper(
    paper_id: UUID,
    compact: bool = Query(default=False),
    session: AsyncSession = Depends(get_session),
    service: PaperService = Depends(get_paper_service),
):
    paper = await service.get_paper(session, paper_id)
    return ApiResponse(success=True, data=_paper_to_response(paper, compact=compact))


@router.get("")
async def list_papers(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    compact: bool = Query(default=False),
    session: AsyncSession = Depends(get_session),
    service: PaperService = Depends(get_paper_service),
):
    papers, total = await service.list_papers(session, page=page, limit=limit)
    return ApiResponse(
        success=True,
        data=[_paper_to_response(p, compact=compact) for p in papers],
        meta=PaginationMeta(total=total, page=page, limit=limit),
    )


@router.put("/{paper_id}")
async def update_paper(
    paper_id: UUID,
    data: PaperUpdate,
    session: AsyncSession = Depends(get_session),
    service: PaperService = Depends(get_paper_service),
):
    paper = await service.update_paper(session, paper_id, data)
    await session.commit()
    return ApiResponse(success=True, data=_paper_to_response(paper))


@router.delete("/{paper_id}", status_code=200)
async def delete_paper(
    paper_id: UUID,
    session: AsyncSession = Depends(get_session),
    service: PaperService = Depends(get_paper_service),
):
    await service.delete_paper(session, paper_id)
    await session.commit()
    return ApiResponse(success=True)


@router.post("/{paper_id}/tags")
async def add_tags(
    paper_id: UUID,
    data: TagRequest,
    session: AsyncSession = Depends(get_session),
    service: PaperService = Depends(get_paper_service),
):
    paper = await service.add_tags(session, paper_id, data.tags)
    await session.commit()
    return ApiResponse(success=True, data=_paper_to_response(paper))


@router.delete("/{paper_id}/tags/{tag_name}")
async def remove_tag(
    paper_id: UUID,
    tag_name: str,
    session: AsyncSession = Depends(get_session),
    service: PaperService = Depends(get_paper_service),
):
    paper = await service.remove_tag(session, paper_id, tag_name)
    await session.commit()
    return ApiResponse(success=True, data=_paper_to_response(paper))
