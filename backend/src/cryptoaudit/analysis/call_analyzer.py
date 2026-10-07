"""Function call site extraction and node context tracking."""

import ast
from typing import Dict, List, Optional

from cryptoaudit.analysis.import_analyzer import ImportTracker


class CallSite:
    """Represents a discovered function call site with context information."""

    def __init__(
        self,
        node: ast.Call,
        resolved_name: str,
        lineno: int,
        col_offset: int,
        args: List[ast.expr],
        keywords: Dict[str, ast.expr],
        enclosing_function: Optional[str] = None,
        enclosing_class: Optional[str] = None,
        assigned_variable: Optional[str] = None,
    ) -> None:
        self.node = node
        self.resolved_name = resolved_name
        self.lineno = lineno
        self.col_offset = col_offset
        self.args = args
        self.keywords = keywords
        self.enclosing_function = enclosing_function
        self.enclosing_class = enclosing_class
        self.assigned_variable = assigned_variable


class CallExtractor(ast.NodeVisitor):
    """AST visitor that extracts function calls and captures enclosing scope context."""

    def __init__(self, import_tracker: ImportTracker) -> None:
        self.import_tracker = import_tracker
        self.calls: List[CallSite] = []
        self._function_stack: List[str] = []
        self._class_stack: List[str] = []
        self._current_assigned_var: Optional[str] = None

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self._class_stack.append(node.name)
        self.generic_visit(node)
        self._class_stack.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._function_stack.append(node.name)
        self.generic_visit(node)
        self._function_stack.pop()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._function_stack.append(node.name)
        self.generic_visit(node)
        self._function_stack.pop()

    def visit_Assign(self, node: ast.Assign) -> None:
        # Track target variable name if single target
        assigned_var = None
        if len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            assigned_var = node.targets[0].id

        previous_var = self._current_assigned_var
        self._current_assigned_var = assigned_var
        self.generic_visit(node)
        self._current_assigned_var = previous_var

    def visit_Call(self, node: ast.Call) -> None:
        resolved = self.import_tracker.resolve_attribute_call(node.func)
        if resolved:
            keywords = {kw.arg: kw.value for kw in node.keywords if kw.arg is not None}
            call_site = CallSite(
                node=node,
                resolved_name=resolved,
                lineno=node.lineno,
                col_offset=node.col_offset,
                args=node.args,
                keywords=keywords,
                enclosing_function=self._function_stack[-1] if self._function_stack else None,
                enclosing_class=self._class_stack[-1] if self._class_stack else None,
                assigned_variable=self._current_assigned_var,
            )
            self.calls.append(call_site)
        self.generic_visit(node)


def extract_calls(tree: ast.AST, import_tracker: ImportTracker) -> List[CallSite]:
    """Extract all function calls from AST tree using import tracker."""
    extractor = CallExtractor(import_tracker)
    extractor.visit(tree)
    return extractor.calls
