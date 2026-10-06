"""AST helper module for literal evaluation, scope-aware constant tracking, and secure generator identification."""

import ast
from typing import Any, List, Optional, Set, Tuple, Union

from cryptoaudit.analyzer.ast_parser import ASTParseResult
from cryptoaudit.analyzer.calls import CallSite

SECURE_GENERATOR_APIS = {
    "os.urandom",
    "secrets.token_bytes",
    "secrets.token_hex",
    "secrets.token_urlsafe",
    "secrets.choice",
    "secrets.SystemRandom",
}


def is_constant_literal(node: ast.AST) -> bool:
    """Check if an AST node is a literal constant (bytes, str, int)."""
    if isinstance(node, ast.Constant):
        return isinstance(node.value, (bytes, str, int))
    return False


def get_literal_value(node: ast.AST) -> Optional[Any]:
    """Extract literal value from an AST node if constant."""
    if isinstance(node, ast.Constant):
        return node.value
    return None


def is_secure_generator_call(node: ast.AST, import_tracker: Any) -> bool:
    """Check if an AST node is a call to a secure randomness generator (os.urandom, secrets.*)."""
    if not isinstance(node, ast.Call):
        return False
    resolved = import_tracker.resolve_attribute_call(node.func)
    if resolved and resolved in SECURE_GENERATOR_APIS:
        return True
    return False


def is_static_constant_expr(node: ast.AST) -> bool:
    """Check if expression evaluates to a static literal value or static binary op (e.g., b'0'*16)."""
    if is_constant_literal(node):
        return True
    if isinstance(node, ast.BinOp):
        return is_static_constant_expr(node.left) and is_static_constant_expr(node.right)
    return False


def _get_function_def(tree: ast.AST, func_name: str) -> Optional[Union[ast.FunctionDef, ast.AsyncFunctionDef]]:
    """Locate ast.FunctionDef or ast.AsyncFunctionDef node in tree by name."""
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == func_name:
            return node
    return None


def _get_function_parameters(func_node: Union[ast.FunctionDef, ast.AsyncFunctionDef]) -> Set[str]:
    """Extract all parameter names for a function definition."""
    params: Set[str] = set()
    args_obj = func_node.args
    for arg in args_obj.posonlyargs + args_obj.args + args_obj.kwonlyargs:
        params.add(arg.arg)
    if args_obj.vararg:
        params.add(args_obj.vararg.arg)
    if args_obj.kwarg:
        params.add(args_obj.kwarg.arg)
    return params


def resolve_scope_aware_constant(
    node: ast.AST,
    call_site: CallSite,
    parse_result: ASTParseResult,
) -> Tuple[bool, Optional[Any]]:
    """
    Scope-aware intra-procedural constant resolver.

    Distinguishes:
    - Direct literal expressions (b"1234567890123456")
    - Local function variables assigned constants inside call_site's enclosing function
    - Module-level constants
    - Function parameters (dynamic caller input unless re-assigned locally)
    - Unrelated functions' local variables (preventing cross-function variable contamination)
    """
    if is_static_constant_expr(node):
        return True, get_literal_value(node)

    if not isinstance(node, ast.Name):
        return False, None

    var_name = node.id
    enclosing_func_name = call_site.enclosing_function

    if enclosing_func_name:
        func_node = _get_function_def(parse_result.tree, enclosing_func_name)
        if func_node:
            func_params = _get_function_parameters(func_node)

            # Look for local assignments to var_name within enclosing_func_name
            local_assigned_val: Optional[ast.AST] = None
            for stmt in ast.walk(func_node):
                if isinstance(stmt, ast.Assign):
                    if getattr(stmt, "lineno", 0) <= call_site.lineno:
                        for target in stmt.targets:
                            if isinstance(target, ast.Name) and target.id == var_name:
                                local_assigned_val = stmt.value

            if local_assigned_val is not None:
                if is_static_constant_expr(local_assigned_val):
                    return True, get_literal_value(local_assigned_val)
                return False, None

            # If var_name is a function parameter and not re-assigned locally, it is dynamic
            if var_name in func_params:
                return False, None

    # Check top-level module scope assignments (outside any function definition)
    for stmt in parse_result.tree.body:
        if isinstance(stmt, ast.Assign):
            for target in stmt.targets:
                if isinstance(target, ast.Name) and target.id == var_name:
                    if is_static_constant_expr(stmt.value):
                        return True, get_literal_value(stmt.value)

    return False, None
