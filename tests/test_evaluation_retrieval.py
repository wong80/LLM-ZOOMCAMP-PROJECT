"""Tests for retrieval evaluation."""


class TestRetrievalEvaluation:
    def test_evaluate_retrieval_returns_metrics(self, sample_ground_truth):
        from app.evaluation import evaluate_retrieval
        metrics = evaluate_retrieval(sample_ground_truth, lambda q: [{"id": gt["relevant_chunk_id"]} for gt in sample_ground_truth[:1]])
        assert "hit_rate" in metrics
        assert "mrr" in metrics
        assert 0.0 <= metrics["hit_rate"] <= 1.0
        assert 0.0 <= metrics["mrr"] <= 1.0

    def test_boost_optimization_improves_hit_rate(self, sample_index, sample_ground_truth):
        from app.evaluation import evaluate_retrieval, optimize_boosts
        from app.search import keyword_search
        baseline = evaluate_retrieval(sample_ground_truth, lambda q: keyword_search(q, index=sample_index))
        best_params = optimize_boosts(sample_index, sample_ground_truth, iterations=10)
        optimized = evaluate_retrieval(sample_ground_truth, lambda q: keyword_search(q, index=sample_index, boost_dict=best_params))
        assert optimized["hit_rate"] >= baseline["hit_rate"]

    def test_evaluate_retrieval_with_perfect_search(self, sample_ground_truth):
        from app.evaluation import evaluate_retrieval
        gt_map = {gt["question"]: gt["relevant_chunk_id"] for gt in sample_ground_truth}
        perfect_search = lambda q: [{"id": gt_map[q]}]
        metrics = evaluate_retrieval(sample_ground_truth, perfect_search)
        assert metrics["hit_rate"] == 1.0
        assert metrics["mrr"] == 1.0
