"""Local-first Semantic & De-Identified Prompt Cache for Cloq.

Caches sanitized prompts locally to achieve high cache hit rates across identical
query templates, cutting development costs and latency to 0ms.
"""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger("cloq.proxy.cache")


class LocalPromptCache:
    """Persistent, file-backed local prompt cache for de-identified queries."""

    def __init__(self, cache_dir: str | Path | None = None) -> None:
        """Initialize the local prompt cache."""
        if cache_dir is None:
            # Default to user's home directory
            self.cache_dir = Path.home() / ".cloq" / "cache"
        else:
            self.cache_dir = Path(cache_dir)

        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.index_file = self.cache_dir / "index.json"
        self._index: dict[str, dict[str, Any]] = {}
        self._load_index()

    def _load_index(self) -> None:
        """Load the cache index from disk."""
        if self.index_file.exists():
            try:
                with open(self.index_file, encoding="utf-8") as f:
                    self._index = json.load(f)
            except Exception as e:
                logger.warning("Failed to load prompt cache index: %s", e)
                self._index = {}
        else:
            self._index = {}

    def _save_index(self) -> None:
        """Persist the cache index to disk."""
        try:
            with open(self.index_file, "w", encoding="utf-8") as f:
                json.dump(self._index, f, indent=2)
        except Exception as e:
            logger.warning("Failed to save prompt cache index: %s", e)

    @staticmethod
    def get_prompt_hash(messages: list[dict[str, Any]], provider: str) -> str:
        """Calculate a stable SHA-256 hash for sanitized messages."""
        normalized = []
        for msg in messages:
            normalized.append({"role": msg.get("role", ""), "content": msg.get("content", "")})
        # Stable JSON serialization
        stable_str = json.dumps(normalized, sort_keys=True)
        return hashlib.sha256(f"{provider}:{stable_str}".encode()).hexdigest()

    def get(self, messages: list[dict[str, Any]], provider: str) -> dict[str, Any] | None:
        """Retrieve a cached sanitized response matching the normalized query."""
        prompt_hash = self.get_prompt_hash(messages, provider)
        entry = self._index.get(prompt_hash)
        if not entry:
            return None

        # Check TTL if configured (optional)
        cache_file = self.cache_dir / f"{prompt_hash}.json"
        if not cache_file.exists():
            return None

        try:
            with open(cache_file, encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning("Failed to load cached response file: %s", e)
            return None

    def set(
        self,
        messages: list[dict[str, Any]],
        provider: str,
        response_body: dict[str, Any],
    ) -> None:
        """Cache a sanitized response mapped to its normalized query template."""
        prompt_hash = self.get_prompt_hash(messages, provider)
        cache_file = self.cache_dir / f"{prompt_hash}.json"

        try:
            # Save the response body
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(response_body, f)

            # Update and save the index metadata
            self._index[prompt_hash] = {
                "provider": provider,
                "created_at": __import__("time").time(),
            }
            self._save_index()
            logger.info("Successfully cached sanitized prompt template | hash: %s", prompt_hash)
        except Exception as e:
            logger.warning("Failed to write to local prompt cache: %s", e)

    def clear(self) -> None:
        """Clear all cached files and reset index."""
        try:
            for cache_file in self.cache_dir.glob("*.json"):
                cache_file.unlink(missing_ok=True)
            self._index = {}
            self._save_index()
            logger.info("Cleared local prompt cache")
        except Exception as e:
            logger.warning("Failed to clear prompt cache: %s", e)
