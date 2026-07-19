"""Build and persist keyword (minsearch) and vector (sentence-transformers) indexes."""

import os
import json
import pickle
import numpy as np
from minsearch import Index
from sentence_transformers import SentenceTransformer
from typing import Optional

EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"


def build_minsearch_index(
    chunks: list[dict],
    text_fields: Optional[list[str]] = None,
    keyword_fields: Optional[list[str]] = None,
) -> Index:
    if text_fields is None:
        text_fields = ["title", "section", "content"]
    if keyword_fields is None:
        keyword_fields = ["id", "doc_library"]
    index = Index(text_fields=text_fields, keyword_fields=keyword_fields)
    index.fit(chunks)
    return index


def save_minsearch_index(index: Index, library_name: str) -> str:
    """Persist a minsearch index to disk via pickle."""
    path = f"data/processed/{library_name}/minsearch.pkl"
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        pickle.dump(index, f)
    return path


def load_minsearch_index(library_name: str) -> Optional[Index]:
    """Load a minsearch index from disk, or None."""
    path = f"data/processed/{library_name}/minsearch.pkl"
    if not os.path.exists(path):
        return None
    with open(path, "rb") as f:
        return pickle.load(f)


def build_vector_index(
    chunks: list[dict],
    model: Optional[SentenceTransformer] = None,
) -> tuple[np.ndarray, list[dict]]:
    if model is None:
        model = SentenceTransformer(EMBEDDING_MODEL_NAME)
    texts = [c["content"] for c in chunks]
    embeddings = model.encode(texts, show_progress_bar=True, convert_to_numpy=True)
    return embeddings, chunks


def save_vector_index(embeddings: np.ndarray, library_name: str) -> str:
    """Save embedding matrix as .npy file."""
    path = f"data/processed/{library_name}/embeddings.npy"
    os.makedirs(os.path.dirname(path), exist_ok=True)
    np.save(path, embeddings)
    return path


def save_chunks_metadata(chunks: list[dict], library_name: str) -> str:
    """Save chunk metadata (no embeddings) as JSON."""
    path = f"data/processed/{library_name}/chunks.json"
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(chunks, f, ensure_ascii=False, indent=2)
    return path
