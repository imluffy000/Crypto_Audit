"""JSON rendering of analysis and repair results."""

from typing import Any, Dict

from cryptoaudit.models.analysis import AnalysisResult
from cryptoaudit.pipeline.pipeline_result import ModuleRun


def format_json_report(result: AnalysisResult) -> str:
    """Format analysis result as a structured JSON string."""
    return result.model_dump_json(indent=2)


def module_run_to_dict(run: ModuleRun, include_code: bool = True) -> Dict[str, Any]:
    return {
        "module_name": run.module.module_name,
        "case_id": run.module.case_id,
        "findings": [f.model_dump(mode="json") for f in run.findings],
        "baseline": run.baseline,
        "results": [
            {
                "outcome": r.outcome.model_dump(mode="json"),
                "repair": r.candidate.repair.model_dump(mode="json"),
                "integrity": r.candidate.integrity.model_dump(mode="json") if r.candidate.integrity else None,
                "validation": r.report.model_dump(mode="json"),
                "diff": r.candidate.diff,
                **({"candidate_code": r.candidate.code} if include_code else {}),
            }
            for r in run.runs
        ],
    }
