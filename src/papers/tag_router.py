import logging

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.dependencies import get_paper_service, get_session
from src.papers.schemas import ApiResponse, PaginationMeta, TagResponse
from src.papers.service import PaperService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/tags", tags=["tags"])


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
