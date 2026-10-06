"""CR4 Rule: Weak KDF Parameters or Static Salt detection."""

import ast
from typing import List, Optional

from cryptoaudit.analyzer.ast_parser import ASTParseResult
from cryptoaudit.analyzer.calls import CallSite
from cryptoaudit.analyzer.literals import get_literal_value, resolve_scope_aware_constant
from cryptoaudit.analyzer.rules.base import BaseRule
from cryptoaudit.core.enums import Confidence
from cryptoaudit.core.models import Finding, RuleConfig


class CR4Rule(BaseRule):
    """Detects weak KDF iteration counts, static hardcoded salts, or fast hash direct key derivation."""

    def __init__(self, config: RuleConfig) -> None:
        super().__init__(config)
        self.min_iterations = config.min_iterations or 600000

    def evaluate(self, call_site: CallSite, parse_result: ASTParseResult) -> List[Finding]:
        findings: List[Finding] = []
        resolved = call_site.resolved_name

        # 1. PBKDF2 APIs (hashlib.pbkdf2_hmac, PBKDF2HMAC)
        if "pbkdf2" in resolved.lower() or "pbkdf2hmac" in resolved.lower():
            # Evaluate Salt parameter
            # Positional signatures:
            # hashlib.pbkdf2_hmac(hash_name, password, salt, iterations, ...) -> args[2] = salt
            # PBKDF2HMAC(algorithm, length, salt, iterations, ...)            -> args[2] = salt
            salt_node: Optional[ast.AST] = call_site.keywords.get("salt")
            if salt_node is None and len(call_site.args) >= 3:
                salt_node = call_site.args[2]

            if salt_node is not None:
                is_static, _ = resolve_scope_aware_constant(salt_node, call_site, parse_result)
                if is_static:
                    source_line = parse_result.get_line_content(call_site.lineno)
                    findings.append(
                        Finding(
                            rule_id=self.config.rule_id,
                            category=self.config.category,
                            severity=self.config.severity,
                            confidence=Confidence.HIGH,
                            file=parse_result.file_path,
                            line=call_site.lineno,
                            column=call_site.col_offset,
                            matched_api=resolved,
                            evidence=source_line.strip(),
                            explanation=f"Static hardcoded salt detected in call to '{resolved}'.",
                            remediation=self.config.remediation,
                            analyzer_version="0.1.0",
                            rule_version=self.config.rule_version,
                        )
                    )

            # Evaluate Iteration Count parameter against self.min_iterations (from cr4.yaml)
            # Positional signatures:
            # hashlib.pbkdf2_hmac(hash_name, password, salt, iterations, ...) -> args[3] = iterations
            # PBKDF2HMAC(algorithm, length, salt, iterations, ...)            -> args[3] = iterations
            iterations_node: Optional[ast.AST] = call_site.keywords.get("iterations")
            if iterations_node is None and len(call_site.args) >= 4:
                iterations_node = call_site.args[3]

            if iterations_node is not None:
                is_static_iter, iter_val = resolve_scope_aware_constant(iterations_node, call_site, parse_result)
                if is_static_iter and isinstance(iter_val, int) and iter_val < self.min_iterations:
                    source_line = parse_result.get_line_content(call_site.lineno)
                    findings.append(
                        Finding(
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
                                f"Weak PBKDF2 iteration count ({iter_val:,}) detected in '{resolved}'. "
                                f"Minimum policy threshold is {self.min_iterations:,} iterations."
                            ),
                            remediation=self.config.remediation,
                            analyzer_version="0.1.0",
                            rule_version=self.config.rule_version,
                        )
                    )

        # 2. Fast hash direct key derivation (e.g. key = hashlib.sha256(password.encode()).digest())
        elif resolved in ("hashlib.sha256", "hashlib.md5") and call_site.assigned_variable:
            var_lower = call_site.assigned_variable.lower()
            if "key" in var_lower or "derived" in var_lower:
                source_line = parse_result.get_line_content(call_site.lineno)
                # Strip comments from line before inspecting context keywords
                code_only = source_line.split("#")[0].strip().lower()
                if any(kw in code_only for kw in ("password", "passwd", "pwd", "secret")):
                    findings.append(
                        Finding(
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
                                f"Direct fast hash key derivation detected using '{resolved}' "
                                f"without a key derivation function (KDF)."
                            ),
                            remediation=self.config.remediation,
                            analyzer_version="0.1.0",
                            rule_version=self.config.rule_version,
                        )
                    )

        return findings
