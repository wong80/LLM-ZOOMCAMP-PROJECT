"""Integration tests for Streamlit UI flow."""

import pytest


@pytest.mark.integration
class TestUiIntegration:
    def test_render_answer_with_citations(self):
        from app.main import render_answer
        html = render_answer({"answer": "Use @app.get()", "citations": ["https://fastapi.tiangolo.com/"]})
        assert "Use @app.get()" in html
        assert "Sources" in html

    def test_save_feedback_flow(self, mocker):
        mocker.patch("app.main.db.get_connection")
        mock_save = mocker.patch("app.main.db.save_feedback")
        from app.main import save_feedback
        save_feedback("conv-1", 1)
        mock_save.assert_called_once()
