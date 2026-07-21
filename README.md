# PyDoc Assistant

A **RAG-powered Q&A system** over Python library documentation. Ask questions in natural language and receive answers grounded in official documentation with source citations.

Built as the capstone project for [DataTalks.Club LLM Zoomcamp 2026](https://github.com/DataTalksClub/llm-zoomcamp).

---

## Problem Statement

Python developers frequently consult library documentation (FastAPI, Pydantic, Requests, etc.) but:
- Official docs are extensive and hard to search through
- Generic web search returns noisy, sometimes outdated results
- There is no single interface that provides precise, cited answers

**PyDoc Assistant** solves this by combining hybrid search (keyword + vector) with an LLM to deliver answers with direct source citations from the official documentation.

---

## Dataset

**Primary:** [FastAPI](https://fastapi.tiangolo.com/) documentation — a Sphinx/ReadTheDocs-generated site with clear URL structure and section hierarchy.

**Pipeline:**
1. Fetch `sitemap.xml` to discover all doc pages
2. Scrape HTML with `httpx` + `BeautifulSoup`
3. Chunk by section heading (`<h1>`, `<h2>`, `<h3>`) — preserves document structure
4. Overlapping chunks with sliding window for better retrieval coverage
5. Store raw chunks as JSONL for reproducibility
6. Build keyword index (minsearch TF-IDF) and vector embeddings (sentence-transformers `all-MiniLM-L6-v2`)
7. Embeddings stored as numpy arrays; chunk metadata as JSON

**Extensible:** Same pipeline works for any ReadTheDocs-hosted project (Pydantic, Requests, SQLAlchemy, Click).

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│  INGESTION                                                               │
│  ReadTheDocs HTML ──▶ scrape & extract ──▶ chunk by heading             │
│  ──▶ store JSONL + minsearch index + vector embeddings (numpy)          │
└──────────────────────────┬──────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  HYBRID SEARCH                                                           │
│  User Query                                                              │
│     ├──▶ Keyword Search (minsearch TF-IDF)                               │
│     ├──▶ Vector Search (sentence-transformers, cosine similarity)        │
│     └──▶ Hybrid Fusion (Reciprocal Rank Fusion / RRF)                    │
│  Returns top-5 ranked chunks with metadata                               │
└──────────────────────────┬──────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  RAG FLOW                                                                │
│  Top-5 chunks ──▶ build_prompt(query, chunks)                            │
│  ──▶ OpenAI GPT-4o-mini ──▶ answer with inline source citations          │
│  ──▶ LLM-as-judge (inline relevance evaluation for monitoring)           │
└──────────────────────────┬──────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  INTERFACE + MONITORING                                                  │
│  Streamlit App ◀──▶ PostgreSQL (conversations + feedback)                │
│                       └──▶ Grafana Dashboard (6 charts)                  │
└─────────────────────────────────────────────────────────────────────────┘
```

### Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| **Hybrid search (keyword + vector)** | Keyword excels at exact term matching; vector captures semantic similarity. RRF fusion combines both strengths. |
| **Section-heading chunking** | Preserves document structure; each chunk is a coherent, self-contained unit. |
| **In-memory vector index (numpy)** | Sufficient for course scale; avoids external vector DB complexity. |
| **GPT-4o-mini as default LLM** | Strong quality-to-cost ratio. GPT-4o available for comparison. |
| **Streamlit for UI** | Fastest path to a polished Python UI; covered in the course. |
| **PostgreSQL + Grafana for monitoring** | Standard open-source stack; covers all monitoring requirements. |

---

## Tech Stack

| Component | Technology |
|-----------|------------|
| Language | Python 3.12 |
| Package manager | `uv` |
| Web scraping | `httpx`, `beautifulsoup4` |
| Keyword search | `minsearch` (TF-IDF/BM25-like) |
| Embeddings | `sentence-transformers` (all-MiniLM-L6-v2, 384-dim) |
| Vector search | numpy cosine similarity |
| LLM | OpenAI API (GPT-4o-mini, GPT-4o) |
| UI | Streamlit |
| Database | PostgreSQL 16 |
| Monitoring | Grafana |
| Containerization | Docker, Docker Compose |
| Bonus: Reranking | Cross-encoder (`cross-encoder/ms-marco-MiniLM-L-6-v2`) |

---

## Project Structure

```
├── app/                        # Application code
│   ├── main.py                 # Streamlit entry point
│   ├── rag.py                  # RAG flow (retrieve → prompt → LLM → answer)
│   ├── search.py               # Hybrid search (keyword, vector, RRF fusion)
│   ├── llm.py                  # OpenAI LLM client
│   ├── db.py                   # PostgreSQL client (conversations + feedback)
│   └── config.py               # Configuration / constants
│
├── ingest/                     # Data ingestion pipeline
│   ├── scrape.py               # Sitemap discovery + HTML scraping
│   ├── chunk.py                # Section-heading chunking logic
│   ├── embed.py                # Embedding generation + vector index build
│   └── run.py                  # Orchestration: scrape → chunk → index
│
├── notebooks/                  # Evaluation notebooks
│   ├── 01-ingestion.ipynb      # Scrape, chunk, index demonstration
│   ├── 02-ground-truth.ipynb   # LLM-generated Q&A pairs
│   ├── 03-retrieval-eval.ipynb # Hit rate, MRR, boost optimization
│   └── 04-rag-eval.ipynb       # LLM-as-judge, model comparison
│
├── data/                       # Data artifacts
│   ├── raw/                    # Raw scraped chunks (JSONL)
│   └── processed/              # Embeddings (npy), chunk metadata (json)
│
├── grafana/                    # Grafana provisioning
│   └── init.py                 # Auto-create datasource + dashboard
│
├── pyproject.toml              # Project metadata + dependencies
├── uv.lock                     # Reproducible dependency lockfile
├── Dockerfile                  # App container definition
├── docker-compose.yaml         # Multi-service orchestration
├── init.py                     # First-run setup (DB tables + Grafana)
└── .env.example                # Environment variable template
```

---

## Setup & Usage

### Prerequisites
- Python 3.12
- `uv` package manager
- OpenAI API key

### Installation

```bash
# Clone the repository
git clone <repo-url>
cd llm-zoomcamp-project

# Create environment and install dependencies
uv sync

# Set your OpenAI API key
cp .env.example .env
# Edit .env with your key: OPENAI_API_KEY=sk-...
```

### Ingestion

```bash
# Scrape, chunk, and index FastAPI documentation
python -m ingest.run --library fastapi
```

### Run the App

```bash
# Start the Streamlit UI
streamlit run app/main.py
```

### Run with Docker

```bash
docker compose up --build -d
python init.py  # Create DB tables + provision Grafana
```

Access:
- **Streamlit App:** http://localhost:8501
- **Grafana Dashboard:** http://localhost:3000 (admin/admin)

---

## Evaluation Methodology

### Retrieval Evaluation

**Ground truth:** For each doc chunk, GPT generates a natural question that the chunk answers.

**Metrics:**
- **Hit Rate** — Fraction of queries where the correct chunk appears in top-k results
- **Mean Reciprocal Rank (MRR)** — Average of `1 / rank` of the first relevant result

**Compared strategies:**

| Strategy | Hit Rate | MRR |
|----------|----------|-----|
| Keyword only (no boost) | X.XX | X.XX |
| Keyword only (optimized boost) | X.XX | X.XX |
| Vector only | X.XX | X.XX |
| Hybrid (keyword + vector, RRF) | X.XX | X.XX |

**Boost optimization:** Random search over field weights (0.0–3.0), 30 iterations, maximizing hit rate on validation set.

### LLM Output Evaluation

**LLM-as-judge:** A separate LLM call classifies answers as `RELEVANT`, `PARTLY_RELEVANT`, or `NON_RELEVANT` relative to the question.

| Model | % RELEVANT | % PARTLY | % NON | Cost per 1K queries |
|-------|-----------|----------|-------|-------------------|
| gpt-4o-mini | XX% | XX% | XX% | $X.XX |
| gpt-4o | XX% | XX% | XX% | $X.XX |

---

## Monitoring

**PostgreSQL** stores every conversation (question, answer, model, tokens, cost, response time, relevance) plus user feedback.

**Grafana dashboard** (6 charts):
1. Questions over time (time series bar)
2. Relevance distribution (pie chart)
3. Average response time (stat)
4. API cost over time (time series line)
5. User feedback ratio (thumbs up/down bar)
6. Model comparison table (count, avg response time)

---

## Bonus Features

| Feature | Description |
|---------|-------------|
| **Hybrid Search (+1 pt)** | Keyword + vector with RRF fusion; separately evaluated |
| **Query Rewriting (+1 pt)** | LLM rewrites user questions for better retrieval matching (e.g., "dep inj" → "dependency injection") |
| **Cross-encoder Reranking (+1 pt)** | Reranks top-20 hybrid results using cross-encoder model for higher precision |

---

## Scoring Checklist (LLM Zoomcamp Rubric)

| Criterion | Points | Where to Find |
|-----------|--------|---------------|
| Problem description | 2 | README (this document) |
| Retrieval flow | 2 | `app/search.py`, `ingest/` |
| Retrieval evaluation | 2 | `notebooks/03-retrieval-eval.ipynb` |
| LLM evaluation | 2 | `notebooks/04-rag-eval.ipynb` |
| Interface | 2 | `app/main.py` (Streamlit) |
| Ingestion pipeline | 2 | `ingest/run.py`, `ingest/scrape.py`, `ingest/chunk.py` |
| Monitoring | 2 | PostgreSQL schema, Grafana dashboard |
| Containerization | 2 | `Dockerfile`, `docker-compose.yaml` |
| Reproducibility | 2 | `uv.lock`, `.env.example`, setup instructions |
| Hybrid search (bonus) | +1 | `app/search.py` — keyword, vector, hybrid functions |
| Reranking (bonus) | +1 | `app/search.py` — cross-encoder rerank function |
| Query rewriting (bonus) | +1 | `app/search.py` — query rewrite function |
| **Total** | **21** | |

---

## Author

Zhi Yuan Wong ([@wong80](https://github.com/wong80))

Built for the DataTalks.Club [LLM Zoomcamp 2026](https://github.com/DataTalksClub/llm-zoomcamp).
