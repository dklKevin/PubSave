from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.dependencies import get_paper_service, get_session
from src.papers.formatters import paper_to_response
from src.papers.schemas import ApiResponse, PaginationMeta, TagRequest, TagResponse
from src.papers.service import PaperService

router = APIRouter(prefix="/api/v1/tags", tags=["tags"])
paper_tags_router = APIRouter(prefix="/api/v1/papers", tags=["paper-tags"])


@router.get("")
async def list_tags(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
    service: PaperService = Depends(get_paper_service),
):
    tags, total = await service.list_tags(session, page=page, limit=limit)
    return ApiResponse(
        success=True,
        data=[TagResponse.model_validate(t) for t in tags],
        meta=PaginationMeta(total=total, page=page, limit=limit),
    )


@paper_tags_router.post("/{paper_id}/tags")
async def add_tags(
    paper_id: UUID,
    data: TagRequest,
    session: AsyncSession = Depends(get_session),
    service: PaperService = Depends(get_paper_service),
):
    paper = await service.add_tags(session, paper_id, data.tags)
    await session.commit()
    return ApiResponse(success=True, data=paper_to_response(paper))


@paper_tags_router.delete("/{paper_id}/tags/{tag_name}")
async def remove_tag(
    paper_id: UUID,
    tag_name: str = Path(max_length=100),
    session: AsyncSession = Depends(get_session),
    service: PaperService = Depends(get_paper_service),
):
    paper = await service.remove_tag(session, paper_id, tag_name)
    await session.commit()
    return ApiResponse(success=True, data=paper_to_response(paper))
