"""Context analyzer for distinguishing credential storage from non-credential usage."""

import ast
import re
from typing import List, Optional, Set

from cryptoaudit.analysis.call_analyzer import CallSite

EXACT_CREDENTIAL_TOKENS = {
    "password",
    "passwd",
    "pwd",
    "secret",
    "credential",
    "credentials",
    "cred",
    "creds",
    "user_pass",
    "db_password",
    "hash_password",
    "user_secret",
    "auth_pass",
    "auth_password",
}

NON_CREDENTIAL_KEYWORDS = {
    "checksum",
    "file",
    "bytes",
    "data",
    "content",
    "image",
    "cache",
    "etag",
    "filename",
    "buf",
    "buffer",
    "download",
    "chunk",
    "hash_file",
    "file_hash",
    "md5_checksum",
    "sha1_checksum",
}


def _extract_identifiers_from_ast(node: ast.AST) -> Set[str]:
    """Recursively extract variable and attribute names from an AST node."""
    identifiers: Set[str] = set()
    for child in ast.walk(node):
        if isinstance(child, ast.Name):
            identifiers.add(child.id.lower())
        elif isinstance(child, ast.Attribute):
            identifiers.add(child.attr.lower())
    return identifiers


def _tokenize_identifier(identifier: str) -> List[str]:
    """Split snake_case, camelCase, or dot-separated identifier into component words."""
    # Split camelCase
    s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", identifier)
    s2 = re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1)
    return [w.lower() for w in re.split(r"[_\.\-\s]+", s2) if w]


def is_credential_context(
    call_site: CallSite,
    source_line: str,
    custom_keywords: Optional[List[str]] = None,
) -> bool:
    """
    Determine if a function call occurs within a credential/password context.

    Evaluates:
    - Target variable name receiving call output
    - Identifiers used in function call arguments
    - Enclosing function/class names
    - Code-only source line text (excluding inline comments)
    """
    target_tokens = set(k.lower() for k in (custom_keywords or EXACT_CREDENTIAL_TOKENS))

    # Strip inline comments from source line to prevent comment-based false positives
    code_only_line = source_line.split("#")[0].strip().lower()

    # Collect AST identifiers in scope
    ast_identifiers: Set[str] = set()

    if call_site.assigned_variable:
        ast_identifiers.add(call_site.assigned_variable)

    if call_site.enclosing_function:
        ast_identifiers.add(call_site.enclosing_function)

    if call_site.enclosing_class:
        ast_identifiers.add(call_site.enclosing_class)

    for arg in call_site.args:
        ast_identifiers.update(_extract_identifiers_from_ast(arg))

    # Check AST identifiers by tokenizing them cleanly
    for ident in ast_identifiers:
        ident_lower = ident.lower()
        if ident_lower in target_tokens:
            return True
        tokens = _tokenize_identifier(ident)
        for token in tokens:
            if token in target_tokens:
                return True

    # Check code-only line (without comments) for target credential tokens
    line_code_words = set(re.findall(r"\b\w+\b", code_only_line))
    for target in target_tokens:
        if target in line_code_words:
            return True

    # Check non-credential indicators (e.g., checksum, file_bytes)
    has_non_cred = any(
        any(non_kw in ident for non_kw in NON_CREDENTIAL_KEYWORDS)
        for ident in ast_identifiers
    ) or any(non_kw in line_code_words for non_kw in NON_CREDENTIAL_KEYWORDS)

    if has_non_cred:
        return False

    return False
