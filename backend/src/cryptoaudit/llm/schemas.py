"""Request/response schemas exchanged with LLM clients."""

from typing import Optional

from pydantic import BaseModel


class LLMRequest(BaseModel):
    model: str
    system: str
    prompt: str
    temperature: float = 0.0
    seed: int = 0
    max_tokens: int = 4096  # generation limit (Ollama num_predict)
    num_ctx: Optional[int] = None  # context window; None = server default


class LLMResponse(BaseModel):
    text: str
    model: str
    duration_seconds: float = 0.0
    model_digest: Optional[str] = None
