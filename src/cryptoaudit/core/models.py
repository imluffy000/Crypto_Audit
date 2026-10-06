"""Pydantic domain models for CryptoAudit analysis and findings."""

from typing import Any, List, Optional
from pydantic import BaseModel, Field

from cryptoaudit.core.enums import Category, Confidence, Severity


class Location(BaseModel):
    """Source code location of a finding."""

    file: str
    line: int
    column: Optional[int] = None


class Finding(BaseModel):
    """Cryptographic misuse finding reported by CryptoAudit."""

    rule_id: str
    category: Category
    severity: Severity
    confidence: Confidence = Confidence.HIGH
    file: str
    line: int
    column: Optional[int] = None
    matched_api: str
    evidence: str
    explanation: str
    remediation: str
    analyzer_version: str = "0.1.0"
    rule_version: str = "1.0.0"


class RuleConfig(BaseModel):
    """Machine-readable configuration schema for an audit rule."""

    rule_id: str
    name: str
    category: Category
    severity: Severity
    description: str
    rule_version: str = "1.0.0"
    targeted_apis: List[str] = Field(default_factory=list)
    weak_algorithms: List[str] = Field(default_factory=list)
    context_keywords: List[str] = Field(default_factory=list)
    min_iterations: Optional[int] = None
    remediation: str


class AnalysisResult(BaseModel):
    """Aggregated analysis report for a source file."""

    target_file: str
    findings: List[Finding] = Field(default_factory=list)
    total_findings: int = 0
    analyzer_version: str = "0.1.0"

    def model_post_init(self, __context: Any) -> None:
        self.total_findings = len(self.findings)
