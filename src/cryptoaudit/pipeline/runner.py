"""Benchmark runner: every case x every configured strategy, persisted as one experiment run."""

import subprocess
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence

from cryptoaudit.benchmark.oracle import load_oracle
from cryptoaudit.benchmark.repository import BenchmarkRepository
from cryptoaudit.ingest.loader import from_public_case
from cryptoaudit.pipeline.orchestrator import ModuleRun, RepairPipeline
from cryptoaudit.storage.experiment_store import ExperimentStore, RunInfo
from cryptoaudit.utils.errors import CryptoAuditError


def current_git_commit(cwd: Optional[Path] = None) -> Optional[str]:
    try:
        proc = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, timeout=10, cwd=cwd)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return proc.stdout.strip() or None if proc.returncode == 0 else None


class BenchmarkRunner:
    def __init__(self, repository: BenchmarkRepository, pipeline: RepairPipeline, store: ExperimentStore) -> None:
        if pipeline.store is not store:
            raise ValueError("pipeline must write to the runner's experiment store")
        self.repository = repository
        self.pipeline = pipeline
        self.store = store

    def run(
        self,
        config: Dict[str, Any],
        case_ids: Optional[Sequence[str]] = None,
        on_case: Optional[Callable[[str, ModuleRun], None]] = None,
        on_error: Optional[Callable[[str, CryptoAuditError], None]] = None,
    ) -> RunInfo:
        selected = list(case_ids) if case_ids else self.repository.case_ids()
        info = self.store.start_run({**config, "case_ids": selected}, git_commit=current_git_commit(Path(__file__).parent))
        for case_id in selected:
            case = self.repository.public_case(case_id)
            oracle = load_oracle(self.repository, case_id)  # handed to validation only
            try:
                module_run = self.pipeline.run_module(from_public_case(case), oracle=oracle, run_id=info.run_id)
            except CryptoAuditError as exc:
                if on_error is not None:
                    on_error(case_id, exc)
                continue
            if on_case is not None:
                on_case(case_id, module_run)
        return info


def describe_strategies(strategies: List[Any]) -> List[Dict[str, Any]]:
    """Reproducibility description of the configured strategies."""
    described = []
    for strategy in strategies:
        entry: Dict[str, Any] = {"strategy_id": strategy.strategy_id.value, "class": type(strategy).__name__}
        for attribute in ("model", "seed", "temperature", "max_tokens", "template_name", "min_iterations"):
            if hasattr(strategy, attribute):
                entry[attribute] = getattr(strategy, attribute)
        if hasattr(strategy, "scanners"):
            entry["scanners"] = [s.name for s in strategy.scanners]
        described.append(entry)
    return described
