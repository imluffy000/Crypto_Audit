"""Results aggregation: per-case verdicts and cross-strategy comparison."""

from cryptoaudit.aggregation.aggregator import build_outcome, compare_strategies, decide
from cryptoaudit.aggregation.models import CaseOutcome, StrategyStats, Verdict

__all__ = ["CaseOutcome", "StrategyStats", "Verdict", "build_outcome", "compare_strategies", "decide"]
