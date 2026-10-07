"""V2 security validation: executable cryptographic security-property checks."""

from pathlib import Path
from typing import Optional

from cryptoaudit.models.repair import Candidate
from cryptoaudit.models.validation import GateId, GateResult
from cryptoaudit.validation.checks import OracleGate
from cryptoaudit.validation.sandbox import Sandbox


class SecurityValidator:
    """Runs the hidden V2 oracle; without one the gate is NOT_RUN and can never yield acceptance."""

    def __init__(self, sandbox: Sandbox) -> None:
        self.gate = OracleGate(GateId.V2, sandbox)

    def validate(self, candidate: Candidate, check_file: Optional[Path], artifacts_dir: Optional[Path]) -> GateResult:
        return self.gate.run(candidate, check_file, artifacts_dir, gating=True)
