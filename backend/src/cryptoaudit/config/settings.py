"""Global settings, overridable through CRYPTOAUDIT_* environment variables (or a .env file)."""

from pathlib import Path
from typing import List, Literal, Optional, Tuple

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

    # Website (API + GitHub OAuth App sign-in)
    github_client_id: Optional[str] = None
    github_client_secret: Optional[SecretStr] = None
    # "private": request the `repo` scope so private repositories can be scanned (GitHub has no read-only
    # private scope; CryptoAudit still only reads). "public": no repository scope, public repositories only.
    github_repo_access: Literal["private", "public"] = "private"
    session_secret: Optional[SecretStr] = None
    public_url: str = "http://localhost:5173"  # browser-facing origin; the API is served under /api
    cors_origins: List[str] = []
    cookie_secure: bool = False  # set true when served over HTTPS
    session_ttl_hours: float = 8.0
    web_db: Path = Path("data/web/cryptoaudit.sqlite")
    scan_workers: int = 2  # scans running at the same time (across users)
    scan_parallelism: int = 4  # files repaired/validated concurrently within one scan
    max_repo_mb: int = 500  # compressed archive of the scanned commit (git history is not downloaded)
    max_unpacked_mb: int = 4096  # total size of everything in the archive, including non-Python files
    max_python_files: int = 5000
    max_file_kb: int = 1024  # larger .py files (usually generated code) are skipped and listed

    @property
    def github_configured(self) -> bool:
        return bool(self.github_client_id and self.github_client_secret)

    @property
    def github_oauth_scopes(self) -> Tuple[str, ...]:
        return ("read:user", "repo") if self.github_repo_access == "private" else ("read:user",)

    @property
    def oauth_redirect_uri(self) -> str:
        return f"{self.public_url.rstrip('/')}/api/auth/github/callback"
