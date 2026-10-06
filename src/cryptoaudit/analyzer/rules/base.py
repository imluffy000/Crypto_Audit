"""Abstract base class for CryptoAudit rules."""

from abc import ABC, abstractmethod
from typing import List

from cryptoaudit.analyzer.ast_parser import ASTParseResult
from cryptoaudit.analyzer.calls import CallSite
from cryptoaudit.core.models import Finding, RuleConfig


class BaseRule(ABC):
    """Base interface for all AST security audit rules."""

    def __init__(self, config: RuleConfig) -> None:
        self.config = config

    @property
    def rule_id(self) -> str:
        return self.config.rule_id

    @abstractmethod
    def evaluate(self, call_site: CallSite, parse_result: ASTParseResult) -> List[Finding]:
        """Evaluate a call site against this rule and return any generated findings."""
        pass
