"""S1 tool-guided strategy tests using deterministic fake scanners."""

import shutil
from typing import List

import pytest

from cryptoaudit.analysis.analyzer import AnalyzerEngine
from cryptoaudit.models.repair import RepairStatus, StrategyId
from cryptoaudit.models.scan import ScannerIssue, ScanReport
from cryptoaudit.repair import build_repair_request
from cryptoaudit.repair.strategies import ToolGuidedRepairStrategy
from cryptoaudit.scanners import BanditScanner
from cryptoaudit.utils.errors import ErrorCode

MD5_SOURCE = "import hashlib\n\ndef hash_password(password):\n    return hashlib.md5(password.encode()).hexdigest()\n"


class FakeScanner:
    def __init__(self, name: str, issues: List[ScannerIssue], available: bool = True) -> None:
        self.name = name
        self.report = ScanReport(tool=name, available=available, issues=issues, error=None if available else "missing")

    def scan_source(self, source, filename="module.py"):
        return self.report


def _request(tmp_path, source):
    module = tmp_path / "module.py"
    module.write_text(source, encoding="utf-8")
    return build_repair_request("module.py", source, AnalyzerEngine().analyze_file(module).findings)


def test_bandit_b324_hint_applies_usedforsecurity(tmp_path):
    scanner = FakeScanner("bandit", [ScannerIssue(tool="bandit", rule_id="B324", line=4)])
    result = ToolGuidedRepairStrategy([scanner]).repair(_request(tmp_path, MD5_SOURCE))
    assert result.status is RepairStatus.PRODUCED
    assert result.strategy_id is StrategyId.S1
    assert "hashlib.md5(password.encode(), usedforsecurity=False).hexdigest()" in result.candidate_code


def test_hint_on_unrelated_line_is_ignored(tmp_path):
    scanner = FakeScanner("bandit", [ScannerIssue(tool="bandit", rule_id="B324", line=1)])
    result = ToolGuidedRepairStrategy([scanner]).repair(_request(tmp_path, MD5_SOURCE))
    assert result.status is RepairStatus.NOT_APPLICABLE
    assert result.candidate_code is None


def test_non_actionable_hint_is_not_applicable(tmp_path):
    source = "import random\n\ndef session_token():\n    return random.choice('ab')\n"
    scanner = FakeScanner("bandit", [ScannerIssue(tool="bandit", rule_id="B311", line=4)])
    result = ToolGuidedRepairStrategy([scanner]).repair(_request(tmp_path, source))
    assert result.status is RepairStatus.NOT_APPLICABLE
    assert result.unrepaired_finding_ids


def test_semgrep_fix_is_applied_by_offsets(tmp_path):
    start = MD5_SOURCE.index("hashlib.md5")
    issue = ScannerIssue(
        tool="semgrep", rule_id="md5", line=4, fix="hashlib.sha256", start_offset=start, end_offset=start + len("hashlib.md5")
    )
    result = ToolGuidedRepairStrategy([FakeScanner("semgrep", [issue])]).repair(_request(tmp_path, MD5_SOURCE))
    assert result.status is RepairStatus.PRODUCED
    assert "hashlib.sha256(password.encode())" in result.candidate_code


def test_all_scanners_unavailable_is_no_repair(tmp_path):
    result = ToolGuidedRepairStrategy([FakeScanner("bandit", [], available=False)]).repair(_request(tmp_path, MD5_SOURCE))
    assert result.status is RepairStatus.NO_REPAIR
    assert result.error_code is ErrorCode.TOOL_UNAVAILABLE


def test_s1_is_deterministic(tmp_path):
    scanner = FakeScanner("bandit", [ScannerIssue(tool="bandit", rule_id="B324", line=4)])
    request = _request(tmp_path, MD5_SOURCE)
    assert ToolGuidedRepairStrategy([scanner]).repair(request).candidate_code == ToolGuidedRepairStrategy(
        [scanner]
    ).repair(request).candidate_code


@pytest.mark.skipif(shutil.which("bandit") is None, reason="bandit not installed")
def test_real_bandit_guidance(tmp_path):
    result = ToolGuidedRepairStrategy([BanditScanner()]).repair(_request(tmp_path, MD5_SOURCE))
    assert result.status is RepairStatus.PRODUCED
    assert "usedforsecurity=False" in result.candidate_code
