"""Shared test fixtures for Cloq test suite."""

from __future__ import annotations

import pytest

from cloq.config.schema import CloqConfig
from cloq.detection.network import NetworkDetector
from cloq.detection.pii import PIIDetector
from cloq.detection.pipeline import DetectionPipeline
from cloq.detection.secrets import SecretsDetector
from cloq.sanitizer.engine import SanitizationSession
from cloq.sanitizer.session_store import SessionStore


@pytest.fixture
def secrets_detector() -> SecretsDetector:
    """A default secrets detector."""
    return SecretsDetector()


@pytest.fixture
def pii_detector() -> PIIDetector:
    """A PII detector (regex fallback mode)."""
    return PIIDetector()


@pytest.fixture
def network_detector() -> NetworkDetector:
    """A network detector with sample internal domains."""
    return NetworkDetector(
        internal_domains=["*.internal.company.com", "*.corp.net"],
    )


@pytest.fixture
def pipeline(
    secrets_detector: SecretsDetector,
    pii_detector: PIIDetector,
    network_detector: NetworkDetector,
) -> DetectionPipeline:
    """A full detection pipeline with all detectors."""
    return DetectionPipeline([secrets_detector, pii_detector, network_detector])


@pytest.fixture
def session() -> SanitizationSession:
    """A fresh sanitization session."""
    return SanitizationSession(session_id="test-session")


@pytest.fixture
def session_store() -> SessionStore:
    """A session store with 60s TTL."""
    return SessionStore(default_ttl=60)


@pytest.fixture
def config() -> CloqConfig:
    """A default Cloq configuration."""
    return CloqConfig()
