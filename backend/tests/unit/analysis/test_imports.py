"""Unit tests for import analyzer module."""

import ast

from cryptoaudit.analysis.import_analyzer import extract_imports


def test_import_detection_and_aliasing():
    """Test 2: Direct and aliased imports are correctly detected and resolved."""
    code = """
import hashlib
import hashlib as hl
from hashlib import md5
from hashlib import sha1 as custom_sha1
"""
    tree = ast.parse(code)
    tracker = extract_imports(tree)

    assert tracker.resolve_symbol("hashlib") == "hashlib"
    assert tracker.resolve_symbol("hl") == "hashlib"
    assert tracker.resolve_symbol("md5") == "hashlib.md5"
    assert tracker.resolve_symbol("custom_sha1") == "hashlib.sha1"
