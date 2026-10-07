"""Versioned prompt templates rendered strictly from a RepairRequest."""

from dataclasses import dataclass
from string import Template
from typing import List

from cryptoaudit.llm.prompt_loader import load_prompt
from cryptoaudit.models.repair import RepairRequest
from cryptoaudit.utils.hashing import stable_hash


@dataclass(frozen=True)
class RenderedPrompt:
    system: str
    user: str
    version: str
    prompt_hash: str  # hash of the template text (not the rendered prompt) for cross-case comparison


def render_prompt(request: RepairRequest, prompt_id: str) -> RenderedPrompt:
    """The prompt is built from the RepairRequest alone, which cannot carry hidden benchmark data."""
    spec = load_prompt("repair", prompt_id)
    system_text, template_text = spec.system, spec.template
    user = Template(template_text).substitute(
        module_name=request.module_name,
        findings=_findings_block(request),
        context=_context_block(request),
        interface=_interface_block(request),
        allowed_libraries=", ".join(request.constraints.allowed_libraries) or "the libraries already imported",
        target_python=request.constraints.target_python,
        source=request.source.rstrip("\n"),
    )
    return RenderedPrompt(
        system=system_text.strip(),
        user=user,
        version=prompt_id,
        prompt_hash=stable_hash([system_text, template_text]),
    )


def _findings_block(request: RepairRequest) -> str:
    lines: List[str] = []
    for finding in request.findings:
        lines.append(f"- [{finding.rule_id} {finding.category.value}] line {finding.line} ({finding.matched_api})")
        lines.append(f"  Issue: {finding.explanation}")
        lines.append(f"  Evidence: {finding.evidence}")
        lines.append(f"  Guidance: {finding.remediation}")
    return "\n".join(lines)


def _context_block(request: RepairRequest) -> str:
    ctx = request.context
    lines = [f"Imports: {'; '.join(ctx.imports) or '(none)'}"]
    for fc in ctx.findings:
        scope = ".".join(p for p in (fc.enclosing_class, fc.enclosing_function) if p) or "module level"
        lines.append(f"- Finding {fc.finding_id} at line {fc.line} in {scope}")
        if fc.referenced_constants:
            lines.append("  Referenced constants: " + "; ".join(fc.referenced_constants.values()))
        if fc.callers:
            lines.append("  Called by: " + ", ".join(fc.callers))
    if ctx.truncated:
        lines.append("(context truncated to budget)")
    return "\n".join(lines)


def _interface_block(request: RepairRequest) -> str:
    return "\n".join(f"- {s.signature}" for s in request.context.public_interface) or "- (no public symbols)"


__all__ = ["RenderedPrompt", "render_prompt"]
