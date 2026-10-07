"""Semgrep baseline scanner wrapper."""

import json
from typing import Optional

from cryptoaudit.models.scan import ScannerIssue, ScanReport
from cryptoaudit.validation.scanners.process import TemporarySource, ToolError, resolve_executable, run_tool

DEFAULT_SEMGREP_CONFIG = "p/python"


class SemgrepScanner:
    name = "semgrep"

    def __init__(self, config: str = DEFAULT_SEMGREP_CONFIG, executable: str = "semgrep", timeout: float = 300.0) -> None:
        self.config = config
        self.executable = executable
        self.timeout = timeout

    def scan_source(self, source: str, filename: str = "module.py") -> ScanReport:
        exe = resolve_executable(self.executable)
        if exe is None:
            return ScanReport(
                tool=self.name, available=False, config=self.config, error=f"'{self.executable}' not found on PATH"
            )
        with TemporarySource(source, filename) as tmp:
            command = [
                exe, "scan", "--config", self.config, "--json", "--metrics=off",
                "--disable-version-check", "-q", tmp.path.name,
            ]
            try:
                run = run_tool(command, self.timeout, cwd=tmp.path.parent)
            except ToolError as exc:
                return ScanReport(tool=self.name, available=False, config=self.config, error=str(exc))
        return parse_semgrep_json(run.stdout, self.config, stderr=run.stderr)


def parse_semgrep_json(stdout: str, config: Optional[str] = None, stderr: str = "") -> ScanReport:
    try:
        data = json.loads(stdout)
    except json.JSONDecodeError:
        return ScanReport(tool="semgrep", available=False, config=config, error=f"Unparseable output: {stderr[:300]}")
    errors = [e for e in data.get("errors") or [] if e.get("level", "error") == "error"]
    if errors:
        message = errors[0].get("message", str(errors[0]))
        return ScanReport(tool="semgrep", available=False, config=config, tool_version=data.get("version"), error=message[:300])
    issues = []
    for item in data.get("results", []):
        start, end, extra = item.get("start", {}), item.get("end", {}), item.get("extra", {})
        issues.append(
            ScannerIssue(
                tool="semgrep",
                rule_id=item.get("check_id", ""),
                line=int(start.get("line", 0)),
                end_line=end.get("line"),
                message=extra.get("message", ""),
                severity=extra.get("severity"),
                fix=extra.get("fix"),
                start_offset=start.get("offset"),
                end_offset=end.get("offset"),
            )
        )
    return ScanReport(tool="semgrep", available=True, tool_version=data.get("version"), config=config, issues=issues)
