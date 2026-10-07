"""Markdown rendering of research findings."""

from typing import List, Optional

from cryptoaudit.evaluation.research import Proportion, ResearchFindings


def _fmt(p: Optional[Proportion]) -> str:
    if p is None or p.rate is None:
        return "n/a"
    ci = f" [{p.ci95[0]:.2f}, {p.ci95[1]:.2f}]" if p.ci95 else ""
    return f"{p.rate:.0%} ({p.successes}/{p.total}){ci}"


def to_markdown(findings: ResearchFindings) -> str:
    lines: List[str] = [f"# CryptoAudit research findings{f' — run {findings.run_id}' if findings.run_id else ''}", ""]
    lines.append(f"Outcomes analysed: {findings.total_outcomes}. Verified = V1 PASS ∧ V2 PASS ∧ (V3 PASS where gating).")
    lines += ["", "## Strategy comparison", ""]
    lines.append("| Strategy | Rule | Attempts | Produced | Verified | Failed | Unverified | No candidate | V0 clean | Clean but not verified |")
    lines.append("|---|---|---|---|---|---|---|---|---|---|")
    for s in findings.strategy_stats:
        lines.append(
            f"| {s.strategy_id.value} | {s.rule_id} | {s.attempts} | {s.produced} | {s.verified} | {s.failed} | "
            f"{s.unverified} | {s.no_candidate} | {s.v0_clean} | {s.scanner_clean_not_verified} |"
        )
    lines += ["", "## Verified rate by category (95% Wilson CI)", ""]
    for rule, p in findings.verified_by_rule.items():
        lines.append(f"- {rule}: {_fmt(p)}")
    lines += ["", "## Scanners vs actual correctness", ""]
    lines.append("| Tool | Detects vulnerable originals | Candidates judged clean | Clean but not verified | Verified but still flagged |")
    lines.append("|---|---|---|---|---|")
    for tool, a in findings.scanners.items():
        lines.append(
            f"| {tool} | {_fmt(a.original_detection)} | {a.candidates_judged_clean} | {_fmt(a.clean_but_not_verified)} | "
            f"{_fmt(a.verified_but_still_flagged)} |"
        )
    lines += ["", "## Compatibility", "", f"Secure + functional repairs that broke legacy data: {_fmt(findings.compatibility_breaks)}"]
    lines += ["", "## Insights", ""]
    lines += [f"- {i}" for i in findings.insights] or ["- (not enough data)"]
    return "\n".join(lines) + "\n"
