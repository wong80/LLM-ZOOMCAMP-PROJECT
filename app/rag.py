"""RAG flow: search → build prompt → LLM → answer with citations."""

import time
from app.search import search
from app.llm import llm, calculate_cost
from app.evaluation import evaluate_relevance


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


def rag(query: str, model: str = "gpt-4o-mini") -> dict:
    t0 = time.time()
    chunks = search(query)
    prompt = build_prompt(query, chunks)
    answer, token_stats = llm(prompt, model)
    relevance, eval_tokens = evaluate_relevance(query, answer)
    t1 = time.time()

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
