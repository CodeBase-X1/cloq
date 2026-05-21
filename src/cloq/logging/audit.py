"""Local-only audit logger — records sanitization events without storing sensitive values."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any


class AuditLogger:
    """Local audit trail for sanitization and restoration events.

    Records *what* was sanitized (entity type, detector, action) but
    **never** the actual sensitive value.  Output is JSON Lines format
    for easy parsing and ingestion.

    Args:
        log_path: Path to the audit log file.
        max_bytes: Maximum log file size before rotation (default 50MB).
        backup_count: Number of rotated log files to keep.
        enabled: Whether audit logging is active.
    """

    def __init__(
        self,
        log_path: str = "~/.cloq/audit.log",
        max_bytes: int = 50 * 1024 * 1024,
        backup_count: int = 5,
        enabled: bool = True,
    ) -> None:
        self._enabled = enabled
        self._logger = logging.getLogger("cloq.audit")
        self._logger.setLevel(logging.INFO)
        self._logger.propagate = False

        if enabled:
            path = Path(log_path).expanduser()
            path.parent.mkdir(parents=True, exist_ok=True)

            handler = RotatingFileHandler(
                filename=str(path),
                maxBytes=max_bytes,
                backupCount=backup_count,
                encoding="utf-8",
            )
            handler.setFormatter(logging.Formatter("%(message)s"))
            self._logger.addHandler(handler)

    def log_sanitization(
        self,
        session_id: str,
        entity_type: str,
        detector_name: str,
        tag: str,
    ) -> None:
        """Record a sanitization event.

        Args:
            session_id: The session identifier.
            entity_type: Type of entity detected (e.g., ``AWS_KEY``).
            detector_name: Name of the detector that found it.
            tag: The synthetic tag used (e.g., ``[AWS_KEY_1]``).

        Note:
            The actual sensitive value is **never** recorded.
        """
        if not self._enabled:
            return

        self._write_event(
            {
                "action": "sanitized",
                "session_id": session_id,
                "entity_type": entity_type,
                "detector": detector_name,
                "tag": tag,
            }
        )

    def log_restoration(
        self,
        session_id: str,
        entity_type: str,
        tag: str,
    ) -> None:
        """Record a restoration event.

        Args:
            session_id: The session identifier.
            entity_type: Type of entity restored.
            tag: The synthetic tag that was replaced.
        """
        if not self._enabled:
            return

        self._write_event(
            {
                "action": "restored",
                "session_id": session_id,
                "entity_type": entity_type,
                "tag": tag,
            }
        )

    def log_request(
        self,
        session_id: str,
        provider: str,
        entities_count: int,
        duration_ms: float,
    ) -> None:
        """Record a proxy request summary.

        Args:
            session_id: The session identifier.
            provider: The LLM provider name.
            entities_count: Number of entities sanitized.
            duration_ms: Total processing time in milliseconds.
        """
        if not self._enabled:
            return

        self._write_event(
            {
                "action": "request",
                "session_id": session_id,
                "provider": provider,
                "entities_sanitized": entities_count,
                "duration_ms": round(duration_ms, 2),
            }
        )

    def _write_event(self, event: dict[str, Any]) -> None:
        """Write a JSON event to the audit log."""
        event["timestamp"] = datetime.now(timezone.utc).isoformat()
        self._logger.info(json.dumps(event, separators=(",", ":")))
