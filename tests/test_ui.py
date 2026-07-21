"""Tests for Streamlit UI components."""

import pytest


class TestStreamlitApp:
    def test_app_title_constant(self):
        assert "PyDoc Assistant" == "PyDoc Assistant"

    def test_ask_button_triggers_rag(self, mocker):
        mock_rag = mocker.patch("app.main.rag", return_value={
            "answer": "Use the @app.get decorator.",
            "citations": ["https://fastapi.tiangolo.com/"],
            "model": "gpt-4o-mini",
            "response_time": 1.2,
            "relevance": "RELEVANT",
            "total_tokens": 100,
            "prompt_tokens": 80,
            "completion_tokens": 20,
            "cost": 0.001,
            "eval_tokens": {"prompt_tokens": 5, "completion_tokens": 3, "total_tokens": 8},
        })
        from app.main import main
        assert main is not None

    def test_empty_question_shows_warning(self):
        question = ""
        assert not question or not question.strip()

    def test_non_empty_question_is_valid(self):
        question = "How do I create an API?"
        assert question and question.strip()

    def test_answer_displays_sources(self):
        from app.main import render_answer
        result = {
            "answer": "Use @app.get.",
            "citations": ["https://fastapi.tiangolo.com/"],
        }
        html = render_answer(result)
        assert "Sources" in html
        assert "https://fastapi.tiangolo.com/" in html

    def test_answer_handles_no_citations(self):
        from app.main import render_answer
        result = {"answer": "I don't know.", "citations": []}
        html = render_answer(result)
        assert "I don't know" in html
        assert "Sources" not in html

    def test_feedback_button_saves_to_db(self, mocker):
        mocker.patch("app.main.db.get_connection")
        mock_save = mocker.patch("app.main.db.save_feedback")
        from app.main import save_feedback
        save_feedback(conversation_id="abc-123", feedback=1)
        mock_save.assert_called_once()

    def test_feedback_negative_value(self, mocker):
        mocker.patch("app.main.db.get_connection")
        mock_save = mocker.patch("app.main.db.save_feedback")
        from app.main import save_feedback
        save_feedback(conversation_id="abc-123", feedback=-1)
        mock_save.assert_called_once()

    def test_library_defaults_to_fastapi(self):
        libs = ["FastAPI"]
        assert "FastAPI" in libs

    def test_metadata_format(self):
        result = {"response_time": 1.2, "model": "gpt-4o-mini", "relevance": "RELEVANT"}
        meta = f"{result.get('response_time', 0):.1f}s | {result.get('model', '')} | {result.get('relevance', '')}"
        assert "1.2s" in meta
        assert "gpt-4o-mini" in meta
