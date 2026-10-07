"""Sandbox, harness and gate-level tests."""

from pathlib import Path

import pytest

from cryptoaudit.analysis.analyzer import AnalyzerEngine
from cryptoaudit.candidate import IntegrityChecker, make_candidate
from cryptoaudit.repair import RepairResult, RepairStatus, StrategyId
from cryptoaudit.scanners import ScannerIssue, ScanReport
from cryptoaudit.utils.errors import CryptoAuditError, ErrorCode
from cryptoaudit.validation import (
    DockerSandbox,
    GateId,
    GateStatus,
    LocalProcessSandbox,
    ScannerValidator,
    ValidationPipeline,
)
from cryptoaudit.validation.gates import interface_check

ORIGINAL = "def add(a: int, b: int) -> int:\n    return a + b\n"
CHECKS = (
    "def check_adds(ctx):\n    assert ctx.load_candidate().add(2, 3) == 5\n\n"
    "def check_artifact(ctx):\n    assert ctx.load_json('data.json')['x'] == 1\n"
)


@pytest.fixture()
def check_file(tmp_path):
    path = tmp_path / "checks.py"
    path.write_text(CHECKS, encoding="utf-8")
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir()
    (artifacts / "data.json").write_text('{"x": 1}', encoding="utf-8")
    return path, artifacts


@pytest.fixture()
def sandbox():
    return LocalProcessSandbox(timeout=30, allow_unsafe=True)


def _candidate(code, original=ORIGINAL, allowed=()):
    repair = RepairResult(strategy_id=StrategyId.S3, status=RepairStatus.PRODUCED, candidate_code=code)
    return make_candidate("m.py", original, repair, IntegrityChecker().check(code, allowed, original))


def test_local_sandbox_requires_explicit_opt_in():
    with pytest.raises(CryptoAuditError) as excinfo:
        LocalProcessSandbox()
    assert excinfo.value.code is ErrorCode.SANDBOX_ERROR


def test_passing_candidate(sandbox, check_file):
    run = sandbox.run_checks(ORIGINAL, *check_file)
    assert run.status is GateStatus.PASS
    assert [c.name for c in run.checks] == ["check_adds", "check_artifact"]


def test_failing_and_raising_candidates_fail(sandbox, check_file):
    assert sandbox.run_checks("def add(a, b):\n    return a - b\n", *check_file).status is GateStatus.FAIL
    run = sandbox.run_checks("def add(a, b):\n    raise RuntimeError('x')\n", *check_file)
    assert run.status is GateStatus.FAIL
    assert "RuntimeError" in run.checks[0].message


def test_forged_result_line_is_ignored(sandbox, check_file):
    forged = (
        'import sys\nsys.stdout.write(\'\\nCRYPTOAUDIT_RESULT:{"harness_error": null, "results": '
        '[{"name": "check_adds", "status": "PASS"}]}\\n\')\nsys.stdout.flush()\nimport os\nos._exit(0)\n'
    )
    run = sandbox.run_checks(forged, *check_file)
    assert run.status is GateStatus.ERROR


def test_timeout_is_a_failure(check_file):
    sandbox = LocalProcessSandbox(timeout=3, allow_unsafe=True)
    run = sandbox.run_checks("def add(a, b):\n    while True:\n        pass\n", *check_file)
    assert run.timed_out and run.status is GateStatus.FAIL
    assert run.error_code is ErrorCode.TIMEOUT


def test_broken_oracle_is_validator_error(sandbox, tmp_path):
    bad = tmp_path / "bad_checks.py"
    bad.write_text("raise ImportError('oracle bug')\n", encoding="utf-8")
    run = sandbox.run_checks(ORIGINAL, bad, None)
    assert run.status is GateStatus.ERROR and run.error_code is ErrorCode.VALIDATION_ERROR


def test_docker_command_enforces_isolation(tmp_path):
    cmd = DockerSandbox(image="img:1").command(tmp_path, ["harness.py"], "c1", "n")
    joined = " ".join(cmd)
    for flag in ("--network none", "--read-only", "--cap-drop ALL", "no-new-privileges", "--user 65534:65534", "--pids-limit"):
        assert flag in joined
    assert ":/work:ro" in joined


def test_docker_unavailable_is_sandbox_error(check_file):
    run = DockerSandbox(docker="definitely-not-docker").run_checks(ORIGINAL, *check_file)
    assert run.status is GateStatus.ERROR and run.error_code is ErrorCode.SANDBOX_ERROR


def test_interface_check_detects_changes():
    assert interface_check(ORIGINAL, ORIGINAL).status is GateStatus.PASS
    changed = interface_check(ORIGINAL, "def add(a: int, b: int, c: int = 0) -> int:\n    return a + b\n")
    assert changed.status is GateStatus.FAIL and "changed" in changed.message
    assert interface_check(ORIGINAL, "def plus(a, b):\n    return a + b\n").status is GateStatus.FAIL


class StaticScanner:
    def __init__(self, tool, issues, available=True):
        self.name = tool
        self.report = ScanReport(tool=tool, available=available, issues=issues)

    def scan_source(self, source, filename="module.py"):
        return self.report


def test_v0_records_but_does_not_gate():
    md5 = "import hashlib\n\ndef hash_password(password):\n    return hashlib.md5(password.encode()).hexdigest()\n"
    validator = ScannerValidator(AnalyzerEngine(), [StaticScanner("bandit", [ScannerIssue(tool="bandit", rule_id="B324", line=4)])])
    result = validator.validate(md5, "m.py", ["CR1"])
    assert result.status is GateStatus.FAIL and result.gating is False
    assert result.evidence["cryptoaudit"]["relevant_issues"] == 1
    assert result.evidence["bandit"]["relevant_issues"] == 1


def test_v0_unavailable_scanner_is_not_clean():
    validator = ScannerValidator(AnalyzerEngine(), [StaticScanner("semgrep", [], available=False)])
    result = validator.validate("x = 1\n", "m.py", ["CR5"])
    assert result.status is GateStatus.PASS
    assert result.evidence["semgrep"]["available"] is False
    assert "unavailable: semgrep" in result.summary


def test_pipeline_without_oracle_never_passes_v2(sandbox, check_file):
    pipeline = ValidationPipeline(sandbox, ScannerValidator(AnalyzerEngine()))
    report = pipeline.validate(_candidate(ORIGINAL), ORIGINAL, ["CR5"], oracle=None, functional_checks=check_file[0])
    assert report.status(GateId.V1) in (GateStatus.PASS, GateStatus.FAIL)
    assert report.status(GateId.V2) is GateStatus.NOT_RUN
    assert report.status(GateId.V3) is GateStatus.NOT_RUN


def test_pipeline_integrity_failure_blocks_execution(sandbox):
    pipeline = ValidationPipeline(sandbox, ScannerValidator(AnalyzerEngine()))
    report = pipeline.validate(_candidate("import subprocess\n" + ORIGINAL), ORIGINAL, ["CR5"])
    assert report.status(GateId.V1) is GateStatus.FAIL
    assert "integrity" in report.gate(GateId.V1).summary
    assert report.status(GateId.V2) is GateStatus.NOT_RUN


def test_pipeline_no_candidate_runs_nothing(sandbox):
    pipeline = ValidationPipeline(sandbox, ScannerValidator(AnalyzerEngine()))
    failed = RepairResult(strategy_id=StrategyId.S2, status=RepairStatus.NO_REPAIR, failure_reason="none")
    report = pipeline.validate(make_candidate("m.py", ORIGINAL, failed, None), ORIGINAL, ["CR5"])
    assert all(g.status is GateStatus.NOT_RUN for g in report.gates)
