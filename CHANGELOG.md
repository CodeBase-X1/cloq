# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2025-XX-XX

### Added

- 🎭 Initial release of Cloq
- **Detection Engine** with three built-in detectors:
  - **Secrets Detector** — AWS keys, GitHub tokens, Stripe keys, JWT, private keys, connection strings, and high-entropy strings
  - **PII Detector** — Emails, phone numbers, credit cards, SSNs (Presidio + regex fallback)
  - **Network Detector** — RFC 1918 private IPs, internal hostnames, localhost references
- **Sanitizer Engine** with reversible synthetic tagging (`[AWS_KEY_1]`, `[EMAIL_1]`)
- **Proxy Server** (FastAPI + httpx) supporting:
  - OpenAI API
  - Anthropic Claude API
  - Google Gemini API
  - Azure OpenAI
  - Any OpenAI-compatible API (Groq, Together, Ollama, etc.)
- **SSE Streaming** support with cross-boundary tag restoration
- **CLI** (`cloq start`, `cloq scan`, `cloq status`, `cloq test`, `cloq config`)
- **Configuration** via YAML files, environment variables, and CLI flags
- **Audit logging** in JSON Lines format (never records actual sensitive values)
- **Plugin architecture** for custom detectors
- GitHub Actions CI/CD (lint, test, publish)
- Comprehensive test suite
