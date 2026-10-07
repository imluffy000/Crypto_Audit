"""Context models: the bounded code context handed to the Repair Engine."""

from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

CONTEXT_VERSION = "1"


class SymbolSignature(BaseModel):
    """A public symbol of a module and its signature."""

    model_config = ConfigDict(frozen=True)

    qualified_name: str
    kind: str  # "function" | "class" | "method"
    signature: str
    lineno: int


class FindingContext(BaseModel):
    """Code surrounding a single finding."""

    model_config = ConfigDict(frozen=True)

    finding_id: str
    rule_id: str
    line: int
    enclosing_function: Optional[str] = None
    enclosing_class: Optional[str] = None
    function_source: Optional[str] = None
    referenced_constants: Dict[str, str] = Field(default_factory=dict)
    callers: List[str] = Field(default_factory=list)


class CodeContext(BaseModel):
    """
    Deterministic, bounded context for repairing one module.

    It is derived only from the module's own source text: no other files,
    no benchmark artifacts and no absolute paths are included.
    """

    model_config = ConfigDict(frozen=True)

    module_name: str
    imports: List[str] = Field(default_factory=list)
    public_interface: List[SymbolSignature] = Field(default_factory=list)
    findings: List[FindingContext] = Field(default_factory=list)
    truncated: bool = False
    context_version: str = CONTEXT_VERSION
    context_hash: str = ""
