"""Unit tests for call site extractor module."""

import ast
from cryptoaudit.analyzer.calls import extract_calls
from cryptoaudit.analyzer.imports import extract_imports


def test_call_extraction_and_scope():
    """Test 3: Function calls are detected with accurate line numbers and scope context."""
    code = """
import hashlib as hl

def hash_pass(password: str):
    res = hl.md5(password.encode())
    return res
"""
    tree = ast.parse(code)
    tracker = extract_imports(tree)
    calls = extract_calls(tree, tracker)

    assert len(calls) == 1
    call = calls[0]
    assert call.resolved_name == "hashlib.md5"
    assert call.lineno == 5
    assert call.enclosing_function == "hash_pass"
    assert call.assigned_variable == "res"
