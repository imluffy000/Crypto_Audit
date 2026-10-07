"""Regression test suite for Issue 1: Correct positional PBKDF2HMAC argument parsing."""

from pathlib import Path

from cryptoaudit.analysis.analyzer import AnalyzerEngine


def test_cr4_vulnerable_positional_pbkdf2hmac(tmp_path: Path):
    """
    Test 1.A:
    PBKDF2HMAC(hashes.SHA256(), 32, b"static_salt", 1000)
    args[0] = algorithm (hashes.SHA256())
    args[1] = length (32)
    args[2] = salt (b"static_salt")
    args[3] = iterations (1000)
    Expects: 1 static salt finding and 1 low iteration count finding.
    """
    source_file = tmp_path / "vulnerable_positional.py"
    source_file.write_text(
        """
import os
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

def derive_key(password: bytes) -> bytes:
    kdf = PBKDF2HMAC(hashes.SHA256(), 32, b"static_salt", 1000)
    return kdf.derive(password)
""",
        encoding="utf-8",
    )

    engine = AnalyzerEngine()
    result = engine.analyze_file(source_file)
    cr4_findings = [f for f in result.findings if f.rule_id == "CR4"]

    assert len(cr4_findings) == 2
    explanations = [f.explanation for f in cr4_findings]
    assert any("Static hardcoded salt" in exp for exp in explanations)
    assert any("Weak PBKDF2 iteration count (1,000)" in exp for exp in explanations)


def test_cr4_secure_positional_pbkdf2hmac(tmp_path: Path):
    """
    Test 1.B:
    PBKDF2HMAC(hashes.SHA256(), 32, os.urandom(16), 600000)
    Secure positional call using dynamic salt and policy-compliant iterations (600,000).
    Expects: 0 findings (no false-positive finding).
    """
    source_file = tmp_path / "secure_positional.py"
    source_file.write_text(
        """
import os
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

def derive_key_secure(password: bytes) -> bytes:
    salt = os.urandom(16)
    kdf = PBKDF2HMAC(hashes.SHA256(), 32, salt, 600000)
    return kdf.derive(password)
""",
        encoding="utf-8",
    )

    engine = AnalyzerEngine()
    result = engine.analyze_file(source_file)
    cr4_findings = [f for f in result.findings if f.rule_id == "CR4"]

    assert len(cr4_findings) == 0


def test_cr4_keyword_arguments_pbkdf2hmac(tmp_path: Path):
    """Verify keyword argument PBKDF2HMAC handling continues to work."""
    source_file = tmp_path / "keyword_pbkdf2.py"
    source_file.write_text(
        """
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

def derive_key_kw(password: bytes) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=b"kw_static_salt",
        iterations=5000,
    )
    return kdf.derive(password)
""",
        encoding="utf-8",
    )

    engine = AnalyzerEngine()
    result = engine.analyze_file(source_file)
    cr4_findings = [f for f in result.findings if f.rule_id == "CR4"]

    assert len(cr4_findings) == 2
