"""Benchmark repository tests: public/hidden separation and case integrity."""

import ast
from pathlib import Path

import pytest

from cryptoaudit.analyzer.engine import AnalyzerEngine
from cryptoaudit.benchmark import BenchmarkRepository
from cryptoaudit.benchmark.oracle import load_oracle
from cryptoaudit.core.errors import CryptoAuditError

EXPECTED_CASES = ["cr1_password_md5", "cr2_ecb_records", "cr3_static_iv", "cr4_weak_kdf", "cr5_session_token"]
SRC = Path(__file__).resolve().parents[3] / "src" / "cryptoaudit"


@pytest.fixture(scope="module")
def repo():
    return BenchmarkRepository()


def test_all_cases_listed(repo):
    assert repo.case_ids() == EXPECTED_CASES


@pytest.mark.parametrize("case_id", EXPECTED_CASES)
def test_public_case_contains_no_hidden_data(repo, case_id):
    case = repo.public_case(case_id)
    dumped = case.model_dump_json()
    assert "CANARY" not in dumped
    assert "hidden" not in dumped.lower()


@pytest.mark.parametrize("case_id", EXPECTED_CASES)
def test_analyzer_detects_the_case_rule(repo, case_id):
    case = repo.public_case(case_id)
    findings = AnalyzerEngine().analyze_file(repo.public_module_path(case_id)).findings
    assert case.spec.rule_id in {f.rule_id for f in findings}


@pytest.mark.parametrize("case_id", EXPECTED_CASES)
def test_oracle_loads_with_canaries(repo, case_id):
    oracle = load_oracle(repo, case_id)
    assert {"V1", "V2"} <= set(oracle.checks)
    for path in oracle.checks.values():
        assert f"CANARY: cryptoaudit-hidden-oracle-{case_id}" in path.read_text(encoding="utf-8")


def test_v3_applicability_matches_architecture(repo):
    applicable = {cid: load_oracle(repo, cid).v3.applicable for cid in EXPECTED_CASES}
    assert applicable == {
        "cr1_password_md5": True,
        "cr2_ecb_records": True,
        "cr3_static_iv": True,
        "cr4_weak_kdf": True,
        "cr5_session_token": False,
    }


def test_path_traversal_is_rejected(repo):
    with pytest.raises(CryptoAuditError):
        repo.public_case("../cases/cr1_password_md5")
    with pytest.raises(CryptoAuditError):
        repo.public_case("does_not_exist")


def test_public_case_ignores_hidden_directory(tmp_path):
    case = tmp_path / "c1" / "public"
    case.mkdir(parents=True)
    (case / "case.yaml").write_text("case_id: c1\nrule_id: CR5\ntitle: t\n", encoding="utf-8")
    (case / "module.py").write_text("x = 1\n", encoding="utf-8")
    hidden = tmp_path / "c1" / "hidden"
    hidden.mkdir()
    (hidden / "secret.py").write_text("SECRET = 1\n", encoding="utf-8")
    loaded = BenchmarkRepository(tmp_path).public_case("c1")
    assert "SECRET" not in loaded.model_dump_json()


def test_module_file_cannot_escape_public_dir(tmp_path):
    case = tmp_path / "c1" / "public"
    case.mkdir(parents=True)
    (case / "case.yaml").write_text("case_id: c1\nrule_id: CR5\ntitle: t\nmodule_file: ../hidden/v1.py\n", encoding="utf-8")
    with pytest.raises(CryptoAuditError):
        BenchmarkRepository(tmp_path).public_case("c1")


FORBIDDEN_IMPORTERS = ["repair", "context", "llm", "scanners"]


@pytest.mark.parametrize("package", FORBIDDEN_IMPORTERS)
def test_generation_side_never_imports_hidden_oracle(package):
    """Import boundary: code that builds candidates must not be able to reach hidden oracles."""
    for path in (SRC / package).rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            names = []
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""]
            for name in names:
                assert "benchmark.oracle" not in name, f"{path} imports the hidden oracle loader"
                assert "validation" not in name.split("."), f"{path} imports validation internals"
