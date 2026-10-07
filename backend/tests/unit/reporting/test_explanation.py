"""Evidence-based and AI explanation tests."""

import pytest

from cryptoaudit.analysis.analyzer import AnalyzerEngine
from cryptoaudit.llm.schemas import LLMRequest, LLMResponse
from cryptoaudit.models.experiment import Verdict
from cryptoaudit.models.repair import RepairResult, RepairStatus, StrategyId, make_candidate
from cryptoaudit.models.validation import GateId, GateResult, GateStatus, ValidationReport
from cryptoaudit.reporting.ai_explanation import DISCLAIMER, generate_ai_explanation
from cryptoaudit.reporting.explanation import NO_ORACLE_LIMITATION, explain, render_text, resolved_calls
from cryptoaudit.utils.errors import CryptoAuditError, ErrorCode
from cryptoaudit.validation.gates import build_outcome
from cryptoaudit.validation.integrity import IntegrityChecker

ORIGINAL = "import hashlib\n\ndef hash_password(password):\n    return hashlib.md5(password.encode()).hexdigest()\n"
REPAIRED = (
    "import hashlib\nimport os\n\ndef hash_password(password):\n"
    '    return hashlib.pbkdf2_hmac("sha256", password.encode(), os.urandom(16), 600000).hex()\n'
)


@pytest.fixture(scope="module")
def findings(tmp_path_factory):
    path = tmp_path_factory.mktemp("m") / "auth.py"
    path.write_text(ORIGINAL, encoding="utf-8")
    return AnalyzerEngine().analyze_file(path).findings


def _case(findings, code=REPAIRED, status=RepairStatus.PRODUCED, v0=GateStatus.PASS, v1=GateStatus.NOT_RUN, v2=GateStatus.NOT_RUN):
    if status is RepairStatus.PRODUCED:
        repair = RepairResult(strategy_id=StrategyId.S2, status=status, candidate_code=code)
        candidate = make_candidate("auth.py", ORIGINAL, repair, IntegrityChecker().check(code))
    else:
        repair = RepairResult(strategy_id=StrategyId.S1, status=status, failure_reason="Scanner guidance offers no fix")
        candidate = make_candidate("auth.py", ORIGINAL, repair, None)
    report = ValidationReport(
        candidate_id=candidate.candidate_id,
        gates=[
            GateResult(gate=GateId.V0, status=v0, gating=False, summary="scan",
                       evidence={"bandit": {"available": True, "relevant_issues": 0 if v0 is GateStatus.PASS else 1}}),
            GateResult(gate=GateId.V1, status=v1, gating=True, summary="functional"),
            GateResult(gate=GateId.V2, status=v2, gating=True, summary="security"),
            GateResult(gate=GateId.V3, status=GateStatus.NOT_RUN, gating=False, summary="compat"),
        ],
    )
    return candidate, report, build_outcome(candidate, report, ["CR1"])


def test_resolved_calls_uses_analyzer_resolution():
    assert "hashlib.md5" in resolved_calls(ORIGINAL)
    assert {"hashlib.pbkdf2_hmac", "os.urandom"} <= resolved_calls(REPAIRED)
    assert resolved_calls("def broken(:") == set()


def test_unverified_explanation_is_evidence_based(findings):
    candidate, report, outcome = _case(findings)
    explanation = explain(findings, ORIGINAL, candidate, report, outcome, has_oracle=False)
    assert explanation.verdict is Verdict.UNVERIFIED and explanation.source == "evidence"
    assert "not verified" in explanation.headline
    text = render_text(explanation)
    assert "Stopped calling: hashlib.md5" in text
    assert "Now calls: hashlib.pbkdf2_hmac, os.urandom" in text
    assert "scanner silence is not proof" in text
    assert explanation.limitations == [NO_ORACLE_LIMITATION]


def test_failed_explanation_names_failing_gate(findings):
    candidate, report, outcome = _case(findings, v1=GateStatus.PASS, v2=GateStatus.FAIL)
    explanation = explain(findings, ORIGINAL, candidate, report, outcome, has_oracle=True)
    assert explanation.verdict is Verdict.FAILED
    assert explanation.headline == "Repair rejected: V2 failed."
    assert explanation.limitations == []


def test_no_candidate_explanation(findings):
    candidate, report, outcome = _case(findings, status=RepairStatus.NOT_APPLICABLE)
    explanation = explain(findings, ORIGINAL, candidate, report, outcome, has_oracle=False)
    assert explanation.verdict is Verdict.NO_CANDIDATE
    assert "NOT_APPLICABLE" in explanation.headline
    assert explanation.limitations == []  # nothing to verify


def test_strategy_notes_use_readable_finding_labels(findings):
    from cryptoaudit.models.finding import finding_id

    candidate, report, outcome = _case(findings)
    fid = finding_id(findings[0])
    noted = candidate.model_copy(update={"repair": candidate.repair.model_copy(update={"notes": [f"{fid}: applied bandit:B324"]})})
    text = render_text(explain(findings, ORIGINAL, noted, report, outcome, has_oracle=False))
    assert fid not in text and f"line {findings[0].line} [CR1]: applied bandit:B324" in text


class RecordingLLM:
    def __init__(self, text="The repair replaces MD5.", error=None):
        self.text, self.error, self.requests = text, error, []

    def generate(self, request: LLMRequest) -> LLMResponse:
        self.requests.append(request)
        if self.error:
            raise self.error
        return LLMResponse(text=self.text, model=request.model)


def test_ai_explanation_is_labelled_and_grounded(findings):
    candidate, report, outcome = _case(findings)
    explanation = explain(findings, ORIGINAL, candidate, report, outcome, has_oracle=False)
    llm = RecordingLLM()
    ai = generate_ai_explanation(llm, "m:1", explanation, candidate.diff)
    assert ai.text == "The repair replaces MD5." and ai.disclaimer == DISCLAIMER
    prompt = llm.requests[0].prompt
    assert '"Unverified"' in prompt and "Stopped calling: hashlib.md5" in prompt and "pbkdf2_hmac" in prompt
    assert "not judge security" in llm.requests[0].system and llm.requests[0].temperature == 0.0


def test_ai_explanation_propagates_llm_errors(findings):
    candidate, report, outcome = _case(findings)
    explanation = explain(findings, ORIGINAL, candidate, report, outcome, has_oracle=False)
    with pytest.raises(CryptoAuditError) as excinfo:
        generate_ai_explanation(RecordingLLM(error=CryptoAuditError(ErrorCode.LLM_ERROR, "down")), "m", explanation, "")
    assert excinfo.value.code is ErrorCode.LLM_ERROR
