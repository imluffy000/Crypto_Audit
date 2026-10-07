"""Context-window budgeting for S3/S4: oversized files are refused, never silently truncated."""

import io
import json

from cryptoaudit.analysis.analyzer import AnalyzerEngine
from cryptoaudit.llm.budget import estimate_tokens, module_budget
from cryptoaudit.llm.ollama_client import OllamaClient
from cryptoaudit.llm.schemas import LLMRequest, LLMResponse
from cryptoaudit.models.repair import RepairStatus
from cryptoaudit.repair.request import build_repair_request
from cryptoaudit.repair.s3_llm import LLMRepairStrategy
from cryptoaudit.repair.s4_migration import MigrationAwareRepairStrategy
from cryptoaudit.utils.errors import ErrorCode

VULNERABLE = "import random\n\ndef generate_session_token():\n    return str(random.randint(0, 999999))\n"


class RecordingLLM:
    def __init__(self):
        self.requests = []

    def generate(self, request: LLMRequest) -> LLMResponse:
        self.requests.append(request)
        return LLMResponse(text="```python\nimport secrets\n\ndef generate_session_token():\n    return secrets.token_hex(16)\n```", model=request.model)


def make_request(tmp_path, source):
    path = tmp_path / "tokens.py"
    path.write_text(source, encoding="utf-8")
    return build_repair_request("tokens.py", source, AnalyzerEngine().analyze_file(path).findings)


def test_estimates_are_conservative():
    assert estimate_tokens("") == 0
    assert estimate_tokens("x" * 300) == 100
    budget = module_budget("p" * 3000, "s" * 3000, num_ctx=4096)
    assert budget.prompt_tokens == 1000 and budget.answer_tokens == 1300 + 256 and budget.fits


def test_small_file_is_sent_with_context_and_output_budget(tmp_path):
    llm = RecordingLLM()
    result = LLMRepairStrategy(llm, model="qwen2.5-coder:7b", num_ctx=8192, max_tokens=8192).repair(make_request(tmp_path, VULNERABLE))
    assert result.status is RepairStatus.PRODUCED
    sent = llm.requests[0]
    assert sent.num_ctx == 8192
    assert 0 < sent.max_tokens <= 8192 - estimate_tokens(sent.system + sent.prompt) + 1
    assert result.generation.num_ctx == 8192 and result.generation.max_tokens == sent.max_tokens


def test_oversized_file_is_refused_without_calling_the_llm(tmp_path):
    padding = "".join(f"CONSTANT_{i} = {i}\n" for i in range(2000))
    llm = RecordingLLM()
    for strategy in (LLMRepairStrategy(llm, num_ctx=4096), MigrationAwareRepairStrategy(llm, num_ctx=4096)):
        result = strategy.repair(make_request(tmp_path, VULNERABLE + padding))
        assert result.status is RepairStatus.NO_REPAIR
        assert result.error_code is ErrorCode.LIMIT_EXCEEDED
        assert "CRYPTOAUDIT_LLM_NUM_CTX" in result.failure_reason
    assert llm.requests == []


class _Resp(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def test_ollama_receives_num_ctx(monkeypatch):
    sent = {}

    def fake_urlopen(req, timeout):
        if req.full_url.endswith("/api/tags"):
            return _Resp(json.dumps({"models": []}).encode())
        sent.update(json.loads(req.data.decode()))
        return _Resp(json.dumps({"response": "ok", "model": "m"}).encode())

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    OllamaClient().generate(LLMRequest(model="m", system="s", prompt="p", num_ctx=16384, max_tokens=900))
    assert sent["options"]["num_ctx"] == 16384 and sent["options"]["num_predict"] == 900


def test_ollama_omits_num_ctx_when_unset(monkeypatch):
    sent = {}

    def fake_urlopen(req, timeout):
        if req.full_url.endswith("/api/tags"):
            return _Resp(json.dumps({"models": []}).encode())
        sent.update(json.loads(req.data.decode()))
        return _Resp(json.dumps({"response": "ok", "model": "m"}).encode())

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    OllamaClient().generate(LLMRequest(model="m", system="s", prompt="p"))
    assert "num_ctx" not in sent["options"]
