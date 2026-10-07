"""Console and JSON formatters for CryptoAudit findings."""

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from cryptoaudit.models.analysis import AnalysisResult


def format_json_report(result: AnalysisResult) -> str:
    """Format analysis result as a structured JSON string."""
    return result.model_dump_json(indent=2)


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
