"""Console rendering of analysis results and repair/validation reports."""


from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table

from cryptoaudit.models.analysis import AnalysisResult
from cryptoaudit.models.experiment import Verdict
from cryptoaudit.models.validation import GateStatus
from cryptoaudit.pipeline.pipeline_result import ModuleRun


def render_console_report(result: AnalysisResult, console: Console = None) -> None:
    """Render a human-readable report to the terminal using Rich."""
    if console is None:
        console = Console()

    console.print()
    console.print(f"[bold blue]CryptoAudit Misuse Analysis Report[/bold blue]")
    console.print(f"[dim]Target file: {result.target_file}[/dim]")
    console.print(f"[dim]Analyzer version: {result.analyzer_version}[/dim]\n")

    if not result.findings:
        console.print(
            Panel(
                "[bold green]No cryptographic misuses detected.[/bold green]",
                title="Audit Status",
                border_style="green",
            )
        )
        return

    table = Table(title=f"Findings ({result.total_findings})", border_style="red")
    table.add_column("Rule ID", style="bold yellow")
    table.add_column("Severity", style="bold red")
    table.add_column("Location", style="cyan")
    table.add_column("Matched API", style="magenta")
    table.add_column("Evidence", style="white")

    for finding in result.findings:
        loc_str = f"L{finding.line}" + (f":C{finding.column}" if finding.column is not None else "")
        table.add_row(
            finding.rule_id,
            finding.severity.value,
            loc_str,
            finding.matched_api,
            finding.evidence,
        )

    console.print(table)
    console.print()

    for i, finding in enumerate(result.findings, 1):
        console.print(f"[bold red]Finding #{i}: [{finding.rule_id}] {finding.category.value}[/bold red]")
        console.print(f"  [bold]File:[/bold] {finding.file}:{finding.line}")
        console.print(f"  [bold]API:[/bold] {finding.matched_api}")
        console.print(f"  [bold]Explanation:[/bold] {finding.explanation}")
        console.print(f"  [bold green]Remediation:[/bold green] {finding.remediation}\n")


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
