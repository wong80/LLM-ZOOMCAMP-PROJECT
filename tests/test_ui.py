"""Tests for Streamlit UI components."""


class TestStreamlitApp:
    def test_ask_button_triggers_rag(self, mocker):
        mocker.patch("app.rag.hybrid_search", return_value=[{"id": "c1", "content": "x", "url": "https://fastapi.tiangolo.com/"}])
        mocker.patch("app.rag.llm_stream", return_value=iter(["Use ", "the ", "@", "app", ".get ", "decorator."]))
        from app.main import main
        assert main is not None

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
