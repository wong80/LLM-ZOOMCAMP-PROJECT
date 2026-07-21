"""Smoke tests: verify evaluation notebooks load without error."""


class TestEvaluationNotebooks:
    def test_ground_truth_module_imports(self):
        from notebooks.ground_truth import generate_question, generate_ground_truth
        assert callable(generate_question)
        assert callable(generate_ground_truth)

    def test_retrieval_eval_imports(self):
        from app.evaluation import hit_rate, mrr, evaluate_retrieval, optimize_boosts
        assert callable(hit_rate)
        assert callable(mrr)
        assert callable(evaluate_retrieval)
        assert callable(optimize_boosts)

    def test_rag_eval_imports(self):
        from app.evaluation import evaluate_relevance, compare_models, comparison_summary
        assert callable(evaluate_relevance)
        assert callable(compare_models)
        assert callable(comparison_summary)
