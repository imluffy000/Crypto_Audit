"""Input filters: size limits, excluded directories and safe repository-relative paths."""

import re
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Optional

MAX_SOURCE_BYTES = 1_000_000

EXCLUDED_DIRS = frozenset({".git", ".venv", "venv", "env", "node_modules", "__pycache__", "build", "dist", ".tox", ".mypy_cache"})

GITHUB_NAME = re.compile(r"^[A-Za-z0-9_.-]{1,100}$")
GIT_REF = re.compile(r"^[A-Za-z0-9._/-]{1,200}$")


@dataclass(frozen=True)
class SnapshotLimits:
    """Bounds for ingesting a remote repository."""

    max_download_bytes: int = 50 * 1024 * 1024  # compressed tarball
    max_unpacked_bytes: int = 500 * 1024 * 1024  # sum of all member sizes in the archive
    max_python_files: int = 500
    max_file_bytes: int = MAX_SOURCE_BYTES


def is_valid_github_name(value: str) -> bool:
    return bool(GITHUB_NAME.match(value)) and value not in {".", ".."}


def is_valid_ref(value: str) -> bool:
    return bool(GIT_REF.match(value)) and ".." not in value and not value.startswith("/")


def safe_relative_path(raw: str) -> Optional[str]:
    """Normalise an archive path to a safe POSIX relative path, or None if it escapes or is absolute."""
    if not raw or raw.startswith(("/", "\\")) or "\\" in raw or ":" in raw:
        return None
    parts = PurePosixPath(raw).parts
    if any(part in ("..", ".", "") for part in parts):
        return None
    return "/".join(parts)


def is_excluded(relative_path: str) -> bool:
    return any(part in EXCLUDED_DIRS for part in PurePosixPath(relative_path).parts[:-1])
