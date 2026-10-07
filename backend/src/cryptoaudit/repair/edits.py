"""Position-based source editing that preserves formatting and comments."""

import ast
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional


@dataclass(frozen=True)
class TextEdit:
    """Replace source[start:end] (character offsets) with replacement."""

    start: int
    end: int
    replacement: str


class SourceIndex:
    """Converts AST (lineno, UTF-8 byte col_offset) positions to character offsets."""

    def __init__(self, source: str) -> None:
        self.source = source
        self.lines = source.splitlines(keepends=True)
        self.line_starts: List[int] = []
        offset = 0
        for line in self.lines:
            self.line_starts.append(offset)
            offset += len(line)

    def offset(self, lineno: int, col_byte: int) -> int:
        line = self.lines[lineno - 1]
        char_col = len(line.encode("utf-8")[:col_byte].decode("utf-8", errors="ignore"))
        return self.line_starts[lineno - 1] + char_col

    def span(self, node: ast.AST) -> tuple[int, int]:
        start = self.offset(node.lineno, node.col_offset)  # type: ignore[attr-defined]
        end = self.offset(node.end_lineno, node.end_col_offset)  # type: ignore[attr-defined]
        return start, end

    def text(self, node: ast.AST) -> str:
        start, end = self.span(node)
        return self.source[start:end]


class OverlappingEditError(ValueError):
    pass


def apply_edits(source: str, edits: Iterable[TextEdit]) -> str:
    unique = sorted(set(edits), key=lambda e: (e.start, e.end))
    for previous, current in zip(unique, unique[1:]):
        if current.start < previous.end:
            raise OverlappingEditError(f"Edits overlap at offsets {previous.start}-{previous.end} / {current.start}")
    result = source
    for edit in reversed(unique):
        result = result[: edit.start] + edit.replacement + result[edit.end :]
    return result


def edits_overlap(edit: TextEdit, others: Iterable[TextEdit]) -> bool:
    return any(edit != other and edit.start < other.end and other.start < edit.end for other in others)


def find_call(tree: ast.AST, line: int, column: Optional[int]) -> Optional[ast.Call]:
    """
    The call node an analyzer finding points at (CallSite records the call's own position).

    Chained calls such as `hashlib.md5(x).hexdigest()` share a start position, so the
    innermost (shortest) call is the one the analyzer resolved.
    """
    matches = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and node.lineno == line and (column is None or node.col_offset == column)
    ]
    if not matches:
        return None
    return min(matches, key=lambda n: (n.end_lineno or 0, n.end_col_offset or 0))


def parent_map(tree: ast.AST) -> Dict[ast.AST, ast.AST]:
    parents: Dict[ast.AST, ast.AST] = {}
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            parents[child] = node
    return parents


def has_plain_import(tree: ast.Module, module: str) -> bool:
    for node in tree.body:
        if isinstance(node, ast.Import) and any(a.name == module and a.asname is None for a in node.names):
            return True
    return False


def ensure_import(source: str, module: str) -> str:
    """Add `import module` after the last top-level import (or the docstring) if missing."""
    tree = ast.parse(source)
    if has_plain_import(tree, module):
        return source

    insert_after_line = 0
    body = tree.body
    if body and isinstance(body[0], ast.Expr) and isinstance(getattr(body[0], "value", None), ast.Constant):
        if isinstance(body[0].value.value, str):
            insert_after_line = body[0].end_lineno or 0
    for node in body:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            insert_after_line = node.end_lineno or insert_after_line

    lines = source.splitlines(keepends=True)
    newline = "\r\n" if lines and lines[0].endswith("\r\n") else "\n"
    if lines and not lines[-1].endswith(("\n", "\r")):
        lines[-1] += newline
    lines.insert(insert_after_line, f"import {module}{newline}")
    return "".join(lines)
