import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from src.exceptions import (
    DuplicatePmidError,
    PaperNotFoundError,
    PubMedFetchError,
    PubSaveError,
    RagUnavailableError,
    TagNotFoundError,
)

logger = logging.getLogger(__name__)

_ERROR_STATUS_MAP = {
    PaperNotFoundError: 404,
    TagNotFoundError: 404,
    DuplicatePmidError: 409,
    PubMedFetchError: 502,
    RagUnavailableError: 503,
}


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(PubSaveError)
    async def pubsave_error_handler(request: Request, exc: PubSaveError) -> JSONResponse:
        status_code = _ERROR_STATUS_MAP.get(type(exc), 500)
        logger.warning("Application error: %s", exc)
        return JSONResponse(
            status_code=status_code,
            content={"success": False, "data": None, "error": str(exc)},
        )

    @app.exception_handler(Exception)
    async def generic_error_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled error: %s", exc)
        return JSONResponse(
            status_code=500,
            content={"success": False, "data": None, "error": "Internal server error"},
        )
