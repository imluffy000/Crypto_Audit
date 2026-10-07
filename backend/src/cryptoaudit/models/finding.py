"""Finding: the canonical cryptographic misuse finding reported by the Analyzer."""

from typing import Optional

from pydantic import BaseModel

from cryptoaudit.models.enums import Category, Confidence, Severity
from cryptoaudit.utils.hashing import stable_hash


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


def finding_id(finding: Finding) -> str:
    """
    Deterministic identifier for a finding.

    Uses the same key the AnalyzerEngine deduplicates on, so two findings the
    engine treats as distinct (e.g. CR4 salt + iterations on one line) get distinct IDs.
    """
    key = [
        finding.file.replace("\\", "/"),
        finding.line,
        finding.column,
        finding.rule_id,
        finding.matched_api,
        finding.explanation,
    ]
    return "F-" + stable_hash(key)[:16]
