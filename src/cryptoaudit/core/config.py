"""Configuration management and YAML rule loader for CryptoAudit."""

from pathlib import Path
from typing import Dict, Optional, Union

import yaml
from pydantic_settings import BaseSettings, SettingsConfigDict

from cryptoaudit.core.models import RuleConfig


class Settings(BaseSettings):
    """Global configuration settings for CryptoAudit."""

    model_config = SettingsConfigDict(env_prefix="CRYPTOAUDIT_")
    rules_dir: Path = Path("configs/rules")
    analyzer_version: str = "0.1.0"

    # Repair / LLM (S3, S4)
    llm_base_url: str = "http://localhost:11434"
    llm_model: str = "codellama:7b-instruct"
    llm_temperature: float = 0.0
    llm_seed: int = 0
    llm_timeout: float = 300.0

    # Validation
    sandbox: str = "docker"  # "docker" (isolated) or "local" (trusted code only)
    sandbox_image: str = "cryptoaudit-sandbox:latest"
    sandbox_timeout: float = 120.0
    enable_bandit: bool = True
    enable_semgrep: bool = True
    semgrep_config: str = "p/python"

    # Experiments
    benchmark_dir: Optional[Path] = None
    experiment_db: Path = Path("data/experiments.sqlite")


def load_rule_config(config_path: Union[str, Path]) -> RuleConfig:
    """Safely load and validate a YAML rule configuration file."""
    path = Path(config_path)
    if not path.is_file():
        raise FileNotFoundError(f"Rule configuration file not found at: {path}")

    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not isinstance(data, dict):
        raise ValueError(f"Invalid rule YAML content in {path}: expected a dictionary mapping.")

    return RuleConfig(**data)
