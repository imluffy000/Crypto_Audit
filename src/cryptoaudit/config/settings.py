"""Global settings, overridable through CRYPTOAUDIT_* environment variables."""

from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Global configuration settings for CryptoAudit."""

    model_config = SettingsConfigDict(env_prefix="CRYPTOAUDIT_")
    rules_file: Path = Path("configs/rules.yaml")
    analyzer_version: str = "0.1.0"

    # Repair / LLM (S3, S4)
    llm_base_url: str = "http://localhost:11434"
    llm_model: str = "codellama:7b-instruct"
    llm_temperature: float = 0.0
    llm_seed: int = 0
    llm_timeout: float = 300.0
    prompts_dir: Optional[Path] = None

    # Validation
    sandbox: str = "docker"  # "docker" (isolated) or "local" (trusted code only)
    sandbox_image: str = "cryptoaudit-sandbox:latest"
    sandbox_timeout: float = 120.0
    enable_bandit: bool = True
    enable_semgrep: bool = True
    semgrep_config: str = "p/python"

    # Experiments
    benchmark_dir: Optional[Path] = None
    experiment_db: Path = Path("data/experiments/experiments.sqlite")
