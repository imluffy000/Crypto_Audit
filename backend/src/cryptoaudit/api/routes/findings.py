"""Findings of a completed scan, their repair candidates, evidence and explanations."""

from typing import List

from fastapi import APIRouter, Depends

from cryptoaudit.api.dependencies import current_session, get_services
from cryptoaudit.api.routes.scan import load_scan
from cryptoaudit.api.schemas import AIExplanationOut, FindingDetailOut, FindingOut, StrategyRunOut
from cryptoaudit.api.services import Services
from cryptoaudit.models.scan import RepositoryScanResult, ScanStatus
from cryptoaudit.reporting.ai_explanation import AIExplanation, generate_ai_explanation
from cryptoaudit.storage.web_store import SessionInfo
from cryptoaudit.utils.errors import CryptoAuditError, ErrorCode

router = APIRouter(prefix="/scans/{scan_id}", tags=["findings"])


def completed_result(services: Services, session: SessionInfo, scan_id: str) -> RepositoryScanResult:
    record = load_scan(services, session, scan_id)
    if record.status is not ScanStatus.COMPLETED or record.result is None:
        raise CryptoAuditError(ErrorCode.INVALID_INPUT, f"Scan is {record.status.value.lower()}; results are not available yet")
    return record.result


@router.get("/findings", response_model=List[FindingOut])
def list_findings(scan_id: str, session: SessionInfo = Depends(current_session), services: Services = Depends(get_services)):
    result = completed_result(services, session, scan_id)
    runs_by_file = {f.path: f.runs for f in result.files}
    return [
        FindingOut(
            finding_id=view.finding_id,
            finding=view.finding,
            best_verdict=view.best_verdict,
            verdicts={run.strategy_id.value: run.verdict for run in runs_by_file.get(view.finding.file, [])},
        )
        for view in result.findings
    ]


@router.get("/findings/{finding_id}", response_model=FindingDetailOut)
def finding_detail(
    scan_id: str, finding_id: str, session: SessionInfo = Depends(current_session), services: Services = Depends(get_services)
):
    result = completed_result(services, session, scan_id)
    view = next((v for v in result.findings if v.finding_id == finding_id), None)
    if view is None:
        raise CryptoAuditError(ErrorCode.NOT_FOUND, "Finding not found")
    file = next(f for f in result.files if f.path == view.finding.file)
    file_findings = [v.finding for v in result.findings if v.finding.file == file.path]
    return FindingDetailOut(
        scan_id=scan_id,
        repository=result.repository,
        finding_id=finding_id,
        finding=view.finding,
        best_verdict=view.best_verdict,
        file_path=file.path,
        original_source=file.source,
        file_findings=file_findings,
        baseline=file.baseline,
        runs=[StrategyRunOut(**run.model_dump(), targets_finding=finding_id in run.repaired_finding_ids) for run in file.runs],
        ai_available=services.llm is not None,
    )


@router.post("/candidates/{candidate_id}/ai-explanation", response_model=AIExplanationOut)
def ai_explanation(
    scan_id: str, candidate_id: str, session: SessionInfo = Depends(current_session), services: Services = Depends(get_services)
):
    result = completed_result(services, session, scan_id)
    run = next((r for f in result.files for r in f.runs if r.candidate_id == candidate_id), None)
    if run is None:
        raise CryptoAuditError(ErrorCode.NOT_FOUND, "Candidate not found")
    cached = services.store.get_ai_explanation(scan_id, candidate_id)
    if cached is not None:
        explanation = AIExplanation.model_validate_json(cached)
    else:
        if services.llm is None or not services.llm_available():
            raise CryptoAuditError(
                ErrorCode.LLM_ERROR, f"AI explanations need a local Ollama server with '{services.settings.llm_model}' pulled"
            )
        explanation = generate_ai_explanation(
            services.llm, services.settings.llm_model, run.explanation, run.diff, num_ctx=services.settings.llm_num_ctx
        )
        services.store.save_ai_explanation(scan_id, candidate_id, explanation.model_dump_json())
    return AIExplanationOut(candidate_id=candidate_id, **explanation.model_dump(exclude={"prompt_hash"}))
