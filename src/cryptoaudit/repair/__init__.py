"""Repair Engine: generates untrusted candidate repairs (S1-S4)."""

from cryptoaudit.repair.base import RepairStrategy
from cryptoaudit.repair.models import (
    GenerationMetadata,
    RepairConstraints,
    RepairRequest,
    RepairResult,
    RepairStatus,
    StrategyId,
)
from cryptoaudit.repair.registry import StrategyRegistry
from cryptoaudit.repair.request import build_repair_request

__all__ = [
    "GenerationMetadata",
    "RepairConstraints",
    "RepairRequest",
    "RepairResult",
    "RepairStatus",
    "RepairStrategy",
    "StrategyId",
    "StrategyRegistry",
    "build_repair_request",
]
