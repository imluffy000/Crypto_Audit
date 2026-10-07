"""Research analysis over stored experiment outcomes."""

import math
from collections import defaultdict
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from pydantic import BaseModel, Field

from cryptoaudit.aggregation.aggregator import compare_strategies
from cryptoaudit.models.experiment import CaseOutcome, StrategyStats, Verdict
from cryptoaudit.models.validation import GateStatus


def wilson_interval(successes: int, total: int, z: float = 1.96) -> Optional[Tuple[float, float]]:
    """95% Wilson score interval for a proportion (robust for small benchmark sizes)."""
    if total == 0:
        return None
    p = successes / total
    denom = 1 + z * z / total
    centre = (p + z * z / (2 * total)) / denom
    margin = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / denom
    return round(max(0.0, centre - margin), 4), round(min(1.0, centre + margin), 4)


class Proportion(BaseModel):
    successes: int
    total: int
    rate: Optional[float] = None
    ci95: Optional[Tuple[float, float]] = None

    @classmethod
    def of(cls, successes: int, total: int) -> "Proportion":
        return cls(
            successes=successes,
            total=total,
            rate=round(successes / total, 4) if total else None,
            ci95=wilson_interval(successes, total),
        )


class ScannerAssessment(BaseModel):
    tool: str
    original_detection: Proportion  # vulnerable originals the tool flags (relevant issues)
    candidates_judged_clean: int
    clean_but_not_verified: Proportion  # overestimation: P(not VERIFIED | tool says clean)
    verified_but_still_flagged: Proportion  # underestimation: P(tool flags | VERIFIED)


class ResearchFindings(BaseModel):
    run_id: Optional[str] = None
    total_outcomes: int
    strategy_stats: List[StrategyStats]
    verified_by_strategy: Dict[str, Proportion]
    verified_by_rule: Dict[str, Proportion]
    hardest_rules: List[str]
    compatibility_breaks: Proportion  # V1+V2 pass but gating V3 fails, among V1+V2 pass with V3 applicable
    scanners: Dict[str, ScannerAssessment]
    insights: List[str] = Field(default_factory=list)


def analyze(outcomes: Sequence[CaseOutcome], baselines: Iterable[Dict[str, Any]] = (), run_id: Optional[str] = None) -> ResearchFindings:
    outcomes = list(outcomes)
    verified_by_strategy = _verified_by(outcomes, lambda o: [o.strategy_id.value])
    verified_by_rule = _verified_by(outcomes, lambda o: o.rule_ids)
    hardest = sorted(
        (rule for rule, p in verified_by_rule.items() if p.total),
        key=lambda rule: (verified_by_rule[rule].rate, rule),
    )

    secure_and_functional = [
        o for o in outcomes
        if o.gates.get("V1") is GateStatus.PASS and o.gates.get("V2") is GateStatus.PASS
        and o.gates.get("V3") not in (None, GateStatus.NOT_APPLICABLE, GateStatus.NOT_RUN)
    ]
    breaks = Proportion.of(sum(o.gates.get("V3") is GateStatus.FAIL for o in secure_and_functional), len(secure_and_functional))

    findings = ResearchFindings(
        run_id=run_id,
        total_outcomes=len(outcomes),
        strategy_stats=compare_strategies(outcomes),
        verified_by_strategy=verified_by_strategy,
        verified_by_rule=verified_by_rule,
        hardest_rules=hardest,
        compatibility_breaks=breaks,
        scanners=_scanner_assessments(outcomes, list(baselines)),
    )
    findings.insights = _insights(findings)
    return findings


def _verified_by(outcomes: List[CaseOutcome], keys) -> Dict[str, Proportion]:
    totals: Dict[str, List[int]] = defaultdict(lambda: [0, 0])
    for outcome in outcomes:
        for key in keys(outcome):
            totals[key][1] += 1
            totals[key][0] += outcome.verdict is Verdict.VERIFIED
    return {key: Proportion.of(v, n) for key, (v, n) in sorted(totals.items())}


def _scanner_assessments(outcomes: List[CaseOutcome], baselines: List[Dict[str, Any]]) -> Dict[str, ScannerAssessment]:
    tools = sorted({tool for o in outcomes for tool in o.scanner_results} | {t for b in baselines for t in b["evidence"]})
    assessments = {}
    for tool in tools:
        scanned = [b["evidence"][tool] for b in baselines if b["evidence"].get(tool, {}).get("available")]
        detected = sum((e.get("relevant_issues") or 0) > 0 for e in scanned)
        judged = [o for o in outcomes if o.scanner_results.get(tool) is not None]
        clean = [o for o in judged if o.scanner_results[tool]]
        verified = [o for o in judged if o.verdict is Verdict.VERIFIED]
        assessments[tool] = ScannerAssessment(
            tool=tool,
            original_detection=Proportion.of(detected, len(scanned)),
            candidates_judged_clean=len(clean),
            clean_but_not_verified=Proportion.of(sum(o.verdict is not Verdict.VERIFIED for o in clean), len(clean)),
            verified_but_still_flagged=Proportion.of(sum(not o.scanner_results[tool] for o in verified), len(verified)),
        )
    return assessments


def _pct(p: Proportion) -> str:
    return "n/a" if p.rate is None else f"{p.rate:.0%} ({p.successes}/{p.total})"


def _insights(f: ResearchFindings) -> List[str]:
    insights: List[str] = []
    for tool, a in f.scanners.items():
        if a.clean_but_not_verified.total:
            insights.append(
                f"{tool}: {_pct(a.clean_but_not_verified)} of candidates it reported clean were not verified "
                "by V1-V3 (scanner overestimation of repair success)."
            )
        if a.verified_but_still_flagged.total and a.verified_but_still_flagged.successes:
            insights.append(f"{tool}: still flags {_pct(a.verified_but_still_flagged)} of verified repairs (e.g. legacy-read code paths).")
    if f.hardest_rules:
        lowest = f.verified_by_rule[f.hardest_rules[0]].rate
        tied = [rule for rule in f.hardest_rules if f.verified_by_rule[rule].rate == lowest]
        label = "Hardest category" if len(tied) == 1 else "Hardest categories (tied)"
        insights.append(f"{label}: {', '.join(tied)} with verified rate {lowest:.0%}.")
    if f.compatibility_breaks.total:
        insights.append(
            f"Security-correct, functional repairs broke legacy compatibility in {_pct(f.compatibility_breaks)} of applicable cases."
        )
    best = max(f.verified_by_strategy.items(), key=lambda kv: (kv[1].rate or 0, kv[0]), default=None)
    if best is not None:
        insights.append(f"Best strategy by verified rate: {best[0]} at {_pct(best[1])}.")
    return insights
