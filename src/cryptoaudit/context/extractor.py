"""AST extraction for the Context Engine: scopes, imports and module constants."""

import ast
from typing import Dict, List, Optional, Tuple, Union

ScopeNode = Union[ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef]


def collect_scopes(tree: ast.AST) -> List[ScopeNode]:
    return [
        node for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
    ]


def enclosing_scopes(scopes: List[ScopeNode], line: int) -> Tuple[Optional[ScopeNode], Optional[ast.ClassDef]]:
    """Innermost function and class whose span contains the line (located by position, not by name)."""
    containing = [s for s in scopes if s.lineno <= line <= (s.end_lineno or s.lineno)]
    functions = [s for s in containing if isinstance(s, (ast.FunctionDef, ast.AsyncFunctionDef))]
    classes = [s for s in containing if isinstance(s, ast.ClassDef)]
    innermost_function = max(functions, key=lambda s: s.lineno, default=None)
    innermost_class = max(classes, key=lambda s: s.lineno, default=None)
    return innermost_function, innermost_class


def import_statements(tree: ast.Module) -> List[str]:
    statements: List[str] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            statements.append(ast.unparse(node))
    return sorted(set(statements), key=statements.index)


def constant_definitions(tree: ast.Module, source: str) -> Dict[str, str]:
    constants: Dict[str, str] = {}
    for stmt in tree.body:
        if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1 and isinstance(stmt.targets[0], ast.Name):
            constants[stmt.targets[0].id] = ast.get_source_segment(source, stmt) or ast.unparse(stmt)
        elif isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name) and stmt.value is not None:
            constants[stmt.target.id] = ast.get_source_segment(source, stmt) or ast.unparse(stmt)
    return constants


def referenced_constants(node: ast.AST, module_constants: Dict[str, str]) -> Dict[str, str]:
    names = {n.id for n in ast.walk(node) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)}
    return {name: module_constants[name] for name in sorted(names) if name in module_constants}
