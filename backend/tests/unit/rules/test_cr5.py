"""Unit tests for CR5 rule (Weak randomness for security tokens)."""

from pathlib import Path

from cryptoaudit.analysis.analyzer import AnalyzerEngine
from cryptoaudit.models.enums import Category, Severity


def test_cr5_vulnerable_token_randomness_detection():
    """Test CR5: Insecure random PRNG calls in token/secret contexts are detected."""
    engine = AnalyzerEngine()
    vulnerable_fixture = Path("tests/fixtures/cr5/vulnerable.py")

    result = engine.analyze_file(vulnerable_fixture)
    cr5_findings = [f for f in result.findings if f.rule_id == "CR5"]
    assert len(cr5_findings) == 2

    for finding in cr5_findings:
        assert finding.category == Category.WEAK_RANDOMNESS_SECURITY_TOKENS
        assert finding.severity == Severity.HIGH
        assert finding.line in (8, 15)


def test_cr5_secure_fixture_no_findings():
    """Test CR5: Non-security random usage (dice roll, colors) and secrets module produce zero CR5 findings."""
    engine = AnalyzerEngine()
    secure_fixture = Path("tests/fixtures/cr5/secure.py")

    result = engine.analyze_file(secure_fixture)
    cr5_findings = [f for f in result.findings if f.rule_id == "CR5"]
    assert len(cr5_findings) == 0
