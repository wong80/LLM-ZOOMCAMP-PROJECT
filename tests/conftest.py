"""Shared pytest fixtures."""

import pytest
import numpy as np
from minsearch import Index
from sentence_transformers import SentenceTransformer


@pytest.fixture
def sample_sitemap_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://fastapi.tiangolo.com/</loc></url>
  <url><loc>https://fastapi.tiangolo.com/tutorial/</loc></url>
  <url><loc>https://fastapi.tiangolo.com/tutorial/path-operation/</loc></url>
  <url><loc>https://fastapi.tiangolo.com/tutorial/body/</loc></url>
  <url><loc>https://fastapi.tiangolo.com/img/favicon.ico</loc></url>
</urlset>"""


@pytest.fixture
def sample_doc_html() -> str:
    return """<html><body>
<div class="content">
  <h1>Tutorial - User Guide</h1>
  <p>Welcome to the FastAPI tutorial.</p>
  <h2>Path Operation</h2>
  <p>A path operation is a combination of an HTTP method and a URL path.</p>
  <p>You define it using decorators like @app.get().</p>
  <h3>Path Operation Example</h3>
  <pre><code>@app.get("/items/{item_id}")</code></pre>
  <p>This example shows a basic path operation.</p>
  <h2>Request Body</h2>
  <p>When you need to send data from a client to your API...</p>
</div></body></html>"""


@pytest.fixture
def sample_multi_heading_html() -> str:
    return """<html><body>
<div class="content">
  <h1>Header 1</h1><p>Content under h1.</p>
  <h2>Header 2</h2><p>Content under h2.</p>
  <h3>Header 3</h3><p>Content under h3.</p>
  <h2>Another h2</h2><p>More content.</p>
</div></body></html>"""


@pytest.fixture
def sample_empty_html() -> str:
    return "<html><body></body></html>"


@pytest.fixture
def sample_chunks() -> list[dict]:
    return [
        {
            "id": "fastapi-path-operation-000",
            "title": "Path Operation",
            "section": "Tutorial - User Guide",
            "content": "A path operation is a combination of an HTTP method and a URL path. "
                       "You define it using decorators like @app.get().",
            "url": "https://fastapi.tiangolo.com/tutorial/path-operation/#path-operation",
            "doc_library": "fastapi",
        },
        {
            "id": "fastapi-request-body-001",
            "title": "Request Body",
            "section": "Tutorial - User Guide",
            "content": "When you need to send data from a client to your API, you declare a model.",
            "url": "https://fastapi.tiangolo.com/tutorial/body/#request-body",
            "doc_library": "fastapi",
        },
        {
            "id": "fastapi-query-params-002",
            "title": "Query Parameters",
            "section": "Tutorial - User Guide",
            "content": "When you declare other function parameters that are not part of the path, "
                       "they are automatically interpreted as query parameters.",
            "url": "https://fastapi.tiangolo.com/tutorial/query-params/#query-parameters",
            "doc_library": "fastapi",
        },
    ]


@pytest.fixture
def sample_ground_truth() -> list[dict]:
    return [
        {"question": "How do I create a path operation in FastAPI?", "relevant_chunk_id": "fastapi-path-operation-000"},
        {"question": "How do I send data in a request body?", "relevant_chunk_id": "fastapi-request-body-001"},
        {"question": "How do query parameters work?", "relevant_chunk_id": "fastapi-query-params-002"},
    ]


@pytest.fixture
def sample_index(sample_chunks) -> Index:
    index = Index(text_fields=["title", "section", "content"], keyword_fields=["id", "doc_library"])
    index.fit(sample_chunks)
    return index


@pytest.fixture(scope="session")
def embedding_model():
    return SentenceTransformer("all-MiniLM-L6-v2")


@pytest.fixture
def sample_embeddings(embedding_model, sample_chunks) -> np.ndarray:
    texts = [c["content"] for c in sample_chunks]
    return embedding_model.encode(texts, convert_to_numpy=True)


@pytest.fixture
def mock_openai_response(mocker):
    import app.llm, json, re
    app.llm._client = None

    mock_response = mocker.MagicMock()
    mock_response.usage.input_tokens = 10
    mock_response.usage.output_tokens = 5
    mock_response.usage.total_tokens = 15

    mock_client = mocker.MagicMock()

    def _make_response(**kw):
        content = (kw.get("input") or [{}])[0].get("content", "")
        chunk_id = "test-001"
        m = re.search(r'relevant_chunk_id": "([^"]+)"', content)
        if m:
            chunk_id = m.group(1)
        m = re.search(r'Title: (.+)', content)
        title = m.group(1).strip() if m else "Section"

        current = json.loads(mock_response.output_text) if isinstance(mock_response.output_text, str) else {}
        current["relevance"] = current.get("relevance", "RELEVANT")
        current["question"] = f"What is {title}?"
        current["relevant_chunk_id"] = chunk_id
        current.setdefault("reason", "Test reason.")
        mock_response.output_text = json.dumps(current)
        return mock_response

    mock_response.output_text = json.dumps({
        "relevance": "RELEVANT", "question": "What is a path operation?",
        "relevant_chunk_id": "test-001", "reason": "Test reason.",
    })
    mock_client.responses.create.side_effect = _make_response
    mocker.patch("app.llm.OpenAI", return_value=mock_client)
    return mock_response


@pytest.fixture
def mock_openai_client(mocker):
    import app.llm
    app.llm._client = None
    mock_client = mocker.MagicMock()
    def side_effect(model=None, input=None, **kw):
        r = mocker.MagicMock()
        r.output_text = '{"relevance": "RELEVANT", "reason": "test"}'
        r.usage.input_tokens = 10
        r.usage.output_tokens = 5
        r.usage.total_tokens = 15
        return r
    mock_client.responses.create.side_effect = side_effect
    mocker.patch("app.llm.OpenAI", return_value=mock_client)
    return mock_client
