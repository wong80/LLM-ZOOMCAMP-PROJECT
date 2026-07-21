"""Tests for ground truth generation."""


class TestGroundTruthGeneration:
    def test_generates_question_from_chunk(self, mock_openai_response):
        from notebooks.ground_truth import generate_question
        chunk = {"id": "test-001", "title": "Path Operation", "content": "A path operation is..."}
        result = generate_question(chunk)
        assert "question" in result
        assert "relevant_chunk_id" in result
        assert result["relevant_chunk_id"] == "test-001"

    def test_batch_generation_returns_all_chunks(self, mock_openai_response):
        from notebooks.ground_truth import generate_ground_truth
        chunks = [{"id": f"c{i}", "title": f"T{i}", "content": f"C{i}"} for i in range(5)]
        results = generate_ground_truth(chunks)
        assert len(results) == len(chunks)
        assert all(r["relevant_chunk_id"] in {c["id"] for c in chunks} for r in results)

    def test_generated_questions_are_unique(self, mock_openai_response):
        from notebooks.ground_truth import generate_ground_truth
        chunks = [{"id": f"c{i}", "title": f"T{i}", "content": f"C{i}"} for i in range(3)]
        results = generate_ground_truth(chunks)
        questions = [r["question"] for r in results]
        assert len(set(questions)) == len(questions)
