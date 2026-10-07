"""Analyzer engine orchestrating AST parsing, import/call analysis, and CR1-CR5 rule evaluation."""

from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Union

from cryptoaudit.analyzer.ast_parser import parse_source_file
from cryptoaudit.analyzer.calls import extract_calls
from cryptoaudit.analyzer.imports import extract_imports
from cryptoaudit.analyzer.rules.base import BaseRule
from cryptoaudit.analyzer.rules.cr1 import CR1Rule
from cryptoaudit.analyzer.rules.cr2 import CR2Rule
from cryptoaudit.analyzer.rules.cr3 import CR3Rule
from cryptoaudit.analyzer.rules.cr4 import CR4Rule
from cryptoaudit.analyzer.rules.cr5 import CR5Rule
from cryptoaudit.core.config import Settings, load_rule_config
from cryptoaudit.core.errors import CryptoAuditError, ErrorCode
from cryptoaudit.core.models import AnalysisResult, Finding

RULE_CLASS_MAP = {
    "CR1": CR1Rule,
    "CR2": CR2Rule,
    "CR3": CR3Rule,
    "CR4": CR4Rule,
    "CR5": CR5Rule,
}


RULE_FILES = ["cr1.yaml", "cr2.yaml", "cr3.yaml", "cr4.yaml", "cr5.yaml"]

# Repository-level rules directory (src/cryptoaudit/analyzer/engine.py -> repo root).
REPO_RULES_DIR = Path(__file__).resolve().parents[3] / "configs" / "rules"


def resolve_rules_dir(rules_dir: Optional[Path] = None) -> Path:
    """
    Resolve the rules directory independent of the current working directory.

    Order: explicit argument, then the configured Settings.rules_dir (cwd-relative,
    the historical default), then the repository's configs/rules directory.
    """
    if rules_dir is not None:
        return Path(rules_dir)
    configured = Settings().rules_dir
    if configured.is_dir():
        return configured
    return REPO_RULES_DIR


def load_default_rules(rules_dir: Optional[Path] = None) -> List[BaseRule]:
    """Load all configured rule YAML files; fail loudly instead of silently loading no rules."""
    resolved_dir = resolve_rules_dir(rules_dir)
    rules: List[BaseRule] = []
    missing: List[str] = []

    for filename in RULE_FILES:
        rule_path = resolved_dir / filename
        if not rule_path.is_file():
            missing.append(filename)
            continue
        config = load_rule_config(rule_path)
        rule_cls = RULE_CLASS_MAP.get(config.rule_id)
        if rule_cls:
            rules.append(rule_cls(config))

    if missing:
        raise CryptoAuditError(
            ErrorCode.ANALYSIS_ERROR,
            f"Rule configuration files missing from {resolved_dir}: {', '.join(missing)}",
            {"rules_dir": str(resolved_dir), "missing": missing},
        )

    return rules


class AnalyzerEngine:
    """Deterministic analyzer engine for Python source code supporting CR1-CR5."""

    def __init__(self, rules: Optional[List[BaseRule]] = None) -> None:
        if rules is not None:
            self.rules = rules
        else:
            self.rules = load_default_rules()

    def analyze_file(self, file_path: Union[str, Path]) -> AnalysisResult:
        """Run the full analysis pipeline on a Python source file deterministically."""
        path = Path(file_path)
        parse_result = parse_source_file(path)
        import_tracker = extract_imports(parse_result.tree)
        call_sites = extract_calls(parse_result.tree, import_tracker)

        raw_findings: List[Finding] = []
        for call_site in call_sites:
            for rule in self.rules:
                rule_findings = rule.evaluate(call_site, parse_result)
                raw_findings.extend(rule_findings)

        # Deduplicate findings by (file, line, column, rule_id, matched_api, explanation)
        seen_keys: Set[Tuple[str, int, Optional[int], str, str, str]] = set()
        unique_findings: List[Finding] = []

        for finding in raw_findings:
            key = (
                finding.file,
                finding.line,
                finding.column,
                finding.rule_id,
                finding.matched_api,
                finding.explanation,
            )
            if key not in seen_keys:
                seen_keys.add(key)
                unique_findings.append(finding)

        # Deterministic sorting by file, line, column, rule_id, explanation
        unique_findings.sort(
            key=lambda f: (f.file, f.line, f.column if f.column is not None else 0, f.rule_id, f.explanation)
        )

        return AnalysisResult(target_file=str(path), findings=unique_findings)
