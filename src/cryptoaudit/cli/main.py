"""Typer CLI entrypoint for CryptoAudit."""

from pathlib import Path
import typer
from rich.console import Console

from cryptoaudit.analyzer.engine import AnalyzerEngine
from cryptoaudit.reporting.findings import format_json_report, render_console_report

app = typer.Typer(
    name="cryptoaudit",
    help="CryptoAudit: Python-focused cryptographic misuse analysis framework.",
    add_completion=False,
)
console = Console()


@app.callback()
def main_callback() -> None:
    """CryptoAudit cryptographic analysis tool."""
    pass


@app.command(name="analyze")
def analyze(
    python_file: Path = typer.Argument(
        ...,
        help="Path to Python source file to analyze.",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        "-j",
        help="Output analysis results in JSON format.",
    ),
) -> None:
    """Analyze a Python file for cryptographic misuses."""
    try:
        engine = AnalyzerEngine()
        result = engine.analyze_file(python_file)

        if json_output:
            typer.echo(format_json_report(result))
        else:
            render_console_report(result, console)

    except Exception as exc:
        console.print(f"[bold red]Error analyzing file {python_file}: {exc}[/bold red]")
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
