"""Service container for the API: everything a route needs, injectable for tests."""

import logging
import secrets
from concurrent.futures import Executor, Future, ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Callable, List, Optional

import httpx

from cryptoaudit.config.settings import Settings
from cryptoaudit.ingest.filters import SnapshotLimits
from cryptoaudit.ingest.github_client import GitHubClient, GitHubOAuth
from cryptoaudit.llm.client import LLMClient
from cryptoaudit.models.repair import StrategyId
from cryptoaudit.pipeline.factory import build_llm, build_pipeline
from cryptoaudit.pipeline.orchestrator import RepairPipeline
from cryptoaudit.storage.web_store import WebStore
from cryptoaudit.validation.sandbox import DockerSandbox

logger = logging.getLogger("cryptoaudit.api")


class InlineExecutor(Executor):
    """Runs submitted work synchronously (tests and single-process debugging)."""

    def submit(self, fn, /, *args, **kwargs) -> Future:  # type: ignore[override]
        future: Future = Future()
        try:
            future.set_result(fn(*args, **kwargs))
        except BaseException as exc:  # recorded on the future, like a worker thread would
            future.set_exception(exc)
        return future


@dataclass
class Services:
    settings: Settings
    store: WebStore
    auth: Optional[GitHubOAuth]
    github: Callable[[str], GitHubClient]
    llm: Optional[LLMClient]
    llm_available: Callable[[], bool]
    pipeline_factory: Callable[[List[StrategyId]], RepairPipeline]
    executor: Executor
    limits: SnapshotLimits = field(default_factory=SnapshotLimits)


def _session_secret(settings: Settings) -> str:
    if settings.session_secret is not None:
        return settings.session_secret.get_secret_value()
    logger.warning("CRYPTOAUDIT_SESSION_SECRET is not set: using an ephemeral secret (sessions end on restart)")
    return secrets.token_urlsafe(48)


def default_services(settings: Optional[Settings] = None, github_transport: Optional[httpx.BaseTransport] = None) -> Services:
    settings = settings or Settings()
    auth = None
    if settings.github_configured:
        auth = GitHubOAuth(
            settings.github_client_id or "",
            settings.github_client_secret.get_secret_value() if settings.github_client_secret else "",
            settings.oauth_redirect_uri,
            scopes=settings.github_oauth_scopes,
            transport=github_transport,
        )
    llm = build_llm(settings)

    def pipeline_factory(strategy_ids: List[StrategyId]) -> RepairPipeline:
        # Web scans never execute repository code (no oracle => executable gates are NOT_RUN),
        # but the validation pipeline still requires an isolated sandbox to be configured.
        return build_pipeline(settings, strategy_ids, DockerSandbox(settings.sandbox_image, settings.sandbox_timeout), llm_client=llm)

    return Services(
        settings=settings,
        store=WebStore(settings.web_db, _session_secret(settings)),
        auth=auth,
        github=lambda token: GitHubClient(token, transport=github_transport),
        llm=llm,
        llm_available=llm.available,
        pipeline_factory=pipeline_factory,
        executor=ThreadPoolExecutor(max_workers=max(1, settings.scan_workers), thread_name_prefix="cryptoaudit-scan"),
        limits=SnapshotLimits(
            max_download_bytes=settings.max_repo_mb * 1024 * 1024,
            max_unpacked_bytes=settings.max_unpacked_mb * 1024 * 1024,
            max_python_files=settings.max_python_files,
            max_file_bytes=settings.max_file_kb * 1024,
        ),
    )
