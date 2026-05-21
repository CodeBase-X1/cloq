"""SSE streaming handler — buffers chunks and restores tags across boundaries."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from cloq.sanitizer.engine import SanitizationSession


class StreamingRestorer:
    """Buffers SSE streaming chunks to restore tags that may span chunk boundaries.

    LLM providers stream responses as Server-Sent Events (SSE), where a
    synthetic tag like ``[AWS_KEY_1]`` might be split across two chunks:
    ``[AWS_K`` and ``EY_1]``.  This class buffers incoming text and
    performs restoration once complete tags are detected.

    Args:
        session: The sanitization session with tag-to-original mappings.
        max_buffer_size: Maximum buffer size before forced flush.
            Defaults to ``4096``.
    """

    def __init__(
        self,
        session: SanitizationSession,
        max_buffer_size: int = 4096,
    ) -> None:
        self._session = session
        self._max_buffer_size = max_buffer_size
        self._buffer = ""
        # Pre-compute the longest tag length for buffer management
        self._max_tag_len = max(
            (len(tag) for tag in session.tag_to_original),
            default=0,
        )

    def feed(self, chunk: str) -> str:
        """Feed a text chunk and return any restorable text.

        Text is buffered until we can be sure no tag spans the boundary.

        Args:
            chunk: A new piece of streaming text.

        Returns:
            The portion of text that has been restored and can be emitted.
        """
        self._buffer += chunk

        if not self._session.tag_to_original:
            # No tags to restore — pass through immediately
            result = self._buffer
            self._buffer = ""
            return result

        # Restore any complete tags in the buffer
        restored = self._buffer
        for tag in sorted(self._session.tag_to_original.keys(), key=len, reverse=True):
            original = self._session.tag_to_original[tag]
            restored = restored.replace(tag, original)

        # Keep a tail buffer in case a tag is being split
        # The tail should be at most max_tag_len - 1 characters
        if self._max_tag_len > 0 and len(restored) > self._max_tag_len:
            safe = restored[: -self._max_tag_len]
            self._buffer = restored[-self._max_tag_len :]
            return safe
        elif len(self._buffer) > self._max_buffer_size:
            # Force flush to avoid unbounded growth
            result = restored
            self._buffer = ""
            return result
        else:
            # Keep buffering
            self._buffer = restored
            return ""

    def flush(self) -> str:
        """Flush any remaining buffered text.

        Call this when the stream ends.

        Returns:
            The remaining restored text.
        """
        result = self._buffer
        self._buffer = ""
        # Final restoration pass
        for tag in sorted(self._session.tag_to_original.keys(), key=len, reverse=True):
            original = self._session.tag_to_original[tag]
            result = result.replace(tag, original)
        return result


async def restore_sse_stream(
    raw_stream: AsyncIterator[bytes],
    session: SanitizationSession,
    provider_name: str = "openai",
) -> AsyncIterator[bytes]:
    """Process an SSE byte stream, restoring tags in the content fields.

    Args:
        raw_stream: The raw SSE byte stream from the upstream LLM.
        session: The sanitization session.
        provider_name: Provider name to determine response format.

    Yields:
        Restored SSE byte chunks.
    """
    restorer = StreamingRestorer(session)

    async for raw_chunk in raw_stream:
        chunk_str = raw_chunk.decode("utf-8", errors="replace")

        # Process each SSE line
        lines = chunk_str.split("\n")
        restored_lines = []

        for line in lines:
            if line.startswith("data: "):
                data = line[6:]
                if data.strip() == "[DONE]":
                    restored_lines.append(line)
                    continue

                try:
                    parsed = json.loads(data)
                    # Extract delta content based on provider
                    content = _extract_delta_content(parsed, provider_name)
                    if content:
                        restored_content = restorer.feed(content)
                        _set_delta_content(parsed, restored_content, provider_name)
                    restored_lines.append(f"data: {json.dumps(parsed)}")
                except (json.JSONDecodeError, KeyError):
                    restored_lines.append(line)
            else:
                restored_lines.append(line)

        yield ("\n".join(restored_lines)).encode("utf-8")

    # Flush remaining buffer
    remaining = restorer.flush()
    if remaining:
        # Emit as a final data chunk
        final = {"choices": [{"delta": {"content": remaining}}]}
        yield f"data: {json.dumps(final)}\n\n".encode()


def _extract_delta_content(parsed: dict, provider: str) -> str | None:
    """Extract streaming content from a parsed SSE data object."""
    if provider in ("openai", "azure", "generic"):
        choices = parsed.get("choices", [])
        if choices:
            delta = choices[0].get("delta", {})
            return delta.get("content")
    elif provider == "anthropic":
        if parsed.get("type") == "content_block_delta":
            delta = parsed.get("delta", {})
            return delta.get("text")
    elif provider == "google":
        candidates = parsed.get("candidates", [])
        if candidates:
            content = candidates[0].get("content", {})
            parts = content.get("parts", [])
            if parts:
                return parts[0].get("text")
    return None


def _set_delta_content(parsed: dict, content: str, provider: str) -> None:
    """Set streaming content in a parsed SSE data object."""
    if provider in ("openai", "azure", "generic"):
        choices = parsed.get("choices", [])
        if choices:
            delta = choices[0].get("delta", {})
            delta["content"] = content
    elif provider == "anthropic":
        if parsed.get("type") == "content_block_delta":
            delta = parsed.get("delta", {})
            delta["text"] = content
    elif provider == "google":
        candidates = parsed.get("candidates", [])
        if candidates:
            content_obj = candidates[0].get("content", {})
            parts = content_obj.get("parts", [])
            if parts:
                parts[0]["text"] = content
