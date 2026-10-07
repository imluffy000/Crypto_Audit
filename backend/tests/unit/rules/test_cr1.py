"""Unit tests for CR1 rule, fixtures, false positives, precision, and determinism."""

from pathlib import Path

from cryptoaudit.analysis.analyzer import AnalyzerEngine
from cryptoaudit.models.enums import Category, Severity


def test_cr1_vulnerable_fixture_detection():
    """
    Test 4, 5 & 7:
    - Direct hashlib.md5 password hashing is detected (Test 4).
    - Direct hashlib.sha1 password hashing is detected (Test 5).
    - Finding contains correct line information (Test 7).
    """
    engine = AnalyzerEngine()
    vulnerable_fixture = Path("tests/fixtures/cr1/vulnerable.py")

    result = engine.analyze_file(vulnerable_fixture)
    assert result.total_findings == 2

    md5_finding = next(f for f in result.findings if f.matched_api == "hashlib.md5")
    assert md5_finding.rule_id == "CR1"
    assert md5_finding.category == Category.WEAK_HASH_CREDENTIALS
    assert md5_finding.severity == Severity.HIGH
    assert md5_finding.line == 9
    assert "password" in md5_finding.evidence.lower()

    sha1_finding = next(f for f in result.findings if f.matched_api == "hashlib.sha1")
    assert sha1_finding.rule_id == "CR1"
    assert sha1_finding.category == Category.WEAK_HASH_CREDENTIALS
    assert sha1_finding.severity == Severity.HIGH
    assert sha1_finding.line == 15
    assert "raw_password" in sha1_finding.evidence.lower() or "user_pass" in sha1_finding.evidence.lower()


def test_cr1_secure_fixture_no_findings():
    """
    Test 6 & 8:
    - Unrelated MD5 checksum use is not classified as credential hashing (Test 6).
    - Secure/reference fixture produces no CR1 finding (Test 8).
    """
    engine = AnalyzerEngine()
    secure_fixture = Path("tests/fixtures/cr1/secure.py")

    result = engine.analyze_file(secure_fixture)
    assert result.total_findings == 0
    assert len(result.findings) == 0


def test_cr1_determinism():
    """
    Test 9:
    Same source code produces deterministic results across multiple analysis runs.
    """
    engine = AnalyzerEngine()
    vulnerable_fixture = Path("tests/fixtures/cr1/vulnerable.py")

    run1 = engine.analyze_file(vulnerable_fixture)
    run2 = engine.analyze_file(vulnerable_fixture)

    assert run1.model_dump_json() == run2.model_dump_json()
