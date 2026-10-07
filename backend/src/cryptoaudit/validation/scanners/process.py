"""Subprocess helpers for running external scanners on a temporary copy of the source."""

import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional


@dataclass
class ToolRun:
    returncode: int
    stdout: str
    stderr: str


class ToolError(RuntimeError):
    pass


def resolve_executable(executable: str) -> Optional[str]:
    return shutil.which(executable)


def run_tool(command: List[str], timeout: float, cwd: Optional[Path] = None) -> ToolRun:
    try:
        proc = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            cwd=cwd,
            shell=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise ToolError(f"{Path(command[0]).name} timed out after {timeout}s") from exc
    except OSError as exc:
        raise ToolError(f"{Path(command[0]).name} failed to start: {exc}") from exc
    return ToolRun(proc.returncode, proc.stdout, proc.stderr)


class TemporarySource:
    """Writes source to a private temporary directory without newline translation."""

    def __init__(self, source: str, filename: str) -> None:
        self.source = source
        self.filename = Path(filename).name or "module.py"
        self._dir: Optional[tempfile.TemporaryDirectory] = None
        self.path: Path

    def __enter__(self) -> "TemporarySource":
        self._dir = tempfile.TemporaryDirectory(prefix="cryptoaudit-scan-")
        self.path = Path(self._dir.name) / self.filename
        with open(self.path, "w", encoding="utf-8", newline="") as handle:
            handle.write(self.source)
        return self

    def __exit__(self, *exc_info: object) -> None:
        if self._dir is not None:
            self._dir.cleanup()
