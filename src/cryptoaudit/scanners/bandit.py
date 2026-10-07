"""Bandit baseline scanner wrapper."""

import json
from typing import Optional

from cryptoaudit.scanners.models import ScannerIssue, ScanReport
from cryptoaudit.scanners.runner import TemporarySource, ToolError, resolve_executable, run_tool


class BanditScanner:
    name = "bandit"

    def __init__(self, executable: str = "bandit", timeout: float = 120.0) -> None:
        self.executable = executable
        self.timeout = timeout
        self._version: Optional[str] = None

    def version(self, exe: str) -> Optional[str]:
        if self._version is None:
            try:
                run = run_tool([exe, "--version"], self.timeout)
                self._version = (run.stdout.strip().splitlines() or [""])[0] or None
            except ToolError:
                self._version = None
        return self._version

    def scan_source(self, source: str, filename: str = "module.py") -> ScanReport:
        exe = resolve_executable(self.executable)
        if exe is None:
            return ScanReport(tool=self.name, available=False, error=f"'{self.executable}' not found on PATH")
        with TemporarySource(source, filename) as tmp:
            try:
                run = run_tool([exe, "-f", "json", "-q", str(tmp.path)], self.timeout)
            except ToolError as exc:
                return ScanReport(tool=self.name, available=False, error=str(exc))
        return parse_bandit_json(run.stdout, self.version(exe), stderr=run.stderr)


def parse_bandit_json(stdout: str, version: Optional[str] = None, stderr: str = "") -> ScanReport:
    try:
        data = json.loads(stdout)
    except json.JSONDecodeError:
        return ScanReport(tool="bandit", available=False, tool_version=version, error=f"Unparseable output: {stderr[:300]}")
    errors = data.get("errors") or []
    if errors:
        return ScanReport(tool="bandit", available=False, tool_version=version, error=str(errors[0])[:300])
    issues = [
        ScannerIssue(
            tool="bandit",
            rule_id=item.get("test_id", ""),
            line=int(item.get("line_number", 0)),
            end_line=(item.get("line_range") or [None])[-1],
            message=item.get("issue_text", ""),
            severity=item.get("issue_severity"),
        )
        for item in data.get("results", [])
    ]
    return ScanReport(tool="bandit", available=True, tool_version=version, issues=issues)
