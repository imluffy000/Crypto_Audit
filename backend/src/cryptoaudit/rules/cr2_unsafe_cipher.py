"""CR2 Rule: Weak or Unauthenticated Encryption Mode (ECB mode detection)."""

import ast
from typing import List

from cryptoaudit.analysis.ast_parser import ASTParseResult
from cryptoaudit.analysis.call_analyzer import CallSite
from cryptoaudit.models.analysis import RuleConfig
from cryptoaudit.models.enums import Confidence
from cryptoaudit.models.finding import Finding
from cryptoaudit.rules.base import BaseRule


class CR2Rule(BaseRule):
    """Detects explicit Electronic Codebook (ECB) mode encryption misuse."""

    def __init__(self, config: RuleConfig) -> None:
        super().__init__(config)

    def evaluate(self, call_site: CallSite, parse_result: ASTParseResult) -> List[Finding]:
        findings: List[Finding] = []
        resolved = call_site.resolved_name

        is_ecb = False
        matched_api = resolved

        # 1. cryptography library: modes.ECB() or cryptography.hazmat.primitives.ciphers.modes.ECB()
        if resolved in ("modes.ECB", "cryptography.hazmat.primitives.ciphers.modes.ECB"):
            is_ecb = True
            matched_api = resolved

        # 2. PyCryptodome / Crypto.Cipher.AES.new(key, AES.MODE_ECB)
        elif resolved in ("AES.new", "Crypto.Cipher.AES.new"):
            # Check positional args or keyword arg 'mode'
            mode_arg = call_site.keywords.get("mode")
            if mode_arg is None and len(call_site.args) >= 2:
                mode_arg = call_site.args[1]

            if mode_arg is not None:
                if isinstance(mode_arg, ast.Attribute) and mode_arg.attr == "MODE_ECB":
                    is_ecb = True
                    matched_api = f"{resolved}(..., {mode_arg.attr})"
                elif isinstance(mode_arg, ast.Name) and mode_arg.id == "MODE_ECB":
                    is_ecb = True
                    matched_api = f"{resolved}(..., {mode_arg.id})"
                elif isinstance(mode_arg, ast.Constant) and mode_arg.value == 1:
                    is_ecb = True
                    matched_api = f"{resolved}(..., MODE_ECB)"

        if is_ecb:
            source_line = parse_result.get_line_content(call_site.lineno)
            finding = Finding(
                rule_id=self.config.rule_id,
                category=self.config.category,
                severity=self.config.severity,
                confidence=Confidence.HIGH,
                file=parse_result.file_path,
                line=call_site.lineno,
                column=call_site.col_offset,
                matched_api=matched_api,
                evidence=source_line.strip(),
                explanation=(
                    f"Use of insecure Electronic Codebook (ECB) encryption mode "
                    f"detected in call to '{matched_api}'."
                ),
                remediation=self.config.remediation,
                analyzer_version="0.1.0",
                rule_version=self.config.rule_version,
            )
            findings.append(finding)

        return findings
