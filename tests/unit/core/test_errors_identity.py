"""Unit tests for structured errors and stable finding identity."""

from cryptoaudit.core.enums import Category, Severity
from cryptoaudit.core.errors import CryptoAuditError, ErrorCode
from cryptoaudit.core.identity import finding_id, stable_hash
from cryptoaudit.core.models import Finding


def _finding(**overrides) -> Finding:
    data = dict(
        rule_id="CR4",
        category=Category.WEAK_KDF_PARAMETERS_OR_STATIC_SALT,
        severity=Severity.HIGH,
        file="pkg/mod.py",
        line=10,
        column=4,
        matched_api="hashlib.pbkdf2_hmac",
        evidence="x = 1",
        explanation="Static hardcoded salt detected.",
        remediation="Use a random salt.",
    )
    data.update(overrides)
    return Finding(**data)


def test_error_carries_code_and_details():
    err = CryptoAuditError(ErrorCode.PARSE_ERROR, "bad syntax", {"line": 3})
    assert err.code is ErrorCode.PARSE_ERROR
    assert "PARSE_ERROR" in str(err)
    assert err.to_dict() == {"code": "PARSE_ERROR", "message": "bad syntax", "details": {"line": 3}}


def test_finding_id_is_deterministic():
    assert finding_id(_finding()) == finding_id(_finding())


def test_finding_id_distinguishes_same_line_findings():
    salt = _finding(explanation="Static hardcoded salt detected.")
    iters = _finding(explanation="Weak PBKDF2 iteration count (1,000) detected.")
    assert finding_id(salt) != finding_id(iters)


def test_finding_id_is_path_separator_independent():
    assert finding_id(_finding(file="pkg\\mod.py")) == finding_id(_finding(file="pkg/mod.py"))


def test_finding_id_ignores_non_key_fields():
    assert finding_id(_finding(evidence="other")) == finding_id(_finding())


def test_stable_hash_is_order_independent_for_dicts():
    assert stable_hash({"a": 1, "b": 2}) == stable_hash({"b": 2, "a": 1})
