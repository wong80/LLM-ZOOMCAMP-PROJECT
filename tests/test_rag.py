"""Tests for RAG flow: prompt builder and end-to-end pipeline."""

import pytest


class TestBuildPrompt:
    def test_includes_query_and_context(self):
        from app.rag import build_prompt
        query = "How do I create a path operation?"
        chunks = [
            {"title": "Path Operation", "content": "A path operation is...", "url": "https://example.com/"},
        ]
        prompt = build_prompt(query, chunks)
        assert query in prompt
        assert "Path Operation" in prompt
        assert "A path operation is..." in prompt
        assert "https://example.com/" in prompt

    def test_includes_citation_instruction(self):
        from app.rag import build_prompt
        prompt = build_prompt("test", [{"title": "T", "content": "C", "url": "https://e.com/"}])
        assert "cite" in prompt.lower()

    def test_handles_empty_chunks(self):
        from app.rag import build_prompt
        prompt = build_prompt("test", [])
        assert "test" in prompt
        assert "don't have enough information" in prompt.lower()


class TestRagFlow:
    def test_rag_returns_expected_keys(self, mocker):
        from app.rag import rag
        mocker.patch("app.rag.search", return_value=[{"id": "c1", "url": "https://e.com/"}])
        mocker.patch("app.rag.build_prompt", return_value="test prompt")
        mocker.patch("app.rag.llm", return_value=("test answer", {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}))
        mocker.patch("app.rag.evaluate_relevance", return_value=("RELEVANT", {"prompt_tokens": 5, "completion_tokens": 3, "total_tokens": 8}))
        mocker.patch("app.rag.calculate_cost", return_value=0.001)
        result = rag("test query")
        assert "answer" in result
        assert "citations" in result
        assert "model" in result
        assert "response_time" in result
        assert "relevance" in result
        assert "cost" in result

    def test_rag_citations_match_search_results(self, mocker):
        from app.rag import rag
        expected_citations = [{"id": "c1", "url": "https://e1.com/"}, {"id": "c2", "url": "https://e2.com/"}]
        mocker.patch("app.rag.search", return_value=expected_citations)
        mocker.patch("app.rag.build_prompt", return_value="prompt")
        mocker.patch("app.rag.llm", return_value=("answer", {"total_tokens": 10}))
        mocker.patch("app.rag.evaluate_relevance", return_value=("RELEVANT", {"total_tokens": 5}))
        mocker.patch("app.rag.calculate_cost", return_value=0.001)
        result = rag("test")
        assert len(result["citations"]) == len(expected_citations)

    def test_rag_response_time_is_positive(self, mocker):
        from app.rag import rag
        mocker.patch("app.rag.search", return_value=[{"id": "c1", "url": "https://e.com/"}])
        mocker.patch("app.rag.build_prompt", return_value="prompt")
        mocker.patch("app.rag.llm", return_value=("answer", {"total_tokens": 10}))
        mocker.patch("app.rag.evaluate_relevance", return_value=("RELEVANT", {"total_tokens": 5}))
        mocker.patch("app.rag.calculate_cost", return_value=0.001)
        result = rag("test")
        assert result["response_time"] >= 0
