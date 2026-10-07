"""Acceptance gates: turn V0-V3 evidence into a verdict. V0 (scanners) never influences acceptance."""

from typing import Dict, List, Optional, Sequence, Tuple

from cryptoaudit.models.experiment import CaseOutcome, Verdict
from cryptoaudit.models.repair import Candidate
from cryptoaudit.models.validation import GateId, GateStatus, ValidationReport

EXECUTABLE_GATES = (GateId.V1, GateId.V2, GateId.V3)


def decide(candidate: Candidate, report: ValidationReport) -> Tuple[Verdict, List[str]]:
    """
    VERIFIED  iff  V1 PASS and V2 PASS and (V3 PASS where applicable and gating).
    Scanner results are deliberately not an input to this function's decision.
    """
    repair = candidate.repair
    if not repair.produced:
        return Verdict.NO_CANDIDATE, [f"Repair status {repair.status.value}: {repair.failure_reason}"]

    reasons: List[str] = []
    if candidate.integrity is not None and not candidate.integrity.passed:
        reasons.append("Integrity checks failed: " + "; ".join(i.message for i in candidate.integrity.issues))
        return Verdict.FAILED, reasons

    gating = [g for g in report.gates if g.gate in EXECUTABLE_GATES and g.gating]
    failed = [g for g in gating if g.status is GateStatus.FAIL]
    missing = [g for g in gating if g.status in (GateStatus.ERROR, GateStatus.NOT_RUN)]
    for gate in report.gates:
        if gate.gate in EXECUTABLE_GATES and not gate.gating and gate.status is GateStatus.FAIL:
            reasons.append(f"{gate.gate.value} failed (non-gating): {gate.summary}")

    if not {GateId.V1, GateId.V2} <= {g.gate for g in gating}:
        reasons.append("V1 and V2 must both be present and gating")
        return Verdict.UNVERIFIED, reasons
    if failed:
        reasons.extend(f"{g.gate.value} FAIL: {g.summary}" for g in failed)
        verdict = Verdict.FAILED
    elif missing:
        reasons.extend(f"{g.gate.value} {g.status.value}: {g.summary}" for g in missing)
        verdict = Verdict.UNVERIFIED
    else:
        reasons.append("All gating validation gates passed")
        verdict = Verdict.VERIFIED

    v0 = report.status(GateId.V0)
    if v0 is GateStatus.PASS and verdict is not Verdict.VERIFIED:
        reasons.append("Scanners report the candidate clean, but validation did not verify it")
    if v0 is GateStatus.FAIL and verdict is Verdict.VERIFIED:
        reasons.append("Validated repair is still flagged by at least one scanner")
    return verdict, reasons


def build_outcome(
    candidate: Candidate,
    report: ValidationReport,
    rule_ids: Sequence[str],
    case_id: Optional[str] = None,
    validation_seconds: float = 0.0,
) -> CaseOutcome:
    verdict, reasons = decide(candidate, report)
    v0 = report.gate(GateId.V0)
    scanner_results: Dict[str, Optional[bool]] = {}
    if v0 is not None:
        for tool, evidence in v0.evidence.items():
            scanner_results[tool] = None if not evidence.get("available") else (evidence.get("relevant_issues") or 0) == 0
    v3 = report.gate(GateId.V3)
    return CaseOutcome(
        case_id=case_id,
        module_name=candidate.module_name,
        rule_ids=sorted(set(rule_ids)),
        strategy_id=candidate.repair.strategy_id,
        candidate_id=candidate.candidate_id,
        repair_status=candidate.repair.status,
        repair_failure_reason=candidate.repair.failure_reason,
        integrity_passed=candidate.integrity.passed if candidate.integrity is not None else None,
        gates={g.gate.value: g.status for g in report.gates},
        v3_gating=bool(v3 and v3.gating),
        scanner_results=scanner_results,
        verdict=verdict,
        reasons=reasons,
        repair_seconds=candidate.repair.duration_seconds,
        validation_seconds=round(validation_seconds, 3),
    )


