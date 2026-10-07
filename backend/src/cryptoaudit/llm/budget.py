"""Context-window budgeting so prompts are never silently truncated by the model server."""

import math
from dataclasses import dataclass

# Conservative characters-per-token for source code and prose (real tokenizers average ~3.5-4).
CHARS_PER_TOKEN = 3.0
ANSWER_OVERHEAD_TOKENS = 256  # code fence, small additions such as imports or a version prefix
ANSWER_GROWTH = 1.3  # a repaired module is usually a little longer than the original


def estimate_tokens(text: str) -> int:
    return math.ceil(len(text) / CHARS_PER_TOKEN)


@dataclass(frozen=True)
class TokenBudget:
    num_ctx: int
    prompt_tokens: int
    answer_tokens: int  # expected size of the complete repaired module

    @property
    def fits(self) -> bool:
        return self.prompt_tokens + self.answer_tokens <= self.num_ctx

    def num_predict(self, cap: int) -> int:
        """Generation limit: everything the context leaves after the prompt, bounded by cap."""
        return max(1, min(cap, self.num_ctx - self.prompt_tokens))


def module_budget(prompt_text: str, module_source: str, num_ctx: int) -> TokenBudget:
    """Budget for prompts whose answer must reproduce a whole module."""
    answer = math.ceil(estimate_tokens(module_source) * ANSWER_GROWTH) + ANSWER_OVERHEAD_TOKENS
    return TokenBudget(num_ctx=num_ctx, prompt_tokens=estimate_tokens(prompt_text), answer_tokens=answer)
