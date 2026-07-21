"""Tests for LLM-as-judge evaluation and model comparison."""

import pytest


class TestLlmEvaluation:
    def test_judge_returns_valid_classification(self, mock_openai_response):
        from app.evaluation import evaluate_relevance
        label, _ = evaluate_relevance("What is an API?", "An API is an application programming interface.")
        assert label in ("RELEVANT", "PARTLY_RELEVANT", "NON_RELEVANT")

    def test_judge_detects_non_relevance(self, mock_openai_response):
        mock_openai_response.output_text = '{"relevance": "NON_RELEVANT", "reason": "Unrelated answer."}'
        from app.evaluation import evaluate_relevance
        label, _ = evaluate_relevance("How do I create a path operation?", "The weather is nice today.")
        assert label == "NON_RELEVANT"

    def test_compare_models_produces_comparison_table(self, mocker):
        from app.evaluation import compare_models
        mocker.patch("app.evaluation.evaluate_relevance", return_value=("RELEVANT", {"total_tokens": 10}))
        mocker.patch("app.rag.rag", return_value={
            "answer": "test", "citations": [], "model": "gpt-4o-mini",
            "response_time": 0.5, "relevance": "RELEVANT", "cost": 0.001,
            "total_tokens": 10,
        })
        results = compare_models(
            questions=["What is an API?", "How do I route?"],
            models=["gpt-4o-mini", "gpt-4o"],
        )
        assert "model" in results.columns
        assert "relevance" in results.columns
        assert len(results) == 4

    def test_comparison_summary_includes_cost(self, mocker):
        from app.evaluation import comparison_summary
        import pandas as pd
        df = pd.DataFrame({
            "model": ["gpt-4o-mini", "gpt-4o"],
            "relevance": ["RELEVANT", "PARTLY_RELEVANT"],
            "cost": [0.001, 0.01],
        })
        summary = comparison_summary(df)
        assert "% RELEVANT" in summary.columns
        assert "Cost per 1K queries" in summary.columns
