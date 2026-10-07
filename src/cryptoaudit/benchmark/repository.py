"""Public access to benchmark cases. Never reads anything under a case's hidden/ directory."""

from pathlib import Path
from typing import List, Optional

import yaml

from cryptoaudit.benchmark.models import CaseSpec, PublicCase
from cryptoaudit.utils.errors import CryptoAuditError, ErrorCode

PUBLIC_DIR = "public"
HIDDEN_DIR = "hidden"
REPO_BENCHMARK_DIR = Path(__file__).resolve().parents[3] / "benchmark" / "cases"


def resolve_benchmark_dir(cases_dir: Optional[Path] = None) -> Path:
    if cases_dir is not None:
        return Path(cases_dir)
    return REPO_BENCHMARK_DIR


class BenchmarkRepository:
    def __init__(self, cases_dir: Optional[Path] = None) -> None:
        self.cases_dir = resolve_benchmark_dir(cases_dir)
        if not self.cases_dir.is_dir():
            raise CryptoAuditError(ErrorCode.INVALID_INPUT, f"Benchmark directory not found: {self.cases_dir}")

    def case_ids(self) -> List[str]:
        return sorted(p.name for p in self.cases_dir.iterdir() if (p / PUBLIC_DIR / "case.yaml").is_file())

    def case_dir(self, case_id: str) -> Path:
        path = (self.cases_dir / case_id).resolve()
        if path.parent != self.cases_dir.resolve() or not (path / PUBLIC_DIR / "case.yaml").is_file():
            raise CryptoAuditError(ErrorCode.INVALID_INPUT, f"Unknown benchmark case: {case_id}")
        return path

    def public_case(self, case_id: str) -> PublicCase:
        public = self.case_dir(case_id) / PUBLIC_DIR
        data = yaml.safe_load((public / "case.yaml").read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise CryptoAuditError(ErrorCode.INVALID_INPUT, f"Invalid case.yaml for {case_id}")
        spec = CaseSpec(**data)
        if spec.case_id != case_id:
            raise CryptoAuditError(ErrorCode.INVALID_INPUT, f"case.yaml id {spec.case_id!r} != directory {case_id!r}")
        module_path = (public / spec.module_file).resolve()
        if module_path.parent != public.resolve() or not module_path.is_file():
            raise CryptoAuditError(ErrorCode.INVALID_INPUT, f"Module file must live in public/: {spec.module_file}")
        return PublicCase(spec=spec, source=module_path.read_text(encoding="utf-8"))

    def public_module_path(self, case_id: str) -> Path:
        case = self.public_case(case_id)
        return self.case_dir(case_id) / PUBLIC_DIR / case.spec.module_file
