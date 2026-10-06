"""Configuration management and YAML rule loader for CryptoAudit."""

from pathlib import Path
from typing import Dict, Union

import yaml
from pydantic_settings import BaseSettings, SettingsConfigDict

from cryptoaudit.core.models import RuleConfig


class Settings(BaseSettings):
    """Global configuration settings for CryptoAudit."""

    model_config = SettingsConfigDict(env_prefix="CRYPTOAUDIT_")
    rules_dir: Path = Path("configs/rules")
    analyzer_version: str = "0.1.0"


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
