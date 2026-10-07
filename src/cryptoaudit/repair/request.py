"""Construction of RepairRequests from public inputs only."""

from typing import Optional, Sequence

from cryptoaudit.context.builder import ContextBuilder
from cryptoaudit.models.finding import Finding
from cryptoaudit.repair.models import RepairConstraints, RepairRequest
from cryptoaudit.utils.errors import CryptoAuditError, ErrorCode


def build_repair_request(
    module_name: str,
    source: str,
    findings: Sequence[Finding],
    constraints: Optional[RepairConstraints] = None,
    context_builder: Optional[ContextBuilder] = None,
) -> RepairRequest:
    """Bundle a module, its findings and bounded context into a RepairRequest."""
    if not findings:
        raise CryptoAuditError(ErrorCode.INVALID_INPUT, "A repair request needs at least one finding")
    builder = context_builder or ContextBuilder()
    context = builder.build(source, findings, module_name)
    return RepairRequest(
        module_name=module_name,
        source=source,
        findings=tuple(findings),
        context=context,
        constraints=constraints or RepairConstraints(),
    )
