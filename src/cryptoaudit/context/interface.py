"""Public interface extraction, shared by the Context Engine and V1 interface checks."""

import ast
from typing import List, Union

from cryptoaudit.context.models import SymbolSignature

FunctionNode = Union[ast.FunctionDef, ast.AsyncFunctionDef]


def function_signature(node: FunctionNode) -> str:
    prefix = "async def" if isinstance(node, ast.AsyncFunctionDef) else "def"
    returns = f" -> {ast.unparse(node.returns)}" if node.returns is not None else ""
    return f"{prefix} {node.name}({ast.unparse(node.args)}){returns}"


def _is_public(name: str) -> bool:
    return not name.startswith("_")


def extract_public_interface(tree: ast.Module) -> List[SymbolSignature]:
    """Top-level public functions and classes, plus public methods of public classes."""
    symbols: List[SymbolSignature] = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and _is_public(node.name):
            symbols.append(
                SymbolSignature(
                    qualified_name=node.name, kind="function", signature=function_signature(node), lineno=node.lineno
                )
            )
        elif isinstance(node, ast.ClassDef) and _is_public(node.name):
            bases = ", ".join(ast.unparse(base) for base in node.bases)
            symbols.append(
                SymbolSignature(
                    qualified_name=node.name,
                    kind="class",
                    signature=f"class {node.name}({bases})" if bases else f"class {node.name}",
                    lineno=node.lineno,
                )
            )
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and (
                    _is_public(item.name) or item.name == "__init__"
                ):
                    symbols.append(
                        SymbolSignature(
                            qualified_name=f"{node.name}.{item.name}",
                            kind="method",
                            signature=function_signature(item),
                            lineno=item.lineno,
                        )
                    )
    return symbols
