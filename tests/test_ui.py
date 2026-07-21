"""Tests for Streamlit UI components."""

import pytest


class TestStreamlitApp:
    def test_app_renders_title(self, streamlit_app):
        from app.main import show_title
        title = show_title()
        assert "PyDoc Assistant" in title

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
        from app.main import handle_question
        result = handle_question("How do I create a path operation?")
        mock_rag.assert_called_once_with("How do I create a path operation?")
        assert "answer" in result

    def test_empty_question_shows_warning(self):
        from app.main import validate_question
        is_valid, message = validate_question("")
        assert not is_valid
        assert "Please enter a question" in message

    def test_non_empty_question_is_valid(self):
        from app.main import validate_question
        is_valid, message = validate_question("How do I create an API?")
        assert is_valid
        assert message == ""

    def test_answer_displays_sources(self, streamlit_app):
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

    def test_library_selector_defaults_to_fastapi(self):
        from app.main import get_library_selector
        libs, default = get_library_selector()
        assert "FastAPI" in libs
        assert default == "FastAPI"

    def test_metadata_bar_displays_info(self):
        from app.main import render_metadata
        result = {"response_time": 1.2, "model": "gpt-4o-mini", "relevance": "RELEVANT"}
        html = render_metadata(result)
        assert "1.2s" in html
        assert "gpt-4o-mini" in html
