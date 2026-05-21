"""Middleware for request logging, CORS, and admin endpoints."""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware

if TYPE_CHECKING:
    from fastapi import FastAPI, Request, Response

logger = logging.getLogger("cloq.middleware")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log each request with timing and status information."""

    async def dispatch(self, request: Request, call_next) -> Response:  # type: ignore[override]
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000

        logger.info(
            "%s %s → %d (%.1fms)",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
        )
        response.headers["X-Cloq-Duration-Ms"] = f"{duration_ms:.1f}"
        return response


def add_middleware(app: FastAPI) -> None:
    """Add all middleware to the FastAPI application.

    Args:
        app: The FastAPI application instance.
    """
    # CORS — allow browser-based tools
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Request logging
    app.add_middleware(RequestLoggingMiddleware)
