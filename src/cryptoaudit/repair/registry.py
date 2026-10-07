"""Registry of repair strategies keyed by StrategyId."""

from typing import Dict, Iterable, List

from cryptoaudit.core.errors import CryptoAuditError, ErrorCode
from cryptoaudit.repair.base import RepairStrategy
from cryptoaudit.repair.models import StrategyId


class StrategyRegistry:
    def __init__(self, strategies: Iterable[RepairStrategy] = ()) -> None:
        self._strategies: Dict[StrategyId, RepairStrategy] = {}
        for strategy in strategies:
            self.register(strategy)

    def register(self, strategy: RepairStrategy) -> None:
        if strategy.strategy_id in self._strategies:
            raise CryptoAuditError(ErrorCode.INVALID_INPUT, f"Strategy {strategy.strategy_id.value} already registered")
        self._strategies[strategy.strategy_id] = strategy

    def get(self, strategy_id: StrategyId) -> RepairStrategy:
        try:
            return self._strategies[strategy_id]
        except KeyError:
            raise CryptoAuditError(
                ErrorCode.INVALID_INPUT, f"Strategy {strategy_id.value} is not registered"
            ) from None

    def ids(self) -> List[StrategyId]:
        return sorted(self._strategies, key=lambda s: s.value)

    def select(self, strategy_ids: Iterable[StrategyId]) -> List[RepairStrategy]:
        return [self.get(sid) for sid in strategy_ids]
