"""
Evidence-based "why" explanations. Every statement is derived from recorded evidence (the
finding, the diff, gate results, scanner results and the verdict); nothing is generated.
"""

import ast
from typing import List, Optional, Sequence, Set

from pydantic import BaseModel, Field

from cryptoaudit.analysis.call_analyzer import extract_calls
from cryptoaudit.analysis.import_analyzer import extract_imports
from cryptoaudit.models.experiment import CaseOutcome, Verdict
from cryptoaudit.models.finding import Finding, finding_id
from cryptoaudit.models.repair import Candidate
from cryptoaudit.models.validation import GateId, GateStatus, ValidationReport

VERDICT_LABELS = {
    Verdict.VERIFIED: "Verified",
    Verdict.FAILED: "Failed",
    Verdict.UNVERIFIED: "Unverified",
    Verdict.NO_CANDIDATE: "No candidate",
}
NO_ORACLE_LIMITATION = (
    "No security-property tests exist for this code, so V2 (security) and V3 (compatibility) cannot run. "
    "'Unverified' is therefore the best possible result: review the change and add tests before merging."
)


class ExplanationSection(BaseModel):
    title: str
    points: List[str] = Field(default_factory=list)


class Explanation(BaseModel):
    source: str = "evidence"
    verdict: Verdict
    headline: str
    sections: List[ExplanationSection] = Field(default_factory=list)
    limitations: List[str] = Field(default_factory=list)


def resolved_calls(source: str) -> Set[str]:
    """Fully qualified names of imported APIs the module calls (via the Analyzer's resolvers)."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return set()
    return {call.resolved_name for call in extract_calls(tree, extract_imports(tree))}


def _diff_stats(diff: str) -> tuple[int, int]:
    added = sum(1 for line in diff.splitlines() if line.startswith("+") and not line.startswith("+++"))
    removed = sum(1 for line in diff.splitlines() if line.startswith("-") and not line.startswith("---"))
    return added, removed


def _headline(outcome: CaseOutcome, report: ValidationReport, candidate: Candidate) -> str:
    if outcome.verdict is Verdict.NO_CANDIDATE:
        return f"No candidate produced ({candidate.repair.status.value}): {candidate.repair.failure_reason}"
    if outcome.verdict is Verdict.VERIFIED:
        return "Repair verified: functional, security-property and applicable compatibility checks all passed."
    if outcome.verdict is Verdict.FAILED:
        failed = [g.gate.value for g in report.gates if g.gating and g.status is GateStatus.FAIL]
        if outcome.integrity_passed is False:
            return "Repair rejected: the candidate failed integrity checks and was never executed."
        return f"Repair rejected: {', '.join(failed) or 'a gating gate'} failed."
    if report.status(GateId.V0) is GateStatus.PASS:
        return (
            "Plausible repair, not verified: scanners report it clean and the public interface is preserved, "
            "but its security properties were not tested."
        )
    return "Repair not verified: validation could not produce enough evidence to accept it."


def explain(
    findings: Sequence[Finding],
    original_source: str,
    candidate: Candidate,
    report: ValidationReport,
    outcome: CaseOutcome,
    has_oracle: bool,
) -> Explanation:
    sections: List[ExplanationSection] = []

    sections.append(
        ExplanationSection(
            title="What CryptoAudit found",
            points=[
                f"Line {f.line} [{f.rule_id} · {f.category.value}]: {f.explanation} Guidance: {f.remediation}"
                for f in findings
            ],
        )
    )

    change = ExplanationSection(title=f"What {candidate.repair.strategy_id.value} changed")
    if candidate.repair.produced:
        before, after = resolved_calls(original_source), resolved_calls(candidate.code or "")
        removed, introduced = sorted(before - after), sorted(after - before)
        if removed:
            change.points.append("Stopped calling: " + ", ".join(removed))
        if introduced:
            change.points.append("Now calls: " + ", ".join(introduced))
        added, deleted = _diff_stats(candidate.diff)
        change.points.append(f"{added} line(s) added, {deleted} line(s) removed.")
        targeted = {finding_id(f): f for f in findings}
        unrepaired = [targeted[i] for i in candidate.repair.unrepaired_finding_ids if i in targeted]
        if unrepaired:
            change.points.append(
                "Left unchanged: " + ", ".join(f"line {f.line} [{f.rule_id}]" for f in unrepaired)
            )
    else:
        change.points.append(f"No code was produced. {candidate.repair.failure_reason}")
    labels = {finding_id(f): f"line {f.line} [{f.rule_id}]" for f in findings}
    for note in candidate.repair.notes:
        for fid, label in labels.items():
            note = note.replace(fid, label)
        change.points.append(f"Strategy note: {note}")
    sections.append(change)

    evidence = ExplanationSection(title="Validation evidence")
    for gate in report.gates:
        role = "recorded only" if gate.gate is GateId.V0 else ("gating" if gate.gating else "non-gating")
        evidence.points.append(f"{gate.gate.value} ({role}): {gate.status.value} - {gate.summary}")
        for check in gate.checks:
            if check.status is not GateStatus.PASS:
                evidence.points.append(f"  {gate.gate.value} check '{check.name}' {check.status.value}: {check.message}")
    sections.append(evidence)

    comparison = ExplanationSection(title="Scanners vs validation")
    verdict_label = VERDICT_LABELS[outcome.verdict]
    for tool, clean in sorted(outcome.scanner_results.items()):
        if clean is None:
            comparison.points.append(f"{tool}: unavailable (not treated as clean).")
        elif clean and outcome.verdict is not Verdict.VERIFIED:
            comparison.points.append(f"{tool}: reports clean, yet validation verdict is {verdict_label} - scanner silence is not proof.")
        elif clean:
            comparison.points.append(f"{tool}: reports clean; validation agrees ({verdict_label}).")
        else:
            comparison.points.append(f"{tool}: still reports the issue (validation verdict: {verdict_label}).")
    if not comparison.points:
        comparison.points.append("No scanner results were recorded for this candidate.")
    sections.append(comparison)

    sections.append(ExplanationSection(title=f"Verdict: {verdict_label}", points=list(outcome.reasons)))

    limitations: List[str] = []
    if not has_oracle and candidate.repair.produced:
        limitations.append(NO_ORACLE_LIMITATION)
    return Explanation(
        verdict=outcome.verdict,
        headline=_headline(outcome, report, candidate),
        sections=sections,
        limitations=limitations,
    )


def render_text(explanation: Explanation, max_points: Optional[int] = None) -> str:
    """Plain-text rendering (used as AI-explanation input and for exports)."""
    lines = [explanation.headline]
    for section in explanation.sections:
        lines.append(f"\n{section.title}:")
        points = section.points if max_points is None else section.points[:max_points]
        lines.extend(f"- {p}" for p in points)
    for limitation in explanation.limitations:
        lines.append(f"\nLimitation: {limitation}")
    return "\n".join(lines)
