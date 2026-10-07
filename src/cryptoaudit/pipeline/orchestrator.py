"""
End-to-end pipeline for one module:

    Input -> Analyzer -> Findings -> Context -> Repair (S1-S4) -> Candidates -> V0-V3 -> Aggregation -> Store

Generation and validation are kept apart: strategies receive a RepairRequest built from public
input only, while the hidden oracle is handed exclusively to the validation pipeline.
"""

import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence

from cryptoaudit.aggregation.aggregator import build_outcome
from cryptoaudit.analysis.analyzer import AnalyzerEngine
from cryptoaudit.benchmark.oracle import HiddenOracle
from cryptoaudit.candidate.integrity import IntegrityChecker
from cryptoaudit.context.builder import ContextBuilder
from cryptoaudit.models.experiment import CaseOutcome
from cryptoaudit.models.finding import Finding
from cryptoaudit.models.repair import Candidate, RepairConstraints, RepairRequest, make_candidate
from cryptoaudit.models.scan import ModuleInput
from cryptoaudit.models.validation import ValidationReport
from cryptoaudit.repair.base import RepairStrategy
from cryptoaudit.repair.request import build_repair_request
from cryptoaudit.storage.experiment_store import ExperimentStore
from cryptoaudit.utils.errors import CryptoAuditError, ErrorCode
from cryptoaudit.validation.pipeline import ValidationPipeline


@dataclass
class StrategyRun:
    candidate: Candidate
    report: ValidationReport
    outcome: CaseOutcome


@dataclass
class ModuleRun:
    module: ModuleInput
    findings: List[Finding] = field(default_factory=list)
    baseline: Dict[str, dict] = field(default_factory=dict)
    request: Optional[RepairRequest] = None
    runs: List[StrategyRun] = field(default_factory=list)

    @property
    def rule_ids(self) -> List[str]:
        return sorted({f.rule_id for f in self.findings})


class RepairPipeline:
    def __init__(
        self,
        analyzer: AnalyzerEngine,
        strategies: Sequence[RepairStrategy],
        validator: ValidationPipeline,
        integrity: Optional[IntegrityChecker] = None,
        context_builder: Optional[ContextBuilder] = None,
        store: Optional[ExperimentStore] = None,
    ) -> None:
        self.analyzer = analyzer
        self.strategies = list(strategies)
        self.validator = validator
        self.integrity = integrity or IntegrityChecker()
        self.context_builder = context_builder or ContextBuilder()
        self.store = store

    def analyze(self, module: ModuleInput) -> List[Finding]:
        """Run the deterministic Analyzer; finding paths are normalised to the module name."""
        with tempfile.TemporaryDirectory(prefix="cryptoaudit-in-") as tmp:
            path = Path(tmp) / module.module_name
            with open(path, "w", encoding="utf-8", newline="") as handle:
                handle.write(module.source)
            try:
                result = self.analyzer.analyze_file(path)
            except ValueError as exc:
                raise CryptoAuditError(ErrorCode.PARSE_ERROR, str(exc).replace(str(path), module.module_name)) from exc
        return [f.model_copy(update={"file": module.module_name}) for f in result.findings]

    def run_module(
        self,
        module: ModuleInput,
        oracle: Optional[HiddenOracle] = None,
        functional_checks: Optional[Path] = None,
        run_id: Optional[str] = None,
    ) -> ModuleRun:
        run = ModuleRun(module=module, findings=self.analyze(module))
        if not run.findings:
            return run

        run.baseline = self.validator.scanner_validator.scan(module.source, module.module_name, run.rule_ids)
        if self.store is not None and run_id is not None:
            self.store.record_baseline(run_id, module.case_id, module.module_name, run.rule_ids, run.baseline)

        constraints = RepairConstraints(allowed_libraries=module.allowed_libraries, target_python=module.target_python)
        run.request = build_repair_request(module.module_name, module.source, run.findings, constraints, self.context_builder)

        for strategy in self.strategies:
            repair = strategy.repair(run.request)
            integrity = (
                self.integrity.check(repair.candidate_code or "", module.allowed_libraries, module.source)
                if repair.produced
                else None
            )
            candidate = make_candidate(module.module_name, module.source, repair, integrity)
            started = time.perf_counter()
            report = self.validator.validate(candidate, module.source, run.rule_ids, oracle, functional_checks)
            outcome = build_outcome(candidate, report, run.rule_ids, module.case_id, time.perf_counter() - started)
            if self.store is not None and run_id is not None:
                self.store.record(run_id, outcome, candidate, report)
            run.runs.append(StrategyRun(candidate=candidate, report=report, outcome=outcome))
        return run
