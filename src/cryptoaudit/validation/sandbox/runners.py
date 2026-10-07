"""
Sandboxed execution of candidate code against hidden checks.

DockerSandbox is the default isolation boundary (no network, CPU/memory/pids limits,
read-only filesystem, dropped capabilities, unprivileged user). LocalProcessSandbox runs
in a scrubbed child interpreter for development on trusted code only and must be opted
into explicitly.
"""

import json
import os
import secrets
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from cryptoaudit.utils.errors import CryptoAuditError, ErrorCode
from cryptoaudit.validation.models import CheckResult, GateStatus
from cryptoaudit.validation.sandbox import harness

HARNESS_SOURCE = Path(harness.__file__)
DEFAULT_TIMEOUT = 120.0
DEFAULT_SANDBOX_IMAGE = "cryptoaudit-sandbox:latest"


@dataclass
class ProcessOutcome:
    returncode: Optional[int]
    stdout: str
    stderr: str
    timed_out: bool = False
    launch_error: Optional[str] = None


@dataclass
class CheckRun:
    """Outcome of running one check file against one candidate."""

    checks: List[CheckResult] = field(default_factory=list)
    error: Optional[str] = None
    error_code: Optional[ErrorCode] = None
    timed_out: bool = False
    duration_seconds: float = 0.0

    @property
    def status(self) -> GateStatus:
        if self.timed_out:
            return GateStatus.FAIL  # a candidate that does not finish within limits fails behaviourally
        if self.error is not None:
            return GateStatus.ERROR
        if not self.checks:
            return GateStatus.ERROR
        return GateStatus.PASS if all(c.status is GateStatus.PASS for c in self.checks) else GateStatus.FAIL


class Sandbox(ABC):
    name = "sandbox"

    def __init__(self, timeout: float = DEFAULT_TIMEOUT) -> None:
        self.timeout = timeout

    def run_checks(self, candidate_code: str, check_file: Path, artifacts_dir: Optional[Path]) -> CheckRun:
        started = time.perf_counter()
        with tempfile.TemporaryDirectory(prefix="cryptoaudit-sbx-") as tmp:
            work = Path(tmp)
            with open(work / "candidate.py", "w", encoding="utf-8", newline="") as handle:
                handle.write(candidate_code)
            shutil.copyfile(HARNESS_SOURCE, work / "harness.py")
            shutil.copyfile(check_file, work / "checks.py")
            if artifacts_dir is not None and artifacts_dir.is_dir():
                shutil.copytree(artifacts_dir, work / "artifacts")
            else:
                (work / "artifacts").mkdir()
            argv = ["harness.py", "--candidate", "candidate.py", "--checks", "checks.py", "--artifacts", "artifacts"]
            nonce = secrets.token_hex(16)
            outcome = self._execute(work, argv, nonce)
        run = _parse_outcome(outcome, self.timeout, nonce)
        run.duration_seconds = round(time.perf_counter() - started, 3)
        return run

    @abstractmethod
    def _execute(self, work: Path, argv: List[str], nonce: str) -> ProcessOutcome:
        """Run `python <argv>` with work as the working directory and the result nonce in the environment."""


class LocalProcessSandbox(Sandbox):
    """
    Child interpreter in isolated mode with a scrubbed environment and a timeout.
    NOT an isolation boundary: no network or filesystem restriction on Windows.
    """

    name = "local"

    def __init__(self, timeout: float = DEFAULT_TIMEOUT, allow_unsafe: bool = False, python: Optional[str] = None) -> None:
        if not allow_unsafe:
            raise CryptoAuditError(
                ErrorCode.SANDBOX_ERROR,
                "LocalProcessSandbox does not isolate untrusted code; pass allow_unsafe=True only for trusted code",
            )
        super().__init__(timeout)
        self.python = python or sys.executable

    def _execute(self, work: Path, argv: List[str], nonce: str) -> ProcessOutcome:
        env = {
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONIOENCODING": "utf-8",
            "PYTHONHASHSEED": "0",
            harness.NONCE_ENV: nonce,
        }
        for key in ("SYSTEMROOT", "PATH", "TEMP", "TMP"):
            if key in os.environ:
                env[key] = os.environ[key]
        kwargs = {}
        if os.name == "posix":
            kwargs["preexec_fn"] = _posix_limits
        try:
            proc = subprocess.run(
                [self.python, "-I", "-B", *argv],
                cwd=work,
                env=env,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=self.timeout,
                **kwargs,
            )
        except subprocess.TimeoutExpired as exc:
            return ProcessOutcome(None, _text(exc.stdout), _text(exc.stderr), timed_out=True)
        except OSError as exc:
            return ProcessOutcome(None, "", "", launch_error=str(exc))
        return ProcessOutcome(proc.returncode, proc.stdout, proc.stderr)


class DockerSandbox(Sandbox):
    name = "docker"

    def __init__(
        self,
        image: str = DEFAULT_SANDBOX_IMAGE,
        timeout: float = DEFAULT_TIMEOUT,
        memory: str = "512m",
        cpus: str = "1",
        pids_limit: int = 64,
        docker: str = "docker",
    ) -> None:
        super().__init__(timeout)
        self.image = image
        self.memory = memory
        self.cpus = cpus
        self.pids_limit = pids_limit
        self.docker = docker

    def command(self, work: Path, argv: List[str], container_name: str, nonce: str = "") -> List[str]:
        return [
            self.docker, "run", "--rm", "--name", container_name,
            "--network", "none",
            "--memory", self.memory, "--memory-swap", self.memory,
            "--cpus", self.cpus,
            "--pids-limit", str(self.pids_limit),
            "--read-only", "--tmpfs", "/tmp:rw,size=64m",
            "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
            "--user", "65534:65534",
            "-e", "PYTHONDONTWRITEBYTECODE=1", "-e", "PYTHONHASHSEED=0", "-e", f"{harness.NONCE_ENV}={nonce}",
            "-v", f"{work.resolve()}:/work:ro", "-w", "/work",
            self.image, "python", "-I", "-B", *argv,
        ]

    def _execute(self, work: Path, argv: List[str], nonce: str) -> ProcessOutcome:
        if shutil.which(self.docker) is None:
            return ProcessOutcome(None, "", "", launch_error=f"'{self.docker}' not found on PATH")
        container = f"cryptoaudit-{uuid.uuid4().hex[:12]}"
        try:
            proc = subprocess.run(
                self.command(work, argv, container, nonce),
                capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=self.timeout + 30,
            )
        except subprocess.TimeoutExpired as exc:
            subprocess.run([self.docker, "kill", container], capture_output=True)
            return ProcessOutcome(None, _text(exc.stdout), _text(exc.stderr), timed_out=True)
        except OSError as exc:
            return ProcessOutcome(None, "", "", launch_error=str(exc))
        if proc.returncode == 125:  # docker itself failed (daemon down, image missing, bad flags)
            return ProcessOutcome(proc.returncode, proc.stdout, proc.stderr, launch_error=proc.stderr.strip()[:300])
        return ProcessOutcome(proc.returncode, proc.stdout, proc.stderr)


def _posix_limits() -> None:  # pragma: no cover - POSIX only
    import resource

    resource.setrlimit(resource.RLIMIT_AS, (1 << 30, 1 << 30))
    resource.setrlimit(resource.RLIMIT_CPU, (120, 120))
    resource.setrlimit(resource.RLIMIT_NPROC, (64, 64))


def _text(value: object) -> str:
    if value is None:
        return ""
    return value.decode("utf-8", errors="replace") if isinstance(value, bytes) else str(value)


def _parse_outcome(outcome: ProcessOutcome, timeout: float, nonce: str) -> CheckRun:
    if outcome.launch_error is not None:
        return CheckRun(error=f"sandbox failed to start: {outcome.launch_error}", error_code=ErrorCode.SANDBOX_ERROR)
    if outcome.timed_out:
        return CheckRun(error=f"execution exceeded {timeout}s", error_code=ErrorCode.TIMEOUT, timed_out=True)
    payload = None
    prefix = f"{harness.MARKER}{nonce}:"
    for line in reversed(outcome.stdout.splitlines()):
        if line.startswith(prefix):
            try:
                payload = json.loads(line[len(prefix):])
            except json.JSONDecodeError:
                payload = None
            break
    if payload is None:
        tail = (outcome.stderr or outcome.stdout).strip()[-400:]
        return CheckRun(
            error=f"harness produced no result (exit {outcome.returncode}): {tail}", error_code=ErrorCode.SANDBOX_ERROR
        )
    if payload.get("harness_error"):
        return CheckRun(error=payload["harness_error"], error_code=ErrorCode.VALIDATION_ERROR)
    checks = [
        CheckResult(name=r["name"], status=GateStatus(r["status"]), message=r.get("message", ""), duration=r.get("duration", 0.0))
        for r in payload.get("results", [])
    ]
    return CheckRun(checks=checks)
