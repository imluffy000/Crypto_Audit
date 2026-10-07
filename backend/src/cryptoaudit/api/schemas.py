"""API request/response schemas. Domain models are reused from cryptoaudit.models; these only shape responses."""

from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from cryptoaudit.models.experiment import Verdict
from cryptoaudit.models.finding import Finding
from cryptoaudit.models.scan import (
    RepositoryScanSummary,
    ScanStatus,
    SkippedFile,
    StageProgress,
    StrategyRunView,
)


class ErrorBody(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: ErrorBody


class HealthOut(BaseModel):
    status: str
    version: str
    github_configured: bool
    manage_access_url: Optional[str] = None
    repo_access: str = "private"
    llm_model: str
    llm_available: bool


class UserOut(BaseModel):
    id: int
    login: str
    name: Optional[str] = None
    email: Optional[str] = None
    avatar_url: Optional[str] = None


class RepoOut(BaseModel):
    id: int
    full_name: str
    owner: str
    name: str
    private: bool
    default_branch: str
    size_kb: int
    description: Optional[str] = None
    language: Optional[str] = None
    updated_at: Optional[str] = None


class TreeNode(BaseModel):
    name: str
    type: str  # "folder" | "file"
    size: Optional[int] = None
    ext: Optional[str] = None
    children: List["TreeNode"] = Field(default_factory=list)


class RepoTreeOut(BaseModel):
    repository: str
    ref: str
    tree: TreeNode
    files: int
    python_files: int
    total_size: int
    truncated: bool


class ScanCreate(BaseModel):
    owner: str
    name: str
    ref: Optional[str] = None


class ScanCreated(BaseModel):
    scan_id: str
    status: ScanStatus


class ScanOut(BaseModel):
    scan_id: str
    repository: str
    ref: str
    commit: Optional[str] = None
    status: ScanStatus
    stages: List[StageProgress]
    error: Optional[Dict[str, object]] = None
    created_at: str
    updated_at: str
    strategies: List[str] = Field(default_factory=list)
    skipped_strategies: Dict[str, str] = Field(default_factory=dict)
    skipped_files: List[SkippedFile] = Field(default_factory=list)
    summary: Optional[RepositoryScanSummary] = None


class FindingOut(BaseModel):
    finding_id: str
    finding: Finding
    best_verdict: Verdict
    verdicts: Dict[str, Verdict] = Field(default_factory=dict)


class StrategyRunOut(StrategyRunView):
    targets_finding: bool


class FindingDetailOut(BaseModel):
    scan_id: str
    repository: str
    finding_id: str
    finding: Finding
    best_verdict: Verdict
    file_path: str
    original_source: str
    file_findings: List[Finding]
    baseline: Dict[str, dict] = Field(default_factory=dict)
    runs: List[StrategyRunOut]
    ai_available: bool


class AIExplanationOut(BaseModel):
    candidate_id: str
    text: str
    disclaimer: str
    model: str
    prompt_id: str
    created_at: str
