"""Shared execution of hidden check files (V1-V3) inside the sandbox."""

import time
from pathlib import Path
from typing import List, Optional

from cryptoaudit.models.repair import Candidate
from cryptoaudit.models.validation import CheckResult, GateId, GateResult, GateStatus
from cryptoaudit.validation.sandbox import Sandbox


class OracleGate:
    """Runs a hidden check file for one gate inside the sandbox."""

    def __init__(self, gate: GateId, sandbox: Sandbox) -> None:
        self.gate = gate
        self.sandbox = sandbox

    def run(
        self,
        candidate: Candidate,
        check_file: Optional[Path],
        artifacts_dir: Optional[Path],
        gating: bool = True,
        pre_checks: Optional[List[CheckResult]] = None,
    ) -> GateResult:
        started = time.perf_counter()
        checks = list(pre_checks or [])
        static_failed = any(c.status is GateStatus.FAIL for c in checks)

        def result(status: GateStatus, summary: str, **extra) -> GateResult:
            return GateResult(
                gate=self.gate, status=status, gating=gating, summary=summary, checks=checks,
                duration_seconds=round(time.perf_counter() - started, 3), **extra,
            )

        if not candidate.repair.produced:
            return result(GateStatus.NOT_RUN, "No candidate code to validate")
        if not candidate.executable:
            issues = "; ".join(i.message for i in (candidate.integrity.issues if candidate.integrity else []))
            status = GateStatus.FAIL if static_failed or self.gate is GateId.V1 else GateStatus.NOT_RUN
            return result(status, f"Not executed: integrity checks failed ({issues})")
        if check_file is None:
            if static_failed:
                return result(GateStatus.FAIL, "Static checks failed; no executable oracle available")
            if checks:
                passed = ", ".join(c.name for c in checks)
                return result(GateStatus.NOT_RUN, f"Static checks passed ({passed}); no executable oracle for this gate")
            return result(GateStatus.NOT_RUN, "No oracle checks available for this gate")

        run = self.sandbox.run_checks(candidate.code or "", check_file, artifacts_dir)
        checks.extend(run.checks)
        evidence = {"sandbox": self.sandbox.name, "sandbox_seconds": run.duration_seconds}
        if run.error is not None and not run.timed_out:
            return result(GateStatus.ERROR, f"Validator could not evaluate: {run.error}", error_code=run.error_code, evidence=evidence)
        if run.timed_out:
            checks.append(CheckResult(name="completes_within_limits", status=GateStatus.FAIL, message=run.error or "timeout"))
            return result(GateStatus.FAIL, "Candidate exceeded execution limits", error_code=run.error_code, evidence=evidence)
        failed = [c.name for c in checks if c.status is not GateStatus.PASS]
        if failed:
            return result(GateStatus.FAIL, f"{len(failed)}/{len(checks)} checks failed: {', '.join(failed)}", evidence=evidence)
        return result(GateStatus.PASS, f"All {len(checks)} checks passed", evidence=evidence)
