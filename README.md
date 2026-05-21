<div align="center">

<img src="assets/logo.png" width="180" alt="Cloq" />

# Cloq

**Your secrets stay local. Your LLM gets the context.**

Cloq is a lightweight local proxy that sits between your IDE and any cloud LLM.  
It detects API keys, PII, and internal IPs — replaces them with reversible tags — and restores them in the response. All on your machine.

[![CI](https://img.shields.io/github/actions/workflow/status/CodeBase-X1/cloq/ci.yml?branch=main&style=flat-square&logo=github&label=CI)](https://github.com/CodeBase-X1/cloq/actions)
[![PyPI](https://img.shields.io/pypi/v/cloq?style=flat-square&logo=pypi&logoColor=white&color=0ea5e9)](https://pypi.org/project/cloq)
[![Python](https://img.shields.io/pypi/pyversions/cloq?style=flat-square&logo=python&logoColor=white)](https://pypi.org/project/cloq)
[![License](https://img.shields.io/badge/license-Apache_2.0-green?style=flat-square)](LICENSE)
[![Stars](https://img.shields.io/github/stars/CodeBase-X1/cloq?style=flat-square&logo=github)](https://github.com/CodeBase-X1/cloq/stargazers)

</div>

---

## Why Cloq?

Developers paste secrets into LLM prompts every day — AWS keys, database URLs, internal IPs, customer emails. Most don't even realize it. Enterprise security teams do, and they block AI tools because of it.

Cloq solves this **without changing your workflow**.

```
Before → "Fix my DB at 10.0.1.50:5432 using key AKIAIOSFODNN7EXAMPLE"
After  → "Fix my DB at [INTERNAL_IP_1] using key [AWS_ACCESS_KEY_1]"
                                                    ↑ LLM sees this
Response restored locally before it reaches you ────┘
```

---

## Install

```bash
pip install cloq
```

## Quickstart

```bash
# 1. Start the proxy (runs on localhost:8989)
cloq start

# 2. Point your LLM client to Cloq instead
export OPENAI_BASE_URL=http://localhost:8989

# 3. Use your tools normally — Cloq handles the rest
```

That's it. No code changes. No new SDK. Just redirect your base URL.

---

## What gets detected

| Category | Examples |
|---|---|
| **Cloud keys** | AWS (`AKIA…`), Google (`AIza…`), GitHub (`ghp_…`), Stripe (`sk_live_…`), Slack tokens |
| **PII** | Emails, phone numbers, credit cards, SSNs |
| **Infrastructure** | Private IPs (RFC 1918), internal hostnames, DB connection strings, JWTs |
| **Generic secrets** | High-entropy strings, private keys (RSA/EC/PGP), `.env`-style assignments |

Custom patterns are supported via `.cloq.yml`.

---

## Supported providers

Works with any provider — just set the base URL:

| Provider | Base URL to set |
|---|---|
| OpenAI | `http://localhost:8989` |
| Anthropic | `http://localhost:8989` |
| Google Gemini | `http://localhost:8989` |
| Azure OpenAI | `http://localhost:8989` |
| Groq / Together / Ollama | `http://localhost:8989` |

---

## More commands

```bash
# Scan a file for secrets without running the proxy
cloq scan path/to/file.py

# Check if the proxy is running
cloq status

# Generate a config file
cloq config init

# Run a self-test
cloq test
```

---

## Configuration

```bash
cloq config init   # creates .cloq.yml in your project root
```

```yaml
# .cloq.yml
proxy:
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
  network:
    enabled: true
    internal_domains:
      - "*.internal.mycompany.com"
```

Config resolves in this order (highest wins): CLI flags → `CLOQ_*` env vars → `.cloq.yml` → defaults.

---

## Use as a library

```python
from cloq.detection.pipeline import DetectionPipeline
from cloq.detection.secrets import SecretsDetector
from cloq.detection.pii import PIIDetector
from cloq.sanitizer.engine import SanitizationSession, sanitize, restore

pipeline = DetectionPipeline([SecretsDetector(), PIIDetector()])

text = "Email dev@corp.com, key AKIAIOSFODNN7EXAMPLE"
results, _ = pipeline.run(text)

session = SanitizationSession(session_id="req-1")
clean = sanitize(text, results, session)
# → "Email [EMAIL_ADDRESS_1], key [AWS_ACCESS_KEY_1]"

# After LLM responds, restore the real values
original = restore(clean, session)
```

---

## Security model

- **Nothing leaves your machine unredacted.** The proxy runs entirely locally.
- **In-memory only.** Tag-to-original mappings are never written to disk.
- **Audit log records actions, never values.** You can prove compliance without storing secrets.
- **No telemetry.** Cloq never phones home.

---

## Contributing

```bash
git clone https://github.com/CodeBase-X1/cloq.git
cd cloq
pip install -e ".[dev]"
make test
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

<div align="center">
<sub>Apache 2.0 · Built by the <a href="https://github.com/CodeBase-X1">CodeBase-X1</a> community</sub>
</div>
