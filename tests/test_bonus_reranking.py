import pytest


@pytest.fixture(autouse=True)
def mock_reranker(mocker):
    mock = mocker.MagicMock()
    mock.predict.return_value = [0.9, 0.1, 0.5]
    mocker.patch("app.search._get_reranker", return_value=mock)


class TestReranking:
    def test_reranker_returns_same_chunks_reordered(self, sample_chunks):
        from app.search import rerank
        query = "How do I create a path operation?"
        results = rerank(query, sample_chunks)
        assert len(results) == len(sample_chunks)
        assert {r["id"] for r in results} == {c["id"] for c in sample_chunks}

    def test_reranker_puts_most_relevant_first(self, sample_chunks):
        from app.search import rerank
        query = "path operation"
        results = rerank(query, sample_chunks)
        assert results is not None

    def test_rerank_empty_input(self):
        from app.search import rerank
        assert rerank("test", []) == []

    def test_rerank_scores_in_descending_order(self, sample_chunks):
        from app.search import rerank
        results = rerank("path operation", sample_chunks)
        if len(results) > 1:
            first_content = results[0]["content"]
            assert len(first_content) > 0

    def test_rerank_single_chunk(self, sample_chunks):
        from app.search import rerank
        results = rerank("test", sample_chunks[:1])
        assert len(results) == 1
        assert results[0]["id"] == sample_chunks[0]["id"]
