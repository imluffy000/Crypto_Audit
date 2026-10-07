"""Analysis models: rule configuration and the per-file analysis result."""

from typing import Any, List, Optional

from pydantic import BaseModel, Field

from cryptoaudit.models.enums import Category, Severity
from cryptoaudit.models.finding import Finding


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
