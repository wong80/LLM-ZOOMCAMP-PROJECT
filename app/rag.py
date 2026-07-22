"""RAG flow: search → build prompt → LLM → answer with citations."""

import time
from app.search import hybrid_search
from app.llm import llm, llm_stream, calculate_cost
from app.evaluation import evaluate_relevance

_rag_cache: dict[tuple[str, str, str], dict] = {}
_RAG_CACHE_MAXSIZE = 128


def build_prompt(query: str, chunks: list[dict]) -> str:
    context_parts = []
    for c in chunks:
        context_parts.append(
            f'[Source: "{c.get("title", "Untitled")}" from {c.get("url", "")}]'
            f'\nContent: {c.get("content", "")}'
        )
    context = "\n\n".join(context_parts)

    no_info = "I don't have enough information to answer that."
    return f"""You are a Python documentation assistant. Answer the QUESTION using only the CONTEXT below. If the answer isn't in the context, say "{no_info}"

For each piece of information you use, cite the source section title and URL in brackets like: [Section: "Title"](url).

CONTEXT:
{context}

QUESTION:
{query}

ANSWER:"""


def rag(query: str, library: str = "fastapi", model: str = "gpt-4o-mini") -> dict:
    t0 = time.time()
    if not query.strip():
        return {"answer": "", "citations": [], "model": model, "response_time": 0,
                "relevance": "", "cached": False, "prompt_tokens": 0,
                "completion_tokens": 0, "total_tokens": 0,
                "eval_tokens": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                "cost": 0.0}
    key = (query, library, model)
    if key in _rag_cache:
        result = dict(_rag_cache[key])
        result["response_time"] = time.time() - t0
        result["cached"] = True
        return result

    library = library or "fastapi"
    chunks = hybrid_search(query, library=library)
    prompt = build_prompt(query, chunks)
    answer, token_stats = llm(prompt, model)
    relevance, eval_tokens = evaluate_relevance(query, answer)
    t1 = time.time()

    result = {
        "answer": answer,
        "citations": [c["url"] for c in chunks],
        "model": model,
        "response_time": t1 - t0,
        "relevance": relevance,
        **token_stats,
        "eval_tokens": eval_tokens,
        "cost": calculate_cost(model, token_stats) + calculate_cost(model, eval_tokens),
        "cached": False,
    }
    if len(_rag_cache) < _RAG_CACHE_MAXSIZE:
        _rag_cache[key] = result
    return result


def rag_stream(query: str, library: str = "fastapi", model: str = "gpt-4o-mini"):
    if not query.strip():
        return
    library = library or "fastapi"
    chunks = hybrid_search(query, library=library)
    if not chunks:
        rag_stream.citations = []
        return
    rag_stream.citations = [c["url"] for c in chunks]
    prompt = build_prompt(query, chunks)
    yield from llm_stream(prompt, model=model)


