"""Tests for PostgreSQL database operations."""

from datetime import datetime, timezone

import pytest


ALL_COLUMNS = [
    "id", "question", "answer", "model_used", "response_time",
    "relevance", "prompt_tokens", "completion_tokens", "total_tokens",
    "eval_prompt_tokens", "eval_completion_tokens", "eval_total_tokens",
    "openai_cost", "timestamp",
]


class TestDatabaseSchema:
    def test_create_conversations_table(self, db_connection):
        cursor = db_connection.cursor()
        cursor.execute("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'conversations'
        """)
        columns = {row[0]: row[1] for row in cursor.fetchall()}
        for col in ALL_COLUMNS:
            assert col in columns, f"Missing column: {col}"

    def test_create_feedback_table(self, db_connection):
        cursor = db_connection.cursor()
        cursor.execute("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'feedback'
        """)
        columns = {row[0] for row in cursor.fetchall()}
        assert "conversation_id" in columns
        assert "feedback" in columns
        assert "timestamp" in columns


class TestConversationCrud:
    def test_save_and_retrieve_conversation(self, db_connection):
        from app.db import save_conversation, get_conversation
        conv = {
            "id": "test-1",
            "question": "What is FastAPI?",
            "answer": "FastAPI is a web framework.",
            "model_used": "gpt-4o-mini",
            "response_time": 1.5,
            "relevance": "RELEVANT",
            "prompt_tokens": 50,
            "completion_tokens": 30,
            "total_tokens": 80,
            "eval_prompt_tokens": 10,
            "eval_completion_tokens": 5,
            "eval_total_tokens": 15,
            "openai_cost": 0.001,
            "timestamp": datetime.now(timezone.utc),
        }
        save_conversation(db_connection, conv)
        cursor = db_connection.cursor()
        cursor.fetchone.return_value = tuple(conv.get(c) for c in ALL_COLUMNS)
        retrieved = get_conversation(db_connection, "test-1")
        for col in ALL_COLUMNS:
            assert col in retrieved, f"Missing key: {col}"
            assert retrieved[col] == conv[col], f"Mismatch for {col}"

    def test_save_duplicate_conversation_id_raises(self, db_connection):
        from app.db import save_conversation
        conv = {"id": "dup-1", "question": "q", "answer": "a", "model_used": "gpt-4o-mini",
                "response_time": 0.5, "relevance": "RELEVANT", "prompt_tokens": 10,
                "completion_tokens": 5, "total_tokens": 15, "eval_prompt_tokens": 0,
                "eval_completion_tokens": 0, "eval_total_tokens": 0,
                "openai_cost": 0.0001, "timestamp": datetime.now(timezone.utc)}
        cursor = db_connection.cursor()
        cursor.execute.side_effect = None
        save_conversation(db_connection, conv)
        cursor.execute.side_effect = Exception("duplicate key")
        with pytest.raises(Exception):
            save_conversation(db_connection, conv)


class TestFeedbackCrud:
    def test_save_feedback_without_conversation_raises(self, db_connection):
        from app.db import save_feedback
        cursor = db_connection.cursor()
        cursor.execute.side_effect = Exception("foreign key violation")
        with pytest.raises(Exception):
            save_feedback(db_connection, "nonexistent", 1)

    def test_save_feedback(self, db_connection):
        from app.db import save_feedback, get_feedback
        from tests.conftest import BASE_CONV
        cursor = db_connection.cursor()
        cursor.execute.side_effect = None
        from app.db import save_conversation
        save_conversation(db_connection, {**BASE_CONV, "id": "fb-test-1"})
        save_feedback(db_connection, "fb-test-1", 1)
        cursor.fetchone.return_value = (1,)
        feedback = get_feedback(db_connection, "fb-test-1")
        assert feedback == 1

    def test_feedback_positive_and_negative(self, db_connection):
        from app.db import save_feedback, get_feedback
        from tests.conftest import BASE_CONV
        from app.db import save_conversation
        cursor = db_connection.cursor()
        cursor.execute.side_effect = None
        for fid, val in [("pos", 1), ("neg", -1)]:
            save_conversation(db_connection, {**BASE_CONV, "id": fid})
            save_feedback(db_connection, fid, val)
            cursor.fetchone.return_value = (val,)
            assert get_feedback(db_connection, fid) == val
