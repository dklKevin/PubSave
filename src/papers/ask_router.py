import logging

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.dependencies import get_embedder, get_llm_client, get_paper_service, get_session
from src.llm.embedder import Embedder
from src.llm.llm_client import LLMClient
from src.papers.schemas import ApiResponse, AskRequest, AskResponse, Citation
from src.papers.service import PaperService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["ask"])


@router.post("/ask")
async def ask(
    data: AskRequest,
    session: AsyncSession = Depends(get_session),
    service: PaperService = Depends(get_paper_service),
    embedder: Embedder | None = Depends(get_embedder),
    llm_client: LLMClient | None = Depends(get_llm_client),
):
    if embedder is None or llm_client is None:
        return JSONResponse(
            status_code=503,
            content={
                "success": False,
                "error": "RAG features unavailable, OPENAI_API_KEY not configured",
            },
        )

    result = await service.ask(session, data.question, data.top_k)
    return ApiResponse(
        success=True,
        data=AskResponse(
            answer=result["answer"],
            citations=[Citation(**c) for c in result["citations"]],
            model=result["model"],
            took_ms=result["took_ms"],
        ),
    )
