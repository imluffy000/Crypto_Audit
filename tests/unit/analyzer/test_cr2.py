"""Unit tests for CR2 rule (Weak/unauthenticated ECB encryption mode)."""

from pathlib import Path
from cryptoaudit.analyzer.engine import AnalyzerEngine
from cryptoaudit.core.enums import Category, Severity


def test_cr2_vulnerable_ecb_detection():
    """Test CR2: PyCryptodome and cryptography ECB mode calls are detected with accurate lines."""
    engine = AnalyzerEngine()
    vulnerable_fixture = Path("tests/fixtures/cr2/vulnerable.py")

    result = engine.analyze_file(vulnerable_fixture)
    cr2_findings = [f for f in result.findings if f.rule_id == "CR2"]
    assert len(cr2_findings) == 2

    for finding in cr2_findings:
        assert finding.category == Category.WEAK_OR_UNAUTHENTICATED_ENCRYPTION
        assert finding.severity == Severity.HIGH
        assert "MODE_ECB" in finding.matched_api or "modes.ECB" in finding.matched_api
        assert finding.line in (9, 15)


def test_cr2_secure_fixture_no_findings():
    """Test CR2: Authenticated AES-GCM encryption produces zero CR2 findings."""
    engine = AnalyzerEngine()
    secure_fixture = Path("tests/fixtures/cr2/secure.py")

    result = engine.analyze_file(secure_fixture)
    cr2_findings = [f for f in result.findings if f.rule_id == "CR2"]
    assert len(cr2_findings) == 0
