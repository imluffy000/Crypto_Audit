"""Builds pipeline components from Settings (dependency wiring in one place)."""

from pathlib import Path
from typing import List, Optional, Sequence

from cryptoaudit.analysis.analyzer import AnalyzerEngine
from cryptoaudit.config.settings import Settings
from cryptoaudit.llm.client import LLMClient, OllamaClient
from cryptoaudit.models.repair import StrategyId
from cryptoaudit.models.scan import Scanner
from cryptoaudit.pipeline.orchestrator import RepairPipeline
from cryptoaudit.repair.base import RepairStrategy
from cryptoaudit.repair.strategies import (
    LLMRepairStrategy,
    MigrationAwareRepairStrategy,
    TemplateRepairStrategy,
    ToolGuidedRepairStrategy,
)
from cryptoaudit.scanners.bandit import BanditScanner
from cryptoaudit.scanners.semgrep import SemgrepScanner
from cryptoaudit.storage.experiment_store import ExperimentStore
from cryptoaudit.utils.errors import CryptoAuditError, ErrorCode
from cryptoaudit.validation.gates import ScannerValidator
from cryptoaudit.validation.pipeline import ValidationPipeline
from cryptoaudit.validation.sandbox import DockerSandbox, LocalProcessSandbox, Sandbox


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
            llm = llm or OllamaClient(settings.llm_base_url, timeout=settings.llm_timeout)
            cls = LLMRepairStrategy if sid is StrategyId.S3 else MigrationAwareRepairStrategy
            strategies.append(
                cls(llm, model=settings.llm_model, temperature=settings.llm_temperature, seed=settings.llm_seed)
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
