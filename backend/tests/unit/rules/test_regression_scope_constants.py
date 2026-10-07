"""Regression test suite for Issue 3: Scope-aware constant resolution in CR3/CR4."""

from pathlib import Path

from cryptoaudit.analysis.analyzer import AnalyzerEngine


def test_cr3_constant_in_unrelated_function_does_not_contaminate_parameter(tmp_path: Path):
    """
    Test 3.A:
    def function_a():
        iv = b"1234567890123456"

    def function_b(iv: bytes, key: bytes):
        cipher = AES.new(key, AES.MODE_CBC, iv=iv)

    The parameter 'iv' in function_b MUST NOT be classified as static merely because function_a contains 'iv = b"..."'.
    Expects: 0 CR3 findings in function_b.
    """
    source_file = tmp_path / "cross_function_contamination.py"
    source_file.write_text(
        """
from Crypto.Cipher import AES

def function_a():
    iv = b"1234567890123456"
    return iv

def function_b(iv: bytes, key: bytes):
    cipher = AES.new(key, AES.MODE_CBC, iv=iv)
    return cipher
""",
        encoding="utf-8",
    )

    engine = AnalyzerEngine()
    result = engine.analyze_file(source_file)
    cr3_findings = [f for f in result.findings if f.rule_id == "CR3"]

    assert len(cr3_findings) == 0


def test_cr3_local_constant_resolved_correctly(tmp_path: Path):
    """
    Test 3.B:
    A local constant assigned in the current function is correctly resolved.
    Expects: 1 CR3 finding.
    """
    source_file = tmp_path / "local_constant.py"
    source_file.write_text(
        """
from Crypto.Cipher import AES

def function_c(key: bytes):
    iv = b"1234567890123456"
    cipher = AES.new(key, AES.MODE_CBC, iv=iv)
    return cipher
""",
        encoding="utf-8",
    )

    engine = AnalyzerEngine()
    result = engine.analyze_file(source_file)
    cr3_findings = [f for f in result.findings if f.rule_id == "CR3"]

    assert len(cr3_findings) == 1
    assert cr3_findings[0].line == 6


def test_cr3_module_level_constant_resolved_correctly(tmp_path: Path):
    """
    Test 3.C:
    A module-level constant is correctly resolved where appropriate.
    Expects: 1 CR3 finding.
    """
    source_file = tmp_path / "module_constant.py"
    source_file.write_text(
        """
from Crypto.Cipher import AES

GLOBAL_STATIC_IV = b"1234567890123456"

def function_d(key: bytes):
    cipher = AES.new(key, AES.MODE_CBC, iv=GLOBAL_STATIC_IV)
    return cipher
""",
        encoding="utf-8",
    )

    engine = AnalyzerEngine()
    result = engine.analyze_file(source_file)
    cr3_findings = [f for f in result.findings if f.rule_id == "CR3"]

    assert len(cr3_findings) == 1
    assert cr3_findings[0].line == 7


def test_cr3_dynamic_urandom_iv_remains_non_static(tmp_path: Path):
    """
    Test 3.D:
    A dynamically generated IV (os.urandom(16)) remains non-static.
    Expects: 0 CR3 findings.
    """
    source_file = tmp_path / "dynamic_iv.py"
    source_file.write_text(
        """
import os
from Crypto.Cipher import AES

def function_e(key: bytes):
    iv = os.urandom(16)
    cipher = AES.new(key, AES.MODE_CBC, iv=iv)
    return cipher
""",
        encoding="utf-8",
    )

    engine = AnalyzerEngine()
    result = engine.analyze_file(source_file)
    cr3_findings = [f for f in result.findings if f.rule_id == "CR3"]

    assert len(cr3_findings) == 0


def test_cr4_cross_function_salt_scope_isolation(tmp_path: Path):
    """
    Test 3.E:
    Same scope-isolation principle applied to static salt resolution in CR4.
    """
    source_file = tmp_path / "cross_func_salt.py"
    source_file.write_text(
        """
import hashlib

def dummy_func():
    salt = b"static_salt_in_other_func"

def real_kdf_func(salt: bytes, password: str):
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 600000)
""",
        encoding="utf-8",
    )

    engine = AnalyzerEngine()
    result = engine.analyze_file(source_file)
    cr4_findings = [f for f in result.findings if f.rule_id == "CR4"]

    assert len(cr4_findings) == 0
