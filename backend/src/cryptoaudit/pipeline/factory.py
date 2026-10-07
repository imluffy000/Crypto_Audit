"""Builds pipeline components from Settings (dependency wiring in one place)."""

from pathlib import Path
from typing import List, Optional, Sequence

from cryptoaudit.analysis.analyzer import AnalyzerEngine
from cryptoaudit.config.settings import Settings
from cryptoaudit.llm.client import LLMClient
from cryptoaudit.llm.ollama_client import OllamaClient
from cryptoaudit.llm.openrouter_client import OpenRouterClient
from cryptoaudit.llm.router import LLMBackend, RoutingLLMClient
from cryptoaudit.models.repair import StrategyId
from cryptoaudit.models.scan import Scanner
from cryptoaudit.pipeline.orchestrator import RepairPipeline
from cryptoaudit.repair.base import RepairStrategy
from cryptoaudit.repair.s1_hint import ToolGuidedRepairStrategy
from cryptoaudit.repair.s2_template import TemplateRepairStrategy
from cryptoaudit.repair.s3_llm import LLMRepairStrategy
from cryptoaudit.repair.s4_migration import MigrationAwareRepairStrategy
from cryptoaudit.storage.sqlite import ExperimentStore
from cryptoaudit.utils.errors import CryptoAuditError, ErrorCode
from cryptoaudit.validation.runner import ValidationPipeline
from cryptoaudit.validation.sandbox import DockerSandbox, LocalProcessSandbox, Sandbox
from cryptoaudit.validation.scanners.bandit import BanditScanner
from cryptoaudit.validation.scanners.semgrep import SemgrepScanner
from cryptoaudit.validation.v0_scanner import ScannerValidator


def parse_strategy_ids(values: Sequence[str]) -> List[StrategyId]:
    ids: List[StrategyId] = []
    for value in values:
        for part in value.split(","):
            part = part.strip().upper()
            if not part:
                continue
            try:
                ids.append(StrategyId(part))
            except ValueError:
                raise CryptoAuditError(ErrorCode.INVALID_INPUT, f"Unknown strategy {part!r}; use S1-S4") from None
    return list(dict.fromkeys(ids))


def build_scanners(settings: Settings) -> List[Scanner]:
    scanners: List[Scanner] = []
    if settings.enable_bandit:
        scanners.append(BanditScanner())
    if settings.enable_semgrep:
        scanners.append(SemgrepScanner(config=settings.semgrep_config))
    return scanners


def build_llm(settings: Settings) -> RoutingLLMClient:
    """LLM client for S3/S4 and AI explanations according to CRYPTOAUDIT_LLM_PROVIDER."""
    backends = []
    if settings.llm_provider in ("ollama", "auto"):
        ollama = OllamaClient(settings.llm_base_url, timeout=settings.llm_timeout)
        backends.append(
            LLMBackend(
                name="ollama",
                client=ollama,
                model=settings.llm_model,
                context_window=settings.llm_num_ctx,
                is_available=lambda: ollama.is_available(settings.llm_model),
                send_num_ctx=True,
            )
        )
    if settings.llm_provider in ("openrouter", "auto") and settings.openrouter_api_key and settings.openrouter_api_key.get_secret_value().strip():
        openrouter = OpenRouterClient(
            settings.openrouter_api_key.get_secret_value(),
            base_url=settings.openrouter_base_url,
            timeout=settings.llm_timeout,
            app_url=settings.public_url,
        )
        backends.append(
            LLMBackend(
                name="openrouter",
                client=openrouter,
                model=settings.openrouter_model,
                context_window=settings.openrouter_context,
                is_available=lambda: openrouter.is_available(settings.openrouter_model),
                send_num_ctx=False,
            )
        )
    return RoutingLLMClient(backends)


def build_strategies(
    ids: Sequence[StrategyId], settings: Settings, llm_client: Optional[LLMClient] = None
) -> List[RepairStrategy]:
    llm = llm_client
    strategies: List[RepairStrategy] = []
    for sid in ids:
        if sid is StrategyId.S1:
            strategies.append(ToolGuidedRepairStrategy(build_scanners(settings)))
        elif sid is StrategyId.S2:
            strategies.append(TemplateRepairStrategy())
        else:
            llm = llm or build_llm(settings)
            cls = LLMRepairStrategy if sid is StrategyId.S3 else MigrationAwareRepairStrategy
            strategies.append(
                cls(
                    llm,
                    model=settings.llm_model,
                    temperature=settings.llm_temperature,
                    seed=settings.llm_seed,
                    max_tokens=settings.llm_max_tokens,
                    num_ctx=settings.llm_num_ctx,
                )
            )
    return strategies


def build_sandbox(settings: Settings, kind: Optional[str] = None, allow_unsafe_local: bool = False) -> Sandbox:
    kind = (kind or settings.sandbox).lower()
    if kind == "docker":
        return DockerSandbox(image=settings.sandbox_image, timeout=settings.sandbox_timeout)
    if kind == "local":
        return LocalProcessSandbox(timeout=settings.sandbox_timeout, allow_unsafe=allow_unsafe_local)
    raise CryptoAuditError(ErrorCode.INVALID_INPUT, f"Unknown sandbox {kind!r}; use 'docker' or 'local'")


def build_pipeline(
    settings: Settings,
    strategy_ids: Sequence[StrategyId],
    sandbox: Sandbox,
    store: Optional[ExperimentStore] = None,
    llm_client: Optional[LLMClient] = None,
) -> RepairPipeline:
    analyzer = AnalyzerEngine()
    return RepairPipeline(
        analyzer=analyzer,
        strategies=build_strategies(strategy_ids, settings, llm_client),
        validator=ValidationPipeline(sandbox, ScannerValidator(analyzer, build_scanners(settings))),
        store=store,
    )


def open_store(settings: Settings, path: Optional[Path] = None) -> ExperimentStore:
    return ExperimentStore(path or settings.experiment_db)
