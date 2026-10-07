"""Repair Engine contract: request, result, statuses and strategy identifiers."""

from enum import Enum
from typing import List, Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field, model_validator

from cryptoaudit.context.models import CodeContext
from cryptoaudit.core.errors import ErrorCode
from cryptoaudit.core.models import Finding


class RepairStatus(str, Enum):
    """Outcome of a repair attempt. Only PRODUCED carries candidate code."""

    PRODUCED = "PRODUCED"
    NO_REPAIR = "NO_REPAIR"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    PARSE_ERROR = "PARSE_ERROR"


class StrategyId(str, Enum):
    S1 = "S1"  # Tool-guided / scanner-hint
    S2 = "S2"  # Deterministic template
    S3 = "S3"  # Local LLM
    S4 = "S4"  # Migration-aware LLM


class RepairConstraints(BaseModel):
    """Public repair constraints. Contains no benchmark-hidden information."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    allowed_libraries: Tuple[str, ...] = ()
    target_python: str = "3.11"
    preserve_public_interface: bool = True


class RepairRequest(BaseModel):
    """
    Everything a repair strategy may see.

    extra="forbid" makes it structurally impossible to attach oracle code,
    hidden artifacts, reference repairs or expected validation outcomes.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    module_name: str
    source: str
    findings: Tuple[Finding, ...] = Field(min_length=1)
    context: CodeContext
    constraints: RepairConstraints = RepairConstraints()


class GenerationMetadata(BaseModel):
    """Reproducibility metadata for LLM-based strategies."""

    model: str
    prompt_version: str
    prompt_hash: str
    temperature: float
    seed: int
    max_tokens: int
    raw_output: Optional[str] = None
    model_digest: Optional[str] = None


class RepairResult(BaseModel):
    """
    Candidate produced by a strategy. Candidate code is untrusted until validated:
    PRODUCED means "code was generated", never "repair is correct".
    """

    strategy_id: StrategyId
    status: RepairStatus
    candidate_code: Optional[str] = None
    repaired_finding_ids: List[str] = Field(default_factory=list)
    unrepaired_finding_ids: List[str] = Field(default_factory=list)
    failure_reason: Optional[str] = None
    error_code: Optional[ErrorCode] = None
    notes: List[str] = Field(default_factory=list)
    duration_seconds: float = 0.0
    generation: Optional[GenerationMetadata] = None

    @model_validator(mode="after")
    def _status_consistency(self) -> "RepairResult":
        if self.status is RepairStatus.PRODUCED:
            if not self.candidate_code or not self.candidate_code.strip():
                raise ValueError("PRODUCED results must carry candidate code")
        else:
            if self.candidate_code is not None:
                raise ValueError(f"{self.status.value} results must not carry candidate code")
            if not self.failure_reason:
                raise ValueError(f"{self.status.value} results must state a failure_reason")
        return self

    @property
    def produced(self) -> bool:
        return self.status is RepairStatus.PRODUCED
