"""Validation models: integrity reports and per-check, per-gate and per-candidate results."""

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from cryptoaudit.utils.errors import ErrorCode


class GateId(str, Enum):
    V0 = "V0"  # Scanner validation (recorded, never gating)
    V1 = "V1"  # Functional validation
    V2 = "V2"  # Security-property validation
    V3 = "V3"  # Legacy compatibility validation


class GateStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    ERROR = "ERROR"  # the validator could not evaluate the candidate
    NOT_APPLICABLE = "NOT_APPLICABLE"  # the gate does not apply to this case (e.g. V3 for CR5)
    NOT_RUN = "NOT_RUN"  # the gate applies but was not executed (no oracle, no code, integrity failure)


class CheckResult(BaseModel):
    name: str
    status: GateStatus
    message: str = ""
    duration: float = 0.0


class GateResult(BaseModel):
    gate: GateId
    status: GateStatus
    gating: bool
    summary: str = ""
    checks: List[CheckResult] = Field(default_factory=list)
    evidence: Dict[str, Any] = Field(default_factory=dict)
    error_code: Optional[ErrorCode] = None
    duration_seconds: float = 0.0


class ValidationReport(BaseModel):
    candidate_id: str
    gates: List[GateResult] = Field(default_factory=list)

    def gate(self, gate_id: GateId) -> Optional[GateResult]:
        return next((g for g in self.gates if g.gate is gate_id), None)

    def status(self, gate_id: GateId) -> GateStatus:
        result = self.gate(gate_id)
        return result.status if result is not None else GateStatus.NOT_RUN


class IntegrityIssue(BaseModel):
    kind: str  # syntax | size | dependency | dangerous_call
    message: str
    line: Optional[int] = None


class IntegrityReport(BaseModel):
    passed: bool
    syntax_ok: bool
    imports: List[str] = Field(default_factory=list)
    issues: List[IntegrityIssue] = Field(default_factory=list)

    def issues_of(self, kind: str) -> List[IntegrityIssue]:
        return [i for i in self.issues if i.kind == kind]
