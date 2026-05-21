"""Sanitization engine — replace detected entities with reversible synthetic tags."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cloq.detection.base import DetectionResult


@dataclass
class SanitizationSession:
    """Manages the bidirectional mapping between tags and original values.

    A session is created per-request and holds all the substitutions made
    so that the response can be *restored* with the real values.

    Attributes:
        session_id: Unique identifier for this session.
        tag_to_original: Maps synthetic tags (e.g., ``[AWS_KEY_1]``) to
            the original sensitive string.
        original_to_tag: Reverse map — original string to its tag.
        tag_format: Template for generating tag strings.
    """

    session_id: str
    tag_to_original: dict[str, str] = field(default_factory=dict)
    original_to_tag: dict[str, str] = field(default_factory=dict)
    tag_format: str = "[{entity_type}_{index}]"

    # Internal counter per entity type
    _counters: dict[str, int] = field(default_factory=dict, repr=False)

    def get_or_create_tag(self, entity_type: str, original_text: str) -> str:
        """Return an existing tag for *original_text*, or create a new one.

        The same original value always maps to the same tag within a session
        (idempotent).

        Args:
            entity_type: Detection category (e.g., ``AWS_KEY``).
            original_text: The sensitive string.

        Returns:
            A synthetic tag string like ``[AWS_KEY_1]``.
        """
        # Return existing tag if we've seen this value before
        if original_text in self.original_to_tag:
            return self.original_to_tag[original_text]

        # Create a new tag
        self._counters.setdefault(entity_type, 0)
        self._counters[entity_type] += 1
        index = self._counters[entity_type]

        tag = self.tag_format.format(entity_type=entity_type, index=index)

        self.tag_to_original[tag] = original_text
        self.original_to_tag[original_text] = tag

        return tag

    @property
    def total_substitutions(self) -> int:
        """Number of unique substitutions in this session."""
        return len(self.tag_to_original)


def sanitize(
    text: str,
    detections: list[DetectionResult],
    session: SanitizationSession,
) -> str:
    """Replace all detected entities in *text* with synthetic tags.

    Processes detections from **right to left** so that earlier indices
    remain valid after substitution.

    Args:
        text: The original text containing sensitive data.
        detections: Detection results from the pipeline (must reference
            positions in *text*).
        session: The session to record tag-to-original mappings.

    Returns:
        The sanitized text with all detected entities replaced by tags.
    """
    if not detections:
        return text

    # Sort detections by start position descending (right-to-left replacement)
    sorted_detections = sorted(detections, key=lambda d: d.start, reverse=True)

    sanitized = text
    for detection in sorted_detections:
        tag = session.get_or_create_tag(detection.entity_type, detection.original_text)
        sanitized = sanitized[: detection.start] + tag + sanitized[detection.end :]

    return sanitized


def restore(text: str, session: SanitizationSession) -> str:
    """Replace all synthetic tags in *text* with the original values.

    This is the reverse operation of :func:`sanitize`, used to re-inject
    real values into the LLM response before returning it to the developer.

    Args:
        text: The LLM response text containing synthetic tags.
        session: The session holding tag-to-original mappings.

    Returns:
        The restored text with real values re-injected.
    """
    restored = text

    # Replace longest tags first to avoid partial matches
    for tag in sorted(session.tag_to_original.keys(), key=len, reverse=True):
        original = session.tag_to_original[tag]
        restored = restored.replace(tag, original)

    return restored


def sanitize_messages(
    messages: list[dict],
    session: SanitizationSession,
    pipeline_run: callable,
) -> list[dict]:
    """Sanitize all text fields in a list of chat messages.

    Handles the standard ``{"role": "...", "content": "..."}`` format
    used by OpenAI, Anthropic, and other providers.

    Args:
        messages: List of message dicts with ``content`` fields.
        session: The sanitization session.
        pipeline_run: A callable that takes text and returns
            ``(detections, metrics)``.

    Returns:
        A new list of messages with sanitized ``content`` fields.
    """
    sanitized_messages = []

    for msg in messages:
        new_msg = dict(msg)

        content = msg.get("content")
        if isinstance(content, str):
            detections, _ = pipeline_run(content)
            new_msg["content"] = sanitize(content, detections, session)
        elif isinstance(content, list):
            # Handle multi-part content (e.g., Anthropic's format with text blocks)
            new_parts = []
            for part in content:
                if isinstance(part, dict) and part.get("type") == "text":
                    text = part.get("text", "")
                    detections, _ = pipeline_run(text)
                    new_parts.append(
                        {
                            **part,
                            "text": sanitize(text, detections, session),
                        }
                    )
                else:
                    new_parts.append(part)
            new_msg["content"] = new_parts

        sanitized_messages.append(new_msg)

    return sanitized_messages
