"""Tests for the network detector."""

from __future__ import annotations

import pytest

from cloq.detection.network import NetworkDetector


@pytest.fixture
def detector() -> NetworkDetector:
    return NetworkDetector(
        internal_domains=["*.internal.company.com", "*.corp.net"],
    )


class TestPrivateIPDetection:
    def test_detects_10_range(self, detector: NetworkDetector) -> None:
        text = "Connect to 10.0.1.50 for the API"
        results = detector.detect(text)
        ip_results = [r for r in results if r.entity_type == "INTERNAL_IP"]
        assert len(ip_results) == 1
        assert ip_results[0].original_text == "10.0.1.50"

    def test_detects_172_range(self, detector: NetworkDetector) -> None:
        text = "Server at 172.16.0.1"
        results = detector.detect(text)
        ip_results = [r for r in results if r.entity_type == "INTERNAL_IP"]
        assert len(ip_results) == 1

    def test_detects_192_168_range(self, detector: NetworkDetector) -> None:
        text = "Gateway: 192.168.1.1"
        results = detector.detect(text)
        ip_results = [r for r in results if r.entity_type == "INTERNAL_IP"]
        assert len(ip_results) == 1

    def test_detects_ip_with_port(self, detector: NetworkDetector) -> None:
        text = "Database at 10.0.1.50:5432"
        results = detector.detect(text)
        ip_results = [r for r in results if r.entity_type == "INTERNAL_IP"]
        assert len(ip_results) == 1
        assert "5432" in ip_results[0].original_text

    def test_ignores_public_ip(self, detector: NetworkDetector) -> None:
        text = "Visit 8.8.8.8 for DNS"
        results = detector.detect(text)
        ip_results = [r for r in results if r.entity_type == "INTERNAL_IP"]
        assert len(ip_results) == 0

    def test_detects_multiple_ips(self, detector: NetworkDetector) -> None:
        text = "Primary: 10.0.1.50, Secondary: 10.0.1.51"
        results = detector.detect(text)
        ip_results = [r for r in results if r.entity_type == "INTERNAL_IP"]
        assert len(ip_results) == 2


class TestLocalhostDetection:
    def test_detects_localhost(self) -> None:
        detector = NetworkDetector(detect_localhost=True)
        text = "Running on localhost:3000"
        results = detector.detect(text)
        local_results = [r for r in results if r.entity_type == "LOCALHOST"]
        assert len(local_results) == 1

    def test_detects_127_0_0_1(self) -> None:
        detector = NetworkDetector(detect_localhost=True)
        text = "API at 127.0.0.1:8080"
        results = detector.detect(text)
        local_results = [r for r in results if r.entity_type == "LOCALHOST"]
        assert len(local_results) == 1

    def test_skips_localhost_when_disabled(self) -> None:
        detector = NetworkDetector(detect_localhost=False)
        text = "Running on localhost:3000"
        results = detector.detect(text)
        local_results = [r for r in results if r.entity_type == "LOCALHOST"]
        assert len(local_results) == 0


class TestInternalDomains:
    def test_detects_internal_domain(self, detector: NetworkDetector) -> None:
        text = "API is at api.internal.company.com"
        results = detector.detect(text)
        domain_results = [r for r in results if r.entity_type == "INTERNAL_HOSTNAME"]
        assert len(domain_results) == 1

    def test_detects_corp_domain(self, detector: NetworkDetector) -> None:
        text = "Check db.corp.net for status"
        results = detector.detect(text)
        domain_results = [r for r in results if r.entity_type == "INTERNAL_HOSTNAME"]
        assert len(domain_results) == 1

    def test_ignores_public_domain(self, detector: NetworkDetector) -> None:
        text = "Visit api.openai.com"
        results = detector.detect(text)
        domain_results = [r for r in results if r.entity_type == "INTERNAL_HOSTNAME"]
        assert len(domain_results) == 0
