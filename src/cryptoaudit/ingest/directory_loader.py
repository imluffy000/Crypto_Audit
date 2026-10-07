"""Directory ingestion: deterministic discovery of Python files."""

from pathlib import Path
from typing import Iterator, Union

from cryptoaudit.ingest.filters import EXCLUDED_DIRS
from cryptoaudit.utils.errors import CryptoAuditError, ErrorCode


def iter_python_files(directory: Union[str, Path]) -> Iterator[Path]:
    """Deterministically yield .py files under directory, skipping virtualenvs, VCS and build output."""
    root = Path(directory)
    if not root.is_dir():
        raise CryptoAuditError(ErrorCode.INVALID_INPUT, f"Not a directory: {root}")
    for path in sorted(root.rglob("*.py")):
        if not any(part in EXCLUDED_DIRS for part in path.relative_to(root).parts[:-1]):
            yield path
