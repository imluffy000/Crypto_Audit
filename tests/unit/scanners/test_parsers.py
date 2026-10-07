"""Parsing tests for Bandit/Semgrep JSON and scanner availability semantics."""

import json
import shutil

import pytest

from cryptoaudit.scanners import BanditScanner, SemgrepScanner, parse_bandit_json, parse_semgrep_json

BANDIT_OUTPUT = json.dumps(
    {
        "errors": [],
        "results": [
            {
                "test_id": "B324",
                "line_number": 5,
                "line_range": [5],
                "issue_text": "Use of weak MD5 hash for security. Consider usedforsecurity=False",
                "issue_severity": "HIGH",
            }
        ],
    }
)

SEMGREP_OUTPUT = json.dumps(
    {
        "version": "1.163.0",
        "errors": [],
        "results": [
            {
                "check_id": "python.lang.security.insecure-hash-algorithm-md5",
                "start": {"line": 5, "offset": 70},
                "end": {"line": 5, "offset": 81},
                "extra": {"message": "md5", "severity": "WARNING", "fix": "hashlib.sha256"},
            }
        ],
    }
)


def test_parse_bandit():
    report = parse_bandit_json(BANDIT_OUTPUT, "bandit 1.9.4")
    assert report.available and report.clean is False
    assert report.issues[0].rule_id == "B324" and report.issues[0].line == 5


def test_parse_semgrep_keeps_fix_and_offsets():
    report = parse_semgrep_json(SEMGREP_OUTPUT, "p/python")
    issue = report.issues[0]
    assert report.tool_version == "1.163.0"
    assert (issue.fix, issue.start_offset, issue.end_offset) == ("hashlib.sha256", 70, 81)


def test_unparseable_output_is_unavailable_not_clean():
    report = parse_bandit_json("not json")
    assert report.available is False
    assert report.clean is None


def test_tool_errors_are_unavailable():
    report = parse_semgrep_json(json.dumps({"errors": [{"level": "error", "message": "config not found"}], "results": []}))
    assert report.available is False and "config not found" in report.error


def test_missing_executable_is_unavailable():
    report = BanditScanner(executable="definitely-not-a-real-bandit").scan_source("x = 1\n")
    assert report.available is False and report.clean is None
    report = SemgrepScanner(executable="definitely-not-a-real-semgrep").scan_source("x = 1\n")
    assert report.available is False


@pytest.mark.skipif(shutil.which("bandit") is None, reason="bandit not installed")
def test_real_bandit_reports_md5():
    source = "import hashlib\n\ndef hash_password(password):\n    return hashlib.md5(password.encode()).hexdigest()\n"
    report = BanditScanner().scan_source(source)
    assert report.available
    assert any(issue.rule_id == "B324" and issue.line == 4 for issue in report.issues)
