import pytest


class TestQueryRewriting:
    def test_expands_abbreviations_directly(self):
        from app.search import rewrite_query
        cases = {
            "dep inj in FastAPI": "dependency injection",
            "how to do dep inj": "dependency injection",
            "path op example": "path operation",
            "req validation": "request validation",
            "resp model": "response model",
        }
        for raw, expected in cases.items():
            result = rewrite_query(raw, method="direct")
            assert expected in result.lower()

    def test_llm_rewrite_returns_string(self, mock_openai_response):
        from app.search import rewrite_query
        result = rewrite_query("how to dep inj", method="llm")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_rewrite_preserves_core_terms(self):
        from app.search import rewrite_query
        original = "How do I create a path operation?"
        result = rewrite_query(original, method="direct")
        assert "path operation" in result.lower() or "create" in result.lower()

    def test_rewrite_handles_empty_string(self):
        from app.search import rewrite_query
        assert rewrite_query("") == ""
        assert rewrite_query("   ").strip() == ""

    def test_rewrite_idempotent(self):
        from app.search import rewrite_query
        q = "dependency injection in FastAPI"
        result = rewrite_query(q, method="direct")
        assert result.lower() == q.lower()
