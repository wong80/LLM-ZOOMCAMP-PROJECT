def _hit_rate(ground_truth, search_fn):
    if not ground_truth:
        return 0.0
    hits = 0
    for item in ground_truth:
        results = search_fn(item["question"])
        ids = {r["id"] for r in results}
        if item["relevant_chunk_id"] in ids:
            hits += 1
    return hits / len(ground_truth)


class TestHybridBonus:
    def test_hybrid_outperforms_keyword(self, sample_index, sample_ground_truth):
        from app.search import keyword_search, hybrid_search
        kw_hr = _hit_rate(sample_ground_truth, lambda q: keyword_search(q, index=sample_index))
        hy_hr = _hit_rate(sample_ground_truth, lambda q: hybrid_search(q, method="hybrid", index=sample_index))
        assert hy_hr >= kw_hr, f"Hybrid HR ({hy_hr}) < Keyword HR ({kw_hr})"

    def test_hybrid_outperforms_vector(self, sample_embeddings, sample_ground_truth):
        from app.search import vector_search, hybrid_search
        vec_hr = _hit_rate(sample_ground_truth, lambda q: vector_search(q, embeddings=sample_embeddings))
        hy_hr = _hit_rate(sample_ground_truth, lambda q: hybrid_search(q, method="hybrid", embeddings=sample_embeddings))
        assert hy_hr >= vec_hr, f"Hybrid HR ({hy_hr}) < Vector HR ({vec_hr})"

    def test_rrf_fusion_combines_results(self, sample_index, sample_embeddings):
        from app.search import keyword_search, vector_search, hybrid_search
        kw_ids = {r["id"] for r in keyword_search("path operation", index=sample_index, num_results=20)}
        vec_ids = {r["id"] for r in vector_search("path operation", embeddings=sample_embeddings, num_results=20)}
        hy_ids = {r["id"] for r in hybrid_search("path operation", method="hybrid", index=sample_index, embeddings=sample_embeddings, num_results=20)}
        assert kw_ids & vec_ids <= hy_ids
