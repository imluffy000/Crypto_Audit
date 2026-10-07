"""Regression tests: rule loading must not depend on the working directory or fail silently."""

from pathlib import Path

import pytest
import yaml

from cryptoaudit.analysis.analyzer import AnalyzerEngine
from cryptoaudit.rules.registry import REPO_RULES_FILE, load_default_rules
from cryptoaudit.utils.errors import CryptoAuditError, ErrorCode

MULTI_FIXTURE = Path("tests/fixtures/multi_rule/vulnerable.py").resolve()


def test_engine_loads_all_rules_from_foreign_working_directory(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    engine = AnalyzerEngine()
    assert sorted(rule.rule_id for rule in engine.rules) == ["CR1", "CR2", "CR3", "CR4", "CR5"]

    result = engine.analyze_file(MULTI_FIXTURE)
    assert {"CR1", "CR2", "CR3", "CR4", "CR5"}.issubset({f.rule_id for f in result.findings})


def test_missing_rules_file_raises_instead_of_loading_zero_rules(tmp_path):
    with pytest.raises(CryptoAuditError) as excinfo:
        load_default_rules(tmp_path / "does-not-exist.yaml")
    assert excinfo.value.code is ErrorCode.ANALYSIS_ERROR


def test_partial_rules_file_raises(tmp_path):
    rules = yaml.safe_load(REPO_RULES_FILE.read_text(encoding="utf-8"))["rules"]
    partial = tmp_path / "rules.yaml"
    partial.write_text(yaml.safe_dump({"rules": rules[:1]}), encoding="utf-8")
    with pytest.raises(CryptoAuditError) as excinfo:
        load_default_rules(partial)
    assert "CR2" in excinfo.value.details["missing"]


def test_malformed_rules_file_raises(tmp_path):
    bad = tmp_path / "rules.yaml"
    bad.write_text("- just a list\n", encoding="utf-8")
    with pytest.raises(CryptoAuditError):
        load_default_rules(bad)


def test_explicit_rule_list_is_still_respected():
    assert AnalyzerEngine(rules=[]).rules == []
