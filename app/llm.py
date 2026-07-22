"""OpenAI LLM wrapper."""

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

MODEL_PRICING = {
    "gpt-4o-mini": {"input": 0.15 / 1e6, "output": 0.60 / 1e6},
    "gpt-4o": {"input": 2.50 / 1e6, "output": 10.00 / 1e6},
}

_client = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI()
    return _client


def llm(prompt: str, model: str = "gpt-4o-mini") -> tuple[str, dict]:
    client = _get_client()
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


def llm_stream(prompt: str, model: str = "gpt-4o-mini"):
    client = _get_client()
    stream = client.responses.create(
        model=model,
        input=[{"role": "user", "content": prompt}],
        stream=True
    )
    for event in stream:
        if event.type == "response.output_text.delta":
            yield event.delta


def calculate_cost(model: str, tokens: dict) -> float:
    pricing = MODEL_PRICING.get(model)
    if pricing is None:
        raise ValueError(f"Unknown model: {model}. Available: {list(MODEL_PRICING.keys())}")
    return pricing["input"] * tokens.get("prompt_tokens", 0) + pricing["output"] * tokens.get("completion_tokens", 0)
