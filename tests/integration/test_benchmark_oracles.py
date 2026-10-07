"""
Oracle validity: every hidden oracle must reject the original vulnerable module on V2 while
accepting its behaviour (V1) and legacy data (V3), and must accept the reference repair on all
gates. Without this, validation results would not be trustworthy research evidence.

Runs trusted benchmark code in the local (non-isolated) sandbox.
"""

from pathlib import Path

import pytest

from cryptoaudit.analysis.analyzer import AnalyzerEngine
from cryptoaudit.benchmark import BenchmarkRepository
from cryptoaudit.benchmark.oracle import load_oracle
from cryptoaudit.candidate import IntegrityChecker, make_candidate
from cryptoaudit.repair import RepairResult, RepairStatus, StrategyId
from cryptoaudit.validation import GateId, GateStatus, LocalProcessSandbox, ScannerValidator, ValidationPipeline

REFERENCE_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "reference_repairs"
CASES = BenchmarkRepository().case_ids()


@pytest.fixture(scope="module")
def pipeline():
    return ValidationPipeline(LocalProcessSandbox(timeout=180, allow_unsafe=True), ScannerValidator(AnalyzerEngine()))


def _validate(pipeline, case_id, code):
    repo = BenchmarkRepository()
    case = repo.public_case(case_id)
    repair = RepairResult(strategy_id=StrategyId.S2, status=RepairStatus.PRODUCED, candidate_code=code)
    integrity = IntegrityChecker().check(code, case.spec.allowed_libraries, case.source)
    candidate = make_candidate(case.module_name, case.source, repair, integrity)
    return pipeline.validate(candidate, case.source, [case.spec.rule_id], load_oracle(repo, case_id)), integrity


@pytest.mark.parametrize("case_id", CASES)
def test_original_is_functional_but_insecure(pipeline, case_id):
    source = BenchmarkRepository().public_case(case_id).source
    report, _ = _validate(pipeline, case_id, source)
    assert report.status(GateId.V1) is GateStatus.PASS, report.gate(GateId.V1)
    assert report.status(GateId.V2) is GateStatus.FAIL, report.gate(GateId.V2)
    assert report.status(GateId.V0) is GateStatus.FAIL  # CryptoAudit still reports the issue
    expected_v3 = GateStatus.NOT_APPLICABLE if case_id == "cr5_session_token" else GateStatus.PASS
    assert report.status(GateId.V3) is expected_v3, report.gate(GateId.V3)


@pytest.mark.parametrize("case_id", CASES)
def test_reference_repair_passes_all_gates(pipeline, case_id):
    code = (REFERENCE_DIR / f"{case_id}.py").read_text(encoding="utf-8")
    report, integrity = _validate(pipeline, case_id, code)
    assert integrity.passed, integrity.issues
    assert report.status(GateId.V1) is GateStatus.PASS, report.gate(GateId.V1)
    assert report.status(GateId.V2) is GateStatus.PASS, report.gate(GateId.V2)
    expected_v3 = GateStatus.NOT_APPLICABLE if case_id == "cr5_session_token" else GateStatus.PASS
    assert report.status(GateId.V3) is expected_v3, report.gate(GateId.V3)
