"""S3/S4 strategy, strict parser, prompt rendering and Ollama client tests (no real LLM needed)."""

import io
import json
import urllib.error
from pathlib import Path

import pytest

from cryptoaudit.analysis.analyzer import AnalyzerEngine
from cryptoaudit.llm import LLMRequest, LLMResponse, OllamaClient
from cryptoaudit.repair import RepairConstraints, RepairStatus, StrategyId, build_repair_request
from cryptoaudit.repair.prompting import OutputParseError, parse_llm_output, render_prompt
from cryptoaudit.repair.strategies import LLMRepairStrategy, MigrationAwareRepairStrategy
from cryptoaudit.utils.errors import CryptoAuditError, ErrorCode

FIXTURE = Path("tests/fixtures/cr5/vulnerable.py")
GOOD_OUTPUT = "Here you go:\n```python\nimport secrets\n\ndef f():\n    return secrets.token_hex(16)\n```\n"


class FakeLLM:
    def __init__(self, text: str = GOOD_OUTPUT, error: CryptoAuditError | None = None) -> None:
        self.text = text
        self.error = error
        self.requests: list[LLMRequest] = []

    def generate(self, request: LLMRequest) -> LLMResponse:
        self.requests.append(request)
        if self.error:
            raise self.error
        return LLMResponse(text=self.text, model=request.model, model_digest="sha256:abc")


@pytest.fixture(scope="module")
def request_obj():
    source = FIXTURE.read_text(encoding="utf-8")
    findings = AnalyzerEngine().analyze_file(FIXTURE).findings
    constraints = RepairConstraints(allowed_libraries=("secrets", "string"), target_python="3.12")
    return build_repair_request("tokens.py", source, findings, constraints)


# --- parser -----------------------------------------------------------------------------------


def test_parser_accepts_single_block():
    assert parse_llm_output(GOOD_OUTPUT).startswith("import secrets")


@pytest.mark.parametrize(
    "text",
    [
        "no code at all",
        "```python\nx = 1\n```\n```python\ny = 2\n```",
        "```python\n\n```",
        "```python\ndef broken(:\n```",
        "```python\n# only a comment\n```",
    ],
)
def test_parser_rejects_malformed_output(text):
    with pytest.raises(OutputParseError):
        parse_llm_output(text)


def test_parser_enforces_size_limit():
    with pytest.raises(OutputParseError):
        parse_llm_output("```python\n" + "x = 1\n" * 100 + "```", max_chars=50)


# --- prompts ----------------------------------------------------------------------------------


def test_prompt_contains_module_findings_interface_and_constraints(request_obj):
    prompt = render_prompt(request_obj, "s3_v1")
    assert "tokens.py" in prompt.user
    assert "[CR5" in prompt.user
    assert "secrets, string" in prompt.user
    assert "3.12" in prompt.user
    assert request_obj.source.strip() in prompt.user
    for symbol in request_obj.context.public_interface:
        assert symbol.signature in prompt.user


def test_s4_prompt_adds_only_migration_section(request_obj):
    s3 = render_prompt(request_obj, "s3_v1")
    s4 = render_prompt(request_obj, "s4_v1")
    assert "Migration requirements" in s4.user and "Migration requirements" not in s3.user
    assert s3.prompt_hash != s4.prompt_hash


def test_prompt_rendering_is_deterministic(request_obj):
    assert render_prompt(request_obj, "s3_v1") == render_prompt(request_obj, "s3_v1")


# --- strategies -------------------------------------------------------------------------------


def test_s3_produces_candidate_with_reproducibility_metadata(request_obj):
    llm = FakeLLM()
    result = LLMRepairStrategy(llm, model="m:1", seed=7).repair(request_obj)
    assert result.status is RepairStatus.PRODUCED and result.strategy_id is StrategyId.S3
    assert result.generation.model == "m:1" and result.generation.seed == 7
    assert result.generation.raw_output == GOOD_OUTPUT
    assert result.generation.model_digest == "sha256:abc"
    assert llm.requests[0].temperature == 0.0


def test_s4_uses_migration_prompt(request_obj):
    llm = FakeLLM()
    result = MigrationAwareRepairStrategy(llm).repair(request_obj)
    assert result.strategy_id is StrategyId.S4
    assert "Migration requirements" in llm.requests[0].prompt


def test_malformed_output_is_parse_error_with_raw_output_kept(request_obj):
    result = LLMRepairStrategy(FakeLLM(text="I fixed it!")).repair(request_obj)
    assert result.status is RepairStatus.PARSE_ERROR
    assert result.candidate_code is None
    assert result.generation.raw_output == "I fixed it!"


def test_llm_failure_is_no_repair_and_single_shot(request_obj):
    llm = FakeLLM(error=CryptoAuditError(ErrorCode.LLM_ERROR, "down"))
    result = LLMRepairStrategy(llm).repair(request_obj)
    assert result.status is RepairStatus.NO_REPAIR
    assert result.error_code is ErrorCode.LLM_ERROR
    assert len(llm.requests) == 1  # no retries


# --- Ollama client ----------------------------------------------------------------------------


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
