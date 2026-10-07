"""Console and JSON rendering of repair + validation results for one module."""

from typing import Any, Dict

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table

from cryptoaudit.aggregation.models import Verdict
from cryptoaudit.pipeline.orchestrator import ModuleRun
from cryptoaudit.validation.models import GateStatus

VERDICT_STYLE = {
    Verdict.VERIFIED: ("bold green", "Verified"),
    Verdict.FAILED: ("bold red", "Failed"),
    Verdict.UNVERIFIED: ("bold yellow", "Unverified"),
    Verdict.NO_CANDIDATE: ("bold magenta", "No candidate"),
}
GATE_STYLE = {
    GateStatus.PASS: "green",
    GateStatus.FAIL: "red",
    GateStatus.ERROR: "yellow",
    GateStatus.NOT_RUN: "dim",
    GateStatus.NOT_APPLICABLE: "dim",
}


def render_module_run(run: ModuleRun, console: Console, show_code: bool = False) -> None:
    module = run.module
    console.print()
    console.print(f"[bold blue]CryptoAudit repair report[/bold blue] — {module.module_name}")
    if not run.findings:
        console.print(Panel("[bold green]No cryptographic misuses detected; nothing to repair.[/bold green]"))
        return

    lines = sorted({f.line for f in run.findings})
    console.print(Syntax(module.source, "python", line_numbers=True, highlight_lines=set(lines)))
    for finding in run.findings:
        console.print(f"  [red]L{finding.line}[/red] [{finding.rule_id}] {finding.explanation}")

    for strategy_run in run.runs:
        outcome = strategy_run.outcome
        candidate = strategy_run.candidate
        style, label = VERDICT_STYLE[outcome.verdict]
        console.print()
        console.rule(f"Strategy {outcome.strategy_id.value} — repair status {outcome.repair_status.value}")

        if candidate.repair.produced:
            if show_code:
                console.print(Syntax(candidate.code or "", "python", line_numbers=True))
            console.print(Syntax(candidate.diff or "(no textual change)", "diff"))
        elif candidate.repair.failure_reason:
            console.print(f"[magenta]{candidate.repair.failure_reason}[/magenta]")

        table = Table(show_header=True, header_style="bold")
        table.add_column("Gate")
        table.add_column("Status")
        table.add_column("Gating")
        table.add_column("Summary", overflow="fold")
        for gate in strategy_run.report.gates:
            colour = GATE_STYLE[gate.status]
            table.add_row(gate.gate.value, f"[{colour}]{gate.status.value}[/{colour}]", "yes" if gate.gating else "no", gate.summary)
        console.print(table)
        console.print(Panel("\n".join(outcome.reasons) or "-", title=f"[{style}]Overall assessment: {label}[/{style}]"))


def module_run_to_dict(run: ModuleRun, include_code: bool = True) -> Dict[str, Any]:
    return {
        "module_name": run.module.module_name,
        "case_id": run.module.case_id,
        "findings": [f.model_dump(mode="json") for f in run.findings],
        "baseline": run.baseline,
        "results": [
            {
                "outcome": r.outcome.model_dump(mode="json"),
                "repair": r.candidate.repair.model_dump(mode="json"),
                "integrity": r.candidate.integrity.model_dump(mode="json") if r.candidate.integrity else None,
                "validation": r.report.model_dump(mode="json"),
                "diff": r.candidate.diff,
                **({"candidate_code": r.candidate.code} if include_code else {}),
            }
            for r in run.runs
        ],
    }
