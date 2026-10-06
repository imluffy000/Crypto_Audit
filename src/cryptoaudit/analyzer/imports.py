"""Import tracking and symbol resolution for Python AST analysis."""

import ast
from typing import Dict, List, Optional


class ImportTracker(ast.NodeVisitor):
    """AST visitor that tracks imported modules and symbol aliases."""

    def __init__(self) -> None:
        # Maps local alias/symbol name to fully qualified name
        # e.g., "hl" -> "hashlib", "md5" -> "hashlib.md5", "my_sha1" -> "hashlib.sha1"
        self.aliases: Dict[str, str] = {}
        self.raw_imports: List[str] = []

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            name = alias.name
            asname = alias.asname or alias.name
            self.aliases[asname] = name
            self.raw_imports.append(f"import {name}" + (f" as {asname}" if alias.asname else ""))
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        module = node.module or ""
        for alias in node.names:
            asname = alias.asname or alias.name
            full_name = f"{module}.{alias.name}" if module else alias.name
            self.aliases[asname] = full_name
            self.raw_imports.append(
                f"from {module} import {alias.name}" + (f" as {asname}" if alias.asname else "")
            )
        self.generic_visit(node)

    def resolve_symbol(self, name: str) -> Optional[str]:
        """Resolve a local variable or function call prefix to its imported symbol if tracked."""
        return self.aliases.get(name)

    def resolve_attribute_call(self, func_node: ast.AST) -> Optional[str]:
        """
        Resolve an AST callable node (ast.Attribute or ast.Name) to its fully qualified name if imported.
        e.g., hl.md5 -> hashlib.md5
              md5 -> hashlib.md5
              hashlib.md5 -> hashlib.md5
        """
        if isinstance(func_node, ast.Name):
            return self.resolve_symbol(func_node.id)
        elif isinstance(func_node, ast.Attribute):
            value_name = self.resolve_attribute_value(func_node.value)
            if value_name:
                root_symbol = value_name.split(".")[0]
                if root_symbol in self.aliases:
                    resolved_base = self.aliases[root_symbol]
                    remainder = value_name[len(root_symbol) :]
                    return f"{resolved_base}{remainder}.{func_node.attr}"
        return None

    def resolve_attribute_value(self, node: ast.AST) -> Optional[str]:
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            base = self.resolve_attribute_value(node.value)
            if base:
                return f"{base}.{node.attr}"
        return None


def extract_imports(tree: ast.AST) -> ImportTracker:
    """Run ImportTracker on an AST tree and return the populated tracker."""
    tracker = ImportTracker()
    tracker.visit(tree)
    return tracker
