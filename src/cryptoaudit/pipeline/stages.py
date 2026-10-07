"""Pipeline stages. Each stage has explicit inputs and outputs and no hidden state."""

import tempfile
import time
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

from cryptoaudit.analysis.analyzer import AnalyzerEngine
from cryptoaudit.models.experiment import CaseOutcome
from cryptoaudit.models.finding import Finding
from cryptoaudit.models.repair import Candidate, RepairRequest, make_candidate
from cryptoaudit.models.scan import ModuleInput
from cryptoaudit.models.validation import ValidationReport
from cryptoaudit.repair.base import RepairStrategy
from cryptoaudit.utils.errors import CryptoAuditError, ErrorCode
from cryptoaudit.validation.gates import build_outcome
from cryptoaudit.validation.integrity import IntegrityChecker
from cryptoaudit.validation.oracle import HiddenOracle
from cryptoaudit.validation.runner import ValidationPipeline


def analysis_stage(analyzer: AnalyzerEngine, module: ModuleInput) -> List[Finding]:
    """Run the deterministic Analyzer; finding paths are normalised to the module name."""
    with tempfile.TemporaryDirectory(prefix="cryptoaudit-in-") as tmp:
        path = Path(tmp) / module.module_name
        with open(path, "w", encoding="utf-8", newline="") as handle:
            handle.write(module.source)
        try:
            result = analyzer.analyze_file(path)
        except ValueError as exc:
            raise CryptoAuditError(ErrorCode.PARSE_ERROR, str(exc).replace(str(path), module.module_name)) from exc
    return [f.model_copy(update={"file": module.module_name}) for f in result.findings]


def candidate_stage(
    strategy: RepairStrategy, request: RepairRequest, module: ModuleInput, integrity: IntegrityChecker
) -> Candidate:
    """Generate one candidate and attach integrity evidence (code is never executed here)."""
    repair = strategy.repair(request)
    report = (
        integrity.check(repair.candidate_code or "", module.allowed_libraries, module.source)
        if repair.produced
        else None
    )
    return make_candidate(module.module_name, module.source, repair, report)


def validation_stage(
    validator: ValidationPipeline,
    candidate: Candidate,
    module: ModuleInput,
    rule_ids: Sequence[str],
    oracle: Optional[HiddenOracle],
    functional_checks: Optional[Path],
) -> Tuple[ValidationReport, CaseOutcome]:
    """Validate a candidate independently and aggregate the evidence into a verdict."""
    started = time.perf_counter()
    report = validator.validate(candidate, module.source, rule_ids, oracle, functional_checks)
    outcome = build_outcome(candidate, report, rule_ids, module.case_id, time.perf_counter() - started)
    return report, outcome
