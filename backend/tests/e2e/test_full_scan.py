"""
End-to-end: benchmark case -> Analyzer -> Context -> S1/S2/S3/S4 -> integrity -> V0-V3 ->
aggregation -> experiment store. Uses deterministic fake scanners/LLM so results are stable.
"""

from typing import Dict, List

import pytest

from cryptoaudit.analysis.analyzer import AnalyzerEngine
from cryptoaudit.ingest.benchmark_loader import BenchmarkRepository
from cryptoaudit.llm import LLMRequest, LLMResponse
from cryptoaudit.models.experiment import Verdict
from cryptoaudit.models.repair import RepairStatus, StrategyId
from cryptoaudit.models.scan import ModuleInput, ScannerIssue, ScanReport
from cryptoaudit.models.validation import GateId, GateStatus
from cryptoaudit.pipeline import BenchmarkRunner, RepairPipeline
from cryptoaudit.repair.s1_hint import ToolGuidedRepairStrategy
from cryptoaudit.repair.s2_template import TemplateRepairStrategy
from cryptoaudit.repair.s3_llm import LLMRepairStrategy
from cryptoaudit.repair.s4_migration import MigrationAwareRepairStrategy
from cryptoaudit.storage import ExperimentStore
from cryptoaudit.validation import LocalProcessSandbox, ScannerValidator, ValidationPipeline
from cryptoaudit.validation.oracle import load_oracle

REPO = BenchmarkRepository()


class HintScanner:
    """Bandit-like scanner: B324 on every hashlib.md5 line, B311 on random usage."""

    name = "bandit"

    def scan_source(self, source, filename="module.py"):
        issues = []
        for number, line in enumerate(source.splitlines(), 1):
            if "hashlib.md5(" in line and "usedforsecurity" not in line:
                issues.append(ScannerIssue(tool="bandit", rule_id="B324", line=number))
            if "random.choice(" in line:
                issues.append(ScannerIssue(tool="bandit", rule_id="B311", line=number))
        return ScanReport(tool="bandit", available=True, issues=issues)


class EchoLLM:
    """Returns the original module unchanged: a plausible but useless LLM answer."""

    def __init__(self) -> None:
        self.prompts: List[LLMRequest] = []

    def generate(self, request: LLMRequest) -> LLMResponse:
        self.prompts.append(request)
        source = request.prompt.split("## Original module\n```python\n", 1)[1].split("\n```", 1)[0]
        return LLMResponse(text=f"```python\n{source}\n```", model=request.model)


class ChattyLLM:
    def generate(self, request: LLMRequest) -> LLMResponse:
        return LLMResponse(text="Sure! Use bcrypt.", model=request.model)


@pytest.fixture(scope="module")
def run_results(tmp_path_factory):
    store = ExperimentStore(tmp_path_factory.mktemp("db") / "exp.sqlite")
    analyzer = AnalyzerEngine()
    llm = EchoLLM()
    scanner = HintScanner()
    pipeline = RepairPipeline(
        analyzer=analyzer,
        strategies=[
            ToolGuidedRepairStrategy([scanner]),
            TemplateRepairStrategy(),
            LLMRepairStrategy(llm, model="echo"),
            MigrationAwareRepairStrategy(ChattyLLM(), model="chatty"),
        ],
        validator=ValidationPipeline(LocalProcessSandbox(timeout=180, allow_unsafe=True), ScannerValidator(analyzer, [scanner])),
        store=store,
    )
    module_runs = {}
    info = BenchmarkRunner(REPO, pipeline, store).run({"test": True}, on_case=lambda cid, run: module_runs.__setitem__(cid, run))
    verdicts: Dict[tuple, Verdict] = {
        (cid, r.outcome.strategy_id.value): r.outcome.verdict for cid, mr in module_runs.items() for r in mr.runs
    }
    return {"store": store, "info": info, "runs": module_runs, "verdicts": verdicts, "llm": llm}


def test_every_case_and_strategy_is_recorded(run_results):
    store, info = run_results["store"], run_results["info"]
    assert len(store.outcomes(info.run_id)) == 5 * 4
    assert len(store.baselines(info.run_id)) == 5
    assert store.runs()[0].config["case_ids"] == REPO.case_ids()


def test_expected_research_outcomes(run_results):
    v = run_results["verdicts"]
    # S2 secrets template fully repairs CR5.
    assert v[("cr5_session_token", "S2")] is Verdict.VERIFIED
    # S2 templates that drop the salt/IV break functionality and legacy data.
    for case in ("cr1_password_md5", "cr3_static_iv", "cr4_weak_kdf"):
        assert v[(case, "S2")] is Verdict.FAILED
    # No ECB template exists: explicitly no candidate, never success.
    assert v[("cr2_ecb_records", "S2")] is Verdict.NO_CANDIDATE
    # An unchanged module echoed by an LLM is never accepted.
    assert all(v[(case, "S3")] is Verdict.FAILED for case in REPO.case_ids())
    # Unparseable LLM output is PARSE_ERROR -> NO_CANDIDATE.
    assert all(v[(case, "S4")] is Verdict.NO_CANDIDATE for case in REPO.case_ids())


def test_scanner_silencing_repair_is_not_accepted(run_results):
    """S1 applies Bandit's own hint (usedforsecurity=False): Bandit goes quiet, V2 still fails."""
    s1 = next(r for r in run_results["runs"]["cr1_password_md5"].runs if r.outcome.strategy_id is StrategyId.S1)
    assert s1.candidate.repair.status is RepairStatus.PRODUCED
    assert "usedforsecurity=False" in s1.candidate.code
    assert s1.outcome.scanner_results["bandit"] is True
    assert s1.report.status(GateId.V2) is GateStatus.FAIL
    assert s1.outcome.verdict is Verdict.FAILED


def test_s1_without_actionable_hint_is_not_applicable(run_results):
    s1 = next(r for r in run_results["runs"]["cr5_session_token"].runs if r.outcome.strategy_id is StrategyId.S1)
    assert s1.candidate.repair.status is RepairStatus.NOT_APPLICABLE
    assert s1.outcome.verdict is Verdict.NO_CANDIDATE


def test_prompts_never_contain_hidden_oracle_content(run_results):
    prompts = run_results["llm"].prompts
    assert len(prompts) == 5
    hidden_snippets = []
    for case_id in REPO.case_ids():
        oracle = load_oracle(REPO, case_id)
        for path in oracle.checks.values():
            hidden_snippets.append(path.read_text(encoding="utf-8").splitlines()[0])
        hidden_snippets.append(f"cryptoaudit-hidden-oracle-{case_id}")
    for request in prompts:
        text = request.system + request.prompt
        assert "CANARY" not in text
        assert "hidden" not in text.lower()
        assert "legacy_" not in text
        for snippet in hidden_snippets:
            assert snippet not in text


def test_repair_requests_never_contain_hidden_content(run_results):
    for module_run in run_results["runs"].values():
        dumped = module_run.request.model_dump_json()
        assert "CANARY" not in dumped and "hidden" not in dumped.lower()
        assert all(f.file == module_run.module.module_name for f in module_run.request.findings)


def test_user_module_without_oracle_is_unverified_at_best(tmp_path):
    analyzer = AnalyzerEngine()
    pipeline = RepairPipeline(
        analyzer=analyzer,
        strategies=[TemplateRepairStrategy()],
        validator=ValidationPipeline(LocalProcessSandbox(timeout=60, allow_unsafe=True), ScannerValidator(analyzer)),
    )
    source = REPO.public_case("cr5_session_token").source
    run = pipeline.run_module(ModuleInput(module_name="tokens.py", source=source))
    outcome = run.runs[0].outcome
    assert outcome.verdict is Verdict.UNVERIFIED
    assert outcome.gates["V0"] is GateStatus.PASS  # scanner-clean is not enough


def test_clean_module_produces_no_repairs():
    analyzer = AnalyzerEngine()
    pipeline = RepairPipeline(
        analyzer=analyzer,
        strategies=[TemplateRepairStrategy()],
        validator=ValidationPipeline(LocalProcessSandbox(allow_unsafe=True), ScannerValidator(analyzer)),
    )
    run = pipeline.run_module(ModuleInput(module_name="ok.py", source="import secrets\nTOKEN = secrets.token_hex(16)\n"))
    assert run.findings == [] and run.runs == []
