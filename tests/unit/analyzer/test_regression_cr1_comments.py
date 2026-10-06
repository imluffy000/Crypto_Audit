"""Regression test suite for Issue 2: Removing comment-based false positives in CR1."""

from pathlib import Path
from cryptoaudit.analyzer.engine import AnalyzerEngine


def test_cr1_comment_with_password_no_false_positive(tmp_path: Path):
    """
    Test 2.A:
    checksum = hashlib.md5(data).hexdigest()  # password handling elsewhere
    The word 'password' in inline comment MUST NOT trigger a CR1 finding.
    Expects: 0 CR1 findings.
    """
    source_file = tmp_path / "checksum_comment.py"
    source_file.write_text(
        """
import hashlib

def compute_checksum(data: bytes) -> str:
    checksum = hashlib.md5(data).hexdigest()  # password handling elsewhere
    return checksum
""",
        encoding="utf-8",
    )

    engine = AnalyzerEngine()
    result = engine.analyze_file(source_file)
    cr1_findings = [f for f in result.findings if f.rule_id == "CR1"]

    assert len(cr1_findings) == 0


def test_cr1_genuine_password_context(tmp_path: Path):
    """
    Test 2.B:
    Genuine password variable/function context.
    Expects: 1 CR1 finding.
    """
    source_file = tmp_path / "genuine_password.py"
    source_file.write_text(
        """
import hashlib

def hash_user_password(password: str) -> str:
    digest = hashlib.md5(password.encode()).hexdigest()
    return digest
""",
        encoding="utf-8",
    )

    engine = AnalyzerEngine()
    result = engine.analyze_file(source_file)
    cr1_findings = [f for f in result.findings if f.rule_id == "CR1"]

    assert len(cr1_findings) == 1
    assert cr1_findings[0].line == 5


def test_cr1_ordinary_file_checksum(tmp_path: Path):
    """
    Test 2.C:
    Ordinary file/checksum usage.
    Expects: 0 CR1 findings.
    """
    source_file = tmp_path / "file_checksum.py"
    source_file.write_text(
        """
import hashlib

def get_file_md5(file_bytes: bytes) -> str:
    file_checksum = hashlib.md5(file_bytes).hexdigest()
    return file_checksum
""",
        encoding="utf-8",
    )

    engine = AnalyzerEngine()
    result = engine.analyze_file(source_file)
    cr1_findings = [f for f in result.findings if f.rule_id == "CR1"]

    assert len(cr1_findings) == 0
