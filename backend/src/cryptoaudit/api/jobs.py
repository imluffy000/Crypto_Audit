"""Background scan jobs: fetch the repository with the user's token and run the repository scan."""

import logging

from cryptoaudit.api.services import Services
from cryptoaudit.ingest.git_loader import fetch_repository
from cryptoaudit.models.scan import STAGE_LABELS, ScanStage, StageProgress
from cryptoaudit.pipeline.repository_scan import RepositoryScanner, select_web_strategies
from cryptoaudit.utils.errors import CryptoAuditError

logger = logging.getLogger("cryptoaudit.api.jobs")


def initial_stages() -> list:
    return [StageProgress(stage=s, label=STAGE_LABELS[s]) for s in ScanStage]


def run_scan(services: Services, scan_id: str, access_token: str, owner: str, name: str, ref: str) -> None:
    """Runs in a worker thread. The token lives only in this call's memory."""
    store = services.store
    scanner = None
    try:
        llm_ok = services.llm is not None and services.llm_available()
        strategy_ids, skipped = select_web_strategies(llm_ok, f"Ollama model '{services.settings.llm_model}' is not available")
        pipeline = services.pipeline_factory(strategy_ids)
        scanner = RepositoryScanner(pipeline, on_progress=lambda stages: store.update_progress(scan_id, stages), skipped_strategies=skipped)

        def fetch():
            with services.github(access_token) as client:
                return fetch_repository(client, owner, name, ref, services.limits)

        result = scanner.run(fetch)
        store.complete_scan(scan_id, result)
    except CryptoAuditError as exc:
        store.fail_scan(scan_id, {"code": exc.code.value, "message": exc.message}, scanner.stages if scanner else None)
    except Exception as exc:  # never leave a scan stuck in RUNNING
        logger.exception("Scan %s crashed", scan_id)
        store.fail_scan(
            scan_id, {"code": "INTERNAL_ERROR", "message": f"{type(exc).__name__}: {exc}"}, scanner.stages if scanner else None
        )
