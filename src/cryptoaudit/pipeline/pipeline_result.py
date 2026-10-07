"""Results produced by the pipeline for one module."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from cryptoaudit.models.experiment import CaseOutcome
from cryptoaudit.models.finding import Finding
from cryptoaudit.models.repair import Candidate, RepairRequest
from cryptoaudit.models.scan import ModuleInput
from cryptoaudit.models.validation import ValidationReport


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
