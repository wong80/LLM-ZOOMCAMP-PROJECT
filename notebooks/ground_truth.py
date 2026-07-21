"""Ground truth generation: for each chunk, ask LLM to produce a question it answers."""

import json
import os
from app.llm import llm


def generate_question(chunk: dict, model: str = "gpt-4o-mini") -> dict:
    prompt = f"""Given this documentation section, generate a natural question that a developer might ask, which this section answers.

Section Title: {chunk['title']}
Content: {chunk['content']}

Return JSON: {{"question": "...", "relevant_chunk_id": "{chunk['id']}"}}"""
    text, _ = llm(prompt, model=model)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"question": text.strip(), "relevant_chunk_id": chunk["id"]}


def generate_ground_truth(chunks: list[dict], model: str = "gpt-4o-mini") -> list[dict]:
    results = []
    for c in chunks:
        result = generate_question(c, model=model)
        results.append(result)
    return results
