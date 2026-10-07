"""File ingestion: load one Python module with its public configuration."""

from pathlib import Path
from typing import Sequence, Union

from cryptoaudit.ingest.filters import MAX_SOURCE_BYTES
from cryptoaudit.models.scan import ModuleInput
from cryptoaudit.utils.errors import CryptoAuditError, ErrorCode


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




