"""LLM provider adapters — extract and inject text from provider-specific formats."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ProviderMatch:
    """Result of matching a request to a specific provider."""

    provider_name: str
    upstream_url: str


class BaseProvider(ABC):
    """Abstract base for LLM provider adapters."""

    name: str
    """Human-readable provider name."""

    @abstractmethod
    def matches(self, path: str, headers: dict[str, str]) -> ProviderMatch | None:
        """Return a :class:`ProviderMatch` if this provider handles the request."""

    @abstractmethod
    def extract_messages(self, body: dict[str, Any]) -> list[dict[str, Any]]:
        """Extract the list of chat messages from the request body."""

    @abstractmethod
    def inject_messages(
        self, body: dict[str, Any], messages: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Return a new body with the messages replaced."""

    @abstractmethod
    def extract_response_text(self, body: dict[str, Any]) -> list[str]:
        """Extract text content from the response body for restoration."""

    @abstractmethod
    def inject_response_text(self, body: dict[str, Any], texts: list[str]) -> dict[str, Any]:
        """Replace response text content after restoration."""


class OpenAIProvider(BaseProvider):
    """Adapter for OpenAI and OpenAI-compatible APIs."""

    name = "openai"

    def __init__(self, base_url: str = "https://api.openai.com") -> None:
        self._base_url = base_url.rstrip("/")

    def matches(self, path: str, headers: dict[str, str]) -> ProviderMatch | None:
        if "/v1/chat/completions" in path or "/v1/completions" in path:
            return ProviderMatch(
                provider_name=self.name,
                upstream_url=f"{self._base_url}{path}",
            )
        return None

    def extract_messages(self, body: dict[str, Any]) -> list[dict[str, Any]]:
        return body.get("messages", [])

    def inject_messages(
        self, body: dict[str, Any], messages: list[dict[str, Any]]
    ) -> dict[str, Any]:
        return {**body, "messages": messages}

    def extract_response_text(self, body: dict[str, Any]) -> list[str]:
        texts = []
        for choice in body.get("choices", []):
            msg = choice.get("message", {})
            if msg.get("content"):
                texts.append(msg["content"])
        return texts

    def inject_response_text(self, body: dict[str, Any], texts: list[str]) -> dict[str, Any]:
        new_body = dict(body)
        choices = list(body.get("choices", []))
        text_idx = 0
        for i, choice in enumerate(choices):
            msg = choice.get("message", {})
            if "content" in msg and msg["content"] and text_idx < len(texts):
                choices[i] = {
                    **choice,
                    "message": {**msg, "content": texts[text_idx]},
                }
                text_idx += 1
        new_body["choices"] = choices
        return new_body


class AnthropicProvider(BaseProvider):
    """Adapter for Anthropic's Claude API."""

    name = "anthropic"

    def __init__(self, base_url: str = "https://api.anthropic.com") -> None:
        self._base_url = base_url.rstrip("/")

    def matches(self, path: str, headers: dict[str, str]) -> ProviderMatch | None:
        if "/v1/messages" in path:
            return ProviderMatch(
                provider_name=self.name,
                upstream_url=f"{self._base_url}{path}",
            )
        # Also check for anthropic-version header
        if "anthropic-version" in headers:
            return ProviderMatch(
                provider_name=self.name,
                upstream_url=f"{self._base_url}{path}",
            )
        return None

    def extract_messages(self, body: dict[str, Any]) -> list[dict[str, Any]]:
        messages = list(body.get("messages", []))
        # Anthropic also has a system prompt at top level
        if "system" in body:
            system = body["system"]
            if isinstance(system, (str, list)):
                messages.insert(0, {"role": "system", "content": system})
        return messages

    def inject_messages(
        self, body: dict[str, Any], messages: list[dict[str, Any]]
    ) -> dict[str, Any]:
        new_body = dict(body)
        actual_messages = []
        for msg in messages:
            if msg.get("role") == "system":
                # Anthropic system prompt goes at top level
                content = msg.get("content", "")
                new_body["system"] = content
            else:
                actual_messages.append(msg)
        new_body["messages"] = actual_messages
        return new_body

    def extract_response_text(self, body: dict[str, Any]) -> list[str]:
        texts = []
        for block in body.get("content", []):
            if block.get("type") == "text":
                texts.append(block["text"])
        return texts

    def inject_response_text(self, body: dict[str, Any], texts: list[str]) -> dict[str, Any]:
        new_body = dict(body)
        content = list(body.get("content", []))
        text_idx = 0
        for i, block in enumerate(content):
            if block.get("type") == "text" and text_idx < len(texts):
                content[i] = {**block, "text": texts[text_idx]}
                text_idx += 1
        new_body["content"] = content
        return new_body


class GoogleProvider(BaseProvider):
    """Adapter for Google's Gemini API."""

    name = "google"

    def __init__(self, base_url: str = "https://generativelanguage.googleapis.com") -> None:
        self._base_url = base_url.rstrip("/")

    def matches(self, path: str, headers: dict[str, str]) -> ProviderMatch | None:
        if ":generateContent" in path or ":streamGenerateContent" in path:
            return ProviderMatch(
                provider_name=self.name,
                upstream_url=f"{self._base_url}{path}",
            )
        return None

    def extract_messages(self, body: dict[str, Any]) -> list[dict[str, Any]]:
        messages = []
        for content in body.get("contents", []):
            role = content.get("role", "user")
            parts = content.get("parts", [])
            for part in parts:
                if "text" in part:
                    messages.append({"role": role, "content": part["text"]})
        return messages

    def inject_messages(
        self, body: dict[str, Any], messages: list[dict[str, Any]]
    ) -> dict[str, Any]:
        new_body = dict(body)
        contents = []
        for msg in messages:
            contents.append(
                {
                    "role": msg.get("role", "user"),
                    "parts": [{"text": msg.get("content", "")}],
                }
            )
        new_body["contents"] = contents
        return new_body

    def extract_response_text(self, body: dict[str, Any]) -> list[str]:
        texts = []
        for candidate in body.get("candidates", []):
            content = candidate.get("content", {})
            for part in content.get("parts", []):
                if "text" in part:
                    texts.append(part["text"])
        return texts

    def inject_response_text(self, body: dict[str, Any], texts: list[str]) -> dict[str, Any]:
        new_body = dict(body)
        candidates = list(body.get("candidates", []))
        text_idx = 0
        for i, candidate in enumerate(candidates):
            content = candidate.get("content", {})
            parts = list(content.get("parts", []))
            for j, part in enumerate(parts):
                if "text" in part and text_idx < len(texts):
                    parts[j] = {**part, "text": texts[text_idx]}
                    text_idx += 1
            candidates[i] = {**candidate, "content": {**content, "parts": parts}}
        new_body["candidates"] = candidates
        return new_body


class AzureOpenAIProvider(OpenAIProvider):
    """Adapter for Azure OpenAI Service.

    Inherits from :class:`OpenAIProvider` since the API format is
    identical — only the URL pattern differs.
    """

    name = "azure"

    def __init__(self, base_url: str = "https://{resource}.openai.azure.com") -> None:
        super().__init__(base_url)

    def matches(self, path: str, headers: dict[str, str]) -> ProviderMatch | None:
        if "/openai/deployments/" in path and "/chat/completions" in path:
            return ProviderMatch(
                provider_name=self.name,
                upstream_url=f"{self._base_url}{path}",
            )
        return None


class GenericProvider(OpenAIProvider):
    """Fallback for any OpenAI-compatible API (Groq, Together, Ollama, etc.)."""

    name = "generic"

    def __init__(self, base_url: str = "") -> None:
        super().__init__(base_url)

    def matches(self, path: str, headers: dict[str, str]) -> ProviderMatch | None:
        # Generic fallback — matches any chat completions path
        if "/chat/completions" in path or "/completions" in path:
            return ProviderMatch(
                provider_name=self.name,
                upstream_url=path,  # Use original URL
            )
        return None


# ── Provider registry ────────────────────────────────────────────────
DEFAULT_PROVIDERS: list[BaseProvider] = [
    OpenAIProvider(),
    AnthropicProvider(),
    GoogleProvider(),
    AzureOpenAIProvider(),
    GenericProvider(),  # Fallback — must be last
]


def detect_provider(
    path: str, headers: dict[str, str]
) -> tuple[BaseProvider, ProviderMatch] | None:
    """Detect which provider should handle a request.

    Args:
        path: The request path.
        headers: Request headers (lowercase keys).

    Returns:
        A tuple of ``(provider, match)`` or ``None`` if no provider matches.
    """
    for provider in DEFAULT_PROVIDERS:
        match = provider.matches(path, headers)
        if match:
            return provider, match
    return None
