"""Benchmark models. PublicCase is the only case view a repair strategy may receive."""

from typing import Tuple

from pydantic import BaseModel, ConfigDict


class CaseSpec(BaseModel):
    """Public metadata from public/case.yaml."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    case_id: str
    rule_id: str
    title: str
    description: str = ""
    module_file: str = "module.py"
    target_python: str = "3.11"
    allowed_libraries: Tuple[str, ...] = ()


class PublicCase(BaseModel):
    """Vulnerable module plus public metadata. Contains no oracle or hidden-artifact data."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    spec: CaseSpec
    source: str

    @property
    def case_id(self) -> str:
        return self.spec.case_id

    @property
    def module_name(self) -> str:
        return self.spec.module_file
