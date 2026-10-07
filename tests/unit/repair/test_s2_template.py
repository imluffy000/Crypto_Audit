"""S2 deterministic template strategy tests."""

import ast
from pathlib import Path

import pytest

from cryptoaudit.analysis.analyzer import AnalyzerEngine
from cryptoaudit.repair import RepairStatus, StrategyId, build_repair_request
from cryptoaudit.repair.strategies import TemplateRepairStrategy


def _repair_source(tmp_path: Path, source: str):
    module = tmp_path / "module.py"
    module.write_text(source, encoding="utf-8")
    findings = AnalyzerEngine().analyze_file(module).findings
    assert findings, "fixture must trigger the analyzer"
    request = build_repair_request("module.py", source, findings)
    return TemplateRepairStrategy().repair(request), findings


def _reanalyze(tmp_path: Path, code: str):
    out = tmp_path / "candidate.py"
    out.write_text(code, encoding="utf-8")
    return AnalyzerEngine().analyze_file(out).findings


def test_cr5_choice_becomes_secrets_choice(tmp_path):
    source = (
        "import random\n\n"
        "def generate_session_token(n=32):\n"
        "    return ''.join(random.choice('abc') for _ in range(n))  # keep comment\n"
    )
    result, _ = _repair_source(tmp_path, source)
    assert result.status is RepairStatus.PRODUCED
    assert result.strategy_id is StrategyId.S2
    assert "secrets.choice('abc')" in result.candidate_code
    assert "# keep comment" in result.candidate_code
    assert "import secrets" in result.candidate_code
    assert _reanalyze(tmp_path, result.candidate_code) == []


@pytest.mark.parametrize(
    "call, expected",
    [
        ("random.randint(100000, 999999)", "(secrets.randbelow((999999) - (100000) + 1) + (100000))"),
        ("random.randrange(10)", "secrets.randbelow(10)"),
        ("random.getrandbits(128)", "secrets.randbits(128)"),
        ("random.random()", "secrets.SystemRandom().random()"),
    ],
)
def test_cr5_call_shapes(tmp_path, call, expected):
    result, _ = _repair_source(tmp_path, f"import random\n\ndef make_token():\n    session_token = {call}\n    return session_token\n")
    assert result.status is RepairStatus.PRODUCED
    assert expected in result.candidate_code


def test_cr1_md5_hexdigest_becomes_pbkdf2(tmp_path):
    source = "import hashlib\n\ndef hash_password(password):\n    return hashlib.md5(password.encode()).hexdigest()\n"
    result, _ = _repair_source(tmp_path, source)
    assert result.status is RepairStatus.PRODUCED
    assert 'hashlib.pbkdf2_hmac("sha256", password.encode(), os.urandom(16), 600000).hex()' in result.candidate_code
    assert "import os" in result.candidate_code
    assert _reanalyze(tmp_path, result.candidate_code) == []


def test_cr1_unsupported_pattern_is_no_repair(tmp_path):
    source = "import hashlib\n\ndef hash_password(password):\n    h = hashlib.md5()\n    h.update(password)\n    return h\n"
    result, findings = _repair_source(tmp_path, source)
    assert result.status is RepairStatus.NO_REPAIR
    assert result.candidate_code is None
    assert len(result.unrepaired_finding_ids) == len(findings)


def test_cr2_has_no_template(tmp_path):
    source = Path("tests/fixtures/cr2/vulnerable.py").read_text(encoding="utf-8")
    result, _ = _repair_source(tmp_path, source)
    assert result.status is RepairStatus.NO_REPAIR
    assert "ECB" in " ".join(result.notes)


def test_cr3_static_iv_replaced_with_random(tmp_path):
    source = (
        "from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes\n"
        "IV = b'0123456789abcdef'\n\n"
        "def encrypt(key, data):\n"
        "    return Cipher(algorithms.AES(key), modes.CBC(IV)).encryptor().update(data)\n"
    )
    result, _ = _repair_source(tmp_path, source)
    assert result.status is RepairStatus.PRODUCED
    assert "modes.CBC(os.urandom(16))" in result.candidate_code


def test_cr4_salt_and_iterations_both_repaired(tmp_path):
    source = (
        "import hashlib\nSALT = b'static'\nITERATIONS = 1000\n\n"
        "def hash_password(password):\n"
        "    return hashlib.pbkdf2_hmac('sha256', password, SALT, ITERATIONS).hex()\n"
    )
    result, findings = _repair_source(tmp_path, source)
    assert len(findings) == 2
    assert result.status is RepairStatus.PRODUCED
    assert "hashlib.pbkdf2_hmac('sha256', password, os.urandom(16), 600000)" in result.candidate_code
    assert len(result.repaired_finding_ids) == 2
    assert _reanalyze(tmp_path, result.candidate_code) == []


def test_partial_repair_records_unrepaired_findings(tmp_path):
    source = (
        "import hashlib\nimport random\n\n"
        "def hash_password(password):\n    h = hashlib.md5()\n    return h\n\n"
        "def session_token():\n    return random.choice('ab')\n"
    )
    result, _ = _repair_source(tmp_path, source)
    assert result.status is RepairStatus.PRODUCED
    assert len(result.repaired_finding_ids) == 1
    assert len(result.unrepaired_finding_ids) == 1


def test_s2_is_deterministic(tmp_path):
    source = Path("tests/fixtures/multi_rule/vulnerable.py").read_text(encoding="utf-8")
    first, _ = _repair_source(tmp_path, source)
    second, _ = _repair_source(tmp_path, source)
    assert first.candidate_code == second.candidate_code
    ast.parse(first.candidate_code)
