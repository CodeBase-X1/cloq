"""Tests for the PII detector (regex fallback mode)."""

from __future__ import annotations

import pytest

from cloq.detection.pii import PIIDetector


@pytest.fixture
def detector() -> PIIDetector:
    return PIIDetector()


class TestEmailDetection:
    def test_detects_email(self, detector: PIIDetector) -> None:
        text = "Contact me at john.doe@company.com for details"
        results = detector.detect(text)
        email_results = [r for r in results if r.entity_type == "EMAIL_ADDRESS"]
        assert len(email_results) == 1
        assert email_results[0].original_text == "john.doe@company.com"

    def test_detects_multiple_emails(self, detector: PIIDetector) -> None:
        text = "Send to alice@example.com and bob@company.org"
        results = detector.detect(text)
        email_results = [r for r in results if r.entity_type == "EMAIL_ADDRESS"]
        assert len(email_results) == 2


class TestPhoneDetection:
    def test_detects_us_phone(self, detector: PIIDetector) -> None:
        text = "Call me at (555) 123-4567"
        results = detector.detect(text)
        phone_results = [r for r in results if r.entity_type == "PHONE_NUMBER"]
        assert len(phone_results) == 1

    def test_detects_phone_with_country_code(self, detector: PIIDetector) -> None:
        text = "Phone: +1-555-123-4567"
        results = detector.detect(text)
        phone_results = [r for r in results if r.entity_type == "PHONE_NUMBER"]
        assert len(phone_results) == 1


class TestCreditCardDetection:
    def test_detects_visa(self, detector: PIIDetector) -> None:
        text = "Card: 4111111111111111"
        results = detector.detect(text)
        cc_results = [r for r in results if r.entity_type == "CREDIT_CARD"]
        assert len(cc_results) == 1

    def test_detects_mastercard(self, detector: PIIDetector) -> None:
        text = "Payment with 5500000000000004"
        results = detector.detect(text)
        cc_results = [r for r in results if r.entity_type == "CREDIT_CARD"]
        assert len(cc_results) == 1


class TestSSNDetection:
    def test_detects_ssn(self, detector: PIIDetector) -> None:
        text = "SSN: 123-45-6789"
        results = detector.detect(text)
        ssn_results = [r for r in results if r.entity_type == "US_SSN"]
        assert len(ssn_results) == 1


class TestPresidioFallback:
    def test_uses_regex_fallback(self) -> None:
        detector = PIIDetector()
        # In test environment, Presidio may not be installed
        # The detector should still work via regex fallback
        text = "Email: test@example.com"
        results = detector.detect(text)
        assert len(results) >= 1


class TestConfigurableEntities:
    def test_respects_entity_filter(self) -> None:
        detector = PIIDetector(entities=["EMAIL_ADDRESS"])
        text = "Email: test@example.com, Phone: 555-123-4567"
        results = detector.detect(text)
        # Should only detect emails, not phones
        entity_types = {r.entity_type for r in results}
        assert "EMAIL_ADDRESS" in entity_types
        assert "PHONE_NUMBER" not in entity_types
