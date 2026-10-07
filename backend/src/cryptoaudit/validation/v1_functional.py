"""V1 functional validation: syntax, public-interface preservation and hidden functional checks."""

import ast
from pathlib import Path
from typing import List, Optional

from cryptoaudit.context.symbol_resolver import extract_public_interface
from cryptoaudit.models.repair import Candidate
from cryptoaudit.models.validation import CheckResult, GateId, GateResult, GateStatus
from cryptoaudit.validation.checks import OracleGate
from cryptoaudit.validation.sandbox import Sandbox


def interface_check(original_source: str, candidate_code: str) -> CheckResult:
    """Every public symbol of the original must survive with an identical signature."""
    try:
        candidate_tree = ast.parse(candidate_code)
    except SyntaxError as exc:
        return CheckResult(name="interface_preserved", status=GateStatus.FAIL, message=f"syntax error: {exc.msg}")
    original = {s.qualified_name: s.signature for s in extract_public_interface(ast.parse(original_source))}
    candidate = {s.qualified_name: s.signature for s in extract_public_interface(candidate_tree)}
    problems: List[str] = []
    for name, signature in original.items():
        if name not in candidate:
            problems.append(f"missing {name}")
        elif candidate[name] != signature:
            problems.append(f"changed {signature!r} -> {candidate[name]!r}")
    if problems:
        return CheckResult(name="interface_preserved", status=GateStatus.FAIL, message="; ".join(problems))
    return CheckResult(name="interface_preserved", status=GateStatus.PASS)


class FunctionalValidator:
    """V1: syntax, public-interface preservation and the functional oracle (hidden or user-supplied)."""

    def __init__(self, sandbox: Sandbox) -> None:
        self.gate = OracleGate(GateId.V1, sandbox)

    def validate(
        self, candidate: Candidate, original_source: str, check_file: Optional[Path], artifacts_dir: Optional[Path]
    ) -> GateResult:
        syntax_ok = candidate.integrity is not None and candidate.integrity.syntax_ok
        pre_checks = [CheckResult(name="syntax_valid", status=GateStatus.PASS if syntax_ok else GateStatus.FAIL)]
        if syntax_ok:
            pre_checks.append(interface_check(original_source, candidate.code or ""))
        return self.gate.run(candidate, check_file, artifacts_dir, gating=True, pre_checks=pre_checks)
