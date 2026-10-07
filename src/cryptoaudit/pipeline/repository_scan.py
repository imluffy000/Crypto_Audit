"""
Repository scan: fetch -> parse -> analyze -> context -> repair -> validate -> explain -> report.

Used by the website. Repository code is analysed and repaired but never executed: user
repositories have no hidden oracle, so executable gates are NOT_RUN and the sandbox is never
invoked. Progress is reported per stage through a callback.
"""

import ast
from collections import Counter, defaultdict
from typing import Callable, Dict, List, Optional, Sequence, Tuple

from cryptoaudit.models.experiment import Verdict
from cryptoaudit.models.finding import Finding, finding_id
from cryptoaudit.models.repair import Candidate, RepairConstraints, RepairRequest, StrategyId
from cryptoaudit.models.scan import (
    STAGE_LABELS,
    FileScanResult,
    FindingView,
    ModuleInput,
    RepositoryScanResult,
    RepositoryScanSummary,
    RepositorySnapshot,
    ScanStage,
    SkippedFile,
    StageProgress,
    StageStatus,
    StrategyRunView,
)
from cryptoaudit.pipeline.orchestrator import RepairPipeline
from cryptoaudit.pipeline.stages import analysis_stage, candidate_stage, validation_stage
from cryptoaudit.repair.request import build_repair_request
from cryptoaudit.reporting.explanation import explain
from cryptoaudit.utils.errors import CryptoAuditError

ProgressCallback = Callable[[List[StageProgress]], None]

# Most useful first when choosing the verdict to show for a finding.
VERDICT_RANK = {Verdict.VERIFIED: 0, Verdict.UNVERIFIED: 1, Verdict.FAILED: 2, Verdict.NO_CANDIDATE: 3}


class RepositoryScanner:
    def __init__(
        self,
        pipeline: RepairPipeline,
        on_progress: Optional[ProgressCallback] = None,
        skipped_strategies: Optional[Dict[str, str]] = None,
    ) -> None:
        self.pipeline = pipeline
        self.on_progress = on_progress
        self.skipped_strategies = dict(skipped_strategies or {})
        self.stages = [StageProgress(stage=stage, label=STAGE_LABELS[stage]) for stage in ScanStage]

    # -- progress -------------------------------------------------------------------------

    def _stage(self, stage: ScanStage) -> StageProgress:
        return next(s for s in self.stages if s.stage is stage)

    def _update(self, stage: ScanStage, status: StageStatus, detail: str = "", current: int = 0, total: int = 0) -> None:
        progress = self._stage(stage)
        progress.status, progress.detail, progress.current, progress.total = status, detail, current, total
        if self.on_progress is not None:
            self.on_progress([s.model_copy() for s in self.stages])

    # -- run ------------------------------------------------------------------------------

    def run(self, fetch: Callable[[], RepositorySnapshot]) -> RepositoryScanResult:
        current = ScanStage.FETCH
        try:
            self._update(current, StageStatus.RUNNING, "Downloading the repository archive")
            snapshot = fetch()
            self._update(current, StageStatus.DONE, f"{len(snapshot.modules)} Python file(s) at {snapshot.commit or snapshot.ref}")

            current = ScanStage.PARSE
            modules, skipped = self._parse(snapshot)

            current = ScanStage.ANALYZE
            findings_by_file = self._analyze(modules)

            current = ScanStage.CONTEXT
            requests = self._context(modules, findings_by_file)

            current = ScanStage.REPAIR
            candidates = self._repair(modules, requests)

            current = ScanStage.VALIDATE
            validated, baselines = self._validate(modules, findings_by_file, candidates)

            current = ScanStage.EXPLAIN
            files = self._explain(modules, findings_by_file, validated, baselines)

            current = ScanStage.REPORT
            self._update(current, StageStatus.RUNNING, "Summarising results")
            result = self._report(snapshot, modules, skipped, findings_by_file, files)
            self._update(current, StageStatus.DONE, f"{result.summary.findings} finding(s) in {result.summary.files_with_findings} file(s)")
            return result
        except Exception as exc:
            message = exc.message if isinstance(exc, CryptoAuditError) else f"{type(exc).__name__}: {exc}"
            self._update(current, StageStatus.FAILED, message)
            raise

    def _parse(self, snapshot: RepositorySnapshot) -> Tuple[List[ModuleInput], List[SkippedFile]]:
        total = len(snapshot.modules)
        self._update(ScanStage.PARSE, StageStatus.RUNNING, "Parsing Python files", 0, total)
        modules, skipped = [], list(snapshot.skipped)
        for index, module in enumerate(snapshot.modules, 1):
            try:
                ast.parse(module.source)
                modules.append(module)
            except SyntaxError as exc:
                skipped.append(SkippedFile(path=module.module_name, reason=f"syntax error at line {exc.lineno}"))
            self._update(ScanStage.PARSE, StageStatus.RUNNING, module.module_name, index, total)
        self._update(ScanStage.PARSE, StageStatus.DONE, f"{len(modules)} parsed, {len(skipped)} skipped", total, total)
        return modules, skipped

    def _analyze(self, modules: Sequence[ModuleInput]) -> Dict[str, List[Finding]]:
        total = len(modules)
        findings_by_file: Dict[str, List[Finding]] = {}
        for index, module in enumerate(modules, 1):
            findings = analysis_stage(self.pipeline.analyzer, module)
            if findings:
                findings_by_file[module.module_name] = findings
            self._update(ScanStage.ANALYZE, StageStatus.RUNNING, module.module_name, index, total)
        count = sum(len(f) for f in findings_by_file.values())
        self._update(ScanStage.ANALYZE, StageStatus.DONE, f"{count} finding(s) in {len(findings_by_file)} file(s)", total, total)
        return findings_by_file

    def _context(self, modules: Sequence[ModuleInput], findings_by_file: Dict[str, List[Finding]]) -> Dict[str, RepairRequest]:
        targets = [m for m in modules if m.module_name in findings_by_file]
        if not targets:
            for stage in (ScanStage.CONTEXT, ScanStage.REPAIR, ScanStage.VALIDATE, ScanStage.EXPLAIN):
                self._update(stage, StageStatus.SKIPPED, "No cryptographic misuse found")
            return {}
        requests: Dict[str, RepairRequest] = {}
        for index, module in enumerate(targets, 1):
            constraints = RepairConstraints(allowed_libraries=module.allowed_libraries, target_python=module.target_python)
            requests[module.module_name] = build_repair_request(
                module.module_name, module.source, findings_by_file[module.module_name], constraints, self.pipeline.context_builder
            )
            self._update(ScanStage.CONTEXT, StageStatus.RUNNING, module.module_name, index, len(targets))
        self._update(ScanStage.CONTEXT, StageStatus.DONE, f"Context built for {len(targets)} file(s)", len(targets), len(targets))
        return requests

    def _repair(self, modules: Sequence[ModuleInput], requests: Dict[str, RepairRequest]) -> Dict[str, List[Candidate]]:
        if not requests:
            return {}
        by_name = {m.module_name: m for m in modules}
        total = len(requests) * len(self.pipeline.strategies)
        done = 0
        candidates: Dict[str, List[Candidate]] = defaultdict(list)
        for path, request in requests.items():
            for strategy in self.pipeline.strategies:
                candidates[path].append(candidate_stage(strategy, request, by_name[path], self.pipeline.integrity))
                done += 1
                self._update(ScanStage.REPAIR, StageStatus.RUNNING, f"{strategy.strategy_id.value} on {path}", done, total)
        produced = sum(c.repair.produced for cs in candidates.values() for c in cs)
        detail = f"{produced} candidate(s) from {', '.join(s.strategy_id.value for s in self.pipeline.strategies)}"
        if self.skipped_strategies:
            detail += f"; skipped {', '.join(sorted(self.skipped_strategies))}"
        self._update(ScanStage.REPAIR, StageStatus.DONE, detail, total, total)
        return candidates

    def _validate(self, modules, findings_by_file, candidates):
        if not candidates:
            return {}, {}
        by_name = {m.module_name: m for m in modules}
        total = sum(len(c) for c in candidates.values())
        done = 0
        validated: Dict[str, list] = defaultdict(list)
        baselines: Dict[str, dict] = {}
        for path, file_candidates in candidates.items():
            module = by_name[path]
            rule_ids = sorted({f.rule_id for f in findings_by_file[path]})
            baselines[path] = self.pipeline.validator.scanner_validator.scan(module.source, path, rule_ids)
            for candidate in file_candidates:
                report, outcome = validation_stage(self.pipeline.validator, candidate, module, rule_ids, None, None)
                validated[path].append((candidate, report, outcome))
                done += 1
                self._update(ScanStage.VALIDATE, StageStatus.RUNNING, f"{candidate.repair.strategy_id.value} on {path}", done, total)
        self._update(ScanStage.VALIDATE, StageStatus.DONE, f"{total} candidate(s) validated", total, total)
        return validated, baselines

    def _explain(self, modules, findings_by_file, validated, baselines) -> List[FileScanResult]:
        if not validated:
            return []
        by_name = {m.module_name: m for m in modules}
        total = sum(len(v) for v in validated.values())
        done = 0
        files: List[FileScanResult] = []
        for path, items in validated.items():
            findings = findings_by_file[path]
            runs = []
            for candidate, report, outcome in items:
                runs.append(
                    StrategyRunView(
                        strategy_id=candidate.repair.strategy_id,
                        candidate_id=candidate.candidate_id,
                        repair_status=candidate.repair.status,
                        failure_reason=candidate.repair.failure_reason,
                        verdict=outcome.verdict,
                        reasons=outcome.reasons,
                        candidate_code=candidate.code,
                        diff=candidate.diff,
                        gates=report.gates,
                        scanner_results=outcome.scanner_results,
                        integrity=candidate.integrity,
                        repaired_finding_ids=candidate.repair.repaired_finding_ids,
                        unrepaired_finding_ids=candidate.repair.unrepaired_finding_ids,
                        explanation=explain(findings, by_name[path].source, candidate, report, outcome, has_oracle=False),
                    )
                )
                done += 1
                self._update(ScanStage.EXPLAIN, StageStatus.RUNNING, path, done, total)
            files.append(
                FileScanResult(
                    path=path,
                    source=by_name[path].source,
                    finding_ids=[finding_id(f) for f in findings],
                    baseline=baselines.get(path, {}),
                    runs=runs,
                )
            )
        self._update(ScanStage.EXPLAIN, StageStatus.DONE, f"{total} explanation(s)", total, total)
        return files

    def _report(self, snapshot, modules, skipped, findings_by_file, files) -> RepositoryScanResult:
        runs_by_file = {f.path: f.runs for f in files}
        views: List[FindingView] = []
        for path, findings in sorted(findings_by_file.items()):
            for finding in findings:
                fid = finding_id(finding)
                relevant = [r for r in runs_by_file.get(path, []) if fid in r.repaired_finding_ids] or runs_by_file.get(path, [])
                best = min((r.verdict for r in relevant), key=VERDICT_RANK.__getitem__, default=Verdict.NO_CANDIDATE)
                views.append(FindingView(finding_id=fid, finding=finding, best_verdict=best))

        verdicts: Dict[str, Counter] = defaultdict(Counter)
        clean_not_verified = 0
        for runs in runs_by_file.values():
            for run in runs:
                verdicts[run.strategy_id.value][run.verdict.value] += 1
                v0 = next((g for g in run.gates if g.gate.value == "V0"), None)
                if v0 is not None and v0.status.value == "PASS" and run.verdict is not Verdict.VERIFIED:
                    clean_not_verified += 1

        summary = RepositoryScanSummary(
            files_scanned=len(modules),
            files_with_findings=len(findings_by_file),
            findings=len(views),
            findings_by_rule=dict(sorted(Counter(v.finding.rule_id for v in views).items())),
            verdicts_by_strategy={k: dict(v) for k, v in sorted(verdicts.items())},
            scanner_clean_not_verified=clean_not_verified,
        )
        return RepositoryScanResult(
            repository=snapshot.full_name,
            ref=snapshot.ref,
            commit=snapshot.commit,
            strategies=[s.strategy_id for s in self.pipeline.strategies],
            skipped_strategies=self.skipped_strategies,
            skipped_files=skipped,
            findings=views,
            files=files,
            summary=summary,
        )


def select_web_strategies(llm_available: bool, llm_reason: str = "Ollama or the configured model is unavailable") -> Tuple[List[StrategyId], Dict[str, str]]:
    """S1 and S2 always run; S3/S4 only when a local LLM can serve the configured model."""
    strategies = [StrategyId.S1, StrategyId.S2]
    if llm_available:
        return strategies + [StrategyId.S3, StrategyId.S4], {}
    return strategies, {StrategyId.S3.value: llm_reason, StrategyId.S4.value: llm_reason}
