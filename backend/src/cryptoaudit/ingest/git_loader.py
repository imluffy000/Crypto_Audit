"""
Remote repository ingestion. The downloaded tarball is buffered in an anonymous temporary file
(so large repositories do not sit in memory); Python sources are read from it in memory. Nothing
from the archive is ever extracted to disk, and nothing is executed.

Python files inside .zip archives committed to the repository are read the same way (in memory,
one level deep, size-limited) and named ``<path/to/archive.zip>/<path inside the zip>``.
"""

import io
import tarfile
import tempfile
import zipfile
from typing import BinaryIO, Union

from cryptoaudit.ingest.filters import SnapshotLimits, is_excluded, safe_relative_path
from cryptoaudit.ingest.github_client import GitHubClient
from cryptoaudit.models.scan import ModuleInput, RepositorySnapshot, SkippedFile
from cryptoaudit.utils.errors import CryptoAuditError, ErrorCode

ARCHIVE_SUFFIXES = (".zip",)


class _Budget:
    """Running total of bytes the repository expands to, including .py files read from zip archives."""

    def __init__(self, limit: int) -> None:
        self.limit = limit
        self.used = 0

    def spend(self, size: int) -> None:
        self.used += max(size, 0)
        if self.used > self.limit:
            raise CryptoAuditError(ErrorCode.LIMIT_EXCEEDED, "Repository archive expands beyond the size limit")


def _add_module(snapshot: RepositorySnapshot, path: str, raw: bytes, limits: SnapshotLimits) -> None:
    if len(raw) > limits.max_file_bytes:  # declared sizes can lie; trust only what was read
        snapshot.skipped.append(SkippedFile(path=path, reason="file too large"))
        return
    try:
        source = raw.decode("utf-8")
    except UnicodeDecodeError:
        snapshot.skipped.append(SkippedFile(path=path, reason="not UTF-8"))
        return
    snapshot.modules.append(ModuleInput(module_name=path, source=source))


def _read_zip(
    snapshot: RepositorySnapshot, archive_path: str, data: bytes, limits: SnapshotLimits, budget: _Budget
) -> None:
    """Read .py members of one zip archive. Nested archives are not opened."""
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            for info in zf.infolist():
                if info.is_dir():
                    continue
                inner = safe_relative_path(info.filename)
                if inner is None:
                    unsafe = f"{archive_path}/{info.filename[:200]}"
                    snapshot.skipped.append(SkippedFile(path=unsafe, reason="unsafe path"))
                    continue
                path = f"{archive_path}/{inner}"
                if inner.endswith(ARCHIVE_SUFFIXES):
                    snapshot.skipped.append(SkippedFile(path=path, reason="nested archive not scanned"))
                    continue
                if not inner.endswith(".py") or is_excluded(inner):
                    continue
                if info.flag_bits & 0x1:
                    snapshot.skipped.append(SkippedFile(path=path, reason="encrypted archive member"))
                    continue
                if info.file_size > limits.max_file_bytes:
                    snapshot.skipped.append(SkippedFile(path=path, reason="file too large"))
                    continue
                if len(snapshot.modules) >= limits.max_python_files:
                    snapshot.skipped.append(SkippedFile(path=path, reason="file count limit reached"))
                    continue
                with zf.open(info) as handle:
                    raw = handle.read(limits.max_file_bytes + 1)
                budget.spend(len(raw))
                _add_module(snapshot, path, raw, limits)
    except (zipfile.BadZipFile, zipfile.LargeZipFile, NotImplementedError, EOFError, OSError) as exc:
        # NotImplementedError: unsupported compression method; OSError/EOFError: truncated or corrupt data
        snapshot.skipped.append(SkippedFile(path=archive_path, reason=f"unreadable zip archive ({type(exc).__name__})"))


def read_python_modules(archive: Union[bytes, BinaryIO], limits: SnapshotLimits) -> RepositorySnapshot:
    """Read .py files from a GitHub tarball (top-level 'owner-repo-sha/' directory is stripped)."""
    fileobj = io.BytesIO(archive) if isinstance(archive, (bytes, bytearray)) else archive
    fileobj.seek(0, io.SEEK_END)
    snapshot = RepositorySnapshot(full_name="", ref="", archive_bytes=fileobj.tell())
    fileobj.seek(0)
    budget = _Budget(limits.max_unpacked_bytes)
    try:
        with tarfile.open(fileobj=fileobj, mode="r:*") as tar:
            for member in tar:
                budget.spend(member.size)
                parts = member.name.split("/", 1)
                if snapshot.commit is None and parts and "-" in parts[0]:
                    snapshot.commit = parts[0].rsplit("-", 1)[-1]
                if len(parts) < 2 or not parts[1]:
                    continue
                relative = safe_relative_path(parts[1])
                if relative is None:
                    snapshot.skipped.append(SkippedFile(path=parts[1][:200], reason="unsafe path"))
                    continue
                is_archive = limits.scan_archives and relative.lower().endswith(ARCHIVE_SUFFIXES)
                if not relative.endswith(".py") and not is_archive:
                    continue
                if not member.isfile():
                    snapshot.skipped.append(SkippedFile(path=relative, reason="not a regular file"))
                    continue
                if is_excluded(relative):
                    continue
                if is_archive:
                    if member.size > limits.max_archive_bytes:
                        snapshot.skipped.append(SkippedFile(path=relative, reason="archive too large"))
                        continue
                    handle = tar.extractfile(member)
                    data = handle.read(limits.max_archive_bytes + 1) if handle else b""
                    _read_zip(snapshot, relative, data, limits, budget)
                    continue
                if member.size > limits.max_file_bytes:
                    snapshot.skipped.append(SkippedFile(path=relative, reason="file too large"))
                    continue
                if len(snapshot.modules) >= limits.max_python_files:
                    snapshot.skipped.append(SkippedFile(path=relative, reason="file count limit reached"))
                    continue
                handle = tar.extractfile(member)
                _add_module(snapshot, relative, handle.read(limits.max_file_bytes + 1) if handle else b"", limits)
    except tarfile.TarError as exc:
        raise CryptoAuditError(ErrorCode.INVALID_INPUT, f"Repository archive is not a valid tarball: {exc}") from exc
    snapshot.modules.sort(key=lambda m: m.module_name)
    return snapshot


def fetch_repository(client: GitHubClient, owner: str, name: str, ref: str, limits: SnapshotLimits) -> RepositorySnapshot:
    with tempfile.TemporaryFile(prefix="cryptoaudit-archive-") as archive:
        client.download_tarball_to(owner, name, ref, limits.max_download_bytes, archive)
        snapshot = read_python_modules(archive, limits)
    return snapshot.model_copy(update={"full_name": f"{owner}/{name}", "ref": ref})
