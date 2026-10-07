"""LLM access layer. The LLM generates candidates only; it never detects or judges."""

from cryptoaudit.llm.client import DEFAULT_MODEL, LLMClient
from cryptoaudit.llm.ollama_client import DEFAULT_OLLAMA_URL, OllamaClient
from cryptoaudit.llm.schemas import LLMRequest, LLMResponse

__all__ = ["DEFAULT_MODEL", "DEFAULT_OLLAMA_URL", "LLMClient", "LLMRequest", "LLMResponse", "OllamaClient"]
