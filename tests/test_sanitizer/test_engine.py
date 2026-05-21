"""Tests for the sanitizer engine."""

from cloq.detection.base import DetectionResult
from cloq.sanitizer.engine import restore, sanitize


class TestSanitizationSession:
    def test_creates_tag(self, session):
        tag = session.get_or_create_tag("AWS_KEY", "AKIAIOSFODNN7EXAMPLE")
        assert tag == "[AWS_KEY_1]"

    def test_idempotent_tags(self, session):
        tag1 = session.get_or_create_tag("AWS_KEY", "AKIAIOSFODNN7EXAMPLE")
        tag2 = session.get_or_create_tag("AWS_KEY", "AKIAIOSFODNN7EXAMPLE")
        assert tag1 == tag2
        assert session.total_substitutions == 1

    def test_different_values_different_tags(self, session):
        tag1 = session.get_or_create_tag("AWS_KEY", "KEY1")
        tag2 = session.get_or_create_tag("AWS_KEY", "KEY2")
        assert tag1 == "[AWS_KEY_1]"
        assert tag2 == "[AWS_KEY_2]"


class TestSanitize:
    def test_sanitizes_text(self, session):
        text = "My key is AKIAIOSFODNN7EXAMPLE here"
        detections = [DetectionResult("AWS_KEY", 10, 30, 0.98, "AKIAIOSFODNN7EXAMPLE", "secrets")]
        result = sanitize(text, detections, session)
        assert result == "My key is [AWS_KEY_1] here"

    def test_empty_detections(self, session):
        assert sanitize("No secrets", [], session) == "No secrets"


class TestRestore:
    def test_restores_tags(self, session):
        session.get_or_create_tag("AWS_KEY", "AKIAIOSFODNN7EXAMPLE")
        result = restore("Key [AWS_KEY_1] is valid", session)
        assert result == "Key AKIAIOSFODNN7EXAMPLE is valid"

    def test_roundtrip(self, session):
        original = "Connect to 10.0.1.50:5432 with key AKIAIOSFODNN7EXAMPLE"
        detections = [
            DetectionResult("INTERNAL_IP", 11, 25, 0.95, "10.0.1.50:5432", "network"),
            DetectionResult("AWS_KEY", 35, 55, 0.98, "AKIAIOSFODNN7EXAMPLE", "secrets"),
        ]
        sanitized = sanitize(original, detections, session)
        assert restore(sanitized, session) == original
