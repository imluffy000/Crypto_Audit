"""Repository scan tests: stages, results, explanations - and proof that repository code is never executed."""

from pathlib import Path

import pytest

from cryptoaudit.analysis.analyzer import AnalyzerEngine
from cryptoaudit.models.experiment import Verdict
from cryptoaudit.models.repair import RepairStatus, StrategyId
from cryptoaudit.models.scan import ModuleInput, RepositorySnapshot, ScanStage, StageStatus
from cryptoaudit.models.validation import GateStatus
from cryptoaudit.pipeline.orchestrator import RepairPipeline
from cryptoaudit.pipeline.repository_scan import RepositoryScanner, select_web_strategies
from cryptoaudit.repair.s2_template import TemplateRepairStrategy
from cryptoaudit.utils.errors import CryptoAuditError, ErrorCode
from cryptoaudit.validation.runner import ValidationPipeline
from cryptoaudit.validation.sandbox import Sandbox
from cryptoaudit.validation.v0_scanner import ScannerValidator

FIXTURES = Path("tests/fixtures")


class ForbiddenSandbox(Sandbox):
    """Fails the test if anything tries to execute repository code."""

    name = "forbidden"

    def _execute(self, work, argv, nonce):
        raise AssertionError("repository code must never be executed by the web scan")


def snapshot() -> RepositorySnapshot:
    modules = [
        ModuleInput(module_name="app/tokens.py", source=(FIXTURES / "cr5" / "vulnerable.py").read_text(encoding="utf-8")),
        ModuleInput(module_name="app/crypto.py", source=(FIXTURES / "multi_rule" / "vulnerable.py").read_text(encoding="utf-8")),
        ModuleInput(module_name="app/clean.py", source="import secrets\nTOKEN = secrets.token_hex(16)\n"),
        ModuleInput(module_name="app/broken.py", source="def broken(:\n"),
    ]
    return RepositorySnapshot(full_name="alice/app", ref="main", commit="abc1234", modules=modules)


def make_scanner(events=None, skipped=None, parallelism=1, progress_interval=0.0):
    analyzer = AnalyzerEngine()
    pipeline = RepairPipeline(
        analyzer=analyzer,
        strategies=[TemplateRepairStrategy()],
        validator=ValidationPipeline(ForbiddenSandbox(), ScannerValidator(analyzer)),
    )
    return RepositoryScanner(
        pipeline,
        on_progress=(events.append if events is not None else None),
        skipped_strategies=skipped,
        parallelism=parallelism,
        progress_interval=progress_interval,
    )


def many_files_snapshot(count=40) -> RepositorySnapshot:
    source = (FIXTURES / "cr5" / "vulnerable.py").read_text(encoding="utf-8")
    modules = [ModuleInput(module_name=f"pkg/m{i:03d}.py", source=source) for i in range(count)]
    return RepositorySnapshot(full_name="alice/big", ref="main", modules=modules)


def without_timings(value):
    """Scan results are deterministic apart from measured durations."""
    if isinstance(value, dict):
        return {k: without_timings(v) for k, v in value.items() if not k.startswith("duration")}
    if isinstance(value, list):
        return [without_timings(v) for v in value]
    return value


def test_parallel_scan_matches_sequential_scan():
    sequential = make_scanner(parallelism=1).run(many_files_snapshot)
    parallel = make_scanner(parallelism=8).run(many_files_snapshot)
    assert without_timings(parallel.model_dump(mode="json")) == without_timings(sequential.model_dump(mode="json"))
    assert [f.path for f in parallel.files] == sorted(f.path for f in parallel.files)


def test_progress_is_throttled_but_never_drops_stage_changes():
    events = []
    make_scanner(events, progress_interval=60.0).run(many_files_snapshot)
    assert len(events) <= 2 * len(ScanStage)  # no per-file updates inside the interval
    seen = {(s.stage, s.status) for event in events for s in event}
    for stage in ScanStage:
        assert (stage, StageStatus.RUNNING) in seen and (stage, StageStatus.DONE) in seen


@pytest.fixture(scope="module")
def scan():
    events = []
    result = make_scanner(events, {"S3": "unavailable", "S4": "unavailable"}).run(snapshot)
    return result, events


def test_all_stages_complete_in_order(scan):
    _, events = scan
    final = events[-1]
    assert [s.stage for s in final] == list(ScanStage)
    assert all(s.status is StageStatus.DONE for s in final)
    first_running = [next(i for i, e in enumerate(events) if e[k].status is StageStatus.RUNNING) for k in range(len(ScanStage))]
    assert first_running == sorted(first_running)


def test_results_cover_findings_and_skips(scan):
    result, _ = scan
    assert result.repository == "alice/app" and result.commit == "abc1234"
    assert result.summary.files_scanned == 3 and result.summary.files_with_findings == 2
    assert {"CR1", "CR2", "CR3", "CR4", "CR5"} <= set(result.summary.findings_by_rule)
    assert [s.path for s in result.skipped_files] == ["app/broken.py"]
    assert result.skipped_strategies == {"S3": "unavailable", "S4": "unavailable"}
    assert all(f.finding.file.startswith("app/") for f in result.findings)


def test_user_code_is_unverified_at_best_and_explained(scan):
    result, _ = scan
    tokens = next(f for f in result.files if f.path == "app/tokens.py")
    run = tokens.runs[0]
    assert run.strategy_id is StrategyId.S2 and run.repair_status is RepairStatus.PRODUCED
    assert run.verdict is Verdict.UNVERIFIED
    assert {g.gate.value: g.status for g in run.gates}["V2"] is GateStatus.NOT_RUN
    assert run.explanation.limitations and "secrets.choice" in run.candidate_code
    assert "cryptoaudit" in tokens.baseline
    assert all(v.best_verdict in (Verdict.UNVERIFIED, Verdict.NO_CANDIDATE, Verdict.FAILED) for v in result.findings)
    assert result.summary.scanner_clean_not_verified >= 1


def test_clean_repository_skips_repair_stages():
    events = []
    clean = RepositorySnapshot(full_name="a/b", ref="main", modules=[ModuleInput(module_name="ok.py", source="x = 1\n")])
    result = make_scanner(events).run(lambda: clean)
    statuses = {s.stage: s.status for s in events[-1]}
    assert statuses[ScanStage.REPAIR] is StageStatus.SKIPPED and statuses[ScanStage.REPORT] is StageStatus.DONE
    assert result.findings == [] and result.files == []


def test_fetch_failure_marks_stage_failed():
    events = []

    def failing_fetch():
        raise CryptoAuditError(ErrorCode.NOT_FOUND, "repository not accessible")

    with pytest.raises(CryptoAuditError):
        make_scanner(events).run(failing_fetch)
    fetch = events[-1][0]
    assert fetch.stage is ScanStage.FETCH and fetch.status is StageStatus.FAILED
    assert fetch.detail == "repository not accessible"


def test_strategy_selection_depends_on_llm_availability():
    assert select_web_strategies(True) == ([StrategyId.S1, StrategyId.S2, StrategyId.S3, StrategyId.S4], {})
    ids, skipped = select_web_strategies(False)
    assert ids == [StrategyId.S1, StrategyId.S2] and set(skipped) == {"S3", "S4"}
