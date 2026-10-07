"""Unit tests for stable finding identity."""

from cryptoaudit.models.enums import Category, Severity
from cryptoaudit.models.finding import Finding, finding_id


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


