"""Candidate repaired code: a repair result plus integrity evidence. Untrusted until validated."""

import difflib
from typing import Optional

from pydantic import BaseModel

from cryptoaudit.candidate.integrity import IntegrityReport
from cryptoaudit.core.identity import stable_hash
from cryptoaudit.repair.models import RepairResult


class Candidate(BaseModel):
    candidate_id: str
    module_name: str
    repair: RepairResult
    integrity: Optional[IntegrityReport] = None  # None when no code was produced
    diff: str = ""

    @property
    def code(self) -> Optional[str]:
        return self.repair.candidate_code

    @property
    def executable(self) -> bool:
        """Only produced code that passed integrity checks may be executed by validation."""
        return self.repair.produced and self.integrity is not None and self.integrity.passed


def unified_diff(original: str, candidate: str, module_name: str) -> str:
    return "".join(
        difflib.unified_diff(
            original.splitlines(keepends=True),
            candidate.splitlines(keepends=True),
            fromfile=f"a/{module_name}",
            tofile=f"b/{module_name}",
        )
    )


def make_candidate(
    module_name: str, original_source: str, repair: RepairResult, integrity: Optional[IntegrityReport]
) -> Candidate:
    code = repair.candidate_code or ""
    return Candidate(
        candidate_id="C-" + stable_hash([module_name, repair.strategy_id.value, repair.status.value, code])[:16],
        module_name=module_name,
        repair=repair,
        integrity=integrity,
        diff=unified_diff(original_source, code, module_name) if repair.produced else "",
    )
