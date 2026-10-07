"""Chooses the LLM backend for each call: the first configured backend that is available."""

import threading
import time
from dataclasses import dataclass
from typing import Callable, List, Optional

from cryptoaudit.llm.schemas import LLMRequest, LLMResponse
from cryptoaudit.utils.errors import CryptoAuditError, ErrorCode

AVAILABILITY_CACHE_SECONDS = 30


@dataclass
class LLMBackend:
    name: str  # "ollama" | "openrouter"
    client: object  # has generate(LLMRequest) -> LLMResponse
    model: str
    context_window: int
    is_available: Callable[[], bool]
    send_num_ctx: bool  # Ollama needs num_ctx; hosted APIs manage their own context


class RoutingLLMClient:
    """
    LLMClient that delegates to the first available backend (e.g. local Ollama, then OpenRouter).
    The backend actually used is reported in every LLMResponse.provider / .model.
    """

    def __init__(self, backends: List[LLMBackend]) -> None:
        self.backends = backends
        self._cached: Optional[LLMBackend] = None
        self._cached_at = 0.0
        self._refreshing = threading.Event()

    def active(self) -> Optional[LLMBackend]:
        now = time.monotonic()
        if self._cached is not None and now - self._cached_at < AVAILABILITY_CACHE_SECONDS:
            return self._cached
        self._cached = next((b for b in self.backends if b.is_available()), None)
        self._cached_at = now
        return self._cached

    def peek(self) -> Optional[LLMBackend]:
        """
        The last known available backend, without waiting on the network. When that knowledge is
        stale (or missing) a refresh runs in the background. Used for status reporting only; calls
        that generate text go through active(), which checks before answering.
        """
        if time.monotonic() - self._cached_at >= AVAILABILITY_CACHE_SECONDS and not self._refreshing.is_set():
            self._refreshing.set()

            def refresh() -> None:
                try:
                    self.active()
                finally:
                    self._refreshing.clear()

            threading.Thread(target=refresh, name="llm-availability", daemon=True).start()
        return self._cached

    def available(self) -> bool:
        return self.active() is not None

    def context_window(self) -> Optional[int]:
        backend = self.active()
        return backend.context_window if backend else None

    def describe(self, wait: bool = True) -> str:
        backend = self.active() if wait else self.peek()
        if backend is not None:
            return f"{backend.name}:{backend.model}"
        return " / ".join(f"{b.name}:{b.model}" for b in self.backends) or "none"

    def unavailable_reason(self) -> str:
        if not self.backends:
            return "No LLM backend is configured"
        return "No LLM backend is available (" + "; ".join(f"{b.name} model '{b.model}' unavailable" for b in self.backends) + ")"

    def generate(self, request: LLMRequest) -> LLMResponse:
        backend = self.active()
        if backend is None:
            raise CryptoAuditError(ErrorCode.LLM_ERROR, self.unavailable_reason())
        routed = request.model_copy(
            update={"model": backend.model, "num_ctx": backend.context_window if backend.send_num_ctx else None}
        )
        response = backend.client.generate(routed)
        return response.model_copy(update={"provider": backend.name})
