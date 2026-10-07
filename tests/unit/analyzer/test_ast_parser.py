"""Unit tests for AST parser module."""

import ast
from pathlib import Path

import pytest

from cryptoaudit.analysis.ast_parser import parse_source_file


def test_parse_valid_python_file(tmp_path: Path):
    """Test 1: Python file parses successfully into AST."""
    source_file = tmp_path / "sample.py"
    source_file.write_text("x = 1\ny = 2\n", encoding="utf-8")

    res = parse_source_file(source_file)
    assert res.file_path == str(source_file)
    assert isinstance(res.tree, ast.Module)
    assert res.get_line_content(1) == "x = 1"
    assert res.get_line_content(2) == "y = 2"


def test_parse_invalid_python_syntax(tmp_path: Path):
    """Test syntax error handling during AST parsing."""
    source_file = tmp_path / "invalid.py"
    source_file.write_text("def broken_func(:\n", encoding="utf-8")

    with pytest.raises(ValueError, match="Syntax error"):
        parse_source_file(source_file)
