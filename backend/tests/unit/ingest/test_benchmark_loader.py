"""Benchmark repository tests: public/hidden separation and case integrity."""

import ast
from pathlib import Path

import pytest

from cryptoaudit.analysis.analyzer import AnalyzerEngine
from cryptoaudit.ingest.benchmark_loader import BenchmarkRepository
from cryptoaudit.utils.errors import CryptoAuditError
from cryptoaudit.validation.oracle import load_oracle

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
        repo.public_case("../cases/cr1/cr1_password_md5")
    with pytest.raises(CryptoAuditError):
        repo.public_case("does_not_exist")


def _write_case(root, rule="cr5", case_id="c1", rule_id="CR5", extra=""):
    case = root / "cases" / rule / case_id
    case.mkdir(parents=True)
    (case / "case.yaml").write_text(f"case_id: {case_id}\nrule_id: {rule_id}\ntitle: t\n{extra}", encoding="utf-8")
    (case / "module.py").write_text("x = 1\n", encoding="utf-8")
    return case


def test_public_case_never_reads_expected_or_artifacts(tmp_path):
    _write_case(tmp_path)
    for role in ("expected", "artifacts"):
        hidden = tmp_path / role / "cr5" / "c1"
        hidden.mkdir(parents=True)
        (hidden / "hidden_check.py").write_text("HIDDEN_MARKER = 1\n", encoding="utf-8")
    loaded = BenchmarkRepository(tmp_path).public_case("c1")
    assert "HIDDEN_MARKER" not in loaded.model_dump_json()


def test_module_file_cannot_escape_case_dir(tmp_path):
    _write_case(tmp_path, extra="module_file: ../../../expected/cr5/c1/v1_functional.py\n")
    with pytest.raises(CryptoAuditError):
        BenchmarkRepository(tmp_path).public_case("c1")


def test_case_must_be_filed_under_its_rule(tmp_path):
    _write_case(tmp_path, rule="cr1", rule_id="CR5")
    with pytest.raises(CryptoAuditError, match="filed under cr1"):
        BenchmarkRepository(tmp_path).public_case("c1")


def test_layout_mirrors_rule_groups(repo):
    root = repo.root
    for case_id in EXPECTED_CASES:
        rule = repo.rule_group(case_id)
        assert rule == case_id.split("_")[0]
        assert (root / "expected" / rule / case_id / "oracle.yaml").is_file()


# Packages on the generation/public side: none may import validation (which owns hidden oracles).
FORBIDDEN_IMPORTERS = ["repair", "context", "llm", "ingest", "analysis", "rules"]


@pytest.mark.parametrize("package", FORBIDDEN_IMPORTERS)
def test_generation_side_never_imports_hidden_oracle(package):
    """Import boundary: code that builds candidates must not be able to reach hidden oracles."""
    files = list((SRC / package).rglob("*.py"))
    assert files, f"package {package} not found"
    for path in files:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            names = []
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""]
            for name in names:
                assert "validation.oracle" not in name, f"{path} imports the hidden oracle loader"
                assert "validation" not in name.split("."), f"{path} imports validation internals"
