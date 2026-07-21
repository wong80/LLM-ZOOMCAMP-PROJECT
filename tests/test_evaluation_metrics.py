"""Tests for evaluation metrics: hit rate and mean reciprocal rank."""

import pytest


class TestHitRate:
    def test_perfect_hit_rate(self):
        from app.evaluation import hit_rate
        results = [[True, False], [True, True], [False, True]]
        assert hit_rate(results) == 1.0

    def test_zero_hit_rate(self):
        from app.evaluation import hit_rate
        results = [[False, False], [False, False]]
        assert hit_rate(results) == 0.0

    def test_partial_hit_rate(self):
        from app.evaluation import hit_rate
        results = [[True, False], [False, False], [True, True]]
        assert hit_rate(results) == pytest.approx(2.0 / 3.0)


class TestMeanReciprocalRank:
    def test_perfect_mrr(self):
        from app.evaluation import mrr
        results = [[True, False], [False, True], [True, False]]
        assert mrr(results) == pytest.approx((1 + 0.5 + 1) / 3)

    def test_mrr_with_missing(self):
        from app.evaluation import mrr
        results = [[False, False], [False, True], [True, False]]
        assert mrr(results) == pytest.approx((0 + 0.5 + 1) / 3)

    def test_mrr_handles_mixed_lengths(self):
        from app.evaluation import mrr
        results = [[True], [False, False, True], [False, False, False, True]]
        assert mrr(results) == pytest.approx((1 + 1/3 + 1/4) / 3)
