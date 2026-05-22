"""FastAPI proxy server — the core of Cloq."""

from __future__ import annotations

import json
import logging
import time
from typing import Any

import httpx
from fastapi import FastAPI, Request, Response
from fastapi.responses import StreamingResponse

from cloq.config.schema import CloqConfig
from cloq.detection.network import NetworkDetector
from cloq.detection.pii import PIIDetector
from cloq.detection.pipeline import DetectionPipeline
from cloq.detection.secrets import SecretsDetector
from cloq.proxy.cache import LocalPromptCache
from cloq.proxy.providers import detect_provider
from cloq.proxy.streaming import restore_sse_stream
from cloq.sanitizer.engine import restore, sanitize_messages
from cloq.sanitizer.session_store import SessionStore

logger = logging.getLogger("cloq.proxy")


def _build_pipeline(config: CloqConfig) -> DetectionPipeline:
    """Construct the detection pipeline from configuration."""
    detectors = []

    if config.detection.secrets.enabled:
        from cloq.detection.secrets import SecretPattern

        custom_patterns = [
            SecretPattern(
                name=p.name,
                entity_type=p.entity_type,
                pattern=__import__("re").compile(p.regex),
                confidence=p.confidence,
            )
            for p in config.detection.secrets.custom_patterns
        ]
        detectors.append(
            SecretsDetector(
                custom_patterns=custom_patterns or None,
                entropy_threshold=config.detection.secrets.entropy_threshold,
                min_entropy_length=config.detection.secrets.min_entropy_length,
            )
        )

    if config.detection.pii.enabled:
        detectors.append(
            PIIDetector(
                entities=config.detection.pii.entities,
                confidence_threshold=config.detection.pii.confidence_threshold,
                language=config.detection.pii.language,
            )
        )

    if config.detection.network.enabled:
        detectors.append(
            NetworkDetector(
                internal_domains=config.detection.network.internal_domains,
                detect_localhost=config.detection.network.detect_localhost,
            )
        )

    return DetectionPipeline(detectors)


def create_app(config: CloqConfig | None = None) -> FastAPI:
    """Create and configure the Cloq FastAPI proxy application.

    Args:
        config: Cloq configuration.  Uses defaults if ``None``.

    Returns:
        A configured FastAPI application ready to serve.
    """
    if config is None:
        config = CloqConfig()

    app = FastAPI(
        title="Cloq",
        description="Local-first context sanitizer for LLM API calls",
        version="0.1.1",
        docs_url=None,  # Disable Swagger UI in production
        redoc_url=None,
    )

    # ── Shared state ─────────────────────────────────────────────────
    pipeline = _build_pipeline(config)
    session_store = SessionStore(
        default_ttl=config.sanitizer.session_ttl_seconds,
        tag_format=config.sanitizer.tag_format,
    )
    prompt_cache = LocalPromptCache()

    # Stats tracking
    stats: dict[str, Any] = {
        "requests_processed": 0,
        "entities_sanitized": 0,
        "entities_restored": 0,
        "cache_hits": 0,
        "cache_misses": 0,
        "start_time": time.time(),
    }

    # ── Health & admin endpoints ─────────────────────────────────────
    @app.get("/health")
    async def health_check() -> dict[str, str]:
        return {"status": "healthy", "version": "0.1.1"}

    @app.get("/stats")
    async def get_stats() -> dict[str, Any]:
        uptime = time.time() - stats["start_time"]
        cache_hits = stats["cache_hits"]
        cache_misses = stats["cache_misses"]
        total_cache_queries = cache_hits + cache_misses
        hit_rate = (cache_hits / total_cache_queries * 100) if total_cache_queries > 0 else 0.0

        # High-impact dev savings estimation:
        # Assuming average query has 1500 prompt tokens + 500 response tokens = 2000 tokens ($0.03 average cost)
        tokens_saved = cache_hits * 2000
        dollars_saved = cache_hits * 0.03

        return {
            **stats,
            "uptime_seconds": round(uptime, 1),
            "active_sessions": session_store.active_count,
            "cache_hit_rate_pct": round(hit_rate, 1),
            "estimated_tokens_saved": tokens_saved,
            "estimated_dollars_saved": round(dollars_saved, 3),
        }

    # ── Catch-all proxy handler ──────────────────────────────────────
    @app.api_route(
        "/{path:path}",
        methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    )
    async def proxy_handler(request: Request, path: str) -> Response:
        """Intercept, sanitize, forward, restore, and return."""
        headers = {k.lower(): v for k, v in request.headers.items()}

        # Detect provider
        provider_result = detect_provider(f"/{path}", headers)
        if provider_result is None:
            return Response(
                content=json.dumps({"error": "Unknown provider or unsupported endpoint"}),
                status_code=400,
                media_type="application/json",
            )

        provider, match = provider_result

        # Read request body
        body_bytes = await request.body()
        try:
            body = json.loads(body_bytes) if body_bytes else {}
        except json.JSONDecodeError:
            body = {}

        is_streaming = body.get("stream", False)

        # Extract messages
        messages = provider.extract_messages(body)

        # Create sanitization session
        session = session_store.create()

        # Sanitize messages
        sanitized_messages = sanitize_messages(
            messages=messages,
            session=session,
            pipeline_run=pipeline.run,
        )

        # Update stats
        stats["requests_processed"] += 1
        stats["entities_sanitized"] += session.total_substitutions

        # Check local de-identified prompt cache (non-streaming only)
        if not is_streaming:
            cached_body = prompt_cache.get(sanitized_messages, provider.name)
            if cached_body is not None:
                logger.info("Semantic Template Cache Hit! Returning response instantly.")
                stats["cache_hits"] += 1
                # Restore response using current session variable mapping
                response_texts = provider.extract_response_text(cached_body)
                restored_texts = [restore(text, session) for text in response_texts]
                restored_body = provider.inject_response_text(cached_body, restored_texts)

                stats["entities_restored"] += session.total_substitutions
                session_store.remove(session.session_id)

                return Response(
                    content=json.dumps(restored_body),
                    status_code=200,
                    media_type="application/json",
                )
            else:
                stats["cache_misses"] += 1
        else:
            stats["cache_misses"] += 1

        # Rebuild request body with sanitized messages
        sanitized_body = provider.inject_messages(body, sanitized_messages)

        # Forward to upstream
        forward_headers = dict(request.headers)
        # Remove hop-by-hop headers
        for h in ["host", "content-length", "transfer-encoding"]:
            forward_headers.pop(h, None)

        logger.info(
            "Proxying to %s | sanitized %d entities",
            match.upstream_url,
            session.total_substitutions,
        )

        async with httpx.AsyncClient(timeout=120.0) as client:
            upstream_response = await client.request(
                method=request.method,
                url=match.upstream_url,
                headers=forward_headers,
                content=json.dumps(sanitized_body).encode(),
                follow_redirects=True,
            )

            if is_streaming:
                # Handle SSE streaming response
                return StreamingResponse(
                    restore_sse_stream(
                        upstream_response.aiter_bytes(),
                        session,
                        provider.name,
                    ),
                    status_code=upstream_response.status_code,
                    headers=dict(upstream_response.headers),
                    media_type="text/event-stream",
                )
            else:
                # Handle regular JSON response
                try:
                    response_body = upstream_response.json()
                except json.JSONDecodeError:
                    return Response(
                        content=upstream_response.content,
                        status_code=upstream_response.status_code,
                        headers=dict(upstream_response.headers),
                    )

                # Store in local de-identified cache (only if successful response)
                if upstream_response.status_code == 200:
                    prompt_cache.set(sanitized_messages, provider.name, response_body)

                # Restore tags in response
                response_texts = provider.extract_response_text(response_body)
                restored_texts = [restore(text, session) for text in response_texts]
                restored_body = provider.inject_response_text(response_body, restored_texts)

                stats["entities_restored"] += session.total_substitutions

                # Clean up session
                session_store.remove(session.session_id)

                return Response(
                    content=json.dumps(restored_body),
                    status_code=upstream_response.status_code,
                    media_type="application/json",
                )

    return app
