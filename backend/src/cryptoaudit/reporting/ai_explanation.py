"""
Optional AI narrative for a repair. The LLM explains the recorded evidence in plain language;
it never decides or changes the verdict, and its output is always labelled as such.
"""

from datetime import datetime, timezone
from string import Template
from typing import Optional

from pydantic import BaseModel

from cryptoaudit.llm.client import LLMClient
from cryptoaudit.llm.prompt_loader import load_prompt
from cryptoaudit.llm.schemas import LLMRequest
from cryptoaudit.reporting.explanation import VERDICT_LABELS, Explanation, render_text
from cryptoaudit.utils.hashing import stable_hash

PROMPT_ID = "explain_v1"
MAX_DIFF_CHARS = 6000
MAX_OUTPUT_CHARS = 2500
DISCLAIMER = "AI explanation - generated from the validation evidence; it is not a security verdict."


class AIExplanation(BaseModel):
    text: str
    disclaimer: str = DISCLAIMER
    model: str
    prompt_id: str
    prompt_hash: str
    created_at: str


def generate_ai_explanation(
    client: LLMClient, model: str, explanation: Explanation, diff: str, seed: int = 0, num_ctx: Optional[int] = None
) -> AIExplanation:
    """Single-shot narrative. Raises CryptoAuditError(LLM_ERROR | TIMEOUT) when the model is unavailable."""
    spec = load_prompt("explanation", PROMPT_ID)
    prompt = Template(spec.template).substitute(
        verdict=VERDICT_LABELS[explanation.verdict],
        evidence=render_text(explanation),
        diff=(diff or "(no code change)")[:MAX_DIFF_CHARS],
    )
    response = client.generate(
        LLMRequest(model=model, system=spec.system, prompt=prompt, temperature=0.0, seed=seed, max_tokens=700, num_ctx=num_ctx)
    )
    return AIExplanation(
        text=response.text.strip()[:MAX_OUTPUT_CHARS],
        model=response.model,
        prompt_id=PROMPT_ID,
        prompt_hash=stable_hash([spec.system, spec.template]),
        created_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
    )
