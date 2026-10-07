"""
Hidden oracle access. VALIDATION-ONLY.

Only cryptoaudit.validation and the pipeline's validation wiring may import this module;
repair strategies, prompting and the context engine must never see its contents.
An import-boundary test enforces this.
"""

from pathlib import Path
from typing import Dict, Optional

import yaml
from pydantic import BaseModel, ConfigDict

from cryptoaudit.ingest.benchmark_loader import HIDDEN_DIR, BenchmarkRepository
from cryptoaudit.utils.errors import CryptoAuditError, ErrorCode


class V3Policy(BaseModel):
    model_config = ConfigDict(frozen=True)

    applicable: bool = False
    gating: bool = False


class HiddenOracle(BaseModel):
    """Paths to hidden check files and artifacts for one case."""

    model_config = ConfigDict(frozen=True)

    case_id: str
    checks: Dict[str, Path]  # gate id ("V1"/"V2"/"V3") -> check file
    artifacts_dir: Optional[Path] = None
    v3: V3Policy = V3Policy()

    def check_file(self, gate: str) -> Optional[Path]:
        return self.checks.get(gate)


def load_oracle(repository: BenchmarkRepository, case_id: str) -> HiddenOracle:
    hidden = repository.case_dir(case_id) / HIDDEN_DIR
    spec_path = hidden / "oracle.yaml"
    if not spec_path.is_file():
        raise CryptoAuditError(ErrorCode.VALIDATION_ERROR, f"No hidden oracle for case {case_id}")
    data = yaml.safe_load(spec_path.read_text(encoding="utf-8")) or {}
    checks: Dict[str, Path] = {}
    for gate, filename in (data.get("checks") or {}).items():
        path = (hidden / filename).resolve()
        if path.parent != hidden.resolve() or not path.is_file():
            raise CryptoAuditError(ErrorCode.VALIDATION_ERROR, f"Oracle check file missing for {case_id}/{gate}")
        checks[str(gate)] = path
    artifacts = hidden / "artifacts"
    return HiddenOracle(
        case_id=case_id,
        checks=checks,
        artifacts_dir=artifacts if artifacts.is_dir() else None,
        v3=V3Policy(**(data.get("v3") or {})),
    )
