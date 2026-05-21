"""Secrets detector — regex + entropy-based detection of API keys, tokens, and credentials."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import ClassVar

from cloq.detection.base import BaseDetector, DetectionResult


@dataclass(frozen=True, slots=True)
class SecretPattern:
    """A named regex pattern for detecting a specific type of secret."""

    name: str
    entity_type: str
    pattern: re.Pattern[str]
    confidence: float = 0.95


# ── Built-in secret patterns ────────────────────────────────────────
_BUILTIN_PATTERNS: list[SecretPattern] = [
    # AWS
    SecretPattern(
        name="aws_access_key",
        entity_type="AWS_ACCESS_KEY",
        pattern=re.compile(r"(?<![A-Z0-9])AKIA[0-9A-Z]{16}(?![A-Z0-9])"),
        confidence=0.98,
    ),
    SecretPattern(
        name="aws_secret_key",
        entity_type="AWS_SECRET_KEY",
        pattern=re.compile(r"(?<![A-Za-z0-9/+=])[A-Za-z0-9/+=]{40}(?![A-Za-z0-9/+=])"),
        confidence=0.60,  # Lower confidence — needs entropy check
    ),
    # Google
    SecretPattern(
        name="google_api_key",
        entity_type="GOOGLE_API_KEY",
        pattern=re.compile(r"AIza[0-9A-Za-z\-_]{35}"),
        confidence=0.95,
    ),
    # GitHub
    SecretPattern(
        name="github_token",
        entity_type="GITHUB_TOKEN",
        pattern=re.compile(r"(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9_]{36,255}"),
        confidence=0.98,
    ),
    # Slack
    SecretPattern(
        name="slack_token",
        entity_type="SLACK_TOKEN",
        pattern=re.compile(r"xox[baprs]-[0-9]{10,13}-[0-9]{10,13}-[a-zA-Z0-9]{24,34}"),
        confidence=0.95,
    ),
    # Stripe
    SecretPattern(
        name="stripe_secret_key",
        entity_type="STRIPE_KEY",
        pattern=re.compile(r"(?:sk|pk)_(?:live|test)_[A-Za-z0-9]{24,99}"),
        confidence=0.98,
    ),
    # JWT
    SecretPattern(
        name="jwt_token",
        entity_type="JWT_TOKEN",
        pattern=re.compile(r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"),
        confidence=0.90,
    ),
    # Private keys (PEM)
    SecretPattern(
        name="private_key",
        entity_type="PRIVATE_KEY",
        pattern=re.compile(
            r"-----BEGIN (?:RSA |EC |DSA |OPENSSH |PGP )?PRIVATE KEY-----"
            r"[\s\S]*?"
            r"-----END (?:RSA |EC |DSA |OPENSSH |PGP )?PRIVATE KEY-----"
        ),
        confidence=0.99,
    ),
    # Azure connection strings
    SecretPattern(
        name="azure_connection_string",
        entity_type="AZURE_CONNECTION_STRING",
        pattern=re.compile(
            r"DefaultEndpointsProtocol=https?;"
            r"AccountName=[^;]+;"
            r"AccountKey=[A-Za-z0-9+/=]+;"
            r"EndpointSuffix=[^;\s]+"
        ),
        confidence=0.98,
    ),
    # Generic connection strings
    SecretPattern(
        name="postgres_connection",
        entity_type="CONNECTION_STRING",
        pattern=re.compile(
            r"(?:postgresql|postgres|mysql|mongodb|redis|amqp)://"
            r"[^\s\"'`<>]{10,}"
        ),
        confidence=0.90,
    ),
    # JDBC connection strings
    SecretPattern(
        name="jdbc_connection",
        entity_type="CONNECTION_STRING",
        pattern=re.compile(r"jdbc:[a-z]+://[^\s\"'`<>]{10,}"),
        confidence=0.90,
    ),
    # Heroku API key
    SecretPattern(
        name="heroku_api_key",
        entity_type="HEROKU_KEY",
        pattern=re.compile(
            r"(?i)heroku[_\-\s]*(?:api[_\-\s]*)?key[_\-\s]*[:=]\s*['\"]?"
            r"([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})"
        ),
        confidence=0.90,
    ),
    # SendGrid API key
    SecretPattern(
        name="sendgrid_key",
        entity_type="SENDGRID_KEY",
        pattern=re.compile(r"SG\.[A-Za-z0-9_-]{22}\.[A-Za-z0-9_-]{43}"),
        confidence=0.95,
    ),
    # Twilio
    SecretPattern(
        name="twilio_key",
        entity_type="TWILIO_KEY",
        pattern=re.compile(r"SK[0-9a-fA-F]{32}"),
        confidence=0.85,
    ),
    # Generic API key in config (key=value patterns)
    SecretPattern(
        name="generic_api_key_assignment",
        entity_type="API_KEY",
        pattern=re.compile(
            r"(?i)(?:api[_\-]?key|api[_\-]?secret|access[_\-]?token|auth[_\-]?token|secret[_\-]?key)"
            r"\s*[:=]\s*['\"]?"
            r"([A-Za-z0-9_\-./+=]{16,})"
            r"['\"]?"
        ),
        confidence=0.80,
    ),
]


def _shannon_entropy(data: str) -> float:
    """Calculate Shannon entropy of a string."""
    if not data:
        return 0.0
    freq: dict[str, int] = {}
    for char in data:
        freq[char] = freq.get(char, 0) + 1
    length = len(data)
    return -sum((count / length) * math.log2(count / length) for count in freq.values())


class SecretsDetector(BaseDetector):
    """Detects API keys, tokens, credentials, and high-entropy strings.

    Uses a combination of regex patterns for known secret formats and
    Shannon entropy analysis for generic high-entropy strings.

    Args:
        custom_patterns: Additional :class:`SecretPattern` instances to
            include alongside the built-in patterns.
        entropy_threshold: Minimum Shannon entropy for a string to be
            flagged as a potential secret.  Defaults to ``4.5``.
        min_entropy_length: Minimum length for entropy-based detection.
            Defaults to ``20``.
    """

    name: ClassVar[str] = "secrets"

    def __init__(
        self,
        custom_patterns: list[SecretPattern] | None = None,
        entropy_threshold: float = 4.5,
        min_entropy_length: int = 20,
    ) -> None:
        self._patterns = list(_BUILTIN_PATTERNS)
        if custom_patterns:
            self._patterns.extend(custom_patterns)
        self._entropy_threshold = entropy_threshold
        self._min_entropy_length = min_entropy_length

    def detect(self, text: str) -> list[DetectionResult]:
        """Scan *text* for secrets using regex patterns and entropy analysis."""
        results: list[DetectionResult] = []

        # 1. Pattern-based detection
        for pattern in self._patterns:
            for match in pattern.pattern.finditer(text):
                # Use group(1) if a capture group exists, else group(0)
                matched_text = match.group(1) if match.lastindex else match.group(0)
                start = match.start(1) if match.lastindex else match.start(0)
                end = match.end(1) if match.lastindex else match.end(0)

                results.append(
                    DetectionResult(
                        entity_type=pattern.entity_type,
                        start=start,
                        end=end,
                        score=pattern.confidence,
                        original_text=matched_text,
                        detector_name=self.name,
                    )
                )

        # 2. Entropy-based detection for unmatched high-entropy tokens
        results.extend(self._detect_high_entropy(text, results))

        return results

    def _detect_high_entropy(
        self,
        text: str,
        existing: list[DetectionResult],
    ) -> list[DetectionResult]:
        """Find high-entropy tokens not already captured by regex patterns."""
        entropy_results: list[DetectionResult] = []
        # Match contiguous alphanumeric+symbol tokens
        token_pattern = re.compile(rf"[A-Za-z0-9_\-./+=]{{{self._min_entropy_length},}}")

        for match in token_pattern.finditer(text):
            token = match.group(0)
            start, end = match.start(), match.end()

            # Skip if already detected by a pattern
            already_covered = any(r.start <= start and r.end >= end for r in existing)
            if already_covered:
                continue

            entropy = _shannon_entropy(token)
            if entropy >= self._entropy_threshold:
                entropy_results.append(
                    DetectionResult(
                        entity_type="HIGH_ENTROPY_STRING",
                        start=start,
                        end=end,
                        score=min(0.7, entropy / 6.0),  # Normalize to ~0.7 max
                        original_text=token,
                        detector_name=self.name,
                    )
                )

        return entropy_results
