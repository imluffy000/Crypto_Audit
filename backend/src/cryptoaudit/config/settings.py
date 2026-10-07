"""Global settings, overridable through CRYPTOAUDIT_* environment variables (or a .env file)."""

from pathlib import Path
from typing import List, Optional

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Global configuration settings for CryptoAudit."""

    model_config = SettingsConfigDict(env_prefix="CRYPTOAUDIT_", env_file=".env", extra="ignore")
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

    # Website (API + GitHub App sign-in)
    github_client_id: Optional[str] = None
    github_client_secret: Optional[SecretStr] = None
    github_app_slug: Optional[str] = None
    session_secret: Optional[SecretStr] = None
    public_url: str = "http://localhost:5173"  # browser-facing origin; the API is served under /api
    cors_origins: List[str] = []
    cookie_secure: bool = False  # set true when served over HTTPS
    session_ttl_hours: float = 8.0
    web_db: Path = Path("data/web/cryptoaudit.sqlite")
    scan_workers: int = 2
    max_repo_mb: int = 50
    max_python_files: int = 500

    @property
    def github_configured(self) -> bool:
        return bool(self.github_client_id and self.github_client_secret)

    @property
    def oauth_redirect_uri(self) -> str:
        return f"{self.public_url.rstrip('/')}/api/auth/github/callback"
