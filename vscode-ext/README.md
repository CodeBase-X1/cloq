# Cloq: Local-First LLM Sanitization Proxy

**Your secrets stay local. Your LLM gets the context.**

This VS Code extension automatically starts the [Cloq proxy](https://github.com/CodeBase-X1/cloq) in the background whenever you open your editor, providing seamless, invisible protection for all your AI coding assistants (like Copilot, Continue.dev, and Cursor).

## Features

- 🛡️ **Zero-Config Protection**: Automatically intercepts and masks API keys, PII, and internal network IPs before they ever leave your machine.
- ⚡ **Prompt Caching**: Normalizes prompts to increase cache hit rates with external LLMs, cutting your token usage by up to 80%.
- 📊 **Live Dashboard**: Click the Cloq icon in your status bar to instantly see real-time metrics on tokens saved and entities protected.
- 🤖 **Universal Compatibility**: Works with OpenAI, Anthropic, Gemini, Groq, and any OpenAI-compatible endpoint.

## Quick Start

1. Install this extension.
2. Ensure you have the `cloq` Python package installed globally on your machine:
   ```bash
   pip install cloq
   ```
3. Open your VS Code AI extension (e.g., Continue.dev) and set the **Base URL** to `http://127.0.0.1:8989/v1`.

You are now fully protected.

## Status Bar Indicators
- `(spin) Cloq Starting...` - The proxy is booting up.
- `(shield) Cloq Active` - The proxy is actively protecting your traffic.
- `(error) Cloq Stopped` - The proxy failed to start (ensure `cloq` is in your PATH).

*Click the status bar item to open the live web dashboard!*
