"""Validation pipeline: runs V0-V3 independently of any claim made by the repair strategy."""

from typing import Optional, Sequence

from cryptoaudit.benchmark.oracle import HiddenOracle
from cryptoaudit.candidate.models import Candidate
from cryptoaudit.validation.gates import OracleGate, ScannerValidator, interface_check
from cryptoaudit.validation.models import CheckResult, GateId, GateResult, GateStatus, ValidationReport
from cryptoaudit.validation.sandbox import Sandbox


class ValidationPipeline:
    def __init__(self, sandbox: Sandbox, scanner_validator: ScannerValidator) -> None:
        self.sandbox = sandbox
        self.scanner_validator = scanner_validator

    def validate(
        self,
        candidate: Candidate,
        original_source: str,
        target_rules: Sequence[str],
        oracle: Optional[HiddenOracle] = None,
        functional_checks=None,
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

        code = candidate.code or ""
        artifacts = oracle.artifacts_dir if oracle else None
        gates = []

        if candidate.integrity is not None and candidate.integrity.syntax_ok:
            gates.append(self.scanner_validator.validate(code, candidate.module_name, target_rules))
        else:
            gates.append(GateResult(gate=GateId.V0, status=GateStatus.NOT_RUN, gating=False, summary="Candidate does not parse"))

        syntax = CheckResult(
            name="syntax_valid",
            status=GateStatus.PASS if candidate.integrity and candidate.integrity.syntax_ok else GateStatus.FAIL,
        )
        pre_checks = [syntax] + ([interface_check(original_source, code)] if syntax.status is GateStatus.PASS else [])
        v1_file = oracle.check_file("V1") if oracle else functional_checks
        gates.append(OracleGate(GateId.V1, self.sandbox).run(candidate, v1_file, artifacts, True, pre_checks))

        gates.append(OracleGate(GateId.V2, self.sandbox).run(candidate, oracle.check_file("V2") if oracle else None, artifacts))

        if oracle is not None and not oracle.v3.applicable:
            gates.append(
                GateResult(gate=GateId.V3, status=GateStatus.NOT_APPLICABLE, gating=False, summary="No persisted legacy artifacts for this case")
            )
        else:
            gating = bool(oracle and oracle.v3.gating)
            gates.append(
                OracleGate(GateId.V3, self.sandbox).run(candidate, oracle.check_file("V3") if oracle else None, artifacts, gating)
            )
        return ValidationReport(candidate_id=candidate.candidate_id, gates=gates)
