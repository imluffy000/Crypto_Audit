"""Ingestion of benchmark cases. Public views only: never reads expected outcomes or hidden artifacts."""

from pathlib import Path
from typing import Dict, List, Optional

import yaml

from cryptoaudit.models.benchmark import CaseSpec, PublicCase
from cryptoaudit.models.scan import ModuleInput
from cryptoaudit.utils.errors import CryptoAuditError, ErrorCode

# benchmark/<role>/<rule>/<case_id>/ - only CASES_DIR is visible to the repair side.
CASES_DIR = "cases"
EXPECTED_DIR = "expected"
ARTIFACTS_DIR = "artifacts"
RESULTS_DIR = "results"
REPO_BENCHMARK_DIR = Path(__file__).resolve().parents[3] / "benchmark"


def resolve_benchmark_dir(benchmark_dir: Optional[Path] = None) -> Path:
    return Path(benchmark_dir) if benchmark_dir is not None else REPO_BENCHMARK_DIR


class BenchmarkRepository:
    """Discovers cases under benchmark/cases/<rule>/<case_id>/ (module + case.yaml)."""

    def __init__(self, benchmark_dir: Optional[Path] = None) -> None:
        self.root = resolve_benchmark_dir(benchmark_dir)
        self.cases_root = self.root / CASES_DIR
        if not self.cases_root.is_dir():
            raise CryptoAuditError(ErrorCode.INVALID_INPUT, f"Benchmark cases directory not found: {self.cases_root}")

    def _index(self) -> Dict[str, Path]:
        return {
            path.parent.name: path.parent
            for path in sorted(self.cases_root.glob("*/*/case.yaml"))
        }

    def case_ids(self) -> List[str]:
        return sorted(self._index())

    def case_dir(self, case_id: str) -> Path:
        path = self._index().get(case_id)
        if path is None:
            raise CryptoAuditError(ErrorCode.INVALID_INPUT, f"Unknown benchmark case: {case_id}")
        return path

    def rule_group(self, case_id: str) -> str:
        """The <rule> directory a case lives in (e.g. 'cr1'); mirrored under expected/ and artifacts/."""
        return self.case_dir(case_id).parent.name

    def public_case(self, case_id: str) -> PublicCase:
        case_dir = self.case_dir(case_id)
        data = yaml.safe_load((case_dir / "case.yaml").read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise CryptoAuditError(ErrorCode.INVALID_INPUT, f"Invalid case.yaml for {case_id}")
        spec = CaseSpec(**data)
        if spec.case_id != case_id:
            raise CryptoAuditError(ErrorCode.INVALID_INPUT, f"case.yaml id {spec.case_id!r} != directory {case_id!r}")
        if spec.rule_id.lower() != case_dir.parent.name:
            raise CryptoAuditError(
                ErrorCode.INVALID_INPUT, f"Case {case_id} is filed under {case_dir.parent.name}/ but targets {spec.rule_id}"
            )
        module_path = (case_dir / spec.module_file).resolve()
        if module_path.parent != case_dir.resolve() or not module_path.is_file():
            raise CryptoAuditError(ErrorCode.INVALID_INPUT, f"Module file must live in the case directory: {spec.module_file}")
        return PublicCase(spec=spec, source=module_path.read_text(encoding="utf-8"))

    def public_module_path(self, case_id: str) -> Path:
        return self.case_dir(case_id) / self.public_case(case_id).spec.module_file


def from_public_case(case: PublicCase) -> ModuleInput:
    return ModuleInput(
        module_name=case.module_name,
        source=case.source,
        case_id=case.case_id,
        allowed_libraries=case.spec.allowed_libraries,
        target_python=case.spec.target_python,
    )
