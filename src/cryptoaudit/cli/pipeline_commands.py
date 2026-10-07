"""CLI commands for repair, validation, benchmark runs and research reports."""

import json
from pathlib import Path
from typing import List, Optional

import typer
from rich.console import Console
from rich.table import Table

from cryptoaudit.benchmark.repository import BenchmarkRepository
from cryptoaudit.core.config import Settings
from cryptoaudit.core.errors import CryptoAuditError
from cryptoaudit.evaluation import analyze as analyze_findings
from cryptoaudit.evaluation import to_markdown
from cryptoaudit.ingest.loader import load_module
from cryptoaudit.pipeline.factory import build_pipeline, build_sandbox, open_store, parse_strategy_ids
from cryptoaudit.pipeline.runner import BenchmarkRunner, describe_strategies
from cryptoaudit.reporting.repair_report import module_run_to_dict, render_module_run

console = Console()
bench_app = typer.Typer(help="Benchmark experiments: run all cases x strategies and analyse results.", add_completion=False)

STRATEGIES_OPTION = typer.Option(["S1,S2"], "--strategy", "-s", help="Strategies to run (S1-S4), repeat or comma-separate.")
SANDBOX_OPTION = typer.Option(None, "--sandbox", help="Validation sandbox: docker (default, isolated) or local.")
UNSAFE_OPTION = typer.Option(
    False, "--unsafe-local-sandbox", help="Allow the non-isolated local sandbox. Only for trusted code."
)


def _fail(exc: CryptoAuditError) -> None:
    console.print(f"[bold red]{exc.code.value}[/bold red]: {exc.message}")
    raise typer.Exit(code=1)


def repair(
    python_file: Path = typer.Argument(..., exists=True, file_okay=True, dir_okay=False, readable=True),
    strategies: List[str] = STRATEGIES_OPTION,
    allowed_lib: List[str] = typer.Option([], "--allowed-lib", help="Library the repair may use (repeatable)."),
    target_python: str = typer.Option("3.11", "--target-python"),
    checks: Optional[Path] = typer.Option(None, "--checks", exists=True, dir_okay=False, help="User V1 check file (check_*(ctx) functions)."),
    sandbox: Optional[str] = SANDBOX_OPTION,
    unsafe_local_sandbox: bool = UNSAFE_OPTION,
    show_code: bool = typer.Option(False, "--show-code", help="Print full repaired modules."),
    json_output: bool = typer.Option(False, "--json", "-j"),
) -> None:
    """Analyze a file, generate candidate repairs and validate them independently."""
    settings = Settings()
    try:
        module = load_module(python_file, allowed_lib, target_python)
        box = build_sandbox(settings, sandbox, unsafe_local_sandbox)
        pipeline = build_pipeline(settings, parse_strategy_ids(strategies), box)
        run = pipeline.run_module(module, functional_checks=checks)
    except CryptoAuditError as exc:
        _fail(exc)
        return
    if json_output:
        typer.echo(json.dumps(module_run_to_dict(run), indent=2))
    else:
        render_module_run(run, console, show_code)
        if checks is None:
            console.print(
                "[dim]No security or compatibility oracle exists for user code, so V2/V3 are NOT_RUN and the best "
                "possible assessment is Unverified. Supply --checks for functional checks.[/dim]"
            )


@bench_app.command("list")
def bench_list(cases_dir: Optional[Path] = typer.Option(None, "--cases-dir")) -> None:
    """List benchmark cases (public metadata only)."""
    try:
        repo = BenchmarkRepository(cases_dir or Settings().benchmark_dir)
    except CryptoAuditError as exc:
        _fail(exc)
        return
    table = Table("Case", "Rule", "Title", "Allowed libraries")
    for case_id in repo.case_ids():
        spec = repo.public_case(case_id).spec
        table.add_row(case_id, spec.rule_id, spec.title, ", ".join(spec.allowed_libraries))
    console.print(table)


@bench_app.command("run")
def bench_run(
    strategies: List[str] = STRATEGIES_OPTION,
    cases: List[str] = typer.Option([], "--case", "-c", help="Case id to run (repeatable); default all."),
    cases_dir: Optional[Path] = typer.Option(None, "--cases-dir"),
    db: Optional[Path] = typer.Option(None, "--db", help="Experiment database path."),
    sandbox: Optional[str] = SANDBOX_OPTION,
    unsafe_local_sandbox: bool = UNSAFE_OPTION,
) -> None:
    """Run the benchmark and append the results to the experiment database."""
    settings = Settings()
    try:
        repo = BenchmarkRepository(cases_dir or settings.benchmark_dir)
        store = open_store(settings, db)
        box = build_sandbox(settings, sandbox, unsafe_local_sandbox)
        pipeline = build_pipeline(settings, parse_strategy_ids(strategies), box, store)
    except CryptoAuditError as exc:
        _fail(exc)
        return
    config = {
        "strategies": describe_strategies(pipeline.strategies),
        "sandbox": {"kind": box.name, "timeout": box.timeout, "image": getattr(box, "image", None)},
        "scanners": [s.name for s in pipeline.validator.scanner_validator.scanners],
        "semgrep_config": settings.semgrep_config if settings.enable_semgrep else None,
    }

    def on_case(case_id, module_run):
        verdicts = ", ".join(f"{r.outcome.strategy_id.value}={r.outcome.verdict.value}" for r in module_run.runs)
        console.print(f"  {case_id}: {verdicts or 'no findings'}")

    def on_error(case_id, exc):
        console.print(f"  [red]{case_id}: {exc.code.value} {exc.message}[/red]")

    console.print(f"Running {len(cases) or len(repo.case_ids())} case(s) with {', '.join(s.strategy_id.value for s in pipeline.strategies)}")
    info = BenchmarkRunner(repo, pipeline, store).run(config, cases or None, on_case, on_error)
    console.print(f"[bold]Run {info.run_id}[/bold] stored in {store.path} (config {info.config_hash[:12]})")


@bench_app.command("report")
def bench_report(
    run_id: Optional[str] = typer.Option(None, "--run-id", help="Run to analyse; default latest."),
    db: Optional[Path] = typer.Option(None, "--db"),
    markdown: Optional[Path] = typer.Option(None, "--markdown", help="Write the Markdown report to this file."),
    json_output: bool = typer.Option(False, "--json", "-j"),
) -> None:
    """Analyse a stored run: strategy comparison, scanner overestimation, compatibility, insights."""
    settings = Settings()
    store = open_store(settings, db)
    run_id = run_id or store.latest_run_id()
    if run_id is None:
        console.print("[yellow]No experiment runs found.[/yellow]")
        raise typer.Exit(code=1)
    findings = analyze_findings(store.outcomes(run_id), store.baselines(run_id), run_id)
    if json_output:
        typer.echo(findings.model_dump_json(indent=2))
        return
    text = to_markdown(findings)
    if markdown is not None:
        markdown.write_text(text, encoding="utf-8")
        console.print(f"Report written to {markdown}")
    else:
        console.print(text)


def register(app: typer.Typer) -> None:
    app.command(name="repair")(repair)
    app.add_typer(bench_app, name="bench")
