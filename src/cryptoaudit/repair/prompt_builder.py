"""Versioned prompt templates rendered strictly from a RepairRequest."""

from dataclasses import dataclass
from pathlib import Path
from string import Template
from typing import List

import yaml

from cryptoaudit.config.settings import Settings
from cryptoaudit.models.repair import RepairRequest
from cryptoaudit.utils.errors import CryptoAuditError, ErrorCode
from cryptoaudit.utils.hashing import stable_hash

# Repository-level prompts directory (src/cryptoaudit/repair/prompt_builder.py -> repo root).
REPO_PROMPTS_DIR = Path(__file__).resolve().parents[3] / "prompts" / "repair"


@dataclass(frozen=True)
class RenderedPrompt:
    system: str
    user: str
    version: str
    prompt_hash: str  # hash of the template text (not the rendered prompt) for cross-case comparison


@dataclass(frozen=True)
class PromptSpec:
    id: str
    system: str
    template: str


def prompts_dir() -> Path:
    configured = Settings().prompts_dir
    return Path(configured) / "repair" if configured is not None else REPO_PROMPTS_DIR


def load_prompt(prompt_id: str) -> PromptSpec:
    """Load a versioned prompt (prompts/repair/<id>.yaml) holding its system and user template."""
    path = prompts_dir() / f"{prompt_id}.yaml"
    if not path.is_file():
        raise CryptoAuditError(ErrorCode.REPAIR_ERROR, f"Prompt {prompt_id!r} not found at {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if data.get("id") != prompt_id or not data.get("system") or not data.get("template"):
        raise CryptoAuditError(ErrorCode.REPAIR_ERROR, f"Prompt file {path.name} must define id, system and template")
    return PromptSpec(id=prompt_id, system=data["system"], template=data["template"])


def render_prompt(request: RepairRequest, prompt_id: str) -> RenderedPrompt:
    """The prompt is built from the RepairRequest alone, which cannot carry hidden benchmark data."""
    spec = load_prompt(prompt_id)
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


__all__ = ["PromptSpec", "RenderedPrompt", "load_prompt", "render_prompt"]
