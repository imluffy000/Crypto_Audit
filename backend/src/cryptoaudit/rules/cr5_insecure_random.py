"""CR5 Rule: Weak Randomness for Security-Sensitive Tokens detection."""

from typing import List, Set

from cryptoaudit.analysis.ast_parser import ASTParseResult
from cryptoaudit.analysis.call_analyzer import CallSite
from cryptoaudit.models.analysis import RuleConfig
from cryptoaudit.models.enums import Confidence
from cryptoaudit.models.finding import Finding
from cryptoaudit.rules.base import BaseRule

RANDOM_MODULE_APIS = {
    "random.random",
    "random.randint",
    "random.randrange",
    "random.choice",
    "random.choices",
    "random.sample",
    "random.getrandbits",
}

DEFAULT_TOKEN_KEYWORDS = {
    "token",
    "session",
    "secret",
    "api_key",
    "auth",
    "password_reset",
    "reset_code",
    "security_code",
    "verification_code",
    "auth_token",
    "user_token",
}


class CR5Rule(BaseRule):
    """Detects standard pseudo-random number generators (random module) used for security tokens."""

    def __init__(self, config: RuleConfig) -> None:
        super().__init__(config)
        self.context_keywords = set(
            k.lower() for k in (config.context_keywords or DEFAULT_TOKEN_KEYWORDS)
        )

    def _is_security_context(self, call_site: CallSite, source_line: str) -> bool:
        """Evaluate whether call site occurs within a security token or secret generation context."""
        identifiers: Set[str] = set()

        if call_site.assigned_variable:
            identifiers.add(call_site.assigned_variable.lower())

        if call_site.enclosing_function:
            identifiers.add(call_site.enclosing_function.lower())

        if call_site.enclosing_class:
            identifiers.add(call_site.enclosing_class.lower())

        line_lower = source_line.lower()

        for kw in self.context_keywords:
            if any(kw in ident for ident in identifiers) or kw in line_lower:
                return True

        return False

    def evaluate(self, call_site: CallSite, parse_result: ASTParseResult) -> List[Finding]:
        findings: List[Finding] = []
        resolved = call_site.resolved_name

        if resolved in RANDOM_MODULE_APIS or resolved.startswith("random."):
            source_line = parse_result.get_line_content(call_site.lineno)

            if self._is_security_context(call_site, source_line):
                finding = Finding(
                    rule_id=self.config.rule_id,
                    category=self.config.category,
                    severity=self.config.severity,
                    confidence=Confidence.HIGH,
                    file=parse_result.file_path,
                    line=call_site.lineno,
                    column=call_site.col_offset,
                    matched_api=resolved,
                    evidence=source_line.strip(),
                    explanation=(
                        f"Use of non-cryptographic PRNG '{resolved}' detected for generating "
                        f"security-sensitive token or secret."
                    ),
                    remediation=self.config.remediation,
                    analyzer_version="0.1.0",
                    rule_version=self.config.rule_version,
                )
                findings.append(finding)

        return findings
