"""V0: scanner re-scan of the candidate. Recorded as evidence; never decides acceptance."""

import tempfile
import time
from pathlib import Path
from typing import Dict, List, Sequence, Set

from cryptoaudit import __version__ as CRYPTOAUDIT_VERSION
from cryptoaudit.analysis.analyzer import AnalyzerEngine
from cryptoaudit.models.scan import Scanner, ScanReport
from cryptoaudit.models.validation import GateId, GateResult, GateStatus

# Bandit test IDs that correspond to each CryptoAudit rule.
BANDIT_RULE_MAP: Dict[str, Set[str]] = {
    "CR1": {"B303", "B324"},
    "CR2": {"B304", "B305"},
    "CR3": set(),
    "CR4": set(),
    "CR5": {"B311"},
}
CRYPTO_KEYWORDS = ("md5", "sha1", "hash", "cipher", "ecb", "crypt", "random", "iv", "nonce", "salt", "kdf", "pbkdf")


def relevant_issue_count(report: ScanReport, target_rules: Sequence[str]) -> int:
    if report.tool == "bandit":
        ids = set().union(*(BANDIT_RULE_MAP.get(r, set()) for r in target_rules)) if target_rules else set()
        return sum(1 for issue in report.issues if issue.rule_id in ids)
    return sum(1 for issue in report.issues if any(k in issue.rule_id.lower() for k in CRYPTO_KEYWORDS))


class ScannerValidator:
    def __init__(self, analyzer: AnalyzerEngine, scanners: Sequence[Scanner] = ()) -> None:
        self.analyzer = analyzer
        self.scanners = list(scanners)

    def scan(self, code: str, module_name: str, target_rules: Sequence[str]) -> Dict[str, dict]:
        """Run CryptoAudit and every baseline scanner on code; also used for baseline detection of originals."""
        evidence: Dict[str, dict] = {"cryptoaudit": self._analyze(code, module_name, target_rules)}
        for scanner in self.scanners:
            report = scanner.scan_source(code, module_name)
            evidence[report.tool] = {
                "available": report.available,
                "tool_version": report.tool_version,
                "config": report.config,
                "total_issues": len(report.issues) if report.available else None,
                "relevant_issues": relevant_issue_count(report, target_rules) if report.available else None,
                "rule_ids": sorted({i.rule_id for i in report.issues}),
                "error": report.error,
            }
        return evidence

    def validate(self, code: str, module_name: str, target_rules: Sequence[str]) -> GateResult:
        started = time.perf_counter()
        evidence = self.scan(code, module_name, target_rules)
        available = {tool: e for tool, e in evidence.items() if e["available"]}
        still_reported: List[str] = [tool for tool, e in available.items() if (e["relevant_issues"] or 0) > 0]
        unavailable = sorted(set(evidence) - set(available))

        if not available:
            status, summary = GateStatus.ERROR, "No scanner could analyse the candidate"
        elif still_reported:
            status, summary = GateStatus.FAIL, f"Issue still reported by: {', '.join(sorted(still_reported))}"
        else:
            status, summary = GateStatus.PASS, "No relevant issue reported by any available scanner"
        if unavailable:
            summary += f" (unavailable: {', '.join(unavailable)})"
        return GateResult(
            gate=GateId.V0,
            status=status,
            gating=False,
            summary=summary + ". Scanner results are evidence only, not acceptance.",
            evidence=evidence,
            duration_seconds=round(time.perf_counter() - started, 3),
        )

    def _analyze(self, code: str, module_name: str, target_rules: Sequence[str]) -> dict:
        with tempfile.TemporaryDirectory(prefix="cryptoaudit-v0-") as tmp:
            path = Path(tmp) / (Path(module_name).name or "module.py")
            with open(path, "w", encoding="utf-8", newline="") as handle:
                handle.write(code)
            try:
                findings = self.analyzer.analyze_file(path).findings
            except Exception as exc:  # e.g. syntax error in candidate
                return {"available": False, "error": f"{type(exc).__name__}: {exc}", "total_issues": None, "relevant_issues": None, "rule_ids": []}
        rules = {f.rule_id for f in findings}
        return {
            "available": True,
            "tool_version": CRYPTOAUDIT_VERSION,
            "config": None,
            "total_issues": len(findings),
            "relevant_issues": sum(1 for f in findings if f.rule_id in set(target_rules)) if target_rules else len(findings),
            "rule_ids": sorted(rules),
            "error": None,
        }
