"""
OpenRouter client (OpenAI-compatible chat completions; stdlib HTTP).

Unlike Ollama this is a remote service: prompts - including the code being repaired - are sent
to OpenRouter and the model provider it routes to. It is only used when explicitly configured.
"""

import json
import socket
import time
import urllib.error
import urllib.request
from typing import Optional, Set

from cryptoaudit.llm.schemas import LLMRequest, LLMResponse
from cryptoaudit.utils.errors import CryptoAuditError, ErrorCode

DEFAULT_OPENROUTER_URL = "https://openrouter.ai/api/v1"
DEFAULT_OPENROUTER_MODEL = "qwen/qwen-2.5-coder-32b-instruct"
MODELS_CACHE_SECONDS = 300


class OpenRouterClient:
    name = "openrouter"

    def __init__(self, api_key: str, base_url: str = DEFAULT_OPENROUTER_URL, timeout: float = 300.0, app_url: str = "") -> None:
        self._api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.app_url = app_url
        self._models: Optional[Set[str]] = None
        self._models_at = 0.0

    def _headers(self) -> dict:
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            "X-Title": "CryptoAudit",
        }
        if self.app_url:
            headers["HTTP-Referer"] = self.app_url
        return headers

    def generate(self, request: LLMRequest) -> LLMResponse:
        payload = {
            "model": request.model,
            "messages": [{"role": "system", "content": request.system}, {"role": "user", "content": request.prompt}],
            "temperature": request.temperature,
            "seed": request.seed,
            "max_tokens": request.max_tokens,
            "stream": False,
        }
        started = time.perf_counter()
        data = self._request("POST", "/chat/completions", payload)
        try:
            text = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            message = (data.get("error") or {}).get("message") if isinstance(data, dict) else None
            raise CryptoAuditError(ErrorCode.LLM_ERROR, f"OpenRouter returned no completion{': ' + message if message else ''}") from None
        if not isinstance(text, str):
            raise CryptoAuditError(ErrorCode.LLM_ERROR, "OpenRouter completion has no text content")
        return LLMResponse(
            text=text,
            model=data.get("model", request.model),
            duration_seconds=round(time.perf_counter() - started, 3),
            provider=self.name,
        )

    def is_available(self, model: str) -> bool:
        """True when an API key is configured and OpenRouter lists the model."""
        if not self._api_key:
            return False
        now = time.monotonic()
        if self._models is None or now - self._models_at > MODELS_CACHE_SECONDS:
            try:
                data = self._request("GET", "/models", None, timeout=min(self.timeout, 15))
                self._models = {m.get("id") for m in data.get("data", []) if isinstance(m, dict)}
                self._models_at = now
            except CryptoAuditError:
                return False
        return model in self._models

    def _request(self, method: str, path: str, payload: Optional[dict], timeout: Optional[float] = None) -> dict:
        body = json.dumps(payload).encode("utf-8") if payload is not None else None
        req = urllib.request.Request(f"{self.base_url}{path}", data=body, headers=self._headers(), method=method)
        try:
            with urllib.request.urlopen(req, timeout=timeout or self.timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except (socket.timeout, TimeoutError) as exc:
            raise CryptoAuditError(ErrorCode.TIMEOUT, f"OpenRouter request timed out after {timeout or self.timeout}s") from exc
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:300]
            reasons = {401: "invalid API key", 402: "insufficient OpenRouter credits", 429: "rate limited"}
            raise CryptoAuditError(ErrorCode.LLM_ERROR, f"OpenRouter HTTP {exc.code} ({reasons.get(exc.code, 'error')}): {detail}") from exc
        except urllib.error.URLError as exc:
            if isinstance(exc.reason, (socket.timeout, TimeoutError)):
                raise CryptoAuditError(ErrorCode.TIMEOUT, "OpenRouter request timed out") from exc
            raise CryptoAuditError(ErrorCode.LLM_ERROR, f"Cannot reach OpenRouter: {exc.reason}") from exc
        except ValueError as exc:
            raise CryptoAuditError(ErrorCode.LLM_ERROR, "OpenRouter returned invalid JSON") from exc
