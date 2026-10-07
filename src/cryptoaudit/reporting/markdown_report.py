"""Markdown rendering of research findings and website scan reports."""

from typing import List, Optional

from cryptoaudit.models.scan import RepositoryScanResult
from cryptoaudit.reporting.research import Proportion, ResearchFindings


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


def scan_to_markdown(result: RepositoryScanResult, scan_id: str) -> str:
    """Markdown export of a website repository scan."""
    lines: List[str] = [
        f"# CryptoAudit report: {result.repository}",
        "",
        f"Scan `{scan_id}` of `{result.ref}`" + (f" at commit `{result.commit}`" if result.commit else "") + ".",
        "",
        "Verdicts: **Verified** = functional, security and compatibility checks passed; **Unverified** = plausible "
        "repair whose security properties were not tested (no oracle exists for this code); **Failed** = a check "
        "failed; **No candidate** = the strategy produced no code.",
        "",
        "## Summary",
        "",
        f"- Python files scanned: {result.summary.files_scanned}",
        f"- Files with findings: {result.summary.files_with_findings}",
        f"- Findings: {result.summary.findings} "
        + (f"({', '.join(f'{k}: {v}' for k, v in result.summary.findings_by_rule.items())})" if result.summary.findings_by_rule else ""),
        f"- Candidates scanners call clean but validation did not verify: {result.summary.scanner_clean_not_verified}",
        f"- Strategies run: {', '.join(s.value for s in result.strategies)}",
    ]
    for strategy, reason in result.skipped_strategies.items():
        lines.append(f"- Strategy {strategy} skipped: {reason}")
    strategies = [s.value for s in result.strategies]
    if result.findings:
        lines += ["", "## Findings", "", "| File | Line | Rule | Best verdict | " + " | ".join(strategies) + " |",
                  "|---|---|---|---|" + "---|" * len(strategies)]
        runs_by_file = {f.path: {r.strategy_id.value: r.verdict.value for r in f.runs} for f in result.files}
        for view in result.findings:
            f = view.finding
            verdicts = runs_by_file.get(f.file, {})
            cells = " | ".join(verdicts.get(s, "-") for s in strategies)
            lines.append(f"| `{f.file}` | {f.line} | {f.rule_id} | {view.best_verdict.value} | {cells} |")
    for file in result.files:
        lines += ["", f"## `{file.path}`", ""]
        for run in file.runs:
            lines.append(f"### {run.strategy_id.value}: {run.verdict.value}")
            lines.append("")
            lines.append(run.explanation.headline)
            for limitation in run.explanation.limitations:
                lines.append(f"\n> {limitation}")
            if run.diff:
                lines += ["", "```diff", run.diff.rstrip("\n"), "```"]
            lines.append("")
    if result.skipped_files:
        lines += ["", "## Skipped files", ""]
        lines += [f"- `{s.path}`: {s.reason}" for s in result.skipped_files]
    return "\n".join(lines).rstrip() + "\n"
