"""
End-to-end pipeline for one module:

    Input -> Analyzer -> Findings -> Context -> Repair (S1-S4) -> Candidates -> V0-V3 -> Aggregation -> Store

Generation and validation are kept apart: strategies receive a RepairRequest built from public
input only, while the hidden oracle is handed exclusively to the validation pipeline.
"""

from pathlib import Path
from typing import List, Optional, Sequence

from cryptoaudit.analysis.analyzer import AnalyzerEngine
from cryptoaudit.context.context_builder import ContextBuilder
from cryptoaudit.models.finding import Finding
from cryptoaudit.models.repair import RepairConstraints
from cryptoaudit.models.scan import ModuleInput
from cryptoaudit.pipeline.pipeline_result import ModuleRun, StrategyRun
from cryptoaudit.pipeline.stages import analysis_stage, candidate_stage, validation_stage
from cryptoaudit.repair.base import RepairStrategy
from cryptoaudit.repair.request import build_repair_request
from cryptoaudit.storage.sqlite import ExperimentStore
from cryptoaudit.validation.integrity import IntegrityChecker
from cryptoaudit.validation.oracle import HiddenOracle
from cryptoaudit.validation.runner import ValidationPipeline


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
        return analysis_stage(self.analyzer, module)

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
            candidate = candidate_stage(strategy, run.request, module, self.integrity)
            report, outcome = validation_stage(self.validator, candidate, module, run.rule_ids, oracle, functional_checks)
            if self.store is not None and run_id is not None:
                self.store.record(run_id, outcome, candidate, report)
            run.runs.append(StrategyRun(candidate=candidate, report=report, outcome=outcome))
        return run
