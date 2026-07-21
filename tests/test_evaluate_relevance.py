"""Tests for inline relevance evaluation."""


class TestEvaluateRelevance:
    def test_returns_valid_label(self, mock_openai_response):
        from app.evaluation import evaluate_relevance
        label, tokens = evaluate_relevance("What is an API?", "An API is...")
        assert label in ("RELEVANT", "PARTLY_RELEVANT", "NON_RELEVANT")

    def test_returns_token_usage(self, mock_openai_response):
        from app.evaluation import evaluate_relevance
        label, tokens = evaluate_relevance("What is an API?", "An API is...")
        assert isinstance(tokens, dict)
        assert "total_tokens" in tokens
