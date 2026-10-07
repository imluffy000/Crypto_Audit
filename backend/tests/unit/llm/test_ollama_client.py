"""Ollama client tests (HTTP mocked; no real LLM needed)."""

import io
import json
import urllib.error

import pytest

from cryptoaudit.llm import LLMRequest, OllamaClient
from cryptoaudit.utils.errors import CryptoAuditError, ErrorCode


class _Resp(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def test_ollama_client_sends_deterministic_options(monkeypatch):
    sent = {}

    def fake_urlopen(req, timeout):
        if req.full_url.endswith("/api/tags"):
            return _Resp(json.dumps({"models": [{"name": "m:1", "digest": "d1"}]}).encode())
        sent.update(json.loads(req.data.decode()))
        return _Resp(json.dumps({"response": "ok", "model": "m:1"}).encode())

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    response = OllamaClient("http://ollama:11434").generate(LLMRequest(model="m:1", system="s", prompt="p", seed=3))
    assert response.text == "ok" and response.model_digest == "d1"
    assert sent["stream"] is False
    assert sent["options"] == {"temperature": 0.0, "seed": 3, "num_predict": 4096}


def test_ollama_unreachable_raises_llm_error(monkeypatch):
    def fake_urlopen(req, timeout):
        raise urllib.error.URLError("connection refused")

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    with pytest.raises(CryptoAuditError) as excinfo:
        OllamaClient().generate(LLMRequest(model="m", system="s", prompt="p"))
    assert excinfo.value.code is ErrorCode.LLM_ERROR


def test_ollama_timeout_raises_timeout(monkeypatch):
    def fake_urlopen(req, timeout):
        raise TimeoutError()

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    with pytest.raises(CryptoAuditError) as excinfo:
        OllamaClient().generate(LLMRequest(model="m", system="s", prompt="p"))
    assert excinfo.value.code is ErrorCode.TIMEOUT
