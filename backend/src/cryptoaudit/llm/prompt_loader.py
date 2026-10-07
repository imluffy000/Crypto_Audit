"""Loader for versioned prompt files: prompts/<category>/<id>.yaml (id, system, template)."""

from dataclasses import dataclass
from pathlib import Path

import yaml

from cryptoaudit.config.settings import Settings
from cryptoaudit.utils.errors import CryptoAuditError, ErrorCode

# Repository-level prompts directory (src/cryptoaudit/llm/prompt_loader.py -> repo root).
REPO_PROMPTS_DIR = Path(__file__).resolve().parents[3] / "prompts"


@dataclass(frozen=True)
class PromptSpec:
    id: str
    system: str
    template: str


def prompts_root() -> Path:
    configured = Settings().prompts_dir
    return Path(configured) if configured is not None else REPO_PROMPTS_DIR


def load_prompt(category: str, prompt_id: str) -> PromptSpec:
    """Load prompts/<category>/<prompt_id>.yaml; any text change requires a new prompt id."""
    path = prompts_root() / category / f"{prompt_id}.yaml"
    if not path.is_file():
        raise CryptoAuditError(ErrorCode.LLM_ERROR, f"Prompt {category}/{prompt_id} not found at {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if data.get("id") != prompt_id or not data.get("system") or not data.get("template"):
        raise CryptoAuditError(ErrorCode.LLM_ERROR, f"Prompt file {path.name} must define id, system and template")
    return PromptSpec(id=prompt_id, system=data["system"], template=data["template"])
