"""Pipeline input: one Python module plus its public configuration."""

from typing import Optional, Tuple

from pydantic import BaseModel, ConfigDict


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
