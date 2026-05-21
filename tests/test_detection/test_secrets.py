"""Tests for the secrets detector."""

from __future__ import annotations

import pytest

from cloq.detection.secrets import SecretsDetector


@pytest.fixture
def detector() -> SecretsDetector:
    return SecretsDetector()


class TestAWSKeys:
    """Test AWS credential detection."""

    def test_detects_aws_access_key(self, detector: SecretsDetector) -> None:
        text = "My key is AKIAIOSFODNN7EXAMPLE here"
        results = detector.detect(text)
        aws_results = [r for r in results if r.entity_type == "AWS_ACCESS_KEY"]
        assert len(aws_results) == 1
        assert aws_results[0].original_text == "AKIAIOSFODNN7EXAMPLE"
        assert aws_results[0].score >= 0.95

    def test_ignores_partial_aws_key(self, detector: SecretsDetector) -> None:
        text = "AKIA is just a prefix"
        results = detector.detect(text)
        aws_results = [r for r in results if r.entity_type == "AWS_ACCESS_KEY"]
        assert len(aws_results) == 0


class TestGitHubTokens:
    """Test GitHub token detection."""

    def test_detects_github_pat(self, detector: SecretsDetector) -> None:
        token = "ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghij"
        text = f"token={token}"
        results = detector.detect(text)
        gh_results = [r for r in results if r.entity_type == "GITHUB_TOKEN"]
        assert len(gh_results) == 1
        assert gh_results[0].original_text == token

    def test_detects_github_oauth(self, detector: SecretsDetector) -> None:
        token = "gho_ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghij"
        results = detector.detect(token)
        gh_results = [r for r in results if r.entity_type == "GITHUB_TOKEN"]
        assert len(gh_results) == 1


class TestStripeKeys:
    """Test Stripe key detection."""

    def test_detects_stripe_secret_key(self, detector: SecretsDetector) -> None:
        # Synthetic key — structurally valid format but not a real credential
        key = "sk_live_" + "X" * 24
        results = detector.detect(f"STRIPE_KEY={key}")
        stripe_results = [r for r in results if r.entity_type == "STRIPE_KEY"]
        assert len(stripe_results) >= 1

    def test_detects_stripe_test_key(self, detector: SecretsDetector) -> None:
        # Synthetic key — structurally valid format but not a real credential
        key = "sk_test_" + "Y" * 24
        results = detector.detect(key)
        stripe_results = [r for r in results if r.entity_type == "STRIPE_KEY"]
        assert len(stripe_results) >= 1


class TestJWT:
    """Test JWT token detection."""

    def test_detects_jwt_token(self, detector: SecretsDetector) -> None:
        jwt = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U"
        results = detector.detect(f"Bearer {jwt}")
        jwt_results = [r for r in results if r.entity_type == "JWT_TOKEN"]
        assert len(jwt_results) == 1


class TestPrivateKeys:
    """Test private key detection."""

    def test_detects_rsa_private_key(self, detector: SecretsDetector) -> None:
        text = """-----BEGIN RSA PRIVATE KEY-----
MIIEowIBAAKCAQEA0Z3VS5JJcds3xfn/ygWyF8PbnGy0AHB7MhgHcTz6sE2I2yPB
-----END RSA PRIVATE KEY-----"""
        results = detector.detect(text)
        key_results = [r for r in results if r.entity_type == "PRIVATE_KEY"]
        assert len(key_results) == 1


class TestConnectionStrings:
    """Test database connection string detection."""

    def test_detects_postgres_url(self, detector: SecretsDetector) -> None:
        text = "DATABASE_URL=postgresql://user:pass@db.internal:5432/mydb"
        results = detector.detect(text)
        conn_results = [r for r in results if r.entity_type == "CONNECTION_STRING"]
        assert len(conn_results) >= 1

    def test_detects_mongodb_url(self, detector: SecretsDetector) -> None:
        text = "mongodb://admin:secret@mongo.internal:27017/production"
        results = detector.detect(text)
        conn_results = [r for r in results if r.entity_type == "CONNECTION_STRING"]
        assert len(conn_results) >= 1

    def test_detects_redis_url(self, detector: SecretsDetector) -> None:
        text = "redis://default:mypassword@redis.internal:6379/0"
        results = detector.detect(text)
        conn_results = [r for r in results if r.entity_type == "CONNECTION_STRING"]
        assert len(conn_results) >= 1


class TestEntropyDetection:
    """Test Shannon entropy-based detection."""

    def test_detects_high_entropy_string(self, detector: SecretsDetector) -> None:
        # A random-looking string with high entropy
        text = "secret=aB3$kL9mNp2xRt5vWy8zA1cD4fG7hJ0"
        results = detector.detect(text)
        # Should detect something (either via pattern or entropy)
        assert len(results) >= 1

    def test_ignores_low_entropy_string(self, detector: SecretsDetector) -> None:
        text = "aaaaaaaaaaaaaaaaaaaaaaaaa"
        results = detector.detect(text)
        entropy_results = [r for r in results if r.entity_type == "HIGH_ENTROPY_STRING"]
        assert len(entropy_results) == 0


class TestGoogleAPIKey:
    """Test Google API key detection."""

    def test_detects_google_api_key(self, detector: SecretsDetector) -> None:
        key = "AIzaSyA1234567890abcdefghijklmnopqrstuv"
        results = detector.detect(f"key={key}")
        google_results = [r for r in results if r.entity_type == "GOOGLE_API_KEY"]
        assert len(google_results) == 1


class TestNoFalsePositives:
    """Ensure common non-secret strings are not flagged."""

    def test_normal_text_not_flagged(self, detector: SecretsDetector) -> None:
        text = "Please fix the login page. The button should be blue."
        results = detector.detect(text)
        assert len(results) == 0

    def test_code_not_flagged(self, detector: SecretsDetector) -> None:
        text = 'def hello_world():\n    print("Hello, World!")\n    return True'
        results = detector.detect(text)
        assert len(results) == 0
