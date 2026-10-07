"""Validation runner: executes V0-V3 independently of any claim made by the repair strategy."""

from pathlib import Path
from typing import Optional, Sequence

from cryptoaudit.models.repair import Candidate
from cryptoaudit.models.validation import GateId, GateResult, GateStatus, ValidationReport
from cryptoaudit.validation.oracle import HiddenOracle
from cryptoaudit.validation.sandbox import Sandbox
from cryptoaudit.validation.v0_scanner import ScannerValidator
from cryptoaudit.validation.v1_functional import FunctionalValidator
from cryptoaudit.validation.v2_security import SecurityValidator
from cryptoaudit.validation.v3_compatibility import CompatibilityValidator


class ValidationPipeline:
    def __init__(self, sandbox: Sandbox, scanner_validator: ScannerValidator) -> None:
        self.sandbox = sandbox
        self.scanner_validator = scanner_validator
        self.functional = FunctionalValidator(sandbox)
        self.security = SecurityValidator(sandbox)
        self.compatibility = CompatibilityValidator(sandbox)

    def validate(
        self,
        candidate: Candidate,
        original_source: str,
        target_rules: Sequence[str],
        oracle: Optional[HiddenOracle] = None,
        functional_checks: Optional[Path] = None,
    ) -> ValidationReport:
        """
        Validate one candidate. `oracle` supplies hidden benchmark checks; for user code without an
        oracle, `functional_checks` may point at a user-supplied V1 check file. Gates without
        executable evidence are NOT_RUN, which can never yield acceptance.
        """
        if not candidate.repair.produced:
            return ValidationReport(
                candidate_id=candidate.candidate_id,
                gates=[
                    GateResult(gate=g, status=GateStatus.NOT_RUN, gating=g is not GateId.V0, summary="No candidate code")
                    for g in GateId
                ],
            )

        artifacts = oracle.artifacts_dir if oracle else None
        if candidate.integrity is not None and candidate.integrity.syntax_ok:
            v0 = self.scanner_validator.validate(candidate.code or "", candidate.module_name, target_rules)
        else:
            v0 = GateResult(gate=GateId.V0, status=GateStatus.NOT_RUN, gating=False, summary="Candidate does not parse")

        gates = [
            v0,
            self.functional.validate(
                candidate, original_source, oracle.check_file("V1") if oracle else functional_checks, artifacts
            ),
            self.security.validate(candidate, oracle.check_file("V2") if oracle else None, artifacts),
            self.compatibility.validate(candidate, oracle),
        ]
        return ValidationReport(candidate_id=candidate.candidate_id, gates=gates)
