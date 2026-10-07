"""S4: migration-aware LLM repair strategy."""

from cryptoaudit.models.repair import StrategyId
from cryptoaudit.repair.s3_llm import LLMRepairStrategy


class MigrationAwareRepairStrategy(LLMRepairStrategy):
    """Identical generation mechanism to S3 plus generic migration-awareness instructions."""

    strategy_id = StrategyId.S4
    prompt_id = "s4_v1"
