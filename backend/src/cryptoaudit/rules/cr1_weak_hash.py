"""CR1 Rule: Weak Hashing for Stored Credentials detection."""

from typing import List

from cryptoaudit.analysis.ast_parser import ASTParseResult
from cryptoaudit.analysis.call_analyzer import CallSite
from cryptoaudit.analysis.context_analyzer import is_credential_context
from cryptoaudit.models.analysis import RuleConfig
from cryptoaudit.models.enums import Confidence
from cryptoaudit.models.finding import Finding
from cryptoaudit.rules.base import BaseRule


class CR1Rule(BaseRule):
    """Detects weak hash functions (MD5, SHA1) in credential/password storage contexts."""

    def __init__(self, config: RuleConfig) -> None:
        super().__init__(config)
        self.targeted_apis = set(config.targeted_apis or ["hashlib.md5", "hashlib.sha1"])

    def evaluate(self, call_site: CallSite, parse_result: ASTParseResult) -> List[Finding]:
        findings: List[Finding] = []

        if call_site.resolved_name in self.targeted_apis:
            source_line = parse_result.get_line_content(call_site.lineno)
            if is_credential_context(call_site, source_line, self.config.context_keywords):
                evidence_line = source_line.strip()
                finding = Finding(
                    rule_id=self.config.rule_id,
                    category=self.config.category,
                    severity=self.config.severity,
                    confidence=Confidence.HIGH,
                    file=parse_result.file_path,
                    line=call_site.lineno,
                    column=call_site.col_offset,
                    matched_api=call_site.resolved_name,
                    evidence=evidence_line,
                    explanation=(
                        f"Use of weak hash function '{call_site.resolved_name}' "
                        f"detected in credential/password storage context."
                    ),
                    remediation=self.config.remediation,
                    analyzer_version="0.1.0",
                    rule_version=self.config.rule_version,
                )
                findings.append(finding)

        return findings
