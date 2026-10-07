"""Experiment models: per-case outcomes, verdicts, strategy statistics and run metadata."""

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from cryptoaudit.models.repair import RepairStatus, StrategyId
from cryptoaudit.models.validation import GateStatus


class Verdict(str, Enum):
    VERIFIED = "VERIFIED"  # every gating gate (V1, V2, V3 where gating) passed
    FAILED = "FAILED"  # integrity or a gating gate failed
    UNVERIFIED = "UNVERIFIED"  # no failure observed, but a gating gate lacked executable evidence
    NO_CANDIDATE = "NO_CANDIDATE"  # the strategy produced no code (NO_REPAIR / NOT_APPLICABLE / PARSE_ERROR)


class CaseOutcome(BaseModel):
    """One strategy's result on one module: the unit stored in the experiment database."""

    case_id: Optional[str] = None
    module_name: str
    rule_ids: List[str]
    strategy_id: StrategyId
    candidate_id: str
    repair_status: RepairStatus
    repair_failure_reason: Optional[str] = None
    integrity_passed: Optional[bool] = None
    gates: Dict[str, GateStatus] = Field(default_factory=dict)
    v3_gating: bool = False
    scanner_results: Dict[str, Optional[bool]] = Field(default_factory=dict)  # tool -> clean? (None = unavailable)
    verdict: Verdict
    reasons: List[str] = Field(default_factory=list)
    repair_seconds: float = 0.0
    validation_seconds: float = 0.0

    @property
    def scanner_clean(self) -> Optional[bool]:
        status = self.gates.get("V0")
        return None if status in (None, GateStatus.ERROR, GateStatus.NOT_RUN) else status is GateStatus.PASS


class StrategyStats(BaseModel):
    strategy_id: StrategyId
    rule_id: str  # "ALL" for the strategy-wide row
    attempts: int = 0
    produced: int = 0
    no_candidate: int = 0
    verified: int = 0
    failed: int = 0
    unverified: int = 0
    integrity_failed: int = 0
    v0_clean: int = 0
    v1_pass: int = 0
    v2_pass: int = 0
    v3_applicable: int = 0
    v3_pass: int = 0
    scanner_clean_not_verified: int = 0
    mean_repair_seconds: float = 0.0
    mean_validation_seconds: float = 0.0

    def rate(self, count: int, denominator: Optional[int] = None) -> Optional[float]:
        base = self.attempts if denominator is None else denominator
        return None if base == 0 else round(count / base, 4)


class RunInfo(BaseModel):
    run_id: str
    created_at: str
    cryptoaudit_version: str
    git_commit: Optional[str]
    config_hash: str
    config: Dict[str, Any]
