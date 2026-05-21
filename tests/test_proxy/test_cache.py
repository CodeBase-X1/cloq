"""Tests for Cloq's De-Identified Prompt Caching (DPC)."""

from __future__ import annotations

import tempfile

from cloq.proxy.cache import LocalPromptCache


def test_cache_hit_and_miss() -> None:
    """Test standard prompt caching set/get functionality."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cache = LocalPromptCache(cache_dir=tmpdir)

        messages = [{"role": "user", "content": "Tell me about [AWS_ACCESS_KEY_1]"}]
        provider = "openai"
        response = {"choices": [{"message": {"role": "assistant", "content": "Details"}}]}

        # Miss initially
        assert cache.get(messages, provider) is None

        # Cache set
        cache.set(messages, provider, response)

        # Hit afterwards
        cached = cache.get(messages, provider)
        assert cached is not None
        assert cached["choices"][0]["message"]["content"] == "Details"


def test_semantic_template_matching() -> None:
    """Verify that different values mapping to the same template trigger cache hits."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cache = LocalPromptCache(cache_dir=tmpdir)

        # Prompt with key A
        messages_a = [{"role": "user", "content": "Use [AWS_ACCESS_KEY_1] to connect."}]
        response = {
            "choices": [
                {"message": {"role": "assistant", "content": "Connected using [AWS_ACCESS_KEY_1]."}}
            ]
        }

        cache.set(messages_a, "openai", response)

        # Prompt with key B (identical normalized structure)
        messages_b = [{"role": "user", "content": "Use [AWS_ACCESS_KEY_1] to connect."}]
        cached = cache.get(messages_b, "openai")

        assert cached is not None
        assert cached["choices"][0]["message"]["content"] == "Connected using [AWS_ACCESS_KEY_1]."
