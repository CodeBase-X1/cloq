"""Cloq — Local-first context sanitizer.

Cloak your secrets before they reach the cloud. Cloq is a lightweight
local proxy that detects and replaces sensitive data (API keys, PII,
internal IPs) with reversible synthetic tags before forwarding prompts
to cloud LLM providers.
"""

__version__ = "0.1.0"
__all__ = ["__version__"]
