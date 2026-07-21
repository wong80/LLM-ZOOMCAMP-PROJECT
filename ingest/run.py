"""Ingestion pipeline: scrape docs, chunk, build and persist indexes.

Usage: python -m ingest.run --library fastapi
"""

import argparse
import httpx
from sentence_transformers import SentenceTransformer

from ingest.scrape import get_doc_urls, scrape_page, USER_AGENT
from ingest.chunk import chunk_document
from ingest.index import (
    build_minsearch_index,
    save_minsearch_index,
    build_vector_index,
    save_vector_index,
    save_chunks_metadata,
    EMBEDDING_MODEL_NAME,
)

SITEMAP_MAP = {
    "fastapi": "https://fastapi.tiangolo.com/sitemap.xml",
}


def ingest_library(library_name: str, overlap: bool = True) -> dict:
    """Scrape, chunk, index, and persist one library's documentation."""
    sitemap_url = SITEMAP_MAP.get(library_name)
    if sitemap_url is None:
        raise ValueError(f"Unknown library: {library_name}. Available: {list(SITEMAP_MAP.keys())}")

    print(f"[ingest] Starting ingestion for '{library_name}'")
    with httpx.Client(headers={"User-Agent": USER_AGENT}, follow_redirects=True, timeout=30.0) as client:
        urls = get_doc_urls(sitemap_url, client=client)
        print(f"[ingest] Found {len(urls)} doc pages")
        all_chunks = []
        for i, url in enumerate(urls):
            print(f"[ingest] Scraping {i+1}/{len(urls)}: {url}")
            page = scrape_page(url, client=client)
            chunks = chunk_document(
                page["content_html"],
                base_url=url,
                doc_library=library_name,
                overlap=overlap,
                start_index=len(all_chunks),
            )
            all_chunks.extend(chunks)

    print(f"[ingest] Total chunks: {len(all_chunks)}")
    meta_path = save_chunks_metadata(all_chunks, library_name)
    print(f"[ingest]   -> metadata: {meta_path}")

    print(f"[ingest] Building minsearch index...")
    index = build_minsearch_index(all_chunks)
    index_path = save_minsearch_index(index, library_name)
    print(f"[ingest]   -> minsearch index: {index_path}")

    print(f"[ingest] Generating embeddings with {EMBEDDING_MODEL_NAME}...")
    model = SentenceTransformer(EMBEDDING_MODEL_NAME)
    embeddings, _ = build_vector_index(all_chunks, model=model)
    emb_path = save_vector_index(embeddings, library_name)
    print(f"[ingest]   -> embeddings: {emb_path}")

    return {
        "library": library_name,
        "total_chunks": len(all_chunks),
        "metadata_path": meta_path,
        "index_path": index_path,
        "embeddings_path": emb_path,
        "num_pages_scraped": len(urls),
    }


def main():
    parser = argparse.ArgumentParser(description="Ingest Python library documentation")
    parser.add_argument("--library", default="fastapi", choices=list(SITEMAP_MAP.keys()),
                        help="Library to ingest")
    parser.add_argument("--overlap", action="store_true", default=True,
                        help="Enable overlapping chunks (default: on)")
    args = parser.parse_args()
    result = ingest_library(library_name=args.library, overlap=args.overlap)
    print(f"\nSummary: {result['total_chunks']} chunks from {result['num_pages_scraped']} pages")


if __name__ == "__main__":
    main()
