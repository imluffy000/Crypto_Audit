"""LLM client interface and a local Ollama implementation (stdlib HTTP, no extra dependencies)."""

import json
import socket
import time
import urllib.error
import urllib.request
from typing import List, Optional

from cryptoaudit.llm.schemas import LLMRequest, LLMResponse
from cryptoaudit.utils.errors import CryptoAuditError, ErrorCode

DEFAULT_OLLAMA_URL = "http://localhost:11434"








class OllamaClient:
    """Single-shot, non-streaming generation against a local Ollama server."""

    def __init__(self, base_url: str = DEFAULT_OLLAMA_URL, timeout: float = 300.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def generate(self, request: LLMRequest) -> LLMResponse:
        payload = {
            "model": request.model,
            "system": request.system,
            "prompt": request.prompt,
            "stream": False,
            "options": {"temperature": request.temperature, "seed": request.seed, "num_predict": request.max_tokens},
        }
        if request.num_ctx is not None:
            # Ollama's default context is small and it silently drops the start of longer prompts.
            payload["options"]["num_ctx"] = request.num_ctx
        started = time.perf_counter()
        data = self._post("/api/generate", payload)
        text = data.get("response")
        if not isinstance(text, str):
            raise CryptoAuditError(ErrorCode.LLM_ERROR, "Ollama response has no 'response' text")
        return LLMResponse(
            text=text,
            model=data.get("model", request.model),
            duration_seconds=round(time.perf_counter() - started, 3),
            model_digest=self.model_digest(request.model),
        )

    def _tags(self) -> Optional[List[dict]]:
        try:
            req = urllib.request.Request(f"{self.base_url}/api/tags", method="GET")
            with urllib.request.urlopen(req, timeout=min(self.timeout, 10)) as resp:
                return json.loads(resp.read().decode("utf-8")).get("models", [])
        except (urllib.error.URLError, OSError, ValueError):
            return None

    @staticmethod
    def _matches(entry: dict, model: str) -> bool:
        names = {entry.get("name"), entry.get("model")}
        return model in names or (":" not in model and f"{model}:latest" in names)

    def model_digest(self, model: str) -> Optional[str]:
        """Best-effort model digest for reproducibility metadata."""
        for entry in self._tags() or []:
            if self._matches(entry, model):
                return entry.get("digest")
        return None

    def is_available(self, model: str) -> bool:
        """True when the Ollama server answers and has the model pulled."""
        return any(self._matches(entry, model) for entry in self._tags() or [])

    def _post(self, path: str, payload: dict) -> dict:
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{self.base_url}{path}", data=body, headers={"Content-Type": "application/json"}, method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except (socket.timeout, TimeoutError) as exc:
            raise CryptoAuditError(ErrorCode.TIMEOUT, f"LLM request timed out after {self.timeout}s") from exc
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:300]
            raise CryptoAuditError(ErrorCode.LLM_ERROR, f"Ollama HTTP {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            if isinstance(exc.reason, (socket.timeout, TimeoutError)):
                raise CryptoAuditError(ErrorCode.TIMEOUT, f"LLM request timed out after {self.timeout}s") from exc
            raise CryptoAuditError(ErrorCode.LLM_ERROR, f"Cannot reach Ollama at {self.base_url}: {exc.reason}") from exc
        except ValueError as exc:
            raise CryptoAuditError(ErrorCode.LLM_ERROR, "Ollama returned invalid JSON") from exc
