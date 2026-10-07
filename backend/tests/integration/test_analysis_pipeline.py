"""Unit tests for multi-rule engine analysis, deduplication, determinism, and safe reference cases."""

from pathlib import Path

from cryptoaudit.analysis.analyzer import AnalyzerEngine


def test_multi_rule_analysis_and_deduplication():
    """Test multi-rule analysis detects CR1-CR5 in a single file without duplicates."""
    engine = AnalyzerEngine()
    multi_fixture = Path("tests/fixtures/multi_rule/vulnerable.py")

    result = engine.analyze_file(multi_fixture)
    rule_ids = {f.rule_id for f in result.findings}

    assert {"CR1", "CR2", "CR3", "CR4", "CR5"}.issubset(rule_ids)

    # Test deduplication: all (file, line, column, rule_id, matched_api, explanation) tuples should be unique
    seen = set()
    for f in result.findings:
        key = (f.file, f.line, f.column, f.rule_id, f.matched_api, f.explanation)
        assert key not in seen, f"Duplicate finding found for key: {key}"
        seen.add(key)


def test_multi_rule_determinism():
    """Test engine determinism: multiple runs on multi-rule fixture produce identical outputs."""
    engine = AnalyzerEngine()
    multi_fixture = Path("tests/fixtures/multi_rule/vulnerable.py")

    run1 = engine.analyze_file(multi_fixture)
    run2 = engine.analyze_file(multi_fixture)

    assert run1.model_dump_json() == run2.model_dump_json()


def test_all_secure_fixtures_produce_zero_findings():
    """Test all secure reference fixtures produce zero findings across CR1-CR5."""
    engine = AnalyzerEngine()
    secure_fixtures = [
        Path("tests/fixtures/cr1/secure.py"),
        Path("tests/fixtures/cr2/secure.py"),
        Path("tests/fixtures/cr3/secure.py"),
        Path("tests/fixtures/cr4/secure.py"),
        Path("tests/fixtures/cr5/secure.py"),
    ]

    for fixture in secure_fixtures:
        result = engine.analyze_file(fixture)
        assert result.total_findings == 0, f"Secure fixture {fixture} produced unexpected findings: {result.findings}"
