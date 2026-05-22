<div align="center">

<img src="https://raw.githubusercontent.com/CodeBase-X1/cloq/main/assets/logo.gif" width="260" alt="Cloq" />

# Cloq

**Your secrets stay local. Your LLM gets the context.**

A local-first context sanitizer that sits between your IDE and the cloud LLM.
It detects API keys, PII, and internal IPs — replaces them with reversible tags — and restores them in the response.
Nothing sensitive ever leaves your machine.

[![CI](https://img.shields.io/github/actions/workflow/status/CodeBase-X1/cloq/ci.yml?branch=main&style=for-the-badge&logo=github&label=CI&color=22c55e)](https://github.com/CodeBase-X1/cloq/actions)
[![Python](https://img.shields.io/badge/python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://pypi.org/project/cloq)
[![License](https://img.shields.io/badge/license-Apache_2.0-0ea5e9?style=for-the-badge)](LICENSE)
[![Stars](https://img.shields.io/github/stars/CodeBase-X1/cloq?style=for-the-badge&logo=github&color=f59e0b)](https://github.com/CodeBase-X1/cloq/stargazers)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-ff69b4?style=for-the-badge)](CONTRIBUTING.md)

[Quick Start](#-quick-start) · [How It Works](#-how-it-works) · [Features](#-features) · [Providers](#-supported-providers) · [Configuration](#%EF%B8%8F-configuration) · [Contributing](#-contributing)

</div>

---

## 🎯 The Problem

Developers paste secrets into LLM prompts every day. AWS keys, database credentials, customer emails, internal IPs — most don't even realize it. Enterprise security teams know, and they block AI tools entirely because of it.

**Cloq eliminates this risk without changing your workflow.**

```diff
- "Fix the bug. DB is at 10.0.1.50:5432 and key is AKIAIOSFODNN7EXAMPLE"
+ "Fix the bug. DB is at [INTERNAL_IP_1] and key is [AWS_ACCESS_KEY_1]"
                                              ↑
                     Cloud LLM only sees sanitized tags
                     Real values restored locally on response
```

---

## ⚡ The Breakthrough: De-Identified Prompt Caching (DPC)

Traditional LLM prompt caches miss as soon as a variable, key, port, IP, or file path changes. 

Because **Cloq sanitizes these variables into uniform tags first**, it acts as a **semantic normalization layer**. Identical coding templates are matched locally, cutting development LLM costs by up to **80%**!

### How DPC Normalizes & Caches Your Prompts:

```
Developer A: "Fix the bug in 10.0.1.50:5432 with key AKIAIOSFODNN7EXAMPLE"
  ↳ Normalizes to: "Fix the bug in [INTERNAL_IP_1] with key [AWS_ACCESS_KEY_1]"
  ↳ CACHE MISS: Sent to Upstream Cloud LLM. Response cached locally as a template.

Developer B: "Fix the bug in 192.168.1.12:5432 with key AKIAI7YYYDNN7ANOTHER"
  ↳ Normalizes to: "Fix the bug in [INTERNAL_IP_1] with key [AWS_ACCESS_KEY_1]"
  ↳ CACHE HIT! Cloq instantly restores Developer B's variables locally in 4ms at $0 cost.
```

No cloud upstream call, zero token usage, completely private, and blazing fast.

---

## 🚀 Quick Start

```bash
# 1. Install globally via pip
pip install cloq

# 2. Run the interactive CLI to start the proxy
cloq-cli
```

*This will launch an interactive menu where you can choose to open the Web UI or run directly in the terminal.*

**To use with your AI tools:**
Just point your LLM client's Base URL to `http://127.0.0.1:8989/v1`

---

## 🖥️ Web UI Dashboard

Cloq comes with a gorgeous, live Web UI that monitors your tokens saved, active sessions, and protected entities in real time.

When running `cloq-cli`, simply select **★ Web UI (Open in Browser)**, or navigate manually to `http://127.0.0.1:8989/ui`.

---

## ⚙️ How It Works

Cloq runs as a **transparent local proxy** on your machine. Every LLM API call passes through it automatically.

```mermaid
sequenceDiagram
    participant Client as IDE / CLI / App
    participant Cloq as Cloq Proxy (Local)
    participant LLM as Cloud LLM (GPT, Claude, Gemini)
    
    Note over Client,Cloq: Local Machine (Private & Secure)
    Client->>Cloq: 1. API Request (with secrets)
    Note over Cloq: 2. Detect sensitive data<br/>3. Replace with [TAGS]
    Cloq->>LLM: 4. Forward sanitized request
    LLM-->>Cloq: 5. Response (with tags)
    Note over Cloq: 6. Restore real values locally
    Cloq-->>Client: 7. Return complete response
```

**Step by step:**

1. **Intercept** — Cloq captures the outgoing API request
2. **Detect** — A pipeline of detectors scans all text fields for sensitive data
3. **Tag** — Each detected entity gets a semantic tag: `[AWS_KEY_1]`, `[EMAIL_ADDRESS_1]`, `[INTERNAL_IP_1]`
4. **Forward** — The sanitized (safe) request goes to the cloud LLM
5. **Restore** — When the LLM responds, tags are replaced back with real values
6. **Return** — Your tool receives the complete, restored response

The same value always maps to the same tag within a session, so the LLM can reason about relationships ("use `[DB_HOST_1]` with `[AWS_KEY_1]`") without ever seeing the real data.

---

## ✨ Features

### 🔐 Detection Engine

Three pluggable detectors that run as a pipeline:

| Detector | What It Finds | Examples |
|:---|:---|:---|
| **Secrets** | API keys, tokens, credentials | AWS `AKIA...`, GitHub `ghp_...`, Stripe `sk_live_...`, Google `AIza...`, Slack `xox...`, JWTs, private keys (RSA/EC/PGP), connection strings (Postgres, MongoDB, Redis, JDBC) |
| **PII** | Personal data | Emails, phone numbers, credit cards (Visa/MC/Amex), SSNs, IBAN codes. Uses [Microsoft Presidio](https://github.com/microsoft/presidio) when installed, falls back to regex |
| **Network** | Infrastructure details | Private IPs (RFC 1918: `10.x`, `172.16-31.x`, `192.168.x`), IPv6 link-local, localhost, internal hostnames via configurable domain patterns |

Plus **entropy-based detection** for generic high-entropy strings that don't match known patterns.

### 🔄 Reversible Tagging

Not just `<REDACTED>` — Cloq uses **semantic, indexed tags** that preserve meaning for the LLM:

```
[AWS_ACCESS_KEY_1]    →  The LLM knows this is a credential
[INTERNAL_IP_1]       →  The LLM knows this is a host address
[EMAIL_ADDRESS_2]     →  The LLM can distinguish between two emails
```

Same value always maps to the same tag (idempotent within a session).

### 📡 Streaming Support

Full SSE streaming support with intelligent buffering — handles tags that are split across chunk boundaries. Adds < 50ms latency.

### 🔌 Plugin Architecture

Add your own detectors for organization-specific patterns:

```python
from cloq.detection.base import BaseDetector, DetectionResult

class MyDetector(BaseDetector):
    name = "my_detector"

    def detect(self, text: str) -> list[DetectionResult]:
        # Your custom detection logic
        ...
```

### 📋 Audit Logging

JSON Lines audit log that records **what type** of data was sanitized, but **never the actual values**:

```json
{"action":"sanitized","entity_type":"AWS_ACCESS_KEY","detector":"secrets","tag":"[AWS_ACCESS_KEY_1]","timestamp":"2025-07-15T10:30:00Z"}
```

---

## 🔌 Supported Providers

Works with **any** LLM provider. Just set the base URL to `http://localhost:8989`:

| Provider | Format | Status |
|:---|:---|:---:|
| **OpenAI** (GPT-4o, o1, o3) | `/v1/chat/completions` | ✅ |
| **Anthropic** (Claude 3.5/4) | `/v1/messages` | ✅ |
| **Google Gemini** | `:generateContent` | ✅ |
| **Azure OpenAI** | `/openai/deployments/*/chat/completions` | ✅ |
| **Groq** | OpenAI-compatible | ✅ |
| **Together AI** | OpenAI-compatible | ✅ |
| **Ollama** | OpenAI-compatible | ✅ |
| **Any OpenAI-compatible API** | `/v1/chat/completions` | ✅ |

---

## 🛠️ CLI Commands

Cloq features a rich interactive CLI. Run `cloq-cli` with no arguments to launch the interactive menu, or use the direct commands below:

```bash
# Core
cloq-cli start                  # Start the proxy server in terminal
cloq-cli status                 # Check if proxy is running + stats
cloq-cli version                # Show current version

# Diagnostics & Monitoring
cloq-cli doctor                 # Run system health checks and verify config
cloq-cli gain                   # View live token and cost savings from cache
cloq-cli dashboard              # Launch the live terminal HUD

# Utilities
cloq-cli scan path/to/file.py   # Scan a file for secrets (standalone)
cloq-cli test                   # Run a self-test with sample data
cloq-cli config init            # Generate a .cloq.yml template
```

Example scan output:

```
               Scan Results: credentials.env
┏━━━━┳━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━┳━━━━━━━━━━┓
┃ #  ┃ Type           ┃ Value                ┃ Score ┃ Detector ┃
┡━━━━╇━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━╇━━━━━━━━━━┩
│ 1  │ INTERNAL_IP    │ 10.0●●●●●●5432       │   95% │ network  │
│ 2  │ AWS_ACCESS_KEY │ AKIA●●●●●●●●●●●●MPLE │   98% │ secrets  │
│ 3  │ EMAIL_ADDRESS  │ dev@●●●●●●●.com      │   80% │ pii      │
└────┴────────────────┴──────────────────────┴───────┴──────────┘

  3 sensitive item(s) detected
  Scanned in 0.7ms
```

---

## ⚙️ Configuration

```bash
cloq config init   # Creates .cloq.yml in your project root
```

```yaml
# .cloq.yml
proxy:
  host: 127.0.0.1
  port: 8989

detection:
  secrets:
    enabled: true
    custom_patterns:
      - name: my_internal_token
        regex: "INT-[A-Z0-9]{32}"
        entity_type: INTERNAL_TOKEN
  pii:
    enabled: true
    confidence_threshold: 0.7
    entities: [EMAIL_ADDRESS, PHONE_NUMBER, CREDIT_CARD]
  network:
    enabled: true
    internal_domains:
      - "*.internal.mycompany.com"
      - "*.corp.mycompany.net"

allowlist:
  values: ["api.openai.com", "api.anthropic.com"]

logging:
  audit:
    enabled: true
    path: "~/.cloq/audit.log"
```

**Config priority** (highest wins): CLI flags → `CLOQ_*` env vars → `.cloq.yml` → `~/.config/cloq/config.yml` → defaults

---

## 🐍 Python API

Use Cloq as a library without the proxy:

```python
from cloq.detection.pipeline import DetectionPipeline
from cloq.detection.secrets import SecretsDetector
from cloq.detection.pii import PIIDetector
from cloq.detection.network import NetworkDetector
from cloq.sanitizer.engine import SanitizationSession, sanitize, restore

# Build a detection pipeline
pipeline = DetectionPipeline([
    SecretsDetector(),
    PIIDetector(),
    NetworkDetector(internal_domains=["*.internal.company.com"]),
])

# Detect + sanitize
text = "DB at 10.0.1.50:5432, key AKIAIOSFODNN7EXAMPLE, email dev@corp.com"
results, metrics = pipeline.run(text)

session = SanitizationSession(session_id="req-1")
sanitized = sanitize(text, results, session)
# → "DB at [INTERNAL_IP_1], key [AWS_ACCESS_KEY_1], email [EMAIL_ADDRESS_1]"

# After LLM responds, restore the real values
response = "[INTERNAL_IP_1] is healthy. Use [AWS_ACCESS_KEY_1] to connect."
restored = restore(response, session)
# → "10.0.1.50:5432 is healthy. Use AKIAIOSFODNN7EXAMPLE to connect."
```

---

## 🏢 Enterprise Value

| Concern | How Cloq Solves It |
|:---|:---|
| **Data leakage** | Sensitive data is replaced before it leaves the machine |
| **Compliance** | Audit log proves what was sanitized without storing secrets |
| **Zero trust** | Nothing goes to the cloud unredacted — ever |
| **No telemetry** | Cloq never phones home. Fully offline capable |
| **Custom policies** | Add organization-specific patterns and domain rules |
| **Developer experience** | Zero friction — one command, no code changes |

---

## 🛡️ Security Model

- **Local-only processing** — The proxy runs entirely on your machine
- **In-memory sessions** — Tag ↔ original mappings are never written to disk
- **Audit without secrets** — Logs record entity types and actions, never actual values
- **No telemetry** — Zero external network calls from Cloq itself
- **Minimal dependencies** — Small attack surface by design

See [SECURITY.md](SECURITY.md) for our vulnerability disclosure policy.

---

## 📦 Project Structure

```
src/cloq/
├── cli/           # Typer + Rich CLI (start, scan, status, test, config)
├── config/        # Pydantic v2 config schema + YAML/env loader
├── detection/     # Pluggable detector pipeline
│   ├── secrets.py # 15+ regex patterns + Shannon entropy
│   ├── pii.py     # Presidio integration + regex fallback
│   └── network.py # RFC 1918 IPs, internal hostnames
├── proxy/         # FastAPI + httpx async proxy server
│   ├── providers.py  # OpenAI, Anthropic, Google, Azure adapters
│   └── streaming.py  # SSE streaming with cross-boundary restoration
├── sanitizer/     # Reversible tag↔original engine + session store
└── logging/       # JSON Lines audit logger
```

---

## 🤝 Contributing

We welcome contributions of all kinds!

```bash
git clone https://github.com/CodeBase-X1/cloq.git
cd cloq
pip install -e ".[dev]"
make test     # Run 55 tests
make lint     # Ruff linting
make format   # Auto-format
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for full guidelines.

---

## 🗺️ Roadmap

- [x] Core detection engine (secrets, PII, network)
- [x] Reversible sanitization with semantic tags
- [x] Multi-provider proxy (OpenAI, Anthropic, Google, Azure)
- [x] SSE streaming support
- [x] CLI with Rich terminal output
- [ ] VS Code extension
- [ ] JetBrains plugin
- [ ] Local ML model integration (spaCy NER)
- [ ] Web dashboard for monitoring
- [ ] Docker image for team deployment
- [ ] GDPR/HIPAA compliance report generation

---

<div align="center">

**Apache 2.0** · Built by the [CodeBase-X1](https://github.com/CodeBase-X1) community

<sub>If Cloq helped you, consider giving it a ⭐</sub>

</div>
