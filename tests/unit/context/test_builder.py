"""Unit tests for the Context Engine."""

import builtins
from pathlib import Path

import pytest

from cryptoaudit.analysis.analyzer import AnalyzerEngine
from cryptoaudit.context import ContextBudget, ContextBuilder
from cryptoaudit.models.finding import finding_id
from cryptoaudit.utils.errors import CryptoAuditError, ErrorCode

FIXTURE = Path("tests/fixtures/context/scopes.py")


@pytest.fixture(scope="module")
def analyzed():
    source = FIXTURE.read_text(encoding="utf-8")
    findings = AnalyzerEngine().analyze_file(FIXTURE).findings
    return source, findings


def _by_line(context, line):
    return next(fc for fc in context.findings if fc.line == line)


def test_locates_enclosing_method_by_position_not_name(analyzed):
    source, findings = analyzed
    context = ContextBuilder().build(source, findings, "scopes.py")
    alpha = _by_line(context, 13)
    assert alpha.enclosing_class == "Alpha"
    assert alpha.enclosing_function == "derive"
    assert "SALT" in alpha.function_source
    assert set(alpha.referenced_constants) == {"SALT", "ITERATIONS"}
    assert alpha.referenced_constants["SALT"] == 'SALT = b"static_salt_1234"'


def test_nested_function_is_innermost_scope(analyzed):
    source, findings = analyzed
    context = ContextBuilder().build(source, findings, "scopes.py")
    nested = _by_line(context, 23)
    assert nested.enclosing_function == "inner_hash_password"
    assert nested.enclosing_class is None
    assert nested.function_source.startswith("def inner_hash_password")


def test_module_level_finding_has_no_function(analyzed):
    source, findings = analyzed
    context = ContextBuilder().build(source, findings, "scopes.py")
    module_level = _by_line(context, 8)
    assert module_level.enclosing_function is None
    assert module_level.function_source is None


def test_public_interface_and_imports(analyzed):
    source, findings = analyzed
    context = ContextBuilder().build(source, findings, "scopes.py")
    names = [s.qualified_name for s in context.public_interface]
    assert names == ["Alpha", "Alpha.derive", "Beta", "Beta.derive", "outer"]
    assert "_private_helper" not in names
    assert context.imports == ["import hashlib", "import random"]


def test_callers_within_module():
    source = "def target():\n    return 1\n\ndef a():\n    return target()\n\ndef b():\n    return 2\n"
    import ast

    from cryptoaudit.context.builder import _callers_of

    assert _callers_of(ast.parse(source), "target") == ["a"]


def test_context_is_deterministic_and_hashed(analyzed):
    source, findings = analyzed
    first = ContextBuilder().build(source, findings, "scopes.py")
    second = ContextBuilder().build(source, list(reversed(findings)), "scopes.py")
    assert first.model_dump_json() == second.model_dump_json()
    assert len(first.context_hash) == 64


def test_finding_ids_match_core_identity(analyzed):
    source, findings = analyzed
    context = ContextBuilder().build(source, findings, "scopes.py")
    assert {fc.finding_id for fc in context.findings} == {finding_id(f) for f in findings}


def test_stale_finding_raises_context_error(analyzed):
    source, findings = analyzed
    edited = source.replace("ITERATIONS)", "ITERATIONS)  ", 1).replace('SALT, ITERATIONS', 'SALT,ITERATIONS')
    with pytest.raises(CryptoAuditError) as excinfo:
        ContextBuilder().build(edited, findings, "scopes.py")
    assert excinfo.value.code is ErrorCode.CONTEXT_ERROR


def test_syntax_error_raises_parse_error(analyzed):
    _, findings = analyzed
    with pytest.raises(CryptoAuditError) as excinfo:
        ContextBuilder().build("def broken(:\n", findings, "scopes.py")
    assert excinfo.value.code is ErrorCode.PARSE_ERROR


def test_function_line_budget_truncates_explicitly(analyzed):
    source, findings = analyzed
    context = ContextBuilder(ContextBudget(max_function_lines=1)).build(source, findings, "scopes.py")
    assert context.truncated is True
    assert "truncated" in _by_line(context, 13).function_source


def test_total_budget_bounds_context(analyzed):
    source, findings = analyzed
    context = ContextBuilder(ContextBudget(max_total_chars=40)).build(source, findings, "scopes.py")
    assert context.truncated is True
    total = sum(len(fc.function_source or "") for fc in context.findings)
    assert total <= 40 + 2 * len("\n    # ... [truncated by CryptoAudit context budget]")


def test_builder_never_opens_files(analyzed, monkeypatch):
    source, findings = analyzed

    def forbidden_open(*args, **kwargs):
        raise AssertionError(f"ContextBuilder must not open files: {args}")

    monkeypatch.setattr(builtins, "open", forbidden_open)
    monkeypatch.setattr(Path, "read_text", forbidden_open)
    context = ContextBuilder().build(source, findings, "scopes.py")
    assert context.module_name == "scopes.py"
