"""Context budget: upper bounds that keep repair context small and deterministic."""

from dataclasses import dataclass

TRUNCATION_MARKER = "    # ... [truncated by CryptoAudit context budget]"


@dataclass(frozen=True)
class ContextBudget:
    """Upper bounds that keep context small and deterministic."""

    max_function_lines: int = 200
    max_total_chars: int = 20_000
