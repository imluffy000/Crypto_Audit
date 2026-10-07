"""CR3 Rule: Static or Reused IV / Nonce detection."""

import ast
from typing import List, Optional

from cryptoaudit.analysis.ast_parser import ASTParseResult
from cryptoaudit.analysis.call_analyzer import CallSite
from cryptoaudit.analysis.literals import resolve_scope_aware_constant
from cryptoaudit.models.analysis import RuleConfig
from cryptoaudit.models.enums import Confidence
from cryptoaudit.models.finding import Finding
from cryptoaudit.rules.base import BaseRule


class CR3Rule(BaseRule):
    """Detects static or hardcoded Initialization Vectors (IVs) or nonces."""

    def __init__(self, config: RuleConfig) -> None:
        super().__init__(config)

    def evaluate(self, call_site: CallSite, parse_result: ASTParseResult) -> List[Finding]:
        findings: List[Finding] = []
        resolved = call_site.resolved_name

        iv_node: Optional[ast.AST] = None
        param_kind = "IV"

        # 1. cryptography modes: modes.CBC(iv), modes.CTR(nonce), modes.GCM(nonce), modes.OFB(iv), modes.CFB(iv)
        if resolved.startswith("modes.") or resolved.startswith("cryptography.hazmat.primitives.ciphers.modes."):
            mode_name = resolved.split(".")[-1]
            if mode_name in ("CBC", "CTR", "GCM", "OFB", "CFB"):
                param_kind = "nonce" if mode_name in ("GCM", "CTR") else "IV"
                if call_site.args:
                    iv_node = call_site.args[0]
                elif "initialization_vector" in call_site.keywords:
                    iv_node = call_site.keywords["initialization_vector"]
                elif "nonce" in call_site.keywords:
                    iv_node = call_site.keywords["nonce"]

        # 2. PyCryptodome: AES.new(key, mode, iv=...) or AES.new(key, mode, nonce=...)
        elif resolved in ("AES.new", "Crypto.Cipher.AES.new"):
            if "iv" in call_site.keywords:
                iv_node = call_site.keywords["iv"]
                param_kind = "IV"
            elif "nonce" in call_site.keywords:
                iv_node = call_site.keywords["nonce"]
                param_kind = "nonce"
            elif len(call_site.args) >= 3:
                iv_node = call_site.args[2]
                param_kind = "IV / nonce"

        if iv_node is not None:
            is_static, _ = resolve_scope_aware_constant(iv_node, call_site, parse_result)
            if is_static:
                source_line = parse_result.get_line_content(call_site.lineno)
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
                        f"Static/constant {param_kind} detected in encryption call to '{resolved}'."
                    ),
                    remediation=self.config.remediation,
                    analyzer_version="0.1.0",
                    rule_version=self.config.rule_version,
                )
                findings.append(finding)

        return findings
