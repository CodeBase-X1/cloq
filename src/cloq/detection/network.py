"""Network detector — finds internal IPs, hostnames, and connection endpoints."""

from __future__ import annotations

import re
from typing import ClassVar

from cloq.detection.base import BaseDetector, DetectionResult

# ── RFC 1918 / private IP ranges ─────────────────────────────────────
_PRIVATE_IP_PATTERN = re.compile(
    r"\b("
    # 10.0.0.0/8
    r"10\.\d{1,3}\.\d{1,3}\.\d{1,3}"
    r"|"
    # 172.16.0.0/12
    r"172\.(?:1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3}"
    r"|"
    # 192.168.0.0/16
    r"192\.168\.\d{1,3}\.\d{1,3}"
    r")"
    # Optional port
    r"(?::(\d{1,5}))?"
    r"\b"
)

# ── IPv6 link-local / ULA patterns ───────────────────────────────────
_IPV6_PRIVATE_PATTERN = re.compile(
    r"\b(fe80:[0-9a-fA-F:]{2,39}|fd[0-9a-fA-F]{2}:[0-9a-fA-F:]{2,39})\b"
)

# ── Localhost references ─────────────────────────────────────────────
_LOCALHOST_PATTERN = re.compile(r"\b(localhost|127\.0\.0\.1|0\.0\.0\.0|::1)(?::(\d{1,5}))?\b")


class NetworkDetector(BaseDetector):
    """Detects internal network infrastructure details in text.

    Finds:
    - RFC 1918 private IP addresses (``10.x``, ``172.16-31.x``, ``192.168.x``)
    - IPv6 link-local and ULA addresses
    - Localhost references
    - Internal hostnames matching configurable domain patterns
    - Internal URLs matching configurable patterns

    Args:
        internal_domains: Glob-style patterns for internal domain names
            (e.g., ``["*.internal.company.com", "*.corp.net"]``).
        detect_localhost: Whether to flag localhost/127.0.0.1 references.
            Defaults to ``True``.
    """

    name: ClassVar[str] = "network"

    def __init__(
        self,
        internal_domains: list[str] | None = None,
        detect_localhost: bool = True,
    ) -> None:
        self._detect_localhost = detect_localhost

        # Convert glob patterns to regex
        self._domain_patterns: list[re.Pattern[str]] = []
        for domain in internal_domains or []:
            # Convert *.example.com → .*\.example\.com
            escaped = re.escape(domain).replace(r"\*", r"[a-zA-Z0-9\-]+")
            self._domain_patterns.append(re.compile(r"\b" + escaped + r"\b", re.IGNORECASE))

    def detect(self, text: str) -> list[DetectionResult]:
        """Scan *text* for internal network references."""
        results: list[DetectionResult] = []

        # 1. Private IPv4 addresses
        for match in _PRIVATE_IP_PATTERN.finditer(text):
            results.append(
                DetectionResult(
                    entity_type="INTERNAL_IP",
                    start=match.start(),
                    end=match.end(),
                    score=0.95,
                    original_text=match.group(0),
                    detector_name=self.name,
                )
            )

        # 2. Private IPv6 addresses
        for match in _IPV6_PRIVATE_PATTERN.finditer(text):
            results.append(
                DetectionResult(
                    entity_type="INTERNAL_IP_V6",
                    start=match.start(),
                    end=match.end(),
                    score=0.90,
                    original_text=match.group(0),
                    detector_name=self.name,
                )
            )

        # 3. Localhost
        if self._detect_localhost:
            for match in _LOCALHOST_PATTERN.finditer(text):
                results.append(
                    DetectionResult(
                        entity_type="LOCALHOST",
                        start=match.start(),
                        end=match.end(),
                        score=0.85,
                        original_text=match.group(0),
                        detector_name=self.name,
                    )
                )

        # 4. Internal domain names
        for domain_re in self._domain_patterns:
            for match in domain_re.finditer(text):
                results.append(
                    DetectionResult(
                        entity_type="INTERNAL_HOSTNAME",
                        start=match.start(),
                        end=match.end(),
                        score=0.90,
                        original_text=match.group(0),
                        detector_name=self.name,
                    )
                )

        return results
