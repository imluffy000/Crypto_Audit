"""Context Engine: builds bounded, deterministic repair context from a module's AST."""

import ast
from typing import Dict, List, Optional, Sequence, Tuple

from cryptoaudit.context.call_graph import callers_of
from cryptoaudit.context.context_budget import TRUNCATION_MARKER, ContextBudget
from cryptoaudit.context.extractor import (
    ScopeNode,
    collect_scopes,
    constant_definitions,
    enclosing_scopes,
    import_statements,
    referenced_constants,
)
from cryptoaudit.context.symbol_resolver import extract_public_interface
from cryptoaudit.models.context import CodeContext, FindingContext
from cryptoaudit.models.finding import Finding, finding_id
from cryptoaudit.utils.errors import CryptoAuditError, ErrorCode
from cryptoaudit.utils.hashing import stable_hash


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
        module_constants = constant_definitions(tree, source)
        scopes = collect_scopes(tree)
        truncated = False
        finding_contexts: List[FindingContext] = []

        for finding in sorted(findings, key=lambda f: (f.line, f.column or 0, f.rule_id, f.explanation)):
            _check_not_stale(finding, lines)
            function_node, class_node = enclosing_scopes(scopes, finding.line)

            function_source: Optional[str] = None
            referenced: Dict[str, str] = {}
            callers: List[str] = []
            if function_node is not None:
                function_source, was_truncated = self._bounded_source(source, function_node)
                truncated = truncated or was_truncated
                referenced = referenced_constants(function_node, module_constants)
                callers = callers_of(tree, function_node.name)
            else:
                for stmt in tree.body:
                    if stmt.lineno <= finding.line <= (stmt.end_lineno or stmt.lineno):
                        referenced = referenced_constants(stmt, module_constants)

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
            imports=import_statements(tree),
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












