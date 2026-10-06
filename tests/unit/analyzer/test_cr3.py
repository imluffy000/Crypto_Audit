"""Unit tests for CR3 rule (Static or reused IV / Nonce)."""

from pathlib import Path
from cryptoaudit.analyzer.engine import AnalyzerEngine
from cryptoaudit.core.enums import Category, Severity


def test_cr3_vulnerable_static_iv_detection():
    """Test CR3: Hardcoded static IV literals and static variable IVs are detected conservatively."""
    engine = AnalyzerEngine()
    vulnerable_fixture = Path("tests/fixtures/cr3/vulnerable.py")

    result = engine.analyze_file(vulnerable_fixture)
    cr3_findings = [f for f in result.findings if f.rule_id == "CR3"]
    assert len(cr3_findings) == 2

    for finding in cr3_findings:
        assert finding.category == Category.STATIC_OR_REUSED_IV_NONCE
        assert finding.severity == Severity.HIGH
        assert "Static/constant" in finding.explanation
        assert finding.line in (11, 17)


def test_cr3_secure_fixture_no_findings():
    """Test CR3: Dynamically generated IVs (os.urandom / secrets) produce zero CR3 findings."""
    engine = AnalyzerEngine()
    secure_fixture = Path("tests/fixtures/cr3/secure.py")

    result = engine.analyze_file(secure_fixture)
    cr3_findings = [f for f in result.findings if f.rule_id == "CR3"]
    assert len(cr3_findings) == 0
