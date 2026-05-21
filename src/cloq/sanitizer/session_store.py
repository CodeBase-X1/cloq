"""Thread-safe session store with TTL-based auto-cleanup."""

from __future__ import annotations

import threading
import time
import uuid

from cloq.sanitizer.engine import SanitizationSession


class SessionStore:
    """Thread-safe store for managing sanitization sessions.

    Sessions are keyed by a unique request ID and automatically
    cleaned up after the configured TTL.

    Args:
        default_ttl: Default time-to-live in seconds for sessions.
            Defaults to ``3600`` (1 hour).
        tag_format: Default tag format for new sessions.
    """

    def __init__(
        self,
        default_ttl: int = 3600,
        tag_format: str = "[{entity_type}_{index}]",
    ) -> None:
        self._sessions: dict[str, tuple[SanitizationSession, float]] = {}
        self._lock = threading.Lock()
        self._default_ttl = default_ttl
        self._tag_format = tag_format

    def create(self, session_id: str | None = None) -> SanitizationSession:
        """Create and store a new sanitization session.

        Args:
            session_id: Optional custom ID.  A UUID is generated if omitted.

        Returns:
            The newly created :class:`SanitizationSession`.
        """
        sid = session_id or uuid.uuid4().hex
        session = SanitizationSession(session_id=sid, tag_format=self._tag_format)
        expiry = time.monotonic() + self._default_ttl

        with self._lock:
            self._sessions[sid] = (session, expiry)

        return session

    def get(self, session_id: str) -> SanitizationSession | None:
        """Retrieve a session by ID, or ``None`` if expired/missing."""
        with self._lock:
            entry = self._sessions.get(session_id)
            if entry is None:
                return None

            session, expiry = entry
            if time.monotonic() > expiry:
                del self._sessions[session_id]
                return None

            return session

    def remove(self, session_id: str) -> None:
        """Explicitly remove a session."""
        with self._lock:
            self._sessions.pop(session_id, None)

    def cleanup_expired(self) -> int:
        """Remove all expired sessions.

        Returns:
            Number of sessions removed.
        """
        now = time.monotonic()
        removed = 0

        with self._lock:
            expired_keys = [sid for sid, (_, expiry) in self._sessions.items() if now > expiry]
            for key in expired_keys:
                del self._sessions[key]
                removed += 1

        return removed

    @property
    def active_count(self) -> int:
        """Number of active (non-expired) sessions."""
        now = time.monotonic()
        with self._lock:
            return sum(1 for _, expiry in self._sessions.values() if now <= expiry)

    def __len__(self) -> int:
        return len(self._sessions)
