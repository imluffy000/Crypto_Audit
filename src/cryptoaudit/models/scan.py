"""Scan models: pipeline input modules and normalised baseline-scanner reports."""

from typing import List, Optional, Protocol, Tuple

from pydantic import BaseModel, ConfigDict, Field


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
