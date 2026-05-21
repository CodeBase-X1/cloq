"""Tests for the session store."""

import time

from cloq.sanitizer.session_store import SessionStore


class TestSessionStore:
    def test_create_and_get(self, session_store):
        session = session_store.create()
        retrieved = session_store.get(session.session_id)
        assert retrieved is not None
        assert retrieved.session_id == session.session_id

    def test_get_missing_returns_none(self, session_store):
        assert session_store.get("nonexistent") is None

    def test_remove(self, session_store):
        session = session_store.create()
        session_store.remove(session.session_id)
        assert session_store.get(session.session_id) is None

    def test_active_count(self, session_store):
        session_store.create()
        session_store.create()
        assert session_store.active_count == 2

    def test_expired_session_returns_none(self):
        store = SessionStore(default_ttl=0)
        session = store.create()
        time.sleep(0.01)
        assert store.get(session.session_id) is None
