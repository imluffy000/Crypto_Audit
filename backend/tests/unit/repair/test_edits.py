"""Tests for position-based source editing."""

import ast

import pytest

from cryptoaudit.repair.edits import (
    OverlappingEditError,
    SourceIndex,
    TextEdit,
    apply_edits,
    ensure_import,
    find_call,
)


def test_source_index_handles_multibyte_characters():
    source = 's = "é"; x = f(1)\n'
    call = find_call(ast.parse(source), 1, None)
    assert SourceIndex(source).text(call) == "f(1)"


def test_apply_edits_in_any_order():
    source = "a = 1\nb = 2\n"
    edits = [TextEdit(4, 5, "10"), TextEdit(10, 11, "20")]
    assert apply_edits(source, reversed(edits)) == "a = 10\nb = 20\n"


def test_apply_edits_rejects_overlap():
    with pytest.raises(OverlappingEditError):
        apply_edits("abcdef", [TextEdit(0, 3, "x"), TextEdit(2, 4, "y")])


def test_identical_edits_are_collapsed():
    assert apply_edits("abc", [TextEdit(0, 1, "z"), TextEdit(0, 1, "z")]) == "zbc"


def test_ensure_import_after_docstring_and_imports():
    source = '"""Doc."""\nimport random\n\nx = 1\n'
    assert ensure_import(source, "secrets") == '"""Doc."""\nimport random\nimport secrets\n\nx = 1\n'


def test_ensure_import_is_idempotent():
    source = "import secrets\n"
    assert ensure_import(source, "secrets") == source


def test_ensure_import_preserves_crlf():
    source = "import random\r\nx = 1\r\n"
    assert ensure_import(source, "os") == "import random\r\nimport os\r\nx = 1\r\n"


def test_ensure_import_in_module_without_imports():
    assert ensure_import("x = 1", "os") == "import os\nx = 1\n"


def test_find_call_prefers_innermost_chained_call():
    source = "import hashlib\nx = hashlib.md5(b'a').hexdigest()\n"
    call = find_call(ast.parse(source), 2, 4)
    assert SourceIndex(source).text(call) == "hashlib.md5(b'a')"
