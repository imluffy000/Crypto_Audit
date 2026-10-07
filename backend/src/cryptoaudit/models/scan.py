"""Scan models: pipeline input, repository snapshots, baseline-scanner reports and repository scan results."""

from enum import Enum
from typing import Dict, List, Optional, Protocol, Tuple

from pydantic import BaseModel, ConfigDict, Field

from cryptoaudit.models.experiment import Verdict
from cryptoaudit.models.explanation import Explanation
from cryptoaudit.models.finding import Finding
from cryptoaudit.models.repair import RepairStatus, StrategyId
from cryptoaudit.models.validation import GateResult, IntegrityReport


class ModuleInput(BaseModel):
    """
    A module to analyse and repair. Holds only public information: for benchmark cases this is
    the PublicCase content; hidden oracles are passed to validation separately.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    module_name: str
    source: str
    case_id: Optional[str] = None
    allowed_libraries: Tuple[str, ...] = ()
    target_python: str = "3.11"


class ScannerIssue(BaseModel):
    tool: str
    rule_id: str
    line: int
    end_line: Optional[int] = None
    message: str = ""
    severity: Optional[str] = None
    fix: Optional[str] = None  # machine-applicable replacement text, when the tool offers one
    start_offset: Optional[int] = None  # UTF-8 byte offsets of the fix span
    end_offset: Optional[int] = None


class ScanReport(BaseModel):
    """
    One scanner run. available=False means the tool could not run: that is
    never the same as "no issues found".
    """

    tool: str
    available: bool
    tool_version: Optional[str] = None
    config: Optional[str] = None
    issues: List[ScannerIssue] = Field(default_factory=list)
    error: Optional[str] = None

    @property
    def clean(self) -> Optional[bool]:
        return None if not self.available else not self.issues


class Scanner(Protocol):
    name: str

    def scan_source(self, source: str, filename: str = "module.py") -> ScanReport: ...


class SkippedFile(BaseModel):
    path: str
    reason: str


class RepositorySnapshot(BaseModel):
    full_name: str
    ref: str
    commit: Optional[str] = None
    modules: List[ModuleInput] = Field(default_factory=list)
    skipped: List[SkippedFile] = Field(default_factory=list)
    archive_bytes: int = 0


class ScanStage(str, Enum):
    """Stages of a repository scan, in execution order."""

    FETCH = "FETCH"
    PARSE = "PARSE"
    ANALYZE = "ANALYZE"
    CONTEXT = "CONTEXT"
    REPAIR = "REPAIR"
    VALIDATE = "VALIDATE"
    EXPLAIN = "EXPLAIN"
    REPORT = "REPORT"


STAGE_LABELS = {
    ScanStage.FETCH: "Fetching repository",
    ScanStage.PARSE: "Parsing Python files",
    ScanStage.ANALYZE: "Cryptographic rule analysis (CR1-CR5)",
    ScanStage.CONTEXT: "Building repair context",
    ScanStage.REPAIR: "Generating candidate repairs",
    ScanStage.VALIDATE: "Validating candidates (V0-V3)",
    ScanStage.EXPLAIN: "Comparing results and explaining why",
    ScanStage.REPORT: "Preparing the report",
}


class StageStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    DONE = "DONE"
    SKIPPED = "SKIPPED"
    FAILED = "FAILED"


class StageProgress(BaseModel):
    stage: ScanStage
    label: str
    status: StageStatus = StageStatus.PENDING
    detail: str = ""
    current: int = 0
    total: int = 0


class StrategyRunView(BaseModel):
    """One strategy's candidate for one file, with validation evidence and explanation."""

    strategy_id: StrategyId
    candidate_id: str
    repair_status: RepairStatus
    failure_reason: Optional[str] = None
    verdict: Verdict
    reasons: List[str] = Field(default_factory=list)
    candidate_code: Optional[str] = None
    diff: str = ""
    gates: List[GateResult] = Field(default_factory=list)
    scanner_results: Dict[str, Optional[bool]] = Field(default_factory=dict)
    integrity: Optional[IntegrityReport] = None
    repaired_finding_ids: List[str] = Field(default_factory=list)
    unrepaired_finding_ids: List[str] = Field(default_factory=list)
    explanation: Explanation


class FindingView(BaseModel):
    """A Finding (the Analyzer's canonical model) plus its ID and best verdict across strategies."""

    finding_id: str
    finding: Finding
    best_verdict: Verdict


class FileScanResult(BaseModel):
    path: str
    source: str
    finding_ids: List[str] = Field(default_factory=list)
    baseline: Dict[str, dict] = Field(default_factory=dict)  # scanner detection on the original file
    runs: List[StrategyRunView] = Field(default_factory=list)


class RepositoryScanSummary(BaseModel):
    files_scanned: int = 0
    files_with_findings: int = 0
    findings: int = 0
    findings_by_rule: Dict[str, int] = Field(default_factory=dict)
    verdicts_by_strategy: Dict[str, Dict[str, int]] = Field(default_factory=dict)
    scanner_clean_not_verified: int = 0


class RepositoryScanResult(BaseModel):
    repository: str
    ref: str
    commit: Optional[str] = None
    strategies: List[StrategyId] = Field(default_factory=list)
    skipped_strategies: Dict[str, str] = Field(default_factory=dict)
    skipped_files: List[SkippedFile] = Field(default_factory=list)
    findings: List[FindingView] = Field(default_factory=list)
    files: List[FileScanResult] = Field(default_factory=list)
    summary: RepositoryScanSummary = Field(default_factory=RepositoryScanSummary)


class ScanStatus(str, Enum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class ScanRecord(BaseModel):
    """A website scan job as stored by the web store."""

    scan_id: str
    repository: str
    ref: str
    status: ScanStatus
    stages: List[StageProgress] = Field(default_factory=list)
    error: Optional[Dict[str, object]] = None
    result: Optional[RepositoryScanResult] = None
    created_at: str
    updated_at: str
