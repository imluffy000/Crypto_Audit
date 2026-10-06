"""AST parser and source code line tracker."""

import ast
from pathlib import Path
from typing import List, Tuple, Union


class ASTParseResult:
    """Holds parsed AST tree and raw source lines for a Python file."""

    def __init__(self, file_path: str, tree: ast.AST, source_lines: List[str]):
        self.file_path = file_path
        self.tree = tree
        self.source_lines = source_lines

    def get_line_content(self, lineno: int) -> str:
        """Return the raw text of a 1-indexed source line."""
        if 1 <= lineno <= len(self.source_lines):
            return self.source_lines[lineno - 1]
        return ""


def parse_source_file(file_path: Union[str, Path]) -> ASTParseResult:
    """Parse a Python source file into an ASTParseResult."""
    path = Path(file_path)
    if not path.is_file():
        raise FileNotFoundError(f"Source file not found: {path}")

    source_text = path.read_text(encoding="utf-8")
    lines = source_text.splitlines()

    try:
        tree = ast.parse(source_text, filename=str(path))
    except SyntaxError as exc:
        raise ValueError(f"Syntax error in {path} at line {exc.lineno}: {exc.msg}") from exc

    return ASTParseResult(file_path=str(path), tree=tree, source_lines=lines)
