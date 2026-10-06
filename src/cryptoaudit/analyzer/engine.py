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
from cryptoaudit.core.config import load_rule_config
from cryptoaudit.core.models import AnalysisResult, Finding

RULE_CLASS_MAP = {
    "CR1": CR1Rule,
    "CR2": CR2Rule,
    "CR3": CR3Rule,
    "CR4": CR4Rule,
    "CR5": CR5Rule,
}


def load_default_rules(rules_dir: Path = Path("configs/rules")) -> List[BaseRule]:
    """Load all configured rule YAML files from rules_dir."""
    rules: List[BaseRule] = []
    rule_files = ["cr1.yaml", "cr2.yaml", "cr3.yaml", "cr4.yaml", "cr5.yaml"]

    for filename in rule_files:
        rule_path = rules_dir / filename
        if rule_path.is_file():
            config = load_rule_config(rule_path)
            rule_cls = RULE_CLASS_MAP.get(config.rule_id)
            if rule_cls:
                rules.append(rule_cls(config))

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
