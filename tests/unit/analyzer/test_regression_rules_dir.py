"""Regression tests: rule loading must not depend on the working directory or fail silently."""

from pathlib import Path

import pytest

from cryptoaudit.analyzer.engine import REPO_RULES_DIR, AnalyzerEngine, load_default_rules
from cryptoaudit.core.errors import CryptoAuditError, ErrorCode

MULTI_FIXTURE = Path("tests/fixtures/multi_rule/vulnerable.py").resolve()


def test_engine_loads_all_rules_from_foreign_working_directory(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    engine = AnalyzerEngine()
    assert sorted(rule.rule_id for rule in engine.rules) == ["CR1", "CR2", "CR3", "CR4", "CR5"]

    result = engine.analyze_file(MULTI_FIXTURE)
    assert {"CR1", "CR2", "CR3", "CR4", "CR5"}.issubset({f.rule_id for f in result.findings})


def test_missing_rules_directory_raises_instead_of_loading_zero_rules(tmp_path):
    with pytest.raises(CryptoAuditError) as excinfo:
        load_default_rules(tmp_path / "does-not-exist")
    assert excinfo.value.code is ErrorCode.ANALYSIS_ERROR


def test_partial_rules_directory_raises(tmp_path):
    (tmp_path / "cr1.yaml").write_text((REPO_RULES_DIR / "cr1.yaml").read_text(encoding="utf-8"), encoding="utf-8")
    with pytest.raises(CryptoAuditError) as excinfo:
        load_default_rules(tmp_path)
    assert "cr2.yaml" in excinfo.value.details["missing"]


def test_explicit_rule_list_is_still_respected():
    assert AnalyzerEngine(rules=[]).rules == []
