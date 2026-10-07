"""S1: tool-guided repair that applies only machine-applicable scanner hints."""

import ast
from typing import List, Optional, Sequence

from cryptoaudit.models.finding import Finding, finding_id
from cryptoaudit.models.repair import RepairRequest, RepairResult, RepairStatus, StrategyId
from cryptoaudit.models.scan import Scanner, ScannerIssue, ScanReport
from cryptoaudit.repair.base import RepairStrategy
from cryptoaudit.repair.edits import SourceIndex, TextEdit, apply_edits, edits_overlap, find_call
from cryptoaudit.utils.errors import ErrorCode

# Bandit test IDs whose own message prescribes a concrete code change.
BANDIT_WEAK_HASH = "B324"  # "Consider usedforsecurity=False"


class ToolGuidedRepairStrategy(RepairStrategy):
    """
    Applies the remediation the scanner itself suggests, aligned to a CryptoAudit finding.

    S1 never adds findings of its own: a hint is used only when it sits on a finding's
    line. Findings without machine-applicable guidance are recorded as NOT_APPLICABLE.
    """

    strategy_id = StrategyId.S1

    def __init__(self, scanners: Sequence[Scanner]) -> None:
        self.scanners = list(scanners)

    def _repair(self, request: RepairRequest) -> RepairResult:
        reports: List[ScanReport] = [s.scan_source(request.source, request.module_name) for s in self.scanners]
        available = [r for r in reports if r.available]
        tool_notes = [f"{r.tool}: {'ran' if r.available else 'unavailable - ' + (r.error or '')}" for r in reports]
        if not available:
            return self.failure(
                RepairStatus.NO_REPAIR, "No scanner available to provide guidance", ErrorCode.TOOL_UNAVAILABLE,
                notes=tool_notes,
            )

        tree = ast.parse(request.source)
        index = SourceIndex(request.source)
        hints = sorted(
            (issue for report in available for issue in report.issues),
            key=lambda i: (i.tool, i.rule_id, i.line, i.start_offset or 0),
        )
        edits: List[TextEdit] = []
        repaired: List[str] = []
        unrepaired: List[str] = []
        notes = list(tool_notes)

        for finding in request.findings:
            fid = finding_id(finding)
            aligned = [h for h in hints if h.line <= finding.line <= (h.end_line or h.line)]
            edit, used = None, None
            for hint in aligned:
                edit = _edit_from_hint(hint, finding, tree, index, request.source)
                if edit is not None and not edits_overlap(edit, edits):
                    used = hint
                    break
                edit = None
            if edit is None or used is None:
                unrepaired.append(fid)
                notes.append(f"{fid}: no machine-applicable hint ({len(aligned)} aligned hint(s))")
                continue
            edits.append(edit)
            repaired.append(fid)
            notes.append(f"{fid}: applied {used.tool}:{used.rule_id}")

        if not edits:
            return self.failure(
                RepairStatus.NOT_APPLICABLE,
                "Scanner guidance offers no machine-applicable fix for these findings",
                unrepaired_finding_ids=unrepaired,
                notes=notes,
            )

        return RepairResult(
            strategy_id=self.strategy_id,
            status=RepairStatus.PRODUCED,
            candidate_code=apply_edits(request.source, edits),
            repaired_finding_ids=repaired,
            unrepaired_finding_ids=unrepaired,
            notes=notes,
        )


def _edit_from_hint(
    hint: ScannerIssue, finding: Finding, tree: ast.AST, index: SourceIndex, source: str
) -> Optional[TextEdit]:
    if hint.tool == "semgrep" and hint.fix is not None and hint.start_offset is not None and hint.end_offset is not None:
        encoded = source.encode("utf-8")
        start = len(encoded[: hint.start_offset].decode("utf-8", errors="ignore"))
        end = len(encoded[: hint.end_offset].decode("utf-8", errors="ignore"))
        return TextEdit(start, end, hint.fix)
    if hint.tool == "bandit" and hint.rule_id == BANDIT_WEAK_HASH:
        return _usedforsecurity_edit(finding, tree, index, source)
    return None


def _usedforsecurity_edit(finding: Finding, tree: ast.AST, index: SourceIndex, source: str) -> Optional[TextEdit]:
    if not finding.matched_api.endswith((".md5", ".sha1")):
        return None
    call = find_call(tree, finding.line, finding.column)
    if call is None or any(k.arg == "usedforsecurity" for k in call.keywords):
        return None
    _, end = index.span(call)
    close = end - 1
    if source[close] != ")":
        return None
    between = source[index.span(call.func)[1] : close]
    before = between.split("(", 1)[1].rstrip() if "(" in between else ""
    if not before:
        text = "usedforsecurity=False"
    elif before.endswith(","):
        text = " usedforsecurity=False"
    else:
        text = ", usedforsecurity=False"
    return TextEdit(close, close, text)
