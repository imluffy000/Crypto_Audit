"""S4: migration-aware LLM repair strategy."""

from cryptoaudit.repair.models import StrategyId
from cryptoaudit.repair.strategies.s3_llm import LLMRepairStrategy


class MigrationAwareRepairStrategy(LLMRepairStrategy):
    """Identical generation mechanism to S3 plus generic migration-awareness instructions."""

    strategy_id = StrategyId.S4
    template_name = "s4_v1"
