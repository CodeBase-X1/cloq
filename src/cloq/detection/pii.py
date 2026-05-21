"""PII detector — wraps Microsoft Presidio for entity detection.

Falls back to lightweight regex-based detection when Presidio is not installed.
"""

from __future__ import annotations

import re
from typing import ClassVar

from cloq.detection.base import BaseDetector, DetectionResult

# ── Default PII entity types to detect ───────────────────────────────
DEFAULT_PII_ENTITIES: list[str] = [
    "EMAIL_ADDRESS",
    "PHONE_NUMBER",
    "CREDIT_CARD",
    "US_SSN",
    "US_PASSPORT",
    "IBAN_CODE",
    "IP_ADDRESS",
    "PERSON",
    "LOCATION",
]

# ── Regex fallback patterns ──────────────────────────────────────────
_FALLBACK_PATTERNS: dict[str, re.Pattern[str]] = {
    "EMAIL_ADDRESS": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"),
    "PHONE_NUMBER": re.compile(r"(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"),
    "CREDIT_CARD": re.compile(
        r"\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13}|"
        r"3(?:0[0-5]|[68][0-9])[0-9]{11}|6(?:011|5[0-9]{2})[0-9]{12}|"
        r"(?:2131|1800|35\d{3})\d{11})\b"
    ),
    "US_SSN": re.compile(r"\b(?!000|666|9\d{2})\d{3}[-\s]?(?!00)\d{2}[-\s]?(?!0000)\d{4}\b"),
    "IBAN_CODE": re.compile(r"\b[A-Z]{2}\d{2}[A-Z0-9]{4}\d{7}(?:[A-Z0-9]?){0,16}\b"),
}


class PIIDetector(BaseDetector):
    """Detects personally identifiable information (PII) in text.

    Uses Microsoft Presidio when available for high-quality NER-backed
    detection.  Falls back to regex patterns when Presidio is not
    installed (``pip install cloq[pii]``).

    Args:
        entities: Entity types to detect.  Defaults to
            :data:`DEFAULT_PII_ENTITIES`.
        confidence_threshold: Minimum Presidio score to keep a result.
            Defaults to ``0.5``.
        language: Language code for Presidio analysis.  Defaults to ``"en"``.
    """

    name: ClassVar[str] = "pii"

    def __init__(
        self,
        entities: list[str] | None = None,
        confidence_threshold: float = 0.5,
        language: str = "en",
    ) -> None:
        self._entities = entities or list(DEFAULT_PII_ENTITIES)
        self._confidence_threshold = confidence_threshold
        self._language = language
        self._presidio_analyzer = None
        self._using_presidio = False

        # Try to import Presidio
        try:
            from presidio_analyzer import AnalyzerEngine  # type: ignore[import-untyped]

            self._presidio_analyzer = AnalyzerEngine()
            self._using_presidio = True
        except ImportError:
            pass

    @property
    def using_presidio(self) -> bool:
        """Whether Presidio is available and being used."""
        return self._using_presidio

    def detect(self, text: str) -> list[DetectionResult]:
        """Scan *text* for PII entities."""
        if self._using_presidio:
            return self._detect_presidio(text)
        return self._detect_regex(text)

    def _detect_presidio(self, text: str) -> list[DetectionResult]:
        """Use Presidio AnalyzerEngine for detection."""
        assert self._presidio_analyzer is not None

        presidio_results = self._presidio_analyzer.analyze(
            text=text,
            entities=self._entities,
            language=self._language,
        )

        results: list[DetectionResult] = []
        for r in presidio_results:
            if r.score < self._confidence_threshold:
                continue
            results.append(
                DetectionResult(
                    entity_type=r.entity_type,
                    start=r.start,
                    end=r.end,
                    score=r.score,
                    original_text=text[r.start : r.end],
                    detector_name=self.name,
                )
            )
        return results

    def _detect_regex(self, text: str) -> list[DetectionResult]:
        """Lightweight regex fallback when Presidio is not installed."""
        results: list[DetectionResult] = []

        for entity_type, pattern in _FALLBACK_PATTERNS.items():
            if entity_type not in self._entities:
                continue
            for match in pattern.finditer(text):
                results.append(
                    DetectionResult(
                        entity_type=entity_type,
                        start=match.start(),
                        end=match.end(),
                        score=0.80,  # Regex-based → slightly lower confidence
                        original_text=match.group(0),
                        detector_name=self.name,
                    )
                )

        return results
