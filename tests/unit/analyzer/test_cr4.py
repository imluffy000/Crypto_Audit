"""Unit tests for CR4 rule (Weak KDF parameters, static salt, fast hash direct key derivation)."""

from pathlib import Path
from cryptoaudit.analyzer.engine import AnalyzerEngine
from cryptoaudit.core.enums import Category, Severity


def test_cr4_vulnerable_kdf_detection():
    """Test CR4: Static salts, iteration counts under 600,000 threshold, and fast-hash key derivation are detected."""
    engine = AnalyzerEngine()
    vulnerable_fixture = Path("tests/fixtures/cr4/vulnerable.py")

    result = engine.analyze_file(vulnerable_fixture)
    cr4_findings = [f for f in result.findings if f.rule_id == "CR4"]
    assert len(cr4_findings) >= 3

    for finding in cr4_findings:
        assert finding.category == Category.WEAK_KDF_PARAMETERS_OR_STATIC_SALT
        assert finding.severity == Severity.HIGH

    # Verify static salt and iteration count findings
    explanations = [f.explanation for f in cr4_findings]
    assert any("Static hardcoded salt" in exp for exp in explanations)
    assert any("Weak PBKDF2 iteration count" in exp for exp in explanations)
    assert any("Direct fast hash key derivation" in exp for exp in explanations)


def test_cr4_secure_fixture_no_findings():
    """Test CR4: 600,000 iterations and os.urandom salt produce zero CR4 findings."""
    engine = AnalyzerEngine()
    secure_fixture = Path("tests/fixtures/cr4/secure.py")

    result = engine.analyze_file(secure_fixture)
    cr4_findings = [f for f in result.findings if f.rule_id == "CR4"]
    assert len(cr4_findings) == 0
