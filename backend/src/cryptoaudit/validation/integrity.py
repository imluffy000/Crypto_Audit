"""Code integrity checks run on every candidate before anything executes it."""

import ast
from typing import Iterable, List, Optional, Sequence, Set

from cryptoaudit.models.validation import IntegrityIssue, IntegrityReport

DEFAULT_MAX_CHARS = 100_000

# Helper stdlib modules that are always acceptable in a repaired crypto module.
SAFE_STDLIB = frozenset(
    {"__future__", "typing", "dataclasses", "enum", "functools", "itertools", "collections", "string", "re",
     "json", "math", "abc", "struct", "warnings"}
)
# Crypto-safe stdlib used when a case does not declare allowed libraries (user code).
DEFAULT_CRYPTO_STDLIB = frozenset({"hashlib", "hmac", "secrets", "os", "base64", "binascii"})
# Never acceptable: process, network, native code, deserialisation and dynamic import surfaces.
DENIED_MODULES = frozenset(
    {"subprocess", "socket", "ctypes", "multiprocessing", "shutil", "urllib", "http", "requests", "ftplib",
     "telnetlib", "smtplib", "pickle", "marshal", "importlib", "builtins", "pty", "signal", "asyncio"}
)
DENIED_BUILTINS = frozenset({"eval", "exec", "compile", "__import__", "breakpoint"})
DENIED_OS_CALLS = frozenset(
    {"system", "popen", "fork", "forkpty", "kill", "killpg", "remove", "unlink", "rmdir", "removedirs",
     "rename", "replace", "chmod", "chown", "putenv", "setuid", "setgid"}
)
DENIED_OS_PREFIXES = ("exec", "spawn")
WRITE_MODES = set("wax+")






class IntegrityChecker:
    def __init__(self, max_chars: int = DEFAULT_MAX_CHARS) -> None:
        self.max_chars = max_chars

    def check(
        self,
        code: str,
        allowed_libraries: Sequence[str] = (),
        original_source: Optional[str] = None,
    ) -> IntegrityReport:
        issues: List[IntegrityIssue] = []
        if len(code) > self.max_chars:
            issues.append(IntegrityIssue(kind="size", message=f"Candidate exceeds {self.max_chars} characters"))
        try:
            tree = ast.parse(code)
        except SyntaxError as exc:
            issues.append(IntegrityIssue(kind="syntax", message=exc.msg or "invalid syntax", line=exc.lineno))
            return IntegrityReport(passed=False, syntax_ok=False, issues=issues)

        allowed = self._allowed_modules(allowed_libraries, original_source)
        imports = sorted(_imported_modules(tree))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.level:
                issues.append(IntegrityIssue(kind="dependency", message="Relative imports are not allowed", line=node.lineno))
        for module in imports:
            root = module.split(".")[0]
            if root in DENIED_MODULES:
                issues.append(IntegrityIssue(kind="dangerous_call", message=f"Denied module imported: {module}"))
            elif root not in allowed:
                issues.append(IntegrityIssue(kind="dependency", message=f"Import outside allowed libraries: {module}"))
        issues.extend(_dangerous_calls(tree))
        return IntegrityReport(passed=not issues, syntax_ok=True, imports=imports, issues=issues)

    @staticmethod
    def _allowed_modules(allowed_libraries: Sequence[str], original_source: Optional[str]) -> Set[str]:
        allowed = set(SAFE_STDLIB) | {lib.split(".")[0] for lib in allowed_libraries}
        if not allowed_libraries:
            allowed |= DEFAULT_CRYPTO_STDLIB
        if original_source is not None:
            try:
                allowed |= {m.split(".")[0] for m in _imported_modules(ast.parse(original_source))}
            except SyntaxError:
                pass
        return allowed - DENIED_MODULES


def _imported_modules(tree: ast.AST) -> Set[str]:
    modules: Set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and not node.level and node.module:
            modules.add(node.module)
    return modules


def _dangerous_calls(tree: ast.AST) -> Iterable[IntegrityIssue]:
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Name) and func.id in DENIED_BUILTINS:
            yield IntegrityIssue(kind="dangerous_call", message=f"Call to {func.id}()", line=node.lineno)
        elif isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name) and func.value.id == "os":
            if func.attr in DENIED_OS_CALLS or func.attr.startswith(DENIED_OS_PREFIXES):
                yield IntegrityIssue(kind="dangerous_call", message=f"Call to os.{func.attr}()", line=node.lineno)
        elif isinstance(func, ast.Name) and func.id == "open" and _opens_for_write(node):
            yield IntegrityIssue(kind="dangerous_call", message="File opened for writing", line=node.lineno)


def _opens_for_write(call: ast.Call) -> bool:
    mode: Optional[ast.AST] = call.args[1] if len(call.args) > 1 else None
    for kw in call.keywords:
        if kw.arg == "mode":
            mode = kw.value
    if mode is None:
        return False
    if isinstance(mode, ast.Constant) and isinstance(mode.value, str):
        return bool(WRITE_MODES & set(mode.value))
    return True  # non-literal mode cannot be verified
