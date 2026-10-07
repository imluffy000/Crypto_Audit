"""LLM client interface and a local Ollama implementation (stdlib HTTP, no extra dependencies)."""

import json
import socket
import time
import urllib.error
import urllib.request
from typing import Optional, Protocol

from pydantic import BaseModel

from cryptoaudit.utils.errors import CryptoAuditError, ErrorCode

DEFAULT_OLLAMA_URL = "http://localhost:11434"
DEFAULT_MODEL = "codellama:7b-instruct"


class LLMRequest(BaseModel):
    model: str
    system: str
    prompt: str
    temperature: float = 0.0
    seed: int = 0
    max_tokens: int = 4096


class LLMResponse(BaseModel):
    text: str
    model: str
    duration_seconds: float = 0.0
    model_digest: Optional[str] = None


class LLMClient(Protocol):
    def generate(self, request: LLMRequest) -> LLMResponse:
        """Return the model output, or raise CryptoAuditError(LLM_ERROR | TIMEOUT)."""
        ...


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

    def model_digest(self, model: str) -> Optional[str]:
        """Best-effort model digest for reproducibility metadata."""
        try:
            req = urllib.request.Request(f"{self.base_url}/api/tags", method="GET")
            with urllib.request.urlopen(req, timeout=min(self.timeout, 10)) as resp:
                tags = json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, OSError, ValueError):
            return None
        for entry in tags.get("models", []):
            if entry.get("name") == model or entry.get("model") == model:
                return entry.get("digest")
        return None

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
