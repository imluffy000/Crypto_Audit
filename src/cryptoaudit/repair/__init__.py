"""Repair Engine: generates untrusted candidate repairs (S1-S4). Models live in cryptoaudit.models.repair."""

from cryptoaudit.repair.base import RepairStrategy
from cryptoaudit.repair.registry import StrategyRegistry
from cryptoaudit.repair.request import build_repair_request

__all__ = ["RepairStrategy", "StrategyRegistry", "build_repair_request"]
