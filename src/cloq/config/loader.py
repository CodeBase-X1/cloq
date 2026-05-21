"""Configuration loader — resolves config from files, env vars, and defaults."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

from cloq.config.schema import CloqConfig

# ── Config file search paths (highest to lowest priority) ────────────
_CONFIG_FILENAMES = [".cloq.yml", ".cloq.yaml"]
_USER_CONFIG_DIR = Path("~/.config/cloq").expanduser()
_ENV_PREFIX = "CLOQ_"


def _find_project_config() -> Path | None:
    """Search upward from CWD for a project-level config file."""
    current = Path.cwd()
    for _ in range(20):  # Safety limit
        for name in _CONFIG_FILENAMES:
            candidate = current / name
            if candidate.is_file():
                return candidate
        parent = current.parent
        if parent == current:
            break
        current = parent
    return None


def _find_user_config() -> Path | None:
    """Check for a user-level config file."""
    for name in _CONFIG_FILENAMES:
        candidate = _USER_CONFIG_DIR / name
        if candidate.is_file():
            return candidate
    # Also check config.yml
    candidate = _USER_CONFIG_DIR / "config.yml"
    if candidate.is_file():
        return candidate
    return None


def _load_yaml(path: Path) -> dict[str, Any]:
    """Load and parse a YAML file."""
    with open(path) as f:
        data = yaml.safe_load(f)
    return data if isinstance(data, dict) else {}


def _deep_merge(base: dict, override: dict) -> dict:
    """Recursively merge *override* into *base* (override wins)."""
    result = dict(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _env_overrides() -> dict[str, Any]:
    """Collect config overrides from environment variables.

    Supports flat ``CLOQ_PROXY__PORT=9090`` style env vars,
    where ``__`` denotes nesting.
    """
    overrides: dict[str, Any] = {}

    for key, value in os.environ.items():
        if not key.startswith(_ENV_PREFIX):
            continue
        # Strip prefix, lowercase, split on __
        parts = key[len(_ENV_PREFIX) :].lower().split("__")

        # Build nested dict
        current = overrides
        for part in parts[:-1]:
            current = current.setdefault(part, {})

        # Try to parse as int/float/bool
        final_key = parts[-1]
        if value.lower() in ("true", "yes", "1"):
            current[final_key] = True
        elif value.lower() in ("false", "no", "0"):
            current[final_key] = False
        else:
            try:
                current[final_key] = int(value)
            except ValueError:
                try:
                    current[final_key] = float(value)
                except ValueError:
                    current[final_key] = value

    return overrides


def load_config(
    config_path: str | Path | None = None,
    cli_overrides: dict[str, Any] | None = None,
) -> CloqConfig:
    """Load Cloq configuration with the following priority (highest wins):

    1. CLI flags (``cli_overrides``)
    2. Environment variables (``CLOQ_*``)
    3. Explicit config file (``config_path``)
    4. Project-level ``.cloq.yml`` (found by searching upward from CWD)
    5. User-level ``~/.config/cloq/config.yml``
    6. Built-in defaults

    Args:
        config_path: Explicit path to a YAML config file.
        cli_overrides: Dictionary of overrides from CLI flags.

    Returns:
        A fully resolved :class:`CloqConfig` instance.
    """
    config_data: dict[str, Any] = {}

    # 5. User-level config (lowest priority file)
    user_config = _find_user_config()
    if user_config:
        config_data = _deep_merge(config_data, _load_yaml(user_config))

    # 4. Project-level config
    project_config = _find_project_config()
    if project_config:
        config_data = _deep_merge(config_data, _load_yaml(project_config))

    # 3. Explicit config file
    if config_path:
        path = Path(config_path)
        if path.is_file():
            config_data = _deep_merge(config_data, _load_yaml(path))

    # 2. Environment variables
    env_data = _env_overrides()
    if env_data:
        config_data = _deep_merge(config_data, env_data)

    # 1. CLI overrides (highest priority)
    if cli_overrides:
        config_data = _deep_merge(config_data, cli_overrides)

    return CloqConfig(**config_data)
