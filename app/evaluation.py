"""Evaluation metrics and LLM-as-judge relevance evaluation."""

import json
import random
import numpy as np
import pandas as pd
from app.llm import llm, calculate_cost


def evaluate_relevance(question: str, answer: str, model: str = "gpt-4o-mini") -> tuple[str, dict]:
    prompt = f"""Evaluate if the ANSWER addresses the QUESTION.

Classes:
- RELEVANT: Answer directly answers the question with correct info
- PARTLY_RELEVANT: Answer touches on the topic but doesn't fully answer
- NON_RELEVANT: Answer doesn't address the question

Question: {question}
Answer: {answer}

Return JSON: {{"relevance": "RELEVANT|PARTLY_RELEVANT|NON_RELEVANT", "reason": "..."}}"""
    text, tokens = llm(prompt, model=model)
    try:
        data = json.loads(text)
        label = data.get("relevance", "PARTLY_RELEVANT")
    except (json.JSONDecodeError, KeyError):
        label = "PARTLY_RELEVANT"
    if label not in ("RELEVANT", "PARTLY_RELEVANT", "NON_RELEVANT"):
        label = "PARTLY_RELEVANT"
    return label, tokens


def hit_rate(results: list[list[bool]]) -> float:
    if not results:
        return 0.0
    return sum(any(r) for r in results) / len(results)


def mrr(results: list[list[bool]]) -> float:
    if not results:
        return 0.0
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


def optimize_boosts(index, ground_truth: list[dict], iterations: int = 30) -> dict:
    best_hr, best_params = 0.0, {}
    fields = ["title", "section", "content"]
    for _ in range(iterations):
        params = {f: random.uniform(0.0, 3.0) for f in fields}
        def search_fn(q, p=params):
            return index.search(q, boost_dict=p, num_results=5)
        hr = hit_rate([
            [r["id"] == gt["relevant_chunk_id"] for r in search_fn(gt["question"])]
            for gt in ground_truth
        ])
        if hr > best_hr:
            best_hr, best_params = hr, params
    return best_params


def compare_models(questions: list[str], models: list[str]) -> pd.DataFrame:
    rows = []
    for q in questions:
        for m in models:
            from app.rag import rag
            result = rag(q, model=m)
            rows.append({"question": q, "model": m, "relevance": result["relevance"], "cost": result["cost"]})
    return pd.DataFrame(rows)


def comparison_summary(df: pd.DataFrame) -> pd.DataFrame:
    grouped = df.groupby("model").agg(
        **{"% RELEVANT": ("relevance", lambda x: (x == "RELEVANT").mean() * 100),
           "% PARTLY": ("relevance", lambda x: (x == "PARTLY_RELEVANT").mean() * 100),
           "% NON": ("relevance", lambda x: (x == "NON_RELEVANT").mean() * 100),
           "Cost per 1K queries": ("cost", lambda x: x.sum() / len(x) * 1000)}
    ).reset_index()
    return grouped
