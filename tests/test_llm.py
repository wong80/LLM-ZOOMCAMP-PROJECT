"""Tests for LLM call wrapper."""

import pytest
from unittest.mock import patch


class TestLlmCall:
    def test_returns_text_and_token_stats(self, mock_openai_response):
        from app.llm import llm
        text, tokens = llm("test prompt", model="gpt-4o-mini")
        assert isinstance(text, str)
        assert len(text) > 0
        assert "prompt_tokens" in tokens
        assert "completion_tokens" in tokens
        assert "total_tokens" in tokens

    def test_passes_model_name_to_api(self, mock_openai_client):
        from app.llm import llm
        llm("test", model="gpt-4o")
        mock_openai_client.responses.create.assert_called_with(
            model="gpt-4o",
            input=[{"role": "user", "content": "test"}]
        )

    def test_raises_on_api_error(self, mock_openai_client):
        mock_openai_client.responses.create.side_effect = RuntimeError("API error")
        from app.llm import llm
        with pytest.raises(RuntimeError, match="API error"):
            llm("test")
