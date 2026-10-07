"""Downloadable report for a completed scan."""

from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse

from cryptoaudit.api.dependencies import current_session, get_services
from cryptoaudit.api.routes.findings import completed_result
from cryptoaudit.api.services import Services
from cryptoaudit.reporting.markdown_report import scan_to_markdown
from cryptoaudit.storage.web_store import SessionInfo

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/{scan_id}.md", response_class=PlainTextResponse)
def markdown_report(scan_id: str, session: SessionInfo = Depends(current_session), services: Services = Depends(get_services)):
    result = completed_result(services, session, scan_id)
    filename = f"cryptoaudit-{result.repository.replace('/', '-')}-{scan_id}.md"
    return PlainTextResponse(
        scan_to_markdown(result, scan_id),
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
