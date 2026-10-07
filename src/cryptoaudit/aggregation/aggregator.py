"""Acceptance logic and cross-strategy comparison. V0 (scanners) never influences acceptance."""

from collections import defaultdict
from statistics import mean
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from cryptoaudit.aggregation.models import CaseOutcome, StrategyStats, Verdict
from cryptoaudit.candidate.models import Candidate
from cryptoaudit.validation.models import GateId, GateStatus, ValidationReport

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


def compare_strategies(outcomes: Iterable[CaseOutcome]) -> List[StrategyStats]:
    """Per (strategy, rule) statistics plus an 'ALL' row per strategy, deterministically ordered."""
    groups: Dict[Tuple[str, str], List[CaseOutcome]] = defaultdict(list)
    for outcome in outcomes:
        for rule in outcome.rule_ids or ["UNKNOWN"]:
            groups[(outcome.strategy_id.value, rule)].append(outcome)
        groups[(outcome.strategy_id.value, "ALL")].append(outcome)

    stats: List[StrategyStats] = []
    for (strategy, rule), items in sorted(groups.items()):
        produced = [o for o in items if o.verdict is not Verdict.NO_CANDIDATE]
        stats.append(
            StrategyStats(
                strategy_id=items[0].strategy_id,
                rule_id=rule,
                attempts=len(items),
                produced=len(produced),
                no_candidate=sum(o.verdict is Verdict.NO_CANDIDATE for o in items),
                verified=sum(o.verdict is Verdict.VERIFIED for o in items),
                failed=sum(o.verdict is Verdict.FAILED for o in items),
                unverified=sum(o.verdict is Verdict.UNVERIFIED for o in items),
                integrity_failed=sum(o.integrity_passed is False for o in items),
                v0_clean=sum(o.scanner_clean is True for o in items),
                v1_pass=sum(o.gates.get("V1") is GateStatus.PASS for o in items),
                v2_pass=sum(o.gates.get("V2") is GateStatus.PASS for o in items),
                v3_applicable=sum(o.gates.get("V3") not in (None, GateStatus.NOT_APPLICABLE) for o in items),
                v3_pass=sum(o.gates.get("V3") is GateStatus.PASS for o in items),
                scanner_clean_not_verified=sum(o.scanner_clean is True and o.verdict is not Verdict.VERIFIED for o in items),
                mean_repair_seconds=round(mean(o.repair_seconds for o in items), 4),
                mean_validation_seconds=round(mean(o.validation_seconds for o in items), 4),
            )
        )
    return stats
