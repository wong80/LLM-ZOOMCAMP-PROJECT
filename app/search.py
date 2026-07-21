"""Hybrid search: keyword (minsearch), vector (semantic), and RRF fusion."""

import numpy as np
from minsearch import Index
from sentence_transformers import SentenceTransformer
from typing import Optional

from ingest.index import load_minsearch_index, EMBEDDING_MODEL_NAME

RRF_K = 60

_embedding_model: Optional[SentenceTransformer] = None


def _get_embedder() -> SentenceTransformer:
    global _embedding_model
    if _embedding_model is None:
        _embedding_model = SentenceTransformer(EMBEDDING_MODEL_NAME)
    return _embedding_model


def _load_default_index(library: str = "fastapi") -> Optional[Index]:
    return load_minsearch_index(library)


def _load_default_embeddings(library: str = "fastapi") -> Optional[tuple[np.ndarray, list[dict]]]:
    import json, os
    emb_path = f"data/processed/{library}/embeddings.npy"
    meta_path = f"data/processed/{library}/chunks.json"
    if not os.path.exists(emb_path) or not os.path.exists(meta_path):
        return None
    return np.load(emb_path), json.load(open(meta_path, encoding="utf-8"))


def keyword_search(
    query: str,
    index: Optional[Index] = None,
    num_results: int = 5,
    boost_dict: Optional[dict] = None,
) -> list[dict]:
    if not query.strip():
        return []
    if index is None:
        index = _load_default_index()
    if index is None:
        return []
    return index.search(query, num_results=num_results, boost_dict=boost_dict or {})


def vector_search(
    query: str,
    embeddings: Optional[np.ndarray] = None,
    chunks: Optional[list[dict]] = None,
    num_results: int = 5,
    model: Optional[SentenceTransformer] = None,
) -> list[dict]:
    if not query.strip():
        return []
    if embeddings is None or chunks is None:
        loaded = _load_default_embeddings()
        if loaded is None:
            return []
        embeddings, chunks = loaded
    if model is None:
        model = _get_embedder()
    query_vec = model.encode([query], convert_to_numpy=True)
    sims = _cosine_similarity(query_vec, embeddings)[0]
    top_indices = np.argsort(-sims)[:num_results]
    return [{**chunks[i], "score": float(sims[i])} for i in top_indices]


def hybrid_search(
    query: str,
    method: str = "hybrid",
    index: Optional[Index] = None,
    embeddings: Optional[np.ndarray] = None,
    chunks: Optional[list[dict]] = None,
    num_results: int = 5,
    model: Optional[SentenceTransformer] = None,
) -> list[dict]:
    if method == "keyword":
        return keyword_search(query, index=index, num_results=num_results)
    elif method == "vector":
        return vector_search(query, embeddings=embeddings, chunks=chunks, num_results=num_results, model=model)
    elif method == "hybrid":
        kw = keyword_search(query, index=index, num_results=num_results * 4)
        vec = vector_search(query, embeddings=embeddings, chunks=chunks, num_results=num_results * 4, model=model)
        return _rrf_fuse(kw, vec, num_results)
    raise ValueError(f"Unknown method: {method}. Use 'keyword', 'vector', or 'hybrid'.")


def search(query: str, method: str = "hybrid", num_results: int = 5) -> list[dict]:
    """Convenience wrapper around hybrid_search."""
    return hybrid_search(query, method=method, num_results=num_results)


def _rrf_fuse(kw_results: list[dict], vec_results: list[dict], num_results: int) -> list[dict]:
    """Reciprocal Rank Fusion of keyword and vector results."""
    scores: dict[str, float] = {}
    chunk_map: dict[str, dict] = {}
    for rank, r in enumerate(kw_results, start=1):
        scores[r["id"]] = scores.get(r["id"], 0.0) + 1.0 / (RRF_K + rank)
        chunk_map[r["id"]] = r
    for rank, r in enumerate(vec_results, start=1):
        scores[r["id"]] = scores.get(r["id"], 0.0) + 1.0 / (RRF_K + rank)
        if r["id"] not in chunk_map:
            chunk_map[r["id"]] = r
    ranked = sorted(scores.items(), key=lambda x: -x[1])
    return [{**chunk_map[rid], "score": round(score, 6)} for rid, score in ranked[:num_results]]


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    a_norm = a / np.linalg.norm(a, axis=1, keepdims=True).clip(min=1e-12)
    b_norm = b / np.linalg.norm(b, axis=1, keepdims=True).clip(min=1e-12)
    return a_norm @ b_norm.T


_ABBREVIATIONS = {
    "dep inj": "dependency injection",
    "path op": "path operation",
    "req": "request",
    "resp": "response",
    "val": "validation",
}


def rewrite_query(query: str, method: str = "direct") -> str:
    if method == "llm":
        from app.llm import llm
        prompt = f"Rewrite this developer question to be more searchable:\n{query}"
        result, _ = llm(prompt, model="gpt-4o-mini")
        return result
    q = query.lower()
    for abbr, full in _ABBREVIATIONS.items():
        q = q.replace(abbr, full)
    return q if q != query.lower() else query


_reranker = None


def _get_reranker():
    global _reranker
    if _reranker is None:
        from sentence_transformers import CrossEncoder
        _reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
    return _reranker


def rerank(query: str, chunks: list[dict]) -> list[dict]:
    if not chunks:
        return []
    pairs = [(query, c["content"]) for c in chunks]
    scores = _get_reranker().predict(pairs)
    scored = list(zip(chunks, scores))
    scored.sort(key=lambda x: x[1], reverse=True)
    return [c for c, _ in scored]
