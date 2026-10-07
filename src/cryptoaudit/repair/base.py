"""Common RepairStrategy interface shared by S1-S4."""

import time
from abc import ABC, abstractmethod
from typing import Any

from cryptoaudit.repair.models import RepairRequest, RepairResult, RepairStatus, StrategyId
from cryptoaudit.utils.errors import CryptoAuditError, ErrorCode


class RepairStrategy(ABC):
    """
    A strategy turns a RepairRequest into a candidate. It never judges security:
    acceptance is decided only by the validation pipeline.
    """

    strategy_id: StrategyId

    def repair(self, request: RepairRequest) -> RepairResult:
        started = time.perf_counter()
        try:
            result = self._repair(request)
        except CryptoAuditError as exc:
            result = self.failure(RepairStatus.NO_REPAIR, exc.message, exc.code)
        except Exception as exc:  # strategy bugs must surface as explicit failures, not crashes
            result = self.failure(RepairStatus.NO_REPAIR, f"{type(exc).__name__}: {exc}", ErrorCode.REPAIR_ERROR)
        return result.model_copy(update={"duration_seconds": round(time.perf_counter() - started, 6)})

    @abstractmethod
    def _repair(self, request: RepairRequest) -> RepairResult:
        """Strategy-specific generation."""

    def failure(
        self, status: RepairStatus, reason: str, error_code: ErrorCode | None = None, **extra: Any
    ) -> RepairResult:
        return RepairResult(
            strategy_id=self.strategy_id, status=status, failure_reason=reason, error_code=error_code, **extra
        )
