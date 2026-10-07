"""OpenRouter client (HTTP mocked) and backend routing: Ollama first, OpenRouter as fallback."""

import io
import json
import urllib.error

import pytest

from cryptoaudit.config.settings import Settings
from cryptoaudit.llm.openrouter_client import OpenRouterClient
from cryptoaudit.llm.router import LLMBackend, RoutingLLMClient
from cryptoaudit.llm.schemas import LLMRequest, LLMResponse
from cryptoaudit.pipeline.factory import build_llm
from cryptoaudit.utils.errors import CryptoAuditError, ErrorCode


class _Resp(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def fake_openrouter(monkeypatch, models=("qwen/qwen-2.5-coder-32b-instruct",), status=200):
    calls = []

    def urlopen(req, timeout):
        calls.append(req)
        if req.full_url.endswith("/models"):
            return _Resp(json.dumps({"data": [{"id": m} for m in models]}).encode())
        if status != 200:
            raise urllib.error.HTTPError(req.full_url, status, "err", {}, io.BytesIO(b'{"error":{"message":"nope"}}'))
        return _Resp(json.dumps({"model": "qwen/qwen-2.5-coder-32b-instruct", "choices": [{"message": {"content": "hello"}}]}).encode())

    monkeypatch.setattr("urllib.request.urlopen", urlopen)
    return calls


def test_openrouter_sends_chat_completion(monkeypatch):
    calls = fake_openrouter(monkeypatch)
    response = OpenRouterClient("sk-or-test").generate(
        LLMRequest(model="qwen/qwen-2.5-coder-32b-instruct", system="sys", prompt="usr", seed=7, max_tokens=500, num_ctx=9999)
    )
    assert response.text == "hello" and response.provider == "openrouter"
    request = calls[0]
    body = json.loads(request.data.decode())
    assert request.full_url == "https://openrouter.ai/api/v1/chat/completions"
    assert request.headers["Authorization"] == "Bearer sk-or-test"
    assert body["messages"] == [{"role": "system", "content": "sys"}, {"role": "user", "content": "usr"}]
    assert body["temperature"] == 0.0 and body["seed"] == 7 and body["max_tokens"] == 500
    assert "num_ctx" not in body


@pytest.mark.parametrize("status, text", [(401, "invalid API key"), (402, "insufficient OpenRouter credits"), (429, "rate limited")])
def test_openrouter_errors_are_explained(monkeypatch, status, text):
    fake_openrouter(monkeypatch, status=status)
    with pytest.raises(CryptoAuditError) as excinfo:
        OpenRouterClient("sk-or-test").generate(LLMRequest(model="m", system="s", prompt="p"))
    assert excinfo.value.code is ErrorCode.LLM_ERROR and text in excinfo.value.message


def test_openrouter_availability(monkeypatch):
    fake_openrouter(monkeypatch)
    assert OpenRouterClient("sk-or-test").is_available("qwen/qwen-2.5-coder-32b-instruct") is True
    assert OpenRouterClient("sk-or-test").is_available("unknown/model") is False
    assert OpenRouterClient("").is_available("qwen/qwen-2.5-coder-32b-instruct") is False


class FakeClient:
    def __init__(self, name):
        self.name = name
        self.requests = []

    def generate(self, request):
        self.requests.append(request)
        return LLMResponse(text="ok", model=request.model)


def backend(name, available, context=8192, send_num_ctx=True):
    return LLMBackend(name=name, client=FakeClient(name), model=f"{name}-model", context_window=context,
                      is_available=lambda: available, send_num_ctx=send_num_ctx)


def test_router_prefers_first_available_backend():
    ollama, openrouter = backend("ollama", True), backend("openrouter", True, 32768, False)
    router = RoutingLLMClient([ollama, openrouter])
    response = router.generate(LLMRequest(model="ignored", system="s", prompt="p"))
    assert response.provider == "ollama" and ollama.client.requests[0].num_ctx == 8192
    assert router.describe() == "ollama:ollama-model"


def test_router_falls_back_when_ollama_is_unavailable():
    ollama, openrouter = backend("ollama", False), backend("openrouter", True, 32768, False)
    router = RoutingLLMClient([ollama, openrouter])
    response = router.generate(LLMRequest(model="ignored", system="s", prompt="p", num_ctx=8192))
    assert response.provider == "openrouter" and response.model == "openrouter-model"
    assert openrouter.client.requests[0].num_ctx is None  # hosted APIs manage their own context
    assert router.context_window() == 32768


def test_router_with_nothing_available_raises_clear_error():
    router = RoutingLLMClient([backend("ollama", False)])
    assert router.available() is False
    with pytest.raises(CryptoAuditError) as excinfo:
        router.generate(LLMRequest(model="m", system="s", prompt="p"))
    assert "ollama model 'ollama-model' unavailable" in excinfo.value.message


def test_build_llm_respects_provider_setting():
    assert [b.name for b in build_llm(Settings(llm_provider="ollama")).backends] == ["ollama"]
    assert [b.name for b in build_llm(Settings(llm_provider="auto")).backends] == ["ollama"]  # no key: no fallback
    assert [b.name for b in build_llm(Settings(llm_provider="auto", openrouter_api_key="  ")).backends] == ["ollama"]
    auto = build_llm(Settings(llm_provider="auto", openrouter_api_key="sk-or-x"))
    assert [b.name for b in auto.backends] == ["ollama", "openrouter"]
    hosted = build_llm(Settings(llm_provider="openrouter", openrouter_api_key="sk-or-x"))
    assert [(b.name, b.model, b.send_num_ctx) for b in hosted.backends] == [("openrouter", "qwen/qwen-2.5-coder-32b-instruct", False)]


def test_s3_records_the_provider_that_generated_the_candidate(tmp_path):
    from cryptoaudit.analysis.analyzer import AnalyzerEngine
    from cryptoaudit.repair.request import build_repair_request
    from cryptoaudit.repair.s3_llm import LLMRepairStrategy

    class Coder(FakeClient):
        def generate(self, request):
            self.requests.append(request)
            return LLMResponse(text="```python\nimport secrets\n\ndef make_token():\n    return secrets.token_hex(8)\n```", model=request.model)

    source = "import random\n\ndef make_token():\n    session_token = random.randint(0, 9)\n    return session_token\n"
    path = tmp_path / "t.py"
    path.write_text(source, encoding="utf-8")
    request = build_repair_request("t.py", source, AnalyzerEngine().analyze_file(path).findings)
    openrouter = LLMBackend("openrouter", Coder("openrouter"), "qwen/qwen-2.5-coder-32b-instruct", 32768, lambda: True, False)
    result = LLMRepairStrategy(RoutingLLMClient([backend("ollama", False), openrouter])).repair(request)
    assert result.generation.provider == "openrouter"
    assert result.generation.model == "qwen/qwen-2.5-coder-32b-instruct"
    assert result.generation.num_ctx == 32768
