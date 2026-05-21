"""Pydantic v2 configuration schema for Cloq."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field


class ProxyConfig(BaseModel):
    """Proxy server settings."""

    host: str = Field(default="127.0.0.1", description="Bind address")
    port: int = Field(default=8989, ge=1, le=65535, description="Bind port")
    workers: int = Field(default=1, ge=1, description="Number of uvicorn workers")
    log_level: str = Field(default="info", description="Uvicorn log level")


class CustomPattern(BaseModel):
    """A user-defined regex pattern for secret detection."""

    name: str = Field(description="Human-readable name for this pattern")
    regex: str = Field(description="Regular expression pattern")
    entity_type: str = Field(description="Entity type label (e.g., INTERNAL_TOKEN)")
    confidence: float = Field(default=0.90, ge=0.0, le=1.0)


class SecretsConfig(BaseModel):
    """Configuration for the secrets detector."""

    enabled: bool = True
    entropy_threshold: float = Field(default=4.5, ge=0.0, le=8.0)
    min_entropy_length: int = Field(default=20, ge=1)
    custom_patterns: list[CustomPattern] = Field(default_factory=list)


class PIIConfig(BaseModel):
    """Configuration for the PII detector."""

    enabled: bool = True
    confidence_threshold: float = Field(default=0.5, ge=0.0, le=1.0)
    language: str = Field(default="en")
    entities: list[str] = Field(
        default_factory=lambda: [
            "EMAIL_ADDRESS",
            "PHONE_NUMBER",
            "CREDIT_CARD",
            "US_SSN",
        ]
    )


class NetworkConfig(BaseModel):
    """Configuration for the network detector."""

    enabled: bool = True
    detect_localhost: bool = True
    internal_domains: list[str] = Field(
        default_factory=list,
        description="Glob patterns for internal domains (e.g., *.internal.company.com)",
    )


class DetectionConfig(BaseModel):
    """Top-level detection configuration."""

    secrets: SecretsConfig = Field(default_factory=SecretsConfig)
    pii: PIIConfig = Field(default_factory=PIIConfig)
    network: NetworkConfig = Field(default_factory=NetworkConfig)


class SanitizerConfig(BaseModel):
    """Sanitizer engine settings."""

    tag_format: str = Field(
        default="[{entity_type}_{index}]",
        description="Template for generating synthetic tags",
    )
    session_ttl_seconds: int = Field(
        default=3600,
        ge=60,
        description="Session time-to-live in seconds",
    )


class AllowlistConfig(BaseModel):
    """Values and patterns to never sanitize."""

    values: list[str] = Field(
        default_factory=lambda: ["api.openai.com", "api.anthropic.com"],
        description="Exact strings to exclude from sanitization",
    )
    patterns: list[str] = Field(
        default_factory=list,
        description="Regex patterns to exclude from sanitization",
    )


class AuditConfig(BaseModel):
    """Audit logging settings."""

    enabled: bool = True
    path: str = Field(
        default="~/.cloq/audit.log",
        description="Path to the audit log file",
    )
    max_size_mb: int = Field(default=50, ge=1, description="Max log file size in MB")
    backup_count: int = Field(default=5, ge=0, description="Number of rotated log files to keep")


class LoggingConfig(BaseModel):
    """Logging configuration."""

    level: str = Field(default="INFO", description="Log level (DEBUG, INFO, WARNING, ERROR)")
    audit: AuditConfig = Field(default_factory=AuditConfig)


class CloqConfig(BaseModel):
    """Root configuration model for Cloq.

    This is the top-level configuration object that aggregates all
    subsystem configurations.  It can be loaded from YAML files,
    environment variables, or CLI flags.
    """

    proxy: ProxyConfig = Field(default_factory=ProxyConfig)
    detection: DetectionConfig = Field(default_factory=DetectionConfig)
    sanitizer: SanitizerConfig = Field(default_factory=SanitizerConfig)
    allowlist: AllowlistConfig = Field(default_factory=AllowlistConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)

    def to_yaml_path(self, path: str | Path) -> None:
        """Write this config to a YAML file."""
        import yaml

        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            yaml.dump(
                self.model_dump(),
                f,
                default_flow_style=False,
                sort_keys=False,
            )
