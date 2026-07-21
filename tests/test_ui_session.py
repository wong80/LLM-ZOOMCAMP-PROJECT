"""Tests for session history management."""

import pytest


class TestSessionHistory:
    def test_session_stores_questions(self, streamlit_app):
        from app.main import SessionManager
        sm = SessionManager()
        sm.add_conversation("q1", "a1")
        sm.add_conversation("q2", "a2")
        assert len(sm.get_history()) == 2
        assert sm.get_history()[0]["question"] == "q1"

    def test_session_max_length(self, streamlit_app):
        from app.main import SessionManager
        sm = SessionManager(max_length=5)
        for i in range(10):
            sm.add_conversation(f"q{i}", f"a{i}")
        assert len(sm.get_history()) == 5

    def test_clear_session(self, streamlit_app):
        from app.main import SessionManager
        sm = SessionManager()
        sm.add_conversation("q1", "a1")
        sm.clear()
        assert sm.get_history() == []
