# Core data model

All shared types live in `backend/src/cryptoaudit/models/` (Pydantic v2), with **one
representation per concept**: `Finding` is the only finding schema and every other model refers to
it. `api/schemas.py` only reshapes these models for HTTP responses.

## The main flow of types

| Step | Type | Defined in |
|---|---|---|
| Input file | `ModuleInput`, `RepositorySnapshot` | `scan.py` |
| Detection | `Finding`, `AnalysisResult` | `finding.py`, `analysis.py` |
| Repair input | `RepairRequest` (frozen, extra fields forbidden), `CodeContext` | `repair.py`, `context.py` |
| Repair output | `RepairResult`, `GenerationMetadata`, `Candidate` | `repair.py` |
| Integrity | `IntegrityReport` | `validation.py` |
| Validation | `GateResult` ×4, `ValidationReport` | `validation.py` |
| Decision | `CaseOutcome` with a `Verdict` | `experiment.py` |
| Explanation | `Explanation` | `explanation.py` |
| Website scan | `StrategyRunView`, `FileScanResult`, `RepositoryScanResult`, `ScanRecord` | `scan.py` |
| Benchmark | `CaseSpec`, `PublicCase`, `StrategyStats`, `RunInfo` | `benchmark.py`, `experiment.py` |

## Diagram

```mermaid
classDiagram
    direction LR

    class ModuleInput {
        module_name: str
        source: str
        case_id: str?
        allowed_libraries: tuple
        target_python: str
    }
    class RepositorySnapshot {
        full_name, ref, commit
        modules: ModuleInput[]
        skipped: SkippedFile[]
        archive_bytes: int
    }
    class Finding {
        rule_id: CR1..CR5
        category, severity, confidence
        file, line, column
        matched_api, evidence
        explanation, remediation
        analyzer_version, rule_version
    }
    class CodeContext {
        module_name, imports
        public_interface: SymbolSignature[]
        findings: FindingContext[]
        truncated, context_hash
    }
    class RepairRequest {
        <<frozen>>
        module_name, source
        findings: Finding[]
        context: CodeContext
        constraints: RepairConstraints
    }
    class RepairResult {
        strategy_id: S1..S4
        status: PRODUCED|NO_REPAIR|NOT_APPLICABLE|PARSE_ERROR
        candidate_code: str?
        repaired_finding_ids, unrepaired_finding_ids
        failure_reason, error_code
        generation: GenerationMetadata?
    }
    class GenerationMetadata {
        provider, model, prompt_version, prompt_hash
        temperature, seed, num_ctx, raw_output
    }
    class Candidate {
        candidate_id, module_name
        repair: RepairResult
        integrity: IntegrityReport
        diff: str
    }
    class IntegrityReport {
        passed, syntax_ok
        imports, issues: IntegrityIssue[]
    }
    class ValidationReport {
        candidate_id
        gates: GateResult[]
    }
    class GateResult {
        gate: V0..V3
        status: PASS|FAIL|ERROR|NOT_APPLICABLE|NOT_RUN
        gating: bool
        summary, checks: CheckResult[], evidence
    }
    class CaseOutcome {
        strategy_id, candidate_id, repair_status
        integrity_passed, gates, v3_gating
        scanner_results
        verdict: VERIFIED|UNVERIFIED|FAILED|NO_CANDIDATE
        reasons
    }
    class Explanation {
        source, verdict, headline
        sections: ExplanationSection[]
        limitations
    }
    class StrategyRunView {
        strategy_id, candidate_id, verdict
        candidate_code, diff, gates
        scanner_results, integrity, explanation
    }
    class FileScanResult {
        path, source, finding_ids
        baseline, runs: StrategyRunView[]
    }
    class RepositoryScanResult {
        repository, ref, commit
        strategies, skipped_strategies, skipped_files
        findings: FindingView[]
        files: FileScanResult[]
        summary: RepositoryScanSummary
    }
    class ScanRecord {
        scan_id, repository, ref
        status: QUEUED|RUNNING|COMPLETED|FAILED
        stages: StageProgress[]
        error, result, created_at, updated_at
    }

    RepositorySnapshot "1" o-- "*" ModuleInput
    ModuleInput ..> Finding : analysis_stage
    RepairRequest "1" o-- "*" Finding
    RepairRequest "1" *-- "1" CodeContext
    RepairRequest ..> RepairResult : strategy.repair()
    RepairResult "1" o-- "0..1" GenerationMetadata
    Candidate "1" *-- "1" RepairResult
    Candidate "1" *-- "1" IntegrityReport
    Candidate ..> ValidationReport : ValidationPipeline.validate()
    ValidationReport "1" *-- "4" GateResult
    ValidationReport ..> CaseOutcome : gates.decide()
    CaseOutcome ..> Explanation : reporting.explanation
    StrategyRunView ..> Explanation
    FileScanResult "1" *-- "*" StrategyRunView
    RepositoryScanResult "1" *-- "*" FileScanResult
    ScanRecord "1" o-- "0..1" RepositoryScanResult
```
