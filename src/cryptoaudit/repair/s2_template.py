"""S2: deterministic, category/library-specific secure template transformations."""

import ast
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Set

from cryptoaudit.models.finding import Finding, finding_id
from cryptoaudit.models.repair import RepairRequest, RepairResult, RepairStatus, StrategyId
from cryptoaudit.repair.base import RepairStrategy
from cryptoaudit.repair.edits import (
    SourceIndex,
    TextEdit,
    apply_edits,
    edits_overlap,
    ensure_import,
    find_call,
    parent_map,
)
from cryptoaudit.utils.errors import ErrorCode

DEFAULT_MIN_ITERATIONS = 600_000
SALT_BYTES = 16
IV_BYTES = 16
GCM_NONCE_BYTES = 12

# random.* -> secrets equivalents where the call shape is preserved by replacing only the callee.
_SECRETS_CALLEE = {"choice": "secrets.choice", "getrandbits": "secrets.randbits"}
_SYSTEM_RANDOM_METHODS = {"random", "uniform", "choices", "sample", "shuffle", "triangular", "betavariate", "gauss"}


@dataclass
class TemplateOutcome:
    edits: List[TextEdit] = field(default_factory=list)
    imports: Set[str] = field(default_factory=set)
    reason: Optional[str] = None  # set when no template applies

    @property
    def applied(self) -> bool:
        return bool(self.edits)


@dataclass
class _Ctx:
    finding: Finding
    call: ast.Call
    parents: Dict[ast.AST, ast.AST]
    index: SourceIndex
    min_iterations: int


def _skip(reason: str) -> TemplateOutcome:
    return TemplateOutcome(reason=reason)


def _replace(ctx: _Ctx, node: ast.AST, text: str, *imports: str) -> TemplateOutcome:
    start, end = ctx.index.span(node)
    return TemplateOutcome(edits=[TextEdit(start, end, text)], imports=set(imports))


def _digest_chain(ctx: _Ctx) -> Optional[tuple[ast.Call, str]]:
    """For `hashlib.X(data).hexdigest()` return (outer call, method name)."""
    attr = ctx.parents.get(ctx.call)
    outer = ctx.parents.get(attr) if attr is not None else None
    if (
        isinstance(attr, ast.Attribute)
        and attr.attr in ("hexdigest", "digest")
        and isinstance(outer, ast.Call)
        and outer.func is attr
        and not outer.args
    ):
        return outer, attr.attr
    return None


def _kdf_replacement(ctx: _Ctx) -> TemplateOutcome:
    """Replace a fast-hash digest chain with a salted, iterated PBKDF2 call."""
    chain = _digest_chain(ctx)
    data_args = [a for a in ctx.call.args]
    if chain is None or len(data_args) != 1 or any(k.arg != "usedforsecurity" for k in ctx.call.keywords):
        return _skip("Unsupported hash usage pattern (expected hashlib.<algo>(data).hexdigest()/digest())")
    outer, method = chain
    data_src = ctx.index.text(data_args[0])
    replacement = f'hashlib.pbkdf2_hmac("sha256", {data_src}, os.urandom({SALT_BYTES}), {ctx.min_iterations})'
    if method == "hexdigest":
        replacement += ".hex()"
    return _replace(ctx, outer, replacement, "hashlib", "os")


def _cr1(ctx: _Ctx) -> TemplateOutcome:
    return _kdf_replacement(ctx)


def _cr2(ctx: _Ctx) -> TemplateOutcome:
    return _skip(
        "No deterministic template: migrating ECB to an authenticated mode requires restructuring "
        "the ciphertext format (nonce and tag storage)"
    )


def _iv_node(call: ast.Call, matched_api: str) -> tuple[Optional[ast.AST], int]:
    mode = matched_api.split(".")[-1]
    if mode in ("CBC", "CTR", "GCM", "OFB", "CFB"):
        size = GCM_NONCE_BYTES if mode == "GCM" else IV_BYTES
        if call.args:
            return call.args[0], size
        for kw in call.keywords:
            if kw.arg in ("initialization_vector", "nonce", "tweak"):
                return kw.value, size
    if matched_api.endswith("AES.new"):
        for kw in call.keywords:
            if kw.arg == "iv":
                return kw.value, IV_BYTES
            if kw.arg == "nonce":
                return kw.value, GCM_NONCE_BYTES
        if len(call.args) >= 3:
            return call.args[2], IV_BYTES
    return None, 0


def _cr3(ctx: _Ctx) -> TemplateOutcome:
    node, size = _iv_node(ctx.call, ctx.finding.matched_api)
    if node is None:
        return _skip("Could not locate the IV/nonce argument")
    return _replace(ctx, node, f"os.urandom({size})", "os")


def _pbkdf2_arg(call: ast.Call, keyword: str, position: int) -> Optional[ast.AST]:
    for kw in call.keywords:
        if kw.arg == keyword:
            return kw.value
    return call.args[position] if len(call.args) > position else None


def _cr4(ctx: _Ctx) -> TemplateOutcome:
    explanation = ctx.finding.explanation
    if explanation.startswith("Static hardcoded salt"):
        node = _pbkdf2_arg(ctx.call, "salt", 2)
        if node is None:
            return _skip("Could not locate the salt argument")
        return _replace(ctx, node, f"os.urandom({SALT_BYTES})", "os")
    if explanation.startswith("Weak PBKDF2 iteration count"):
        node = _pbkdf2_arg(ctx.call, "iterations", 3)
        if node is None:
            return _skip("Could not locate the iterations argument")
        return _replace(ctx, node, str(ctx.min_iterations))
    if explanation.startswith("Direct fast hash key derivation"):
        return _kdf_replacement(ctx)
    return _skip("Unrecognised CR4 finding kind")


def _cr5(ctx: _Ctx) -> TemplateOutcome:
    name = ctx.finding.matched_api.split(".")[-1]
    call = ctx.call
    plain_positional = not call.keywords and not any(isinstance(a, ast.Starred) for a in call.args)
    text = ctx.index.text
    if name == "SystemRandom":
        return _skip("random.SystemRandom is already a CSPRNG; no template change")
    if name in _SECRETS_CALLEE:
        return _replace(ctx, call.func, _SECRETS_CALLEE[name], "secrets")
    if name in _SYSTEM_RANDOM_METHODS:
        return _replace(ctx, call.func, f"secrets.SystemRandom().{name}", "secrets")
    if name == "randint" and plain_positional and len(call.args) == 2:
        low, high = (text(a) for a in call.args)
        return _replace(ctx, call, f"(secrets.randbelow(({high}) - ({low}) + 1) + ({low}))", "secrets")
    if name == "randrange" and plain_positional and len(call.args) == 1:
        return _replace(ctx, call, f"secrets.randbelow({text(call.args[0])})", "secrets")
    if name == "randrange" and plain_positional and len(call.args) == 2:
        start, stop = (text(a) for a in call.args)
        return _replace(ctx, call, f"(({start}) + secrets.randbelow(({stop}) - ({start})))", "secrets")
    return _skip(f"No template for random.{name} with this call shape")


TEMPLATES: Dict[str, Callable[[_Ctx], TemplateOutcome]] = {
    "CR1": _cr1,
    "CR2": _cr2,
    "CR3": _cr3,
    "CR4": _cr4,
    "CR5": _cr5,
}


class TemplateRepairStrategy(RepairStrategy):
    """Applies predefined secure transformations. No template means NO_REPAIR, never an invented fallback."""

    strategy_id = StrategyId.S2

    def __init__(self, min_iterations: int = DEFAULT_MIN_ITERATIONS) -> None:
        self.min_iterations = min_iterations

    def _repair(self, request: RepairRequest) -> RepairResult:
        try:
            tree = ast.parse(request.source)
        except SyntaxError as exc:
            return self.failure(RepairStatus.NO_REPAIR, f"Source does not parse: {exc.msg}", ErrorCode.INVALID_INPUT)

        index = SourceIndex(request.source)
        parents = parent_map(tree)
        edits: List[TextEdit] = []
        imports: Set[str] = set()
        repaired: List[str] = []
        unrepaired: List[str] = []
        notes: List[str] = []

        for finding in request.findings:
            fid = finding_id(finding)
            call = find_call(tree, finding.line, finding.column)
            template = TEMPLATES.get(finding.rule_id)
            if call is None or template is None:
                unrepaired.append(fid)
                notes.append(f"{fid}: {'call site not found' if call is None else 'no template for rule'}")
                continue
            outcome = template(_Ctx(finding, call, parents, index, self.min_iterations))
            if not outcome.applied:
                unrepaired.append(fid)
                notes.append(f"{fid} ({finding.rule_id}): {outcome.reason}")
                continue
            if any(edits_overlap(edit, edits) for edit in outcome.edits):
                unrepaired.append(fid)
                notes.append(f"{fid} ({finding.rule_id}): overlaps an edit for another finding")
                continue
            edits.extend(outcome.edits)
            imports |= outcome.imports
            repaired.append(fid)

        if not edits:
            return self.failure(
                RepairStatus.NO_REPAIR,
                "No template applies to any finding",
                unrepaired_finding_ids=unrepaired,
                notes=notes,
            )

        candidate = apply_edits(request.source, edits)
        for module in sorted(imports):
            candidate = ensure_import(candidate, module)
        ast.parse(candidate)  # a template bug must surface as REPAIR_ERROR via the base wrapper

        return RepairResult(
            strategy_id=self.strategy_id,
            status=RepairStatus.PRODUCED,
            candidate_code=candidate,
            repaired_finding_ids=repaired,
            unrepaired_finding_ids=unrepaired,
            notes=notes,
        )
