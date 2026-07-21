import pytest


@pytest.mark.integration
class TestBonusIntegration:
    def test_full_pipeline_with_all_bonuses(self, mocker):
        """End-to-end: rewrite → search → rerank → RAG → answer."""
        from app.rag import rag_with_bonuses
        mocker.patch("app.rag.rewrite_query", return_value="improved query")
        mocker.patch("app.rag.hybrid_search", return_value=[{"id": "c1", "content": "test", "url": "https://e.com/"}])
        mocker.patch("app.rag.rerank", return_value=[{"id": "c1", "content": "test", "url": "https://e.com/"}])
        mocker.patch("app.rag.build_prompt", return_value="prompt")
        mocker.patch("app.rag.llm", return_value=("answer", {"total_tokens": 10}))
        mocker.patch("app.rag.evaluate_relevance", return_value=("RELEVANT", {"total_tokens": 5}))
        mocker.patch("app.rag.calculate_cost", return_value=0.001)
        result = rag_with_bonuses("dep inj in FastAPI")
        assert result["answer"] == "answer"
