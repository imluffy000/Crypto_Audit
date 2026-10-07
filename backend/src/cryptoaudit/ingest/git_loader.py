"""
Remote repository ingestion. Python sources are read from the GitHub tarball in memory:
nothing from the archive is written to disk and nothing is executed.
"""

import io
import tarfile

from cryptoaudit.ingest.filters import SnapshotLimits, is_excluded, safe_relative_path
from cryptoaudit.ingest.github_client import GitHubClient
from cryptoaudit.models.scan import ModuleInput, RepositorySnapshot, SkippedFile
from cryptoaudit.utils.errors import CryptoAuditError, ErrorCode


def read_python_modules(archive: bytes, limits: SnapshotLimits) -> RepositorySnapshot:
    """Extract .py files from a GitHub tarball (top-level 'owner-repo-sha/' directory is stripped)."""
    snapshot = RepositorySnapshot(full_name="", ref="", archive_bytes=len(archive))
    unpacked = 0
    try:
        with tarfile.open(fileobj=io.BytesIO(archive), mode="r:*") as tar:
            for member in tar:
                unpacked += max(member.size, 0)
                if unpacked > limits.max_unpacked_bytes:
                    raise CryptoAuditError(ErrorCode.LIMIT_EXCEEDED, "Repository archive expands beyond the size limit")
                parts = member.name.split("/", 1)
                if snapshot.commit is None and parts and "-" in parts[0]:
                    snapshot.commit = parts[0].rsplit("-", 1)[-1]
                if len(parts) < 2 or not parts[1]:
                    continue
                relative = safe_relative_path(parts[1])
                if relative is None:
                    snapshot.skipped.append(SkippedFile(path=parts[1][:200], reason="unsafe path"))
                    continue
                if not relative.endswith(".py"):
                    continue
                if not member.isfile():
                    snapshot.skipped.append(SkippedFile(path=relative, reason="not a regular file"))
                    continue
                if is_excluded(relative):
                    continue
                if member.size > limits.max_file_bytes:
                    snapshot.skipped.append(SkippedFile(path=relative, reason="file too large"))
                    continue
                if len(snapshot.modules) >= limits.max_python_files:
                    snapshot.skipped.append(SkippedFile(path=relative, reason="file count limit reached"))
                    continue
                handle = tar.extractfile(member)
                raw = handle.read(limits.max_file_bytes + 1) if handle else b""
                try:
                    source = raw.decode("utf-8")
                except UnicodeDecodeError:
                    snapshot.skipped.append(SkippedFile(path=relative, reason="not UTF-8"))
                    continue
                snapshot.modules.append(ModuleInput(module_name=relative, source=source))
    except tarfile.TarError as exc:
        raise CryptoAuditError(ErrorCode.INVALID_INPUT, f"Repository archive is not a valid tarball: {exc}") from exc
    snapshot.modules.sort(key=lambda m: m.module_name)
    return snapshot


def fetch_repository(client: GitHubClient, owner: str, name: str, ref: str, limits: SnapshotLimits) -> RepositorySnapshot:
    archive = client.download_tarball(owner, name, ref, limits.max_download_bytes)
    snapshot = read_python_modules(archive, limits)
    return snapshot.model_copy(update={"full_name": f"{owner}/{name}", "ref": ref})
