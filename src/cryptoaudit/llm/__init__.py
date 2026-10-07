"""LLM access layer. The LLM generates candidates only; it never detects or judges."""

from cryptoaudit.llm.client import DEFAULT_MODEL, DEFAULT_OLLAMA_URL, LLMClient, LLMRequest, LLMResponse, OllamaClient

__all__ = ["DEFAULT_MODEL", "DEFAULT_OLLAMA_URL", "LLMClient", "LLMRequest", "LLMResponse", "OllamaClient"]
