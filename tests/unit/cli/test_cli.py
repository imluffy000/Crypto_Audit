"""CLI tests for analyze, repair and bench commands (local sandbox, no external scanners)."""

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from cryptoaudit.cli.main import app

runner = CliRunner()
CR5 = Path("benchmark/cases/cr5/cr5_session_token/module.py")


@pytest.fixture(autouse=True)
def no_external_scanners(monkeypatch):
    monkeypatch.setenv("CRYPTOAUDIT_ENABLE_BANDIT", "false")
    monkeypatch.setenv("CRYPTOAUDIT_ENABLE_SEMGREP", "false")


def test_analyze_still_works():
    result = runner.invoke(app, ["analyze", str(CR5), "--json"])
    assert result.exit_code == 0
    assert json.loads(result.output)["findings"][0]["rule_id"] == "CR5"


def test_repair_json_reports_unverified_without_oracle():
    result = runner.invoke(app, ["repair", str(CR5), "-s", "S2", "--sandbox", "local", "--unsafe-local-sandbox", "--json"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    outcome = data["results"][0]["outcome"]
    assert outcome["strategy_id"] == "S2" and outcome["verdict"] == "UNVERIFIED"
    assert "secrets.choice" in data["results"][0]["candidate_code"]


def test_repair_console_shows_assessment():
    result = runner.invoke(app, ["repair", str(CR5), "-s", "S2", "--sandbox", "local", "--unsafe-local-sandbox"])
    assert result.exit_code == 0, result.output
    assert "Overall assessment: Unverified" in result.output
    assert "V2" in result.output


def test_repair_with_user_checks(tmp_path):
    checks = tmp_path / "checks.py"
    checks.write_text("def check_length(ctx):\n    assert len(ctx.load_candidate().generate_session_token()) == 32\n", encoding="utf-8")
    result = runner.invoke(
        app, ["repair", str(CR5), "-s", "S2", "--checks", str(checks), "--sandbox", "local", "--unsafe-local-sandbox", "--json"]
    )
    gates = json.loads(result.output)["results"][0]["outcome"]["gates"]
    assert gates["V1"] == "PASS" and gates["V2"] == "NOT_RUN"


def test_local_sandbox_requires_explicit_flag():
    result = runner.invoke(app, ["repair", str(CR5), "-s", "S2", "--sandbox", "local"])
    assert result.exit_code == 1
    assert "SANDBOX_ERROR" in result.output


def test_unknown_strategy_is_rejected():
    result = runner.invoke(app, ["repair", str(CR5), "-s", "S9", "--sandbox", "local", "--unsafe-local-sandbox"])
    assert result.exit_code == 1 and "INVALID_INPUT" in result.output


def test_bench_list():
    result = runner.invoke(app, ["bench", "list"])
    assert result.exit_code == 0
    assert "cr1_password_md5" in result.output and "CR5" in result.output


def test_bench_run_and_report(tmp_path):
    db = tmp_path / "exp.sqlite"
    run = runner.invoke(
        app, ["bench", "run", "-s", "S2", "-c", "cr5_session_token", "--db", str(db), "--sandbox", "local", "--unsafe-local-sandbox"]
    )
    assert run.exit_code == 0, run.output
    assert "S2=VERIFIED" in run.output

    report_path = tmp_path / "report.md"
    report = runner.invoke(app, ["bench", "report", "--db", str(db), "--markdown", str(report_path)])
    assert report.exit_code == 0, report.output
    assert "Strategy comparison" in report_path.read_text(encoding="utf-8")

    as_json = runner.invoke(app, ["bench", "report", "--db", str(db), "--json"])
    assert json.loads(as_json.output)["verified_by_strategy"]["S2"]["successes"] == 1


def test_bench_report_without_runs(tmp_path):
    result = runner.invoke(app, ["bench", "report", "--db", str(tmp_path / "empty.sqlite")])
    assert result.exit_code == 1
