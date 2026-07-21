"""Integration tests for Streamlit UI flow."""

import pytest


@pytest.mark.integration
class TestUiIntegration:
    def test_full_query_flow(self, mocker):
        from app.main import handle_question, render_answer, save_feedback
        mocker.patch("app.main.db.get_connection")
        mock_rag = mocker.patch("app.main.rag", return_value={
            "answer": "Use @app.get()",
            "citations": ["https://fastapi.tiangolo.com/"],
            "model": "gpt-4o-mini",
            "response_time": 0.8,
            "relevance": "RELEVANT",
            "total_tokens": 50,
            "prompt_tokens": 40,
            "completion_tokens": 10,
            "cost": 0.0005,
            "eval_tokens": {"prompt_tokens": 5, "completion_tokens": 3, "total_tokens": 8},
        })
        mock_save = mocker.patch("app.main.db.save_feedback")

        result = handle_question("How do I create a route?")
        assert result["answer"] == "Use @app.get()"

        html = render_answer(result)
        assert "Use @app.get()" in html

        save_feedback("conv-1", 1)
        mock_save.assert_called_once()
