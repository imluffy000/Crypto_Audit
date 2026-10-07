"""Context Engine: builds bounded, deterministic repair context from a module's AST."""

import ast
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple, Union

from cryptoaudit.context.interface import extract_public_interface
from cryptoaudit.models.context import CodeContext, FindingContext
from cryptoaudit.models.finding import Finding, finding_id
from cryptoaudit.utils.errors import CryptoAuditError, ErrorCode
from cryptoaudit.utils.hashing import stable_hash

ScopeNode = Union[ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef]
TRUNCATION_MARKER = "    # ... [truncated by CryptoAudit context budget]"


@dataclass(frozen=True)
class ContextBudget:
    """Upper bounds that keep context small and deterministic."""

    max_function_lines: int = 200
    max_total_chars: int = 20_000


class ContextBuilder:
    """
    Builds CodeContext from source text only.

    The builder never opens files: callers pass the module source, which keeps the
    information boundary explicit (no sibling files, no hidden artifacts).
    """

    def __init__(self, budget: Optional[ContextBudget] = None) -> None:
        self.budget = budget or ContextBudget()

    def build(self, source: str, findings: Sequence[Finding], module_name: str) -> CodeContext:
        try:
            tree = ast.parse(source)
        except SyntaxError as exc:
            raise CryptoAuditError(
                ErrorCode.PARSE_ERROR, f"Cannot build context: syntax error at line {exc.lineno}", {"line": exc.lineno}
            ) from exc

        lines = source.splitlines()
        module_constants = _module_constants(tree, source)
        scopes = _collect_scopes(tree)
        truncated = False
        finding_contexts: List[FindingContext] = []

        for finding in sorted(findings, key=lambda f: (f.line, f.column or 0, f.rule_id, f.explanation)):
            _check_not_stale(finding, lines)
            function_node, class_node = _enclosing_scopes(scopes, finding.line)

            function_source: Optional[str] = None
            referenced: Dict[str, str] = {}
            callers: List[str] = []
            if function_node is not None:
                function_source, was_truncated = self._bounded_source(source, function_node)
                truncated = truncated or was_truncated
                referenced = _referenced_constants(function_node, module_constants)
                callers = _callers_of(tree, function_node.name)
            else:
                for stmt in tree.body:
                    if stmt.lineno <= finding.line <= (stmt.end_lineno or stmt.lineno):
                        referenced = _referenced_constants(stmt, module_constants)

            finding_contexts.append(
                FindingContext(
                    finding_id=finding_id(finding),
                    rule_id=finding.rule_id,
                    line=finding.line,
                    enclosing_function=function_node.name if function_node is not None else None,
                    enclosing_class=class_node.name if class_node is not None else None,
                    function_source=function_source,
                    referenced_constants=referenced,
                    callers=callers,
                )
            )

        finding_contexts, budget_truncated = self._apply_total_budget(finding_contexts)
        context = CodeContext(
            module_name=module_name,
            imports=_imports(tree),
            public_interface=extract_public_interface(tree),
            findings=finding_contexts,
            truncated=truncated or budget_truncated,
        )
        return context.model_copy(update={"context_hash": stable_hash(context.model_dump(exclude={"context_hash"}))})

    def _bounded_source(self, source: str, node: ScopeNode) -> Tuple[str, bool]:
        segment = ast.get_source_segment(source, node) or ""
        segment_lines = segment.splitlines()
        if len(segment_lines) <= self.budget.max_function_lines:
            return segment, False
        kept = segment_lines[: self.budget.max_function_lines]
        return "\n".join(kept + [TRUNCATION_MARKER]), True

    def _apply_total_budget(self, contexts: List[FindingContext]) -> Tuple[List[FindingContext], bool]:
        """Drop repeated function bodies first, then truncate, until the total budget holds."""
        seen_sources = set()
        deduped: List[FindingContext] = []
        for ctx in contexts:
            if ctx.function_source is not None and ctx.function_source in seen_sources:
                ctx = ctx.model_copy(update={"function_source": None})
            elif ctx.function_source is not None:
                seen_sources.add(ctx.function_source)
            deduped.append(ctx)

        total = sum(len(ctx.function_source or "") for ctx in deduped)
        if total <= self.budget.max_total_chars:
            return deduped, False

        remaining = self.budget.max_total_chars
        bounded: List[FindingContext] = []
        for ctx in deduped:
            src = ctx.function_source or ""
            if len(src) > remaining:
                src = src[: max(remaining, 0)] + ("\n" + TRUNCATION_MARKER if remaining > 0 else "")
                ctx = ctx.model_copy(update={"function_source": src if remaining > 0 else None})
            remaining -= len(src)
            bounded.append(ctx)
        return bounded, True


def _check_not_stale(finding: Finding, lines: List[str]) -> None:
    if not 1 <= finding.line <= len(lines) or lines[finding.line - 1].strip() != finding.evidence.strip():
        raise CryptoAuditError(
            ErrorCode.CONTEXT_ERROR,
            "Finding does not match the supplied source (stale finding or wrong module)",
            {"finding_id": finding_id(finding), "line": finding.line},
        )


def _collect_scopes(tree: ast.AST) -> List[ScopeNode]:
    return [
        node for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
    ]


def _enclosing_scopes(scopes: List[ScopeNode], line: int) -> Tuple[Optional[ScopeNode], Optional[ast.ClassDef]]:
    """Innermost function and class whose span contains the line (located by position, not by name)."""
    containing = [s for s in scopes if s.lineno <= line <= (s.end_lineno or s.lineno)]
    functions = [s for s in containing if isinstance(s, (ast.FunctionDef, ast.AsyncFunctionDef))]
    classes = [s for s in containing if isinstance(s, ast.ClassDef)]
    innermost_function = max(functions, key=lambda s: s.lineno, default=None)
    innermost_class = max(classes, key=lambda s: s.lineno, default=None)
    return innermost_function, innermost_class


def _imports(tree: ast.Module) -> List[str]:
    statements: List[str] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            statements.append(ast.unparse(node))
    return sorted(set(statements), key=statements.index)


def _module_constants(tree: ast.Module, source: str) -> Dict[str, str]:
    constants: Dict[str, str] = {}
    for stmt in tree.body:
        if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1 and isinstance(stmt.targets[0], ast.Name):
            constants[stmt.targets[0].id] = ast.get_source_segment(source, stmt) or ast.unparse(stmt)
        elif isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name) and stmt.value is not None:
            constants[stmt.target.id] = ast.get_source_segment(source, stmt) or ast.unparse(stmt)
    return constants


def _referenced_constants(node: ast.AST, module_constants: Dict[str, str]) -> Dict[str, str]:
    names = {n.id for n in ast.walk(node) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)}
    return {name: module_constants[name] for name in sorted(names) if name in module_constants}


def _callers_of(tree: ast.AST, function_name: str) -> List[str]:
    """Functions in the same module that call function_name directly."""
    callers = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name != function_name:
            for call in ast.walk(node):
                if isinstance(call, ast.Call):
                    func = call.func
                    called = func.id if isinstance(func, ast.Name) else func.attr if isinstance(func, ast.Attribute) else None
                    if called == function_name:
                        callers.add(node.name)
    return sorted(callers)
