"""Input ingestion for user files, directories and benchmark cases."""

from pathlib import Path
from typing import Iterator, Sequence, Union

from cryptoaudit.benchmark.models import PublicCase
from cryptoaudit.ingest.models import ModuleInput
from cryptoaudit.utils.errors import CryptoAuditError, ErrorCode

MAX_SOURCE_BYTES = 1_000_000
EXCLUDED_DIRS = frozenset({".git", ".venv", "venv", "env", "node_modules", "__pycache__", "build", "dist", ".tox", ".mypy_cache"})


def load_module(
    path: Union[str, Path],
    allowed_libraries: Sequence[str] = (),
    target_python: str = "3.11",
    max_bytes: int = MAX_SOURCE_BYTES,
) -> ModuleInput:
    file = Path(path)
    if not file.is_file():
        raise CryptoAuditError(ErrorCode.INVALID_INPUT, f"Not a file: {file}")
    if file.suffix != ".py":
        raise CryptoAuditError(ErrorCode.INVALID_INPUT, f"Only Python source files are supported: {file.name}")
    size = file.stat().st_size
    if size > max_bytes:
        raise CryptoAuditError(ErrorCode.INVALID_INPUT, f"{file.name} is {size} bytes; limit is {max_bytes}")
    try:
        source = file.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise CryptoAuditError(ErrorCode.INVALID_INPUT, f"{file.name} is not valid UTF-8") from exc
    return ModuleInput(
        module_name=file.name,
        source=source,
        allowed_libraries=tuple(allowed_libraries),
        target_python=target_python,
    )


def iter_python_files(directory: Union[str, Path]) -> Iterator[Path]:
    """Deterministically yield .py files under directory, skipping virtualenvs, VCS and build output."""
    root = Path(directory)
    if not root.is_dir():
        raise CryptoAuditError(ErrorCode.INVALID_INPUT, f"Not a directory: {root}")
    for path in sorted(root.rglob("*.py")):
        if not any(part in EXCLUDED_DIRS for part in path.relative_to(root).parts[:-1]):
            yield path


def from_public_case(case: PublicCase) -> ModuleInput:
    return ModuleInput(
        module_name=case.module_name,
        source=case.source,
        case_id=case.case_id,
        allowed_libraries=case.spec.allowed_libraries,
        target_python=case.spec.target_python,
    )
