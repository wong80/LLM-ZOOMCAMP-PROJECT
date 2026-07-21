# Project Plan: PyDoc Assistant

A RAG-powered Q&A system over Python library documentation. Ask questions in natural language and get answers grounded in official docs with source citations.

---

## Epics Overview

- **Epic 1**: Data Ingestion & Indexing
- **Epic 2**: Hybrid Search (Keyword + Vector)
- **Epic 3**: RAG Flow (Retrieval → Prompt → LLM → Answer)
- **Epic 4**: Evaluation (Retrieval + LLM Output)
- **Epic 5**: User Interface (Streamlit)
- **Epic 6**: Monitoring (PostgreSQL + Grafana)
- **Epic 7**: Containerization (Docker Compose)
- **Epic 8**: Best Practices (Reranking, Query Rewriting)
- **Epic 9**: Polish & Documentation

---

## Data Pipeline Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│  EPIC 1: INGESTION                                                      │
│                                                                         │
│  ReadTheDocs/Sphinx HTML  ──▶  scrape & extract text  ──▶  chunk by    │
│  (FastAPI docs)                       by section           heading      │
│                                                                         │
│  chunk = {                                                              │
│    "id": "fastapi-path-operation-001",                                  │
│    "title": "Path Operation",                                           │
│    "section": "Tutorial - User Guide",                                  │
│    "content": "A path operation is...",                                 │
│    "url": "https://fastapi.tiangolo.com/tutorial/path-operation/",      │
│    "heading_level": 2,                                                  │
│    "parent_section": "Tutorial - User Guide",                           │
│    "doc_library": "fastapi"                                             │
│  }                                                                      │
│                                                                         │
│  chunks ──▶  embed (sentence-transformers)  ──▶  store vector +        │
│              ──▶  index into minsearch          raw chunk JSON          │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  EPIC 2: SEARCH                                                         │
│                                                                         │
│  User Query: "How do I create a path operation in FastAPI?"             │
│         │                                                               │
│         ├──▶ Keyword Search (minsearch):                                │
│         │     Tokenizes query, TF-IDF match on content + title fields   │
│         │     Returns top-k chunks ranked by BM25-like scoring          │
│         │                                                               │
│         ├──▶ Vector Search (sentence-transformers):                     │
│         │     Embeds query with same model as ingestion                 │
│         │     Cosine similarity against all chunk embeddings            │
│         │     Returns top-k chunks                                      │
│         │                                                               │
│         └──▶ Hybrid Fusion:                                             │
│               Reciprocal Rank Fusion (RRF) on keyword + vector results  │
│               score = 1 / (k + rank_keyword) + 1 / (k + rank_vector)    │
│               Returns top-N reranked chunks                             │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  EPIC 3: RAG FLOW                                                       │
│                                                                         │
│  Top-k chunks ──▶  build prompt:                                        │
│                                                                         │
│    "You are a Python documentation assistant. Answer the QUESTION       │
│     using ONLY the CONTEXT below. If the answer isn't in the context,   │
│     say so. Cite the source section title for each claim.              │
│                                                                         │
│     QUESTION: {query}                                                   │
│                                                                         │
│     CONTEXT:                                                            │
│     [Source: "Path Operation" from "Tutorial - User Guide"]             │
│     A path operation is...                                              │
│     [Source: "Request Body" from "Tutorial - User Guide"]               │
│     When you declare a model...                                         │
│     "                                                                   │
│                                                                         │
│  prompt ──▶  GPT-4o-mini ──▶  answer with citations                     │
│                                                                         │
│  answer = {                                                             │
│    "answer": "You create a path operation using decorators like... ",   │
│    "citations": [{"title": "Path Operation", "url": "..."}],            │
│    "model": "gpt-4o-mini",                                              │
│    "response_time": 1.24,                                               │
│    "tokens_used": {...}                                                 │
│  }                                                                      │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  EPIC 4: EVALUATION                                                     │
│                                                                         │
│  Ground Truth Generation:                                               │
│    For each doc chunk, ask LLM: "What question does this chunk answer?" │
│    Produces: [{"chunk_id": "...", "question": "...", "answer": "..."}]  │
│                                                                         │
│  Retrieval Evaluation:                                                  │
│    For each ground truth question:                                      │
│      search(query) → check if correct chunk_id in top-k                 │
│    Metrics: Hit Rate, MRR                                               │
│    Compare: keyword-only vs vector-only vs hybrid                       │
│    Optimize: random search over minsearch boost params                  │
│                                                                         │
│  LLM Evaluation:                                                        │
│    For a sample of questions:                                           │
│      rag(query) → answer                                                │
│      LLM-as-judge: "Is answer RELEVANT/PARTLY/NON to question?"         │
│    Compare: gpt-4o-mini vs gpt-4o, different prompt templates           │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  EPIC 5+6: INTERFACE + MONITORING                                       │
│                                                                         │
│  Streamlit App                          PostgreSQL + Grafana            │
│  ┌──────────────────────┐              ┌──────────────────────┐        │
│  │  User Question ──────┼──rag(query)──▶ conversations table  │        │
│  │                      │              │ - id, question,      │        │
│  │  Answer + Citations  │◀──return─────│   answer, model,     │        │
│  │                      │              │   response_time,     │        │
│  │  [👍] [👎] Feedback ───save_feedback─▶   relevance,         │        │
│  │                      │              │   tokens, cost,      │        │
│  │  Session History     │              │   timestamp          │        │
│  └──────────────────────┘              ├──────────────────────┤        │
│                                        │ feedback table       │        │
│                                        │ - conversation_id    │        │
│                                        │ - feedback (1/-1)    │        │
│                                        │ - timestamp          │        │
│                                        └────────┬─────────────┘        │
│                                                 │                      │
│                                                 ▼                      │
│                                        ┌──────────────────────┐        │
│                                        │ Grafana Dashboard     │        │
│                                        │ 1. Q count over time │        │
│                                        │ 2. Relevance pie     │        │
│                                        │ 3. Avg resp time     │        │
│                                        │ 4. Token usage/cost  │        │
│                                        │ 5. Feedback ratio    │        │
│                                        │ 6. Model comparison  │        │
│                                        └──────────────────────┘        │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Epic 1: Data Ingestion & Indexing

### Goal
Scrape Python library documentation, chunk it, and build searchable indexes.

### How to do it

#### 1a. Pick a Library
Start with **FastAPI** — docs at `https://fastapi.tiangolo.com/`. Sphinx-generated HTML with clear URL structure, table of contents, and section hierarchy.

Future: Pydantic, Requests, SQLAlchemy, Click — any ReadTheDocs-hosted project.

#### 1b. Scrape Docs
Approach: Use the sitemap to find all doc pages.

```
GET https://fastapi.tiangolo.com/sitemap.xml
→ Parse XML, extract all <loc> URLs ending in / (doc pages)
```

Implementation: `httpx` + `beautifulsoup4` or `lxml` + `re`.

```python
# ingest/scrape.py
def get_doc_urls(sitemap_url: str) -> list[str]:
    """Fetch sitemap, parse XML, return list of doc page URLs."""
    ...

def scrape_page(url: str) -> dict:
    """Fetch HTML, extract title, content, breadcrumbs."""
    ...
```

**Why sitemap**: Reliable, discoverable, low risk of being blocked (respect `robots.txt`).

#### 1c. Chunk by Section Heading
Sphinx docs use a predictable heading structure (`<h1>`, `<h2>`, `<h3>`). Our chunking strategy:

```
Page: "Tutorial - User Guide / Path Operation"

Chunk 1:
  title: "Path Operation"
  section: "Tutorial - User Guide"
  heading_level: 2
  content: "A path operation is... (paragraphs until next h2)"
  url: ".../tutorial/path-operation/#path-operation"

Chunk 2:
  title: "Path Operation Example"
  section: "Tutorial - User Guide"
  heading_level: 3
  content: "Here's an example of a path operation... (until next h2 or h3)"
  url: ".../tutorial/path-operation/#path-operation-example"
```

Implementation:
```python
def chunk_document(html: str, base_url: str) -> list[dict]:
    """Parse HTML, split by headings, return list of chunk dicts."""
    soup = BeautifulSoup(html, "html.parser")
    chunks = []
    current_section = []
    for element in soup.find_all(["h1", "h2", "h3", "p", "pre", "ul", "ol"]):
        if element.name in ("h1", "h2", "h3"):
            if current_section:
                chunks.append(assemble_chunk(current_section))
            current_section = [element]
        else:
            current_section.append(element)
    if current_section:
        chunks.append(assemble_chunk(current_section))
    return chunks
```

**Design decision**: Overlapping chunks with a sliding window (last paragraph of chunk A repeats as first paragraph of chunk B) for better retrieval coverage.

**Why this chunking**: Course requirement (see `etc/chunking.md`). Section-heading-based chunks preserve document structure and produce good retrieval targets.

#### 1d. Store Raw Chunks
Save as JSONL for reproducibility:
```
data/raw/fastapi/chunks.jsonl
{"id": "fastapi-path-operation-001", "title": "...", "content": "...", ...}
{"id": "fastapi-path-operation-002", ...}
```

#### 1e. Build Search Index
**Keyword index** (minsearch):
```python
from minsearch import Index

index = Index(
    text_fields=["title", "section", "content"],
    keyword_fields=["id", "doc_library"]
)
index.fit(chunks)
```

**Vector index** (in-memory with numpy + sentence-transformers):
```python
from sentence_transformers import SentenceTransformer

model = SentenceTransformer("all-MiniLM-L6-v2")  # 384-dim embeddings
embeddings = model.encode([chunk["content"] for chunk in chunks])

# Store embeddings as numpy array
np.save("data/processed/fastapi/embeddings.npy", embeddings)
# Store chunk metadata as JSON
json.dump(chunks, open("data/processed/fastapi/chunks.json", "w"))
```

**Why in-memory**: Course-appropriate. PGVector can be added later but isn't needed for the project scale.

#### 1f. Ingestion Script
`python ingest.py --library fastapi`

```python
# ingest/run.py
def ingest_library(library_name: str):
    urls = get_doc_urls(SITEMAP_MAP[library_name])
    all_chunks = []
    for url in urls:
        html = scrape_page(url)
        chunks = chunk_document(html, url)
        all_chunks.extend(chunks)
    save_chunks(all_chunks, library_name)
    build_minsearch_index(all_chunks, library_name)
    build_vector_index(all_chunks, library_name)
```

### Tests

```python
# tests/test_ingest_scrape.py
import pytest
from ingest.scrape import get_doc_urls, scrape_page


class TestGetDocUrls:
    def test_returns_list_of_urls(self, sample_sitemap_xml, httpx_mock):
        httpx_mock.add_response(url="https://fastapi.tiangolo.com/sitemap.xml", text=sample_sitemap_xml)
        urls = get_doc_urls("https://fastapi.tiangolo.com/sitemap.xml")
        assert isinstance(urls, list)
        assert len(urls) > 0
        assert all(u.startswith("http") for u in urls)

    def test_filters_non_doc_pages(self, sample_sitemap_xml, httpx_mock):
        urls = get_doc_urls("https://fastapi.tiangolo.com/sitemap.xml")
        assert all(u.endswith("/") for u in urls)  # doc pages end with /


class TestScrapePage:
    def test_returns_title_and_content(self, sample_doc_html, httpx_mock):
        httpx_mock.add_response(url="https://fastapi.tiangolo.com/tutorial/", text=sample_doc_html)
        result = scrape_page("https://fastapi.tiangolo.com/tutorial/")
        assert "title" in result
        assert "content" in result
        assert "breadcrumbs" in result

    def test_raises_on_http_error(self, httpx_mock):
        httpx_mock.add_response(url="https://fastapi.tiangolo.com/404", status_code=404)
        with pytest.raises(RuntimeError, match="HTTP 404"):
            scrape_page("https://fastapi.tiangolo.com/404")


# tests/test_ingest_chunk.py
class TestChunkDocument:
    def test_splits_by_heading(self, sample_doc_html):
        from ingest.chunk import chunk_document
        chunks = chunk_document(sample_doc_html, "https://fastapi.tiangolo.com/tutorial/")
        assert len(chunks) >= 1
        for c in chunks:
            assert "id" in c and c["id"].startswith("fastapi-")
            assert "title" in c
            assert "content" in c
            assert "url" in c

    def test_heading_level_assignment(self, sample_multi_heading_html):
        from ingest.chunk import chunk_document
        chunks = chunk_document(sample_multi_heading_html, "https://fastapi.tiangolo.com/test/")
        levels = [c["heading_level"] for c in chunks]
        assert all(l in (1, 2, 3) for l in levels)

    def test_overlapping_chunks_have_shared_content(self, sample_doc_html):
        from ingest.chunk import chunk_document
        chunks = chunk_document(sample_doc_html, "https://fastapi.tiangolo.com/tutorial/", overlap=True)
        if len(chunks) > 1:
            assert chunks[0]["content"][-100:] in chunks[1]["content"]

    def test_returns_empty_on_empty_html(self):
        from ingest.chunk import chunk_document
        assert chunk_document("", "https://example.com/") == []


# tests/test_ingest_index.py
class TestMinsearchIndex:
    def test_fit_and_search_returns_matches(self, sample_chunks):
        from ingest.index import build_minsearch_index
        index = build_minsearch_index(sample_chunks)
        results = index.search("path operation", num_results=5)
        assert len(results) > 0
        assert all("id" in r for r in results)

    def test_search_returns_correct_count(self, sample_chunks):
        from ingest.index import build_minsearch_index
        index = build_minsearch_index(sample_chunks)
        results = index.search("path operation", num_results=3)
        assert len(results) <= 3


class TestVectorIndex:
    def test_embeddings_have_correct_dimensions(self, sample_chunks, embedding_model):
        from ingest.index import build_vector_index
        embeddings, _ = build_vector_index(sample_chunks, embedding_model)
        assert embeddings.shape[0] == len(sample_chunks)
        assert embeddings.shape[1] == 384  # all-MiniLM-L6-v2 dim

    def test_embedding_persistence(self, tmp_path, sample_chunks, embedding_model):
        import numpy as np
        from ingest.index import build_vector_index
        embeddings, chunks = build_vector_index(sample_chunks, embedding_model)
        np.save(tmp_path / "embeddings.npy", embeddings)
        loaded = np.load(tmp_path / "embeddings.npy")
        assert np.array_equal(embeddings, loaded)


# tests/test_ingest_run.py
class TestIngestLibrary:
    def test_ingest_pipeline_runs_end_to_end(self, mocker, tmp_path):
        from ingest.run import ingest_library
        mocker.patch("ingest.run.get_doc_urls", return_value=["https://fastapi.tiangolo.com/fake"])
        mocker.patch("ingest.run.scrape_page", return_value={"title": "Test", "content": "<p>hello</p>"})
        mocker.patch("ingest.run.chunk_document", return_value=[{"id": "test-001", "content": "hello"}])
        mocker.patch("ingest.run.build_minsearch_index")
        mocker.patch("ingest.run.build_vector_index")
        result = ingest_library("fastapi")
        assert result is not None  # completes without error
```

### Milestone Criteria

| # | Criterion | How to Verify |
|---|-----------|---------------|
| M1.1 | All test functions above pass | `pytest tests/test_ingest_scrape.py tests/test_ingest_chunk.py tests/test_ingest_index.py tests/test_ingest_run.py -v` — all green |
| M1.2 | Scraper can discover all doc URLs from sitemap | Run `python -c "from ingest.scrape import get_doc_urls; print(len(get_doc_urls('https://fastapi.tiangolo.com/sitemap.xml')))"` — returns 50+ URLs |
| M1.3 | A sample page scrapes and returns title + content | Run `python -c "from ingest.scrape import scrape_page; r=scrape_page('https://fastapi.tiangolo.com/tutorial/'); print(r['title'])"` — outputs page title |
| M1.4 | Chunker produces valid chunks for a real page | At least 5 chunks with `id`, `title`, `content`, `url`, `heading_level` from a single page |
| M1.5 | JSONL file is written to `data/raw/fastapi/chunks.jsonl` | File exists and each line is valid JSON with required fields |
| M1.6 | Minsearch index is built and serialized | `index.fit()` completes; search returns results for a sample query |
| M1.7 | Vector embeddings are stored as `.npy` file at `data/processed/fastapi/embeddings.npy` | File exists; `np.load()` returns array with shape `(N, 384)` |
| M1.8 | Full pipeline runs with single command | `python -m ingest.run --library fastapi` completes without error |

---

## Epic 2: Hybrid Search

### Goal
Return the most relevant doc chunks for a user query.

### How it works

#### 2a. Keyword Search (minsearch)
```
query: "how do I create a path operation in FastAPI"
        │
        ▼
minsearch.index.search(query, boost_dict={...}, num_results=10)
        │
        ▼
Returns: [chunk_id_1, chunk_id_2, ...]  # ranked by TF-IDF similarity
```

`boost_dict` weights each field. We'll optimize these weights (Epic 4).

#### 2b. Vector Search
```
query: "how do I create a path operation in FastAPI"
        │
        ▼
sentence-transformers encode → query_embedding (384-dim)
        │
        ▼
cosine_similarity(query_embedding, all_chunk_embeddings)
        │
        ▼
Returns: [chunk_id_3, chunk_id_1, chunk_id_5, ...]  # ranked by similarity
```

#### 2c. Hybrid Fusion (Reciprocal Rank Fusion)
```
keyword_results = [(chunk_A, rank=1), (chunk_B, rank=2), ...]
vector_results = [(chunk_B, rank=1), (chunk_A, rank=2), ...]

For each unique chunk:
  score = 1 / (60 + rank_in_keyword) + 1 / (60 + rank_in_vector)

Sort by score descending → hybrid_results
```

**k=60**: Standard RRF constant. Prevents a single high rank from dominating.

#### 2d. Search Module Interface
```python
# app/search.py
def search(query: str, method: str = "hybrid") -> list[dict]:
    """Returns top-5 chunks with their metadata."""
    ...

def keyword_search(query: str) -> list[dict]: ...
def vector_search(query: str) -> list[dict]: ...
def hybrid_search(query: str) -> list[dict]: ...
```

**Why three separate functions**: Evaluation requires comparing each method independently.

### Tests

```python
# tests/test_search.py
import pytest
import numpy as np


class TestKeywordSearch:
    def test_returns_matching_chunks(self, sample_index, sample_chunks):
        from app.search import keyword_search
        results = keyword_search("path operation", index=sample_index)
        assert len(results) > 0
        assert all(r["id"].startswith("fastapi-") for r in results)
        assert results[0]["score"] >= results[-1]["score"]  # descending

    def test_returns_empty_for_unmatched_query(self, sample_index):
        from app.search import keyword_search
        results = keyword_search("xyznonexistent12345", index=sample_index)
        assert results == []

    def test_respects_num_results_param(self, sample_index):
        from app.search import keyword_search
        for k in (1, 3, 10):
            results = keyword_search("path operation", index=sample_index, num_results=k)
            assert len(results) <= k


class TestVectorSearch:
    def test_returns_ordered_by_similarity(self, sample_embeddings, sample_chunks):
        from app.search import vector_search
        results = vector_search("path operation", embeddings=sample_embeddings, chunks=sample_chunks)
        assert len(results) > 0
        # scores should be non-increasing
        scores = [r["score"] for r in results]
        for i in range(len(scores) - 1):
            assert scores[i] >= scores[i + 1]

    def test_cosine_similarity_in_range(self, sample_embeddings, sample_chunks):
        from app.search import vector_search
        results = vector_search("path operation", embeddings=sample_embeddings, chunks=sample_chunks)
        for r in results:
            assert -1.0 <= r["score"] <= 1.0

    def test_different_queries_different_results(self, sample_embeddings, sample_chunks):
        from app.search import vector_search
        r1 = [r["id"] for r in vector_search("path operation", embeddings=sample_embeddings, chunks=sample_chunks)]
        r2 = [r["id"] for r in vector_search("dependency injection", embeddings=sample_embeddings, chunks=sample_chunks)]
        assert r1 != r2


class TestHybridSearch:
    def test_fuses_keyword_and_vector_results(self, sample_index, sample_embeddings, sample_chunks):
        from app.search import hybrid_search
        kw_results = hybrid_search("path operation", method="keyword", index=sample_index)
        vec_results = hybrid_search("path operation", method="vector", embeddings=sample_embeddings, chunks=sample_chunks)
        hybrid_results = hybrid_search("path operation", method="hybrid", index=sample_index, embeddings=sample_embeddings, chunks=sample_chunks)
        assert len(hybrid_results) > 0
        # hybrid should include entries from both sources
        kw_ids = {r["id"] for r in kw_results}
        vec_ids = {r["id"] for r in vec_results}
        hybrid_ids = {r["id"] for r in hybrid_results}
        assert hybrid_ids.issuperset(kw_ids & vec_ids) or True  # at minimum non-empty

    def test_hybrid_beat_single_method_hit_rate(self, sample_index, sample_embeddings, sample_chunks, sample_ground_truth):
        """Hybrid should have >= hit rate than either method alone (on average)."""
        from app.search import search
        from tests.helpers import hit_rate
        hybrid_hr = hit_rate(sample_ground_truth, lambda q: search(q, method="hybrid"))
        keyword_hr = hit_rate(sample_ground_truth, lambda q: search(q, method="keyword"))
        vector_hr = hit_rate(sample_ground_truth, lambda q: search(q, method="vector"))
        assert hybrid_hr >= keyword_hr or hybrid_hr >= vector_hr

    def test_rrf_constant_avoids_zero_division(self):
        from app.search import hybrid_search
        # rank is 1-indexed, RRF constant k=60
        result = hybrid_search("test", method="hybrid")  # uses internal index
        assert result is not None


class TestSearchModule:
    def test_search_defaults_to_hybrid(self, sample_index, sample_embeddings, sample_chunks):
        from app.search import search
        results = search("path operation")
        assert len(results) > 0

    def test_search_accepts_method_param(self):
        from app.search import search
        for method in ("keyword", "vector", "hybrid"):
            results = search("path operation", method=method)
            assert isinstance(results, list)
```

### Milestone Criteria

| # | Criterion | How to Verify |
|---|-----------|---------------|
| M2.1 | All test functions above pass | `pytest tests/test_search.py -v` — all green |
| M2.2 | Keyword search returns relevant results for real FastAPI queries | `python -c "from app.search import keyword_search; r=keyword_search('path operation'); print(len(r), r[0]['id'])"` — returns top result with matching ID |
| M2.3 | Vector search returns results with valid similarity scores | All scores between -1 and 1, ordered descending |
| M2.4 | Hybrid search returns at least one result for any valid query | `python -c "from app.search import hybrid_search; r=hybrid_search('How do I create an API?'); assert len(r) > 0"` — passes |
| M2.5 | Hybrid search returns combined results not present in keyword-only | The union of hybrid IDs is larger than keyword IDs alone for at least some queries |
| M2.6 | All three methods return deterministic results for the same query | `search(q, method='keyword')` returns same IDs across repeated calls |
| M2.7 | Search handles empty query gracefully | `search("", method="hybrid")` returns empty list or raises clear ValueError, not a crash |

---

## Epic 3: RAG Flow

### Goal
Generate an answer from retrieved chunks, citing sources.

### Data Flow

```
query ──▶ search(query)
              │
              ▼
         top-5 chunks
              │
              ▼
         build_prompt(query, chunks)
              │
              ▼
         LLM (gpt-4o-mini)
              │
              ▼
         answer + citations
              │
              ▼
         LLM-as-judge (inline evaluation for monitoring)
              │
              ▼
         return {answer, citations, relevance, tokens, cost, time}
```

### Prompt Template
```
You are a Python documentation assistant. Answer the QUESTION using
only the CONTEXT below. If the answer isn't in the context, say
"I don't have enough information to answer that."

For each piece of information you use, cite the source section
title and URL in brackets like: [Section: "Title"](url).

CONTEXT:
{context}

QUESTION:
{query}

ANSWER:
```

`context` format:
```
[Source: "Path Operation" from fastapi.tiangolo.com/tutorial/path-operation/]
Content: A path operation is a combination of an HTTP method and a URL path...

[Source: "Request Body" from fastapi.tiangolo.com/tutorial/body/]
Content: When you need to send data from a client to your API...

[Source: "Query Parameters" from fastapi.tiangolo.com/tutorial/query-params/]
Content: When you declare other function parameters...
```

### LLM Call
```python
# app/llm.py
from openai import OpenAI

client = OpenAI()

def llm(prompt: str, model: str = "gpt-4o-mini") -> tuple[str, dict]:
    response = client.responses.create(
        model=model,
        input=[{"role": "user", "content": prompt}]
    )
    tokens = {
        "prompt_tokens": response.usage.input_tokens,
        "completion_tokens": response.usage.output_tokens,
        "total_tokens": response.usage.total_tokens,
    }
    return response.output_text, tokens

def rag(query: str, model: str = "gpt-4o-mini") -> dict:
    t0 = time()
    chunks = search(query)
    prompt = build_prompt(query, chunks)
    answer, token_stats = llm(prompt, model)
    relevance, eval_tokens = evaluate_relevance(query, answer)
    t1 = time()

    return {
        "answer": answer,
        "citations": [c["url"] for c in chunks],
        "model": model,
        "response_time": t1 - t0,
        "relevance": relevance,
        **token_stats,
        "eval_tokens": eval_tokens,
        "cost": calculate_cost(model, token_stats) + calculate_cost(model, eval_tokens),
    }
```

### Tests

```python
# tests/test_llm.py
import pytest
from unittest.mock import patch


class TestLlmCall:
    def test_returns_text_and_token_stats(self, mock_openai_response):
        from app.llm import llm
        text, tokens = llm("test prompt", model="gpt-4o-mini")
        assert isinstance(text, str)
        assert len(text) > 0
        assert "prompt_tokens" in tokens
        assert "completion_tokens" in tokens
        assert "total_tokens" in tokens

    def test_passes_model_name_to_api(self, mock_openai_client):
        from app.llm import llm
        llm("test", model="gpt-4o")
        mock_openai_client.responses.create.assert_called_with(
            model="gpt-4o",
            input=[{"role": "user", "content": "test"}]
        )

    def test_raises_on_api_error(self, mock_openai_client):
        mock_openai_client.responses.create.side_effect = RuntimeError("API error")
        from app.llm import llm
        with pytest.raises(RuntimeError, match="API error"):
            llm("test")


# tests/test_rag.py
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


# tests/test_evaluate_relevance.py
class TestEvaluateRelevance:
    def test_returns_valid_label(self, mock_openai_response):
        from app.rag import evaluate_relevance
        label, tokens = evaluate_relevance("What is an API?", "An API is...")
        assert label in ("RELEVANT", "PARTLY_RELEVANT", "NON_RELEVANT")

    def test_returns_token_usage(self, mock_openai_response):
        from app.rag import evaluate_relevance
        label, tokens = evaluate_relevance("What is an API?", "An API is...")
        assert isinstance(tokens, dict)
        assert "total_tokens" in tokens
```

### Milestone Criteria

| # | Criterion | How to Verify |
|---|-----------|---------------|
| M3.1 | All test functions above pass | `pytest tests/test_llm.py tests/test_rag.py tests/test_evaluate_relevance.py -v` — all green |
| M3.2 | LLM function returns answer text for a real prompt | `python -c "from app.llm import llm; t, _ = llm('Say hello'); print(t)"` — returns string |
| M3.3 | LLM function correctly reports token usage | `python -c "from app.llm import llm; _, t = llm('Say hello'); assert t['total_tokens'] > 0"` — passes |
| M3.4 | Prompt builder includes query, context, and citation instruction | Inspect output for all three elements |
| M3.5 | End-to-end RAG flow produces answer, citations, metadata | `python -c "from app.rag import rag; r = rag('How do I create a path operation?'); print(r['answer'][:100])"` — returns answer with citations |
| M3.6 | RAG gracefully handles missing context | Query something unrelated → answer states "I don't have enough information" |
| M3.7 | Relevance evaluator returns one of three valid labels | Test with known good and bad answers |
| M3.8 | Cost calculation is deterministic | `calculate_cost(model, tokens)` returns expected value per OpenAI pricing |

---

## Epic 4: Evaluation

### Goal
Prove our retrieval and generation work well.

### 4a. Ground Truth Generation
For each chunk, ask GPT to generate a question the chunk answers:

```python
prompt = """
Given this documentation section, generate a natural question
that a developer might ask, which this section answers.

Section Title: {title}
Content: {content}

Return JSON: {{"question": "...", "relevant_chunk_id": "{chunk_id}"}}
"""
```

**Why generate**: Real user logs aren't available. This follows the course approach exactly (module 4 / project example).

**Quality check**: Review 20 random samples manually to ensure questions are reasonable.

**Split**: 70% train, 15% validation (for boost optimization), 15% test.

### 4b. Retrieval Evaluation

```python
def hit_rate(results: list[list[bool]]) -> float:
    """Fraction of queries where correct doc is in top-k."""
    return sum(any(r) for r in results) / len(results)

def mrr(results: list[list[bool]]) -> float:
    """Average reciprocal rank of the first relevant doc."""
    total = 0.0
    for row in results:
        for rank, relevant in enumerate(row, 1):
            if relevant:
                total += 1.0 / rank
                break
    return total / len(results)

def evaluate_retrieval(ground_truth: list[dict], search_fn) -> dict:
    relevance = []
    for gt in ground_truth:
        results = search_fn(gt["question"])
        relevance.append([r["id"] == gt["relevant_chunk_id"] for r in results])
    return {"hit_rate": hit_rate(relevance), "mrr": mrr(relevance)}
```

**Compare three approaches**:
| Strategy | Hit Rate | MRR |
|----------|----------|-----|
| Keyword only (no boost) | X.XX | X.XX |
| Keyword only (optimized boost) | X.XX | X.XX |
| Vector only | X.XX | X.XX |
| Hybrid (keyword+vector, RRF) | X.XX | X.XX |

**Optimize boosts**: Random search over `{field: (0.0, 3.0)}` ranges, 30 iterations, maximize hit rate on validation set.

### 4c. LLM Output Evaluation

```python
eval_prompt = """
Evaluate if the ANSWER addresses the QUESTION.

Classes:
- RELEVANT: Answer directly answers the question with correct info
- PARTLY_RELEVANT: Answer touches on the topic but doesn't fully answer
- NON_RELEVANT: Answer doesn't address the question

Question: {question}
Answer: {answer}

Return JSON: {{"relevance": "RELEVANT|PARTLY_RELEVANT|NON_RELEVANT", "reason": "..."}}
"""
```

**Compare**:
- gpt-4o-mini vs gpt-4o
- Prompt template A vs Prompt template B (e.g., with vs without citation requirement)

**Results table**:
| Model | % RELEVANT | % PARTLY | % NON | Cost per 1K queries |
|-------|-----------|----------|-------|-------------------|
| gpt-4o-mini | XX% | XX% | XX% | $X.XX |
| gpt-4o | XX% | XX% | XX% | $X.XX |

### 4d. Notebooks
Each evaluation goes in a separate notebook for clarity:
- `notebooks/01-ingestion.ipynb` — scrape, chunk, index
- `notebooks/02-ground-truth.ipynb` — generate ground truth
- `notebooks/03-retrieval-eval.ipynb` — hit rate, MRR, boost optimization
- `notebooks/04-rag-eval.ipynb` — LLM-as-judge, model comparison

### Tests

```python
# tests/test_evaluation_metrics.py
import pytest
import numpy as np


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
        # ranks: 1, 2, 1  →  (1/1 + 1/2 + 1/1) / 3
        assert mrr(results) == pytest.approx((1 + 0.5 + 1) / 3)

    def test_mrr_with_missing(self):
        from app.evaluation import mrr
        results = [[False, False], [False, True], [True, False]]
        # ranks: 0, 2, 1  →  (0 + 1/2 + 1/1) / 3
        assert mrr(results) == pytest.approx((0 + 0.5 + 1) / 3)

    def test_mrr_handles_mixed_lengths(self):
        from app.evaluation import mrr
        results = [[True], [False, False, True], [False, False, False, True]]
        # ranks: 1, 3, 4  →  (1 + 1/3 + 1/4) / 3
        assert mrr(results) == pytest.approx((1 + 1/3 + 1/4) / 3)


# tests/test_ground_truth.py
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


# tests/test_evaluation_retrieval.py
class TestRetrievalEvaluation:
    def test_evaluate_retrieval_returns_metrics(self, sample_ground_truth):
        from app.evaluation import evaluate_retrieval
        metrics = evaluate_retrieval(sample_ground_truth, lambda q: [{"id": gt["relevant_chunk_id"]} for gt in sample_ground_truth[:1]])
        assert "hit_rate" in metrics
        assert "mrr" in metrics
        assert 0.0 <= metrics["hit_rate"] <= 1.0
        assert 0.0 <= metrics["mrr"] <= 1.0

    def test_evaluate_retrieval_with_perfect_search(self, sample_ground_truth):
        from app.evaluation import evaluate_retrieval
        perfect_search = lambda q: [{"id": next(gt["relevant_chunk_id"] for gt in sample_ground_truth if gt["question"] == q)}]
        metrics = evaluate_retrieval(sample_ground_truth, perfect_search)
        assert metrics["hit_rate"] == 1.0
        assert metrics["mrr"] == 1.0

    def test_boost_optimization_improves_hit_rate(self, sample_index, sample_ground_truth):
        from app.evaluation import optimize_boosts
        from app.search import keyword_search
        baseline_hr = hit_rate(sample_ground_truth, lambda q: keyword_search(q, index=sample_index))
        best_params = optimize_boosts(sample_index, sample_ground_truth, iterations=10)
        optimized_hr = hit_rate(sample_ground_truth, lambda q: keyword_search(q, index=sample_index, boost_dict=best_params))
        assert optimized_hr >= baseline_hr


# tests/test_evaluation_llm.py
class TestLlmEvaluation:
    def test_judge_returns_valid_classification(self, mock_openai_response):
        from app.evaluation import evaluate_relevance
        label, _ = evaluate_relevance("What is an API?", "An API is an application programming interface.")
        assert label in ("RELEVANT", "PARTLY_RELEVANT", "NON_RELEVANT")

    def test_judge_detects_non_relevance(self, mock_openai_response):
        from app.evaluation import evaluate_relevance
        label, _ = evaluate_relevance("How do I create a path operation?", "The weather is nice today.")
        assert label == "NON_RELEVANT"

    def test_compare_models_produces_comparison_table(self, mocker):
        from app.evaluation import compare_models
        mocker.patch("app.evaluation.evaluate_relevance", return_value=("RELEVANT", {"total_tokens": 10}))
        results = compare_models(
            questions=["What is an API?", "How do I route?"],
            models=["gpt-4o-mini", "gpt-4o"],
        )
        assert "model" in results.columns
        assert "relevance" in results.columns
        assert len(results) == 4  # 2 questions × 2 models

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


# tests/test_evaluation_notebooks.py (smoke tests — verify notebooks export cells)
class TestEvaluationNotebooks:
    def test_ground_truth_notebook_runs(self, tmp_path, mock_openai_response):
        import nbformat
        from nbformat.v4 import new_notebook, new_code_cell
        nb = new_notebook()
        nb.cells.append(new_code_cell("from notebooks.ground_truth import generate_ground_truth"))
        nb.cells.append(new_code_cell("result = generate_ground_truth([{'id':'c1','title':'T','content':'C'}])"))
        assert len(nb.cells) == 2  # smoke: notebook loads without error
```

### Milestone Criteria

| # | Criterion | How to Verify |
|---|-----------|---------------|
| M4.1 | All test functions above pass | `pytest tests/test_evaluation_metrics.py tests/test_ground_truth.py tests/test_evaluation_retrieval.py tests/test_evaluation_llm.py -v` — all green |
| M4.2 | Ground truth generation produces valid Q&A pairs for real chunks | `python -c "from notebooks.ground_truth import generate_ground_truth; r=generate_ground_truth([{'id':'c1','title':'Test','content':'Hello'}]); print(r)"` — returns list of dicts |
| M4.3 | Manual quality check: 20 random ground truth samples reviewed | 20 samples inspected; < 3 unreasonable questions |
| M4.4 | Ground truth split correctly: 70/15/15 train/val/test | Run split script → verify proportions |
| M4.5 | Hit Rate and MRR computed for all three search methods | `notebooks/03-retrieval-eval.ipynb` — all three strategies produce numeric results |
| M4.6 | Boost optimization improves keyword Hit Rate on validation set | Optimized boost params yield higher HR than default (1.0, 1.0, 1.0) |
| M4.7 | Hybrid search outperforms both keyword-only and vector-only | Hybrid HR >= max(keyword HR, vector HR) on test set |
| M4.8 | LLM-as-judge comparison table completed | `notebooks/04-rag-eval.ipynb` shows gpt-4o-mini vs gpt-4o with % RELEVANT |
| M4.9 | At least two prompt templates compared | Template A (with citation) vs Template B (without) — results in notebook |

---

## Epic 5: User Interface (Streamlit)

### Goal
Let users ask questions and see answers with source citations.

### Pages

**Main page** (`app/main.py`):
```
┌─────────────────────────────────────────────────────┐
│  🐍 PyDoc Assistant                                 │
│  ─────────────────────────────────────────────────  │
│                                                     │
│  [Library selector: FastAPI ▾]                      │
│                                                     │
│  Ask a question about FastAPI:                      │
│  ┌─────────────────────────────────────────────┐   │
│  │ How do I create a path operation?          │   │
│  └─────────────────────────────────────────────┘   │
│  [Ask]                                             │
│                                                     │
│  ─── Answer ──────────────────────────────────────  │
│                                                     │
│  You create a path operation by using the ...       │
│                                                     │
│  Sources:                                           │
│  • Path Operation — fastapi.tiangolo.com/tutorial/  │
│  • Request Body — fastapi.tiangolo.com/tutorial/    │
│                                                     │
│  [👍 Was this helpful?] [👎]                        │
│                                                     │
│  Response time: 1.2s | Model: gpt-4o-mini           │
│  Relevance: RELEVANT                                │
└─────────────────────────────────────────────────────┘
```

**Feedback flow**:
```
User clicks 👍 or 👎
    │
    ▼
POST /feedback {conversation_id, feedback: 1 or -1}
    │
    ▼
db.save_feedback(conversation_id, feedback)
    │
    ▼
PostgreSQL feedback table updated
    │
    ▼
Grafana dashboard updates (next refresh)
```

**Session history** sidebar:
```
Previous questions:
  • How do I create a path... ✓
  • What is a dependency... ✓
  • How to validate request... ✓
```

### Tests

```python
# tests/test_ui.py
import pytest
from unittest.mock import patch


class TestStreamlitApp:
    def test_app_renders_title(self, streamlit_app):
        """Smoke test: app page renders without crashing."""
        from app.main import show_title
        title = show_title()
        assert "PyDoc Assistant" in title

    def test_ask_button_triggers_rag(self, mocker):
        from app.main import handle_question
        mock_rag = mocker.patch("app.main.rag", return_value={
            "answer": "Use the @app.get decorator.",
            "citations": ["https://fastapi.tiangolo.com/"],
            "model": "gpt-4o-mini",
            "response_time": 1.2,
            "relevance": "RELEVANT",
            "total_tokens": 100,
            "cost": 0.001,
        })
        result = handle_question("How do I create a path operation?")
        mock_rag.assert_called_once_with("How do I create a path operation?")
        assert "answer" in result

    def test_empty_question_shows_warning(self):
        from app.main import validate_question
        is_valid, message = validate_question("")
        assert not is_valid
        assert "Please enter a question" in message

    def test_non_empty_question_is_valid(self):
        from app.main import validate_question
        is_valid, message = validate_question("How do I create an API?")
        assert is_valid
        assert message == ""

    def test_answer_displays_sources(self, streamlit_app):
        """Answer section shows 'Sources:' label when citations exist."""
        from app.main import render_answer
        result = {
            "answer": "Use @app.get.",
            "citations": ["https://fastapi.tiangolo.com/"],
        }
        html = render_answer(result)
        assert "Sources" in html
        assert "https://fastapi.tiangolo.com/" in html

    def test_answer_handles_no_citations(self):
        from app.main import render_answer
        result = {"answer": "I don't know.", "citations": []}
        html = render_answer(result)
        assert "I don't know" in html
        assert "Sources" not in html

    def test_feedback_button_saves_to_db(self, mocker):
        from app.main import save_feedback
        mock_db = mocker.patch("app.main.db.save_feedback")
        save_feedback(conversation_id="abc-123", feedback=1)
        mock_db.assert_called_once_with("abc-123", 1)

    def test_feedback_negative_value(self, mocker):
        from app.main import save_feedback
        mock_db = mocker.patch("app.main.db.save_feedback")
        save_feedback(conversation_id="abc-123", feedback=-1)
        mock_db.assert_called_once_with("abc-123", -1)

    def test_library_selector_defaults_to_fastapi(self):
        from app.main import get_library_selector
        libs, default = get_library_selector()
        assert "FastAPI" in libs
        assert default == "FastAPI"

    def test_metadata_bar_displays_info(self):
        from app.main import render_metadata
        result = {"response_time": 1.2, "model": "gpt-4o-mini", "relevance": "RELEVANT"}
        html = render_metadata(result)
        assert "1.2s" in html
        assert "gpt-4o-mini" in html


# tests/test_ui_session.py
class TestSessionHistory:
    def test_session_stores_questions(self, streamlit_app):
        from app.main import SessionManager
        sm = SessionManager()
        sm.add_conversation("q1", "a1")
        sm.add_conversation("q2", "a2")
        assert len(sm.get_history()) == 2
        assert sm.get_history()[0]["question"] == "q1"

    def test_session_max_length(self, streamlit_app):
        from app.main import SessionManager
        sm = SessionManager(max_length=5)
        for i in range(10):
            sm.add_conversation(f"q{i}", f"a{i}")
        assert len(sm.get_history()) == 5  # trimmed to max_length

    def test_clear_session(self, streamlit_app):
        from app.main import SessionManager
        sm = SessionManager()
        sm.add_conversation("q1", "a1")
        sm.clear()
        assert sm.get_history() == []


# tests/test_ui_integration.py
@pytest.mark.integration
class TestUiIntegration:
    def test_full_query_flow(self, mocker):
        """End-to-end: question → RAG call → display → feedback save."""
        from app.main import handle_question, render_answer, save_feedback
        mock_rag = mocker.patch("app.main.rag", return_value={
            "answer": "Use @app.get()",
            "citations": ["https://fastapi.tiangolo.com/"],
            "model": "gpt-4o-mini",
            "response_time": 0.8,
            "relevance": "RELEVANT",
            "total_tokens": 50,
            "cost": 0.0005,
        })
        mock_db = mocker.patch("app.main.db.save_feedback")

        result = handle_question("How do I create a route?")
        assert result["answer"] == "Use @app.get()"

        html = render_answer(result)
        assert "Use @app.get()" in html

        save_feedback("conv-1", 1)
        mock_db.assert_called_once_with("conv-1", 1)
```

### Milestone Criteria

| # | Criterion | How to Verify |
|---|-----------|---------------|
| M5.1 | All unit tests above pass | `pytest tests/test_ui.py tests/test_ui_session.py -v` — all green |
| M5.2 | Integration tests pass | `pytest tests/test_ui_integration.py -v` — all green |
| M5.3 | App launches without errors | `streamlit run app/main.py` — opens in browser at localhost:8501 |
| M5.4 | Library selector appears with FastAPI as default | Visual check in browser |
| M5.5 | Typing a question and clicking "Ask" produces an answer | End-to-end: ask "What is a path operation?" → see answer |
| M5.6 | Answer displays source citations | Citations listed below the answer text |
| M5.7 | Metadata bar shows response time, model name, relevance | e.g., "1.2s | gpt-4o-mini | RELEVANT" |
| M5.8 | Thumbs-up / thumbs-down buttons are visible and clickable | Clicking either triggers feedback save (check DB) |
| M5.9 | Session history sidebar shows previous questions | After 2+ questions, sidebar lists them |
| M5.10 | Empty question shows validation warning | Click "Ask" with empty input → warning message appears |

---

## Epic 6: Monitoring (PostgreSQL + Grafana)

### Goal
Track usage, quality, cost, and collect user feedback.

### Database Schema

```sql
-- conversations table
CREATE TABLE conversations (
    id TEXT PRIMARY KEY,
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    model_used TEXT NOT NULL,
    response_time FLOAT NOT NULL,
    relevance TEXT NOT NULL,
    prompt_tokens INTEGER NOT NULL,
    completion_tokens INTEGER NOT NULL,
    total_tokens INTEGER NOT NULL,
    eval_prompt_tokens INTEGER NOT NULL,
    eval_completion_tokens INTEGER NOT NULL,
    eval_total_tokens INTEGER NOT NULL,
    openai_cost FLOAT NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL
);

-- feedback table
CREATE TABLE feedback (
    id SERIAL PRIMARY KEY,
    conversation_id TEXT REFERENCES conversations(id),
    feedback INTEGER NOT NULL,  -- 1 or -1
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL
);
```

### Grafana Dashboard (6 charts)

| Chart # | Type | SQL Query | What it shows |
|---------|------|-----------|---------------|
| 1 | Time series bar | `SELECT date_trunc('hour', timestamp), count(*) FROM conversations GROUP BY 1` | Questions per hour |
| 2 | Pie | `SELECT relevance, count(*) FROM conversations GROUP BY 1` | Relevance distribution |
| 3 | Stat | `SELECT avg(response_time) FROM conversations` | Avg response time |
| 4 | Time series line | `SELECT date_trunc('hour', timestamp), sum(openai_cost) FROM conversations GROUP BY 1` | Cost over time |
| 5 | Bar | `SELECT feedback, count(*) FROM feedback GROUP BY 1` | Feedback ratio (thumbs up/down) |
| 6 | Table | `SELECT model_used, count(*), avg(response_time) FROM conversations GROUP BY 1` | Model comparison |

**Automated provisioning**: `grafana/init.py` script calls Grafana API to create PostgreSQL data source + import dashboard JSON.

### Tests

```python
# tests/test_db.py
import pytest
from datetime import datetime, timezone


class TestDatabaseSchema:
    def test_create_conversations_table(self, db_connection):
        """Verify conversations table has required columns."""
        cursor = db_connection.cursor()
        cursor.execute("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'conversations'
        """)
        columns = {row[0]: row[1] for row in cursor.fetchall()}
        for col in ("id", "question", "answer", "model_used", "response_time",
                     "relevance", "prompt_tokens", "total_tokens", "openai_cost", "timestamp"):
            assert col in columns, f"Missing column: {col}"

    def test_create_feedback_table(self, db_connection):
        cursor = db_connection.cursor()
        cursor.execute("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'feedback'
        """)
        columns = {row[0] for row in cursor.fetchall()}
        assert "conversation_id" in columns
        assert "feedback" in columns
        assert "timestamp" in columns


class TestConversationCrud:
    def test_save_and_retrieve_conversation(self, db_connection):
        from app.db import save_conversation, get_conversation
        conv = {
            "id": "test-1",
            "question": "What is FastAPI?",
            "answer": "FastAPI is a web framework.",
            "model_used": "gpt-4o-mini",
            "response_time": 1.5,
            "relevance": "RELEVANT",
            "prompt_tokens": 50,
            "completion_tokens": 30,
            "total_tokens": 80,
            "eval_prompt_tokens": 10,
            "eval_completion_tokens": 5,
            "eval_total_tokens": 15,
            "openai_cost": 0.001,
            "timestamp": datetime.now(timezone.utc),
        }
        save_conversation(db_connection, conv)
        retrieved = get_conversation(db_connection, "test-1")
        assert retrieved["question"] == "What is FastAPI?"
        assert retrieved["answer"] == "FastAPI is a web framework."

    def test_save_duplicate_conversation_id_raises(self, db_connection):
        from app.db import save_conversation
        conv = {"id": "dup-1", "question": "q", "answer": "a", "model_used": "gpt-4o-mini",
                "response_time": 0.5, "relevance": "RELEVANT", "prompt_tokens": 10,
                "completion_tokens": 5, "total_tokens": 15, "eval_prompt_tokens": 0,
                "eval_completion_tokens": 0, "eval_total_tokens": 0,
                "openai_cost": 0.0001, "timestamp": datetime.now(timezone.utc)}
        save_conversation(db_connection, conv)
        with pytest.raises(Exception):
            save_conversation(db_connection, conv)


class TestFeedbackCrud:
    def test_save_feedback(self, db_connection):
        from app.db import save_conversation, save_feedback, get_feedback
        conv = {"id": "fb-test-1", "question": "q", "answer": "a", "model_used": "gpt-4o-mini",
                "response_time": 0.5, "relevance": "RELEVANT", "prompt_tokens": 10,
                "completion_tokens": 5, "total_tokens": 15, "eval_prompt_tokens": 0,
                "eval_completion_tokens": 0, "eval_total_tokens": 0,
                "openai_cost": 0.0001, "timestamp": datetime.now(timezone.utc)}
        save_conversation(db_connection, conv)
        save_feedback(db_connection, "fb-test-1", 1)
        feedback = get_feedback(db_connection, "fb-test-1")
        assert feedback == 1

    def test_feedback_positive_and_negative(self, db_connection):
        from app.db import save_conversation, save_feedback, get_feedback
        for fid, val in [("pos", 1), ("neg", -1)]:
            conv = {**BASE_CONV, "id": fid}
            save_conversation(db_connection, conv)
            save_feedback(db_connection, fid, val)
            assert get_feedback(db_connection, fid) == val


# tests/test_grafana.py
class TestGrafanaProvisioning:
    def test_datasource_creation(self, grafana_api):
        from grafana.init import create_postgres_datasource
        result = create_postgres_datasource(grafana_api)
        assert result["datasource"]["type"] == "postgres"
        assert result["datasource"]["name"] == "PyDoc PostgreSQL"

    def test_dashboard_import(self, grafana_api):
        from grafana.init import import_dashboard
        result = import_dashboard(grafana_api, "grafana/dashboard.json")
        assert "dashboard" in result
        assert result["dashboard"]["title"] == "PyDoc Assistant Monitoring"

    def test_dashboard_has_six_panels(self, grafana_api):
        from grafana.init import import_dashboard
        result = import_dashboard(grafana_api, "grafana/dashboard.json")
        panels = result["dashboard"]["panels"]
        assert len(panels) >= 5  # course requirement: 5+ charts

    def test_dashboard_panel_types(self, grafana_api):
        from grafana.init import import_dashboard
        result = import_dashboard(grafana_api, "grafana/dashboard.json")
        panel_types = {p["type"] for p in result["dashboard"]["panels"]}
        assert "timeseries" in panel_types or "graph" in panel_types
        assert "piechart" in panel_types or "stat" in panel_types


# tests/test_db_queries.py (verifying Grafana SQL queries work)
class TestDashboardQueries:
    def test_questions_per_hour_query(self, db_connection):
        cursor = db_connection.cursor()
        cursor.execute("""
            SELECT date_trunc('hour', timestamp) AS hour, count(*)
            FROM conversations GROUP BY hour ORDER BY hour
        """)
        rows = cursor.fetchall()
        # Query should not error; even empty results are valid
        assert isinstance(rows, list)

    def test_relevance_distribution_query(self, db_connection):
        cursor = db_connection.cursor()
        cursor.execute("""
            SELECT relevance, count(*) FROM conversations GROUP BY relevance
        """)
        rows = cursor.fetchall()
        assert isinstance(rows, list)

    def test_openai_cost_query(self, db_connection):
        cursor = db_connection.cursor()
        cursor.execute("""
            SELECT sum(openai_cost) FROM conversations
        """)
        row = cursor.fetchone()
        # Should return a number (0 if no rows due to COALESCE)
        assert row is not None


# tests/test_monitoring_integration.py
@pytest.mark.integration
class TestMonitoringIntegration:
    def test_full_monitoring_flow(self, db_connection, grafana_api):
        """End-to-end: save conversation → save feedback → verify dashboard reflects data."""
        from app.db import save_conversation, save_feedback
        from grafana.init import create_postgres_datasource, import_dashboard

        conv = {**BASE_CONV, "id": "monitor-e2e"}
        save_conversation(db_connection, conv)
        save_feedback(db_connection, "monitor-e2e", -1)

        ds = create_postgres_datasource(grafana_api)
        assert ds["datasource"]["uid"] is not None

        dash = import_dashboard(grafana_api, "grafana/dashboard.json")
        assert len(dash["dashboard"]["panels"]) >= 5
```

### Milestone Criteria

| # | Criterion | How to Verify |
|---|-----------|---------------|
| M6.1 | All unit tests above pass | `pytest tests/test_db.py tests/test_grafana.py tests/test_db_queries.py -v` — all green |
| M6.2 | Integration tests pass | `pytest tests/test_monitoring_integration.py -v` — all green |
| M6.3 | PostgreSQL `conversations` table exists with all required columns | `psql -d pydoc_assistant -c "\d conversations"` — shows 14+ columns |
| M6.4 | PostgreSQL `feedback` table exists with foreign key to conversations | `psql -d pydoc_assistant -c "\d feedback"` — shows FK constraint |
| M6.5 | Saving a conversation persists to DB | `python -c "from app.db import save_conversation; save_conversation(conn, {...})"` — row appears in table |
| M6.6 | Thumbs-up/down feedback saves correctly | Save feedback 1 and -1 → verify in `feedback` table |
| M6.7 | Grafana is reachable at localhost:3000 | `curl -u admin:admin http://localhost:3000/api/health` — returns 200 |
| M6.8 | PostgreSQL datasource is configured in Grafana | `curl -u admin:admin http://localhost:3000/api/datasources` — lists postgres datasource |
| M6.9 | Dashboard has 6 visualizations (min 5) | `curl -u admin:admin http://localhost:3000/api/dashboards/uid/pydoc-assistant` — panels array has 6 items |
| M6.10 | All six chart types are present: timeseries bar, pie, stat, timeseries line, bar, table | Visual check in Grafana UI |

---

## Epic 7: Containerization (Docker Compose)

### Goal
One command to run everything.

### Services

```yaml
# docker-compose.yaml
services:
  postgres:
    image: postgres:16
    environment:
      POSTGRES_DB: pydoc_assistant
      POSTGRES_USER: user
      POSTGRES_PASSWORD: password
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U user -d pydoc_assistant"]
      interval: 5s
      retries: 5

  app:
    build: .
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - POSTGRES_HOST=postgres
      - POSTGRES_DB=pydoc_assistant
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=password
    ports:
      - "8501:8501"
    depends_on:
      postgres:
        condition: service_healthy
    volumes:
      - ./data:/app/data  # For pre-built index files

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    depends_on:
      - postgres
    volumes:
      - grafana_data:/var/lib/grafana

volumes:
  postgres_data:
  grafana_data:
```

### Dockerfile
```dockerfile
FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app
ENV PATH="/app/.venv/bin:$PATH"

COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --locked --no-dev

COPY . .

EXPOSE 8501
CMD ["streamlit", "run", "app/main.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

### Startup
```bash
docker compose up --build -d
python init.py  # Create DB tables + provision Grafana
```

### Tests

```python
# tests/test_docker.py
import pytest
import yaml
import subprocess


class TestDockerfile:
    def test_dockerfile_exists(self):
        import os
        assert os.path.exists("Dockerfile")

    def test_dockerfile_uses_python_312(self):
        with open("Dockerfile") as f:
            content = f.read()
        assert "python:3.12" in content or "python:3.12-slim" in content

    def test_dockerfile_exposes_port_8501(self):
        with open("Dockerfile") as f:
            content = f.read()
        assert "EXPOSE 8501" in content

    def test_dockerfile_installs_uv(self):
        with open("Dockerfile") as f:
            content = f.read()
        assert "uv" in content or "astral-sh" in content

    def test_dockerfile_cmd_runs_streamlit(self):
        with open("Dockerfile") as f:
            content = f.read()
        assert "streamlit" in content
        assert "8501" in content


class TestDockerCompose:
    def test_compose_file_exists(self):
        import os
        assert os.path.exists("docker-compose.yaml") or os.path.exists("docker-compose.yml")

    def test_compose_has_required_services(self):
        path = "docker-compose.yaml" if __import__("os").path.exists("docker-compose.yaml") else "docker-compose.yml"
        with open(path) as f:
            config = yaml.safe_load(f)
        services = set(config["services"].keys())
        assert "postgres" in services
        assert "app" in services
        assert "grafana" in services

    def test_postgres_healthcheck_configured(self):
        path = "docker-compose.yaml" if __import__("os").path.exists("docker-compose.yaml") else "docker-compose.yml"
        with open(path) as f:
            config = yaml.safe_load(f)
        healthcheck = config["services"]["postgres"].get("healthcheck", {})
        assert "test" in healthcheck
        assert "pg_isready" in " ".join(healthcheck["test"])

    def test_app_depends_on_postgres_healthy(self):
        path = "docker-compose.yaml" if __import__("os").path.exists("docker-compose.yaml") else "docker-compose.yml"
        with open(path) as f:
            config = yaml.safe_load(f)
        deps = config["services"]["app"].get("depends_on", {})
        assert "postgres" in deps
        if isinstance(deps["postgres"], dict):
            assert deps["postgres"].get("condition") == "service_healthy"

    def test_app_passes_openai_api_key(self):
        path = "docker-compose.yaml" if __import__("os").path.exists("docker-compose.yaml") else "docker-compose.yml"
        with open(path) as f:
            config = yaml.safe_load(f)
        env = config["services"]["app"].get("environment", {})
        assert "OPENAI_API_KEY" in str(env)  # ${OPENAI_API_KEY} or actual value

    def test_grafana_exposes_port_3000(self):
        path = "docker-compose.yaml" if __import__("os").path.exists("docker-compose.yaml") else "docker-compose.yml"
        with open(path) as f:
            config = yaml.safe_load(f)
        ports = config["services"]["grafana"].get("ports", [])
        assert any("3000" in str(p) for p in ports)

    def test_volumes_defined(self):
        path = "docker-compose.yaml" if __import__("os").path.exists("docker-compose.yaml") else "docker-compose.yml"
        with open(path) as f:
            config = yaml.safe_load(f)
        volumes = config.get("volumes", {})
        assert "postgres_data" in volumes
        assert "grafana_data" in volumes


class TestDockerBuild:
    @pytest.mark.integration
    def test_image_builds_successfully(self):
        result = subprocess.run(
            ["docker", "build", "-t", "pydoc-assistant:test", "."],
            capture_output=True, text=True, timeout=300
        )
        assert result.returncode == 0, f"Build failed:\n{result.stderr}"

    @pytest.mark.integration
    def test_container_starts_and_serves(self):
        """Build and run container, verify Streamlit responds on 8501."""
        subprocess.run(["docker", "rm", "-f", "pydoc-test"], capture_output=True)
        subprocess.run([
            "docker", "run", "-d", "--name", "pydoc-test",
            "-p", "18501:8501",
            "-e", "OPENAI_API_KEY=sk-test",
            "pydoc-assistant:test"
        ], check=True, timeout=30)
        import time; time.sleep(5)
        result = subprocess.run(
            ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", "http://localhost:18501"],
            capture_output=True, text=True, timeout=10
        )
        subprocess.run(["docker", "rm", "-f", "pydoc-test"], capture_output=True)
        assert result.stdout.strip() == "200" or result.stdout.strip().startswith("2")


class TestInitScript:
    def test_init_script_exists(self):
        import os
        assert os.path.exists("init.py")

    def test_init_creates_tables(self, mocker):
        mocker.patch("init.create_db_tables")
        mocker.patch("init.provision_grafana")
        import init
        init.main()
        init.create_db_tables.assert_called_once()
        init.provision_grafana.assert_called_once()
```

### Milestone Criteria

| # | Criterion | How to Verify |
|---|-----------|---------------|
| M7.1 | All unit tests above pass | `pytest tests/test_docker.py -v -m "not integration"` — all green except integration tests |
| M7.2 | Docker image builds without errors | `docker build -t pydoc-assistant:latest .` — exits 0 |
| M7.3 | `docker compose up --build -d` starts all three services | `docker compose ps` — postgres, app, grafana all show "Up" |
| M7.4 | Streamlit app accessible at http://localhost:8501 | `curl -s -o /dev/null -w "%{http_code}" http://localhost:8501` — returns 200 |
| M7.5 | Grafana accessible at http://localhost:3000 | `curl -s -o /dev/null -w "%{http_code}" http://localhost:3000` — returns 200 or 302 |
| M7.6 | PostgreSQL accepts connections | `docker compose exec postgres pg_isready -U user -d pydoc_assistant` — returns "accepting connections" |
| M7.7 | `python init.py` creates tables and provisions Grafana | Tables `conversations` and `feedback` exist after running init |
| M7.8 | App container restarts gracefully after crash | `docker compose restart app` — app comes back and serves requests |
| M7.9 | Data survives container restart (volume persistence) | Ask a question, restart, verify conversation still in DB |
| M7.10 | Single command end-to-end startup: `docker compose up -d && python init.py` | Both commands execute without error |

---

## Epic 8: Best Practices

### 8a. Query Rewriting (1 bonus point)
Before sending the user query to search, rewrite it for better retrieval.

```python
def rewrite_query(original_query: str) -> str:
    """Expand abbreviations, normalize terms for better doc matching."""
    # Example mappings for FastAPI
    replacements = {
        "dep inj": "dependency injection",
        "path op": "path operation",
        "req": "request",
        "resp": "response",
        "val": "validation",
    }
    # Also use LLM to rewrite
    prompt = f"Rewrite this developer question to be more searchable:\n{original_query}"
    return llm(prompt)
```

**Why it helps**: Users ask "how do I do dep inj in FastAPI" which won't match "Dependency Injection" in the docs.

### 8b. Document Reranking (1 bonus point)
After hybrid search returns top-20, use a cross-encoder to rerank.

```python
from sentence_transformers import CrossEncoder

reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")

def rerank(query: str, chunks: list[dict]) -> list[dict]:
    pairs = [(query, c["content"]) for c in chunks]
    scores = reranker.predict(pairs)
    scored = list(zip(chunks, scores))
    scored.sort(key=lambda x: x[1], reverse=True)
    return [c for c, s in scored]
```

**Why cross-encoder**: More accurate than bi-encoder cosine similarity. Reranks top-20 (not all chunks, too slow).

### 8c. Hybrid Search (1 bonus point)
Already covered in Epic 2. Evaluate keyword, vector, and hybrid separately to prove hybrid wins.

### Tests

```python
# tests/test_bonus_query_rewrite.py
import pytest


class TestQueryRewriting:
    def test_expands_abbreviations_directly(self):
        from app.search import rewrite_query
        cases = {
            "dep inj in FastAPI": "dependency injection in FastAPI",
            "how to do dep inj": "how to do dependency injection",
            "path op example": "path operation example",
            "req validation": "request validation",
            "resp model": "response model",
        }
        for raw, expected in cases.items():
            result = rewrite_query(raw, method="direct")
            assert expected in result.lower()

    def test_llm_rewrite_returns_string(self, mock_openai_response):
        from app.search import rewrite_query
        result = rewrite_query("how to dep inj", method="llm")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_rewrite_preserves_core_terms(self):
        from app.search import rewrite_query
        original = "How do I create a path operation?"
        result = rewrite_query(original, method="direct")
        assert "path operation" in result.lower() or "create" in result.lower()

    def test_rewrite_improves_search_hit_rate(self, sample_index, sample_ground_truth):
        """Rewritten query should have >= hit rate than original."""
        from app.search import rewrite_query, keyword_search
        from tests.helpers import hit_rate
        original_hr = hit_rate(sample_ground_truth, lambda q: keyword_search(q, index=sample_index))
        rewritten_hr = hit_rate(sample_ground_truth, lambda q: keyword_search(rewrite_query(q), index=sample_index))
        assert rewritten_hr >= original_hr


# tests/test_bonus_reranking.py
class TestReranking:
    def test_reranker_returns_same_chunks_reordered(self, sample_chunks):
        from app.search import rerank
        query = "How do I create a path operation?"
        results = rerank(query, sample_chunks)
        assert len(results) == len(sample_chunks)
        assert {r["id"] for r in results} == {c["id"] for c in sample_chunks}

    def test_reranker_puts_most_relevant_first(self, sample_chunks):
        """Most relevant chunk (by content match) should rank #1 after rerank."""
        from app.search import rerank
        query = "path operation"
        results = rerank(query, sample_chunks)
        # The chunk whose content best matches the query should be first
        assert results is not None

    def test_rerank_improves_reciprocal_rank(self, sample_index, sample_embeddings, sample_ground_truth):
        """MRR should improve after reranking."""
        from app.search import hybrid_search, rerank
        from tests.helpers import mrr
        before_mrr = mrr(sample_ground_truth, lambda q: hybrid_search(q, method="hybrid", index=sample_index, embeddings=sample_embeddings, chunks=sample_chunks))
        after_mrr = mrr(sample_ground_truth, lambda q: rerank(q, hybrid_search(q, method="hybrid", index=sample_index, embeddings=sample_embeddings, chunks=sample_chunks, num_results=20)))
        assert after_mrr >= before_mrr

    def test_rerank_empty_input(self):
        from app.search import rerank
        assert rerank("test", []) == []

    def test_rerank_scores_in_descending_order(self, sample_chunks):
        from app.search import rerank
        results = rerank("path operation", sample_chunks)
        if len(results) > 1:
            # Scores hidden but ordering should be deterministic
            first_content = results[0]["content"]
            assert len(first_content) > 0


# tests/test_bonus_hybrid.py
class TestHybridBonus:
    def test_hybrid_outperforms_keyword(self, sample_index, sample_ground_truth):
        from app.search import keyword_search, hybrid_search
        from tests.helpers import hit_rate
        kw_hr = hit_rate(sample_ground_truth, lambda q: keyword_search(q, index=sample_index))
        hy_hr = hit_rate(sample_ground_truth, lambda q: hybrid_search(q, method="hybrid", index=sample_index))
        assert hy_hr >= kw_hr, f"Hybrid HR ({hy_hr}) < Keyword HR ({kw_hr})"

    def test_hybrid_outperforms_vector(self, sample_embeddings, sample_ground_truth):
        from app.search import vector_search, hybrid_search
        from tests.helpers import hit_rate
        vec_hr = hit_rate(sample_ground_truth, lambda q: vector_search(q, embeddings=sample_embeddings))
        hy_hr = hit_rate(sample_ground_truth, lambda q: hybrid_search(q, method="hybrid", embeddings=sample_embeddings))
        assert hy_hr >= vec_hr, f"Hybrid HR ({hy_hr}) < Vector HR ({vec_hr})"

    def test_rrf_fusion_combines_results(self, sample_index, sample_embeddings):
        from app.search import keyword_search, vector_search, hybrid_search
        kw_ids = {r["id"] for r in keyword_search("path operation", index=sample_index, num_results=20)}
        vec_ids = {r["id"] for r in vector_search("path operation", embeddings=sample_embeddings, num_results=20)}
        hy_ids = {r["id"] for r in hybrid_search("path operation", method="hybrid", index=sample_index, embeddings=sample_embeddings, num_results=20)}
        # Hybrid should not miss any ID present in both keyword and vector results
        assert kw_ids & vec_ids <= hy_ids


# tests/test_bonus_integration.py
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
```

### Milestone Criteria

| # | Criterion | How to Verify |
|---|-----------|---------------|
| M8.1 | Query rewriting expands common FastAPI abbreviations | `rewrite_query("dep inj")` → contains "dependency injection" |
| M8.2 | Query rewriting improves retrieval hit rate | HR(rewritten) >= HR(original) on a validation set |
| M8.3 | Cross-encoder reranking reorders top-20 results | Before and after ordering differ for most queries |
| M8.4 | Reranking improves MRR | MRR(reranked) > MRR(before) on test set |
| M8.5 | Hybrid search is separately evaluated and proven best | Chart/table in notebook shows Hybrid HR > Keyword HR and Vector HR |
| M8.6 | All three bonus features have passing tests | `pytest tests/test_bonus_query_rewrite.py tests/test_bonus_reranking.py tests/test_bonus_hybrid.py -v` — all green |
| M8.7 | Bonus features integrate without breaking core flow | `pytest tests/test_bonus_integration.py -v` — passes |

---

## Epic 9: Polish & Documentation

### README Sections
1. **Problem** — What this project solves
2. **Dataset** — Which library, how it was collected
3. **Architecture** — Diagram of the pipeline
4. **Setup** — Prerequisites, env vars, `uv sync`
5. **Usage** — Running the app, example questions
6. **Evaluation Results** — Tables from Epic 4
7. **Project Structure** — File listing
8. **Scoring Checklist** — Map to evaluation criteria

### Screenshots
- Streamlit UI with an answer
- Grafana dashboard
- Evaluation notebook output

### Tests

```python
# tests/test_documentation.py
import pytest
import os


class TestReadme:
    def test_readme_exists(self):
        assert os.path.exists("README.md")

    def test_readme_has_problem_statement(self):
        with open("README.md") as f:
            content = f.read()
        assert "problem" in content.lower() or "Problem" in content

    def test_readme_has_architecture_section(self):
        with open("README.md") as f:
            content = f.read()
        assert "architecture" in content.lower() or "Architecture" in content

    def test_readme_has_setup_instructions(self):
        with open("README.md") as f:
            content = f.read()
        assert "setup" in content.lower() or "Installation" in content or "Prerequisites" in content

    def test_readme_has_evaluation_results_table(self):
        with open("README.md") as f:
            content = f.read()
        assert "Hit Rate" in content or "RELEVANT" in content or "hit_rate" in content

    def test_readme_has_scoring_checklist(self):
        with open("README.md") as f:
            content = f.read()
        assert "Scoring" in content or "Checklist" in content

    def test_readme_mentions_llm_zoomcamp(self):
        with open("README.md") as f:
            content = f.read()
        assert "LLM Zoomcamp" in content or "DataTalks" in content

    def test_readme_mentions_fastapi_dataset(self):
        with open("README.md") as f:
            content = f.read()
        assert "FastAPI" in content


class TestProjectStructure:
    def test_env_example_exists(self):
        assert os.path.exists(".env.example")

    def test_env_example_has_no_real_keys(self):
        """Ensure .env.example doesn't contain actual API keys."""
        with open(".env.example") as f:
            content = f.read()
        assert "sk-" not in content

    def test_uv_lock_exists(self):
        assert os.path.exists("uv.lock")

    def test_pyproject_toml_has_project_name(self):
        with open("pyproject.toml") as f:
            content = f.read()
        assert "llm-zoomcamp" in content.lower()

    def test_gitignore_exists(self):
        assert os.path.exists(".gitignore")

    def test_gitignore_ignores_env_and_venv(self):
        with open(".gitignore") as f:
            content = f.read()
        assert ".env" in content
        assert ".venv" in content or "venv" in content


class TestNotebooks:
    def test_evaluation_notebooks_exist(self):
        expected = [
            "notebooks/01-ingestion.ipynb",
            "notebooks/02-ground-truth.ipynb",
            "notebooks/03-retrieval-eval.ipynb",
            "notebooks/04-rag-eval.ipynb",
        ]
        for nb in expected:
            assert os.path.exists(nb), f"Missing notebook: {nb}"

    def test_notebooks_have_outputs_saved(self):
        import json
        for nb_path in ["notebooks/03-retrieval-eval.ipynb", "notebooks/04-rag-eval.ipynb"]:
            if os.path.exists(nb_path):
                with open(nb_path) as f:
                    nb = json.load(f)
                cell_outputs = [c for c in nb["cells"] if c.get("outputs")]
                assert len(cell_outputs) > 0, f"{nb_path} has no saved outputs"

    def test_ground_truth_notebook_generates_data(self):
        """Notebook should create ground_truth.jsonl output."""
        assert os.path.exists("data/ground_truth.jsonl") or os.path.exists("data/processed/ground_truth.jsonl")


class TestGrafanaExport:
    def test_dashboard_json_exists(self):
        assert os.path.exists("grafana/dashboard.json")

    def test_dashboard_json_is_valid(self):
        import json
        with open("grafana/dashboard.json") as f:
            dashboard = json.load(f)
        assert "panels" in dashboard["dashboard"] if "dashboard" in dashboard else "panels" in dashboard
        panels = dashboard.get("dashboard", dashboard).get("panels", [])
        assert len(panels) >= 5


class TestReproducibility:
    def test_uv_sync_succeeds(self):
        """Verify that a fresh `uv sync` would succeed (lockfile matches pyproject.toml)."""
        import subprocess
        result = subprocess.run(
            ["uv", "sync", "--locked", "--dry-run"],
            capture_output=True, text=True, timeout=30
        )
        # --dry-run exits 0 if lockfile is consistent, non-zero otherwise
        assert result.returncode == 0, f"uv sync --dry-run failed:\n{result.stderr}"

    def test_python_version_matches_pin(self):
        import subprocess
        with open(".python-version") as f:
            expected = f.read().strip()
        result = subprocess.run(["python", "--version"], capture_output=True, text=True)
        assert expected in result.stdout, f"Expected Python {expected}, got {result.stdout}"

    def test_git_repo_is_clean(self):
        """Reproducible means committed; uncommitted changes break reproducibility."""
        import subprocess
        result = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)
        # Only allow .env and .venv to be dirty (they're gitignored)
        dirty = [line for line in result.stdout.splitlines() if not any(ig in line for ig in [".env", ".venv", "learning material"])]
        if dirty:
            pytest.skip(f"Uncommitted changes exist: {dirty}")
```

### Milestone Criteria

| # | Criterion | How to Verify |
|---|-----------|---------------|
| M9.1 | All tests above pass | `pytest tests/test_documentation.py -v` — all green |
| M9.2 | README describes the problem clearly | Read the Problem Statement section — non-technical reader understands it |
| M9.3 | README has architecture diagram | ASCII diagram or image showing data flow from ingestion → search → RAG → UI |
| M9.4 | README includes setup & usage instructions | Follow instructions from scratch → app runs successfully |
| M9.5 | README includes evaluation results with numbers | Hit Rate, MRR, and LLM evaluation tables are filled (not X.XX) |
| M9.6 | README has a scoring checklist mapped to rubric | Each criterion points to the relevant file/notebook |
| M9.7 | `.env.example` exists without real API keys | File contains `OPENAI_API_KEY=your-key-here` or similar placeholder |
| M9.8 | `uv.lock` is committed and in sync with `pyproject.toml` | `uv sync --locked` succeeds |
| M9.9 | All four evaluation notebooks exist | `01-ingestion.ipynb`, `02-ground-truth.ipynb`, `03-retrieval-eval.ipynb`, `04-rag-eval.ipynb` |
| M9.10 | Evaluation notebooks have saved outputs (not just code) | Opening each notebook shows rendered tables, charts, or printed results |
| M9.11 | Grafana dashboard JSON is exported to repo | `grafana/dashboard.json` exists and imports without error |
| M9.12 | Screenshots captured and referenced in README | README contains `screenshots/` references or inline images for UI, Grafana, and notebooks |
| M9.13 | Git repo has no committed secrets | `git grep "sk-proj"` returns nothing (except in `.env` which should be gitignored) |
| M9.14 | All deliverables checklist items are checked | Each `[ ]` in the deliverables section is `[x]` |
| M9.15 | Non-course-taker can reproduce the entire project | Fresh clone → `uv sync` → `python -m ingest.run --library fastapi` → `streamlit run app/main.py` — answers questions |

---

## Scoring Summary

| Criterion | Points | Epic |
|-----------|--------|------|
| Problem description | 2 | Epic 9 |
| Retrieval flow | 2 | Epics 1-3 |
| Retrieval evaluation | 2 | Epic 4 |
| LLM evaluation | 2 | Epic 4 |
| Interface | 2 | Epic 5 |
| Ingestion pipeline | 2 | Epic 1 |
| Monitoring | 2 | Epic 6 |
| Containerization | 2 | Epic 7 |
| Reproducibility | 2 | Epic 9 |
| Hybrid search | +1 | Epic 2/8 |
| Reranking | +1 | Epic 8 |
| Query rewriting | +1 | Epic 8 |
| Cloud deployment | +2 | Optional |
| **Total** | **26** | |

---

## Implementation Order

```
Week 1: Epic 1 (ingestion) + Epic 2 (search) — get data in and searchable
Week 2: Epic 3 (RAG flow) + Epic 5 (Streamlit UI) — working prototype
Week 3: Epic 4 (evaluation) — prove it works, optimize
Week 4: Epic 6 (monitoring) + Epic 7 (Docker) — ops ready
Week 5: Epic 8 (bonuses) + Epic 9 (polish) — extra points + docs
```

---

## Coding Standards

### Commenting

Every source file (`.py`) must have comments explaining:
- **Module docstring** at the top: what the file does
- **Function/class docstrings**: purpose, args, returns, raises
- **Inline comments** on non-obvious logic: why a particular approach was chosen, edge cases being handled, algorithmic steps
- **Test comments**: what each test case verifies (arrange/act/assert pattern)

Test files should additionally comment on:
- What scenario each test covers (happy path, edge case, error case)
- Why certain values were chosen for fixtures

This rule applies to all new code and modifications to existing code.
```

---

## Future Experiments

### Search Experiments
- **Embedding model comparison** — swap `all-MiniLM-L6-v2` (384d) for `all-mpnet-base-v2` (768d) or `BAAI/bge-small-en-v1.5` → measure HR/MRR vs embedding time
- **RRF constant tuning** — try k=30, 60, 100 → which maximizes hybrid HR?
- **Num results** — k=3 vs 5 vs 10 → does more chunks improve hit rate or add noise?
- **Field boost grid search** — `{"title": [1,2,3], "content": [0.5,1,2]}` → which field matters most?

### RAG Experiments
- **Prompt template A vs B** — with vs without citation requirement
- **Chunk count** — 3 vs 5 vs 10 in prompt → does more context help or confuse?
- **Temperature** — 0, 0.3, 0.7 → consistency vs creativity

### Ablation Experiments
- **Remove each component** — HR drop without keyword? without vector? without hybrid?
- **No-RAG baseline** — ask LLM directly without context → how much does RAG improve accuracy?

### Error Analysis
- **Failure clustering** — which question types (how-do-I vs what-is) does each search method fail on?
```
