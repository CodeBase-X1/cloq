# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in Cloq, please report it responsibly.

**⚠️ Do NOT open a public GitHub issue for security vulnerabilities.**

### How to Report

1. Email us at **security@cloq.dev**
2. Include a detailed description of the vulnerability
3. Provide steps to reproduce if possible
4. Allow us reasonable time to address the issue before disclosure

### What to Expect

- We will acknowledge your report within **48 hours**
- We will provide a timeline for a fix within **7 days**
- We will notify you when the vulnerability is fixed
- We will credit you in the release notes (unless you prefer anonymity)

## Supported Versions

| Version | Supported |
|---------|-----------|
| 0.1.x   | ✅         |

## Security Design Principles

Cloq is designed with security-first principles:

1. **Local-only processing** — Sensitive data never leaves the developer's machine
2. **In-memory sessions** — Tag-to-original mappings are never written to disk unencrypted
3. **Audit without secrets** — The audit log records entity types but never the actual values
4. **No telemetry** — Cloq does not phone home or collect any usage data
5. **Minimal dependencies** — We minimize the attack surface by keeping dependencies lean
