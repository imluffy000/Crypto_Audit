"""In-module call relationships."""

import ast
from typing import List


def callers_of(tree: ast.AST, function_name: str) -> List[str]:
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
