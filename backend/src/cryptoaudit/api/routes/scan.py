"""Start repository scans and follow their progress."""

from typing import List

from fastapi import APIRouter, Depends

from cryptoaudit.api.dependencies import current_session, get_services
from cryptoaudit.api.jobs import initial_stages, run_scan
from cryptoaudit.api.schemas import ScanCreate, ScanCreated, ScanOut
from cryptoaudit.api.services import Services
from cryptoaudit.ingest.filters import is_valid_github_name, is_valid_ref
from cryptoaudit.models.scan import ScanRecord, ScanStatus
from cryptoaudit.storage.web_store import SessionInfo
from cryptoaudit.utils.errors import CryptoAuditError, ErrorCode

router = APIRouter(prefix="/scans", tags=["scans"])
MAX_ACTIVE_SCANS_PER_USER = 1


def scan_out(record: ScanRecord) -> ScanOut:
    result = record.result
    return ScanOut(
        scan_id=record.scan_id,
        repository=record.repository,
        ref=record.ref,
        commit=result.commit if result else None,
        status=record.status,
        stages=record.stages,
        error=record.error,
        created_at=record.created_at,
        updated_at=record.updated_at,
        strategies=[s.value for s in result.strategies] if result else [],
        skipped_strategies=result.skipped_strategies if result else {},
        skipped_files=result.skipped_files if result else [],
        summary=result.summary if result else None,
    )


def load_scan(services: Services, session: SessionInfo, scan_id: str) -> ScanRecord:
    record = services.store.get_scan(scan_id, session.user.id)
    if record is None:
        raise CryptoAuditError(ErrorCode.NOT_FOUND, "Scan not found")
    return record


@router.post("", response_model=ScanCreated, status_code=202)
def start_scan(
    body: ScanCreate, session: SessionInfo = Depends(current_session), services: Services = Depends(get_services)
) -> ScanCreated:
    if not (is_valid_github_name(body.owner) and is_valid_github_name(body.name)) or (body.ref and not is_valid_ref(body.ref)):
        raise CryptoAuditError(ErrorCode.INVALID_INPUT, "Invalid repository or ref")
    if services.store.active_scan_count(session.user.id) >= MAX_ACTIVE_SCANS_PER_USER:
        raise CryptoAuditError(ErrorCode.RATE_LIMITED, "A scan is already running; wait for it to finish")
    with services.github(session.access_token) as client:
        repo = client.get_repo(body.owner, body.name)
    if repo.size_kb > services.settings.max_repo_mb * 1024:
        raise CryptoAuditError(ErrorCode.LIMIT_EXCEEDED, f"Repository is larger than {services.settings.max_repo_mb} MB")
    ref = body.ref or repo.default_branch
    scan_id = services.store.create_scan(session.user.id, repo.full_name, ref, initial_stages())
    services.executor.submit(run_scan, services, scan_id, session.access_token, repo.owner, repo.name, ref)
    return ScanCreated(scan_id=scan_id, status=ScanStatus.QUEUED)


@router.get("", response_model=List[ScanOut])
def list_scans(session: SessionInfo = Depends(current_session), services: Services = Depends(get_services)) -> List[ScanOut]:
    return [scan_out(record) for record in services.store.list_scans(session.user.id)]


@router.get("/{scan_id}", response_model=ScanOut)
def get_scan(scan_id: str, session: SessionInfo = Depends(current_session), services: Services = Depends(get_services)) -> ScanOut:
    return scan_out(load_scan(services, session, scan_id))
