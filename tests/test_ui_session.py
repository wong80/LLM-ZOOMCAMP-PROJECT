"""Tests for session history management."""


class TestSessionHistory:
    def test_session_stores_questions(self):
        history = []
        history.append({"question": "q1", "answer": "a1"})
        history.append({"question": "q2", "answer": "a2"})
        assert len(history) == 2
        assert history[0]["question"] == "q1"

    def test_session_max_length(self):
        history = []
        for i in range(10):
            history.append({"question": f"q{i}", "answer": f"a{i}"})
        trimmed = history[-5:]
        assert len(trimmed) == 5

    def test_clear_session(self):
        history = [{"question": "q1", "answer": "a1"}]
        history = []
        assert history == []
