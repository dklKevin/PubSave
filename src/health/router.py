import logging

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.dependencies import get_session

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check(session: AsyncSession = Depends(get_session)):
    try:
        await session.execute(text("SELECT 1"))
        return {"success": True, "data": {"status": "healthy"}}
    except Exception:
        logger.exception("Health check failed")
        return JSONResponse(
            status_code=503,
            content={"success": False, "error": "Database unreachable"},
        )
