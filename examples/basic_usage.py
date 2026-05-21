"""Basic usage example for Cloq detection and sanitization."""

from cloq.detection.network import NetworkDetector
from cloq.detection.pii import PIIDetector
from cloq.detection.pipeline import DetectionPipeline
from cloq.detection.secrets import SecretsDetector
from cloq.sanitizer.engine import SanitizationSession, restore, sanitize


def main() -> None:
    # 1. Create a detection pipeline
    pipeline = DetectionPipeline([
        SecretsDetector(),
        PIIDetector(),
        NetworkDetector(internal_domains=["*.internal.company.com"]),
    ])

    # 2. Sample text with sensitive data
    text = (
        "Fix the authentication bug. "
        "The database is at 10.0.1.50:5432, "
        "my AWS key is AKIAIOSFODNN7EXAMPLE, "
        "and contact me at dev@company.com"
    )

    print("📄 Original text:")
    print(f"   {text}\n")

    # 3. Detect sensitive data
    results, metrics = pipeline.run(text)
    print(f"🔍 Detected {len(results)} sensitive items in {metrics.total_duration_ms:.1f}ms:")
    for r in results:
        print(f"   • {r.entity_type}: {r.original_text[:20]}... (score: {r.score:.0%})")

    # 4. Sanitize
    session = SanitizationSession(session_id="example")
    sanitized = sanitize(text, results, session)
    print(f"\n🔒 Sanitized text:")
    print(f"   {sanitized}\n")

    # 5. Restore (simulating LLM response)
    llm_response = f"I fixed the bug. Connect to [INTERNAL_IP_1] and use [AWS_ACCESS_KEY_1]."
    restored = restore(llm_response, session)
    print(f"🔓 Restored LLM response:")
    print(f"   {restored}\n")

    # 6. Show tag mapping
    print("📋 Tag mapping:")
    for tag, original in session.tag_to_original.items():
        print(f"   {tag} → {original}")


if __name__ == "__main__":
    main()
