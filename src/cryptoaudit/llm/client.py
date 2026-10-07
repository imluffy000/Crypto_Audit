"""LLM client interface. The LLM generates candidates only; it never detects or judges."""

from typing import Protocol

from cryptoaudit.llm.schemas import LLMRequest, LLMResponse

DEFAULT_MODEL = "codellama:7b-instruct"


class LLMClient(Protocol):
    def generate(self, request: LLMRequest) -> LLMResponse:
        """Return the model output, or raise CryptoAuditError(LLM_ERROR | TIMEOUT)."""
        ...
