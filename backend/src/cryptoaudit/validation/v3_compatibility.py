"""V3 compatibility validation: legacy artifacts persisted by the original code must remain usable."""

from typing import Optional

from cryptoaudit.models.repair import Candidate
from cryptoaudit.models.validation import GateId, GateResult, GateStatus
from cryptoaudit.validation.checks import OracleGate
from cryptoaudit.validation.oracle import HiddenOracle
from cryptoaudit.validation.sandbox import Sandbox


class CompatibilityValidator:
    """Applies only where the case defines persisted legacy artifacts; otherwise NOT_APPLICABLE (never PASS)."""

    def __init__(self, sandbox: Sandbox) -> None:
        self.gate = OracleGate(GateId.V3, sandbox)

    def validate(self, candidate: Candidate, oracle: Optional[HiddenOracle]) -> GateResult:
        if oracle is not None and not oracle.v3.applicable:
            return GateResult(
                gate=GateId.V3,
                status=GateStatus.NOT_APPLICABLE,
                gating=False,
                summary="No persisted legacy artifacts for this case",
            )
        return self.gate.run(
            candidate,
            oracle.check_file("V3") if oracle else None,
            oracle.artifacts_dir if oracle else None,
            gating=bool(oracle and oracle.v3.gating),
        )
