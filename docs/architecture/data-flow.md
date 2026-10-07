# CryptoAudit data flow

## One module through the pipeline

```
ModuleInput (models.scan)                         ingest/
   │  source text + public config (allowed libraries, target Python, case id)
   ▼
analysis_stage ─► List[Finding] (models.finding)  analysis/ + rules/   deterministic, paths normalised
   │
   ▼
build_repair_request ─► RepairRequest             context/ + repair/request.py
   │  findings + CodeContext (bounded, hashed) + RepairConstraints; frozen, extra fields forbidden
   ▼
candidate_stage, per strategy S1–S4 ─► Candidate  repair/ + validation/integrity.py
   │  RepairResult (status, code, generation metadata) + IntegrityReport + diff
   ▼
validation_stage ─► ValidationReport + CaseOutcome validation/ (runner, v0–v3, gates)
   │  V0 scanners (evidence) · V1/V2/V3 in the sandbox · verdict from V1 ∧ V2 ∧ V3-if-gating
   ▼
ExperimentStore.record (append-only)               storage/
   ▼
reporting.research.analyze ─► ResearchFindings     reporting/
```

Stage functions live in `pipeline/stages.py`; `pipeline/orchestrator.py` wires them for one module
and `pipeline/benchmark_runner.py` repeats it for every case × strategy as one experiment run.

## Information boundary

| Data | Produced by | May be read by | Must never reach |
|---|---|---|---|
| `benchmark/cases/` (module, case.yaml) | corpus authors | everything | – |
| `benchmark/expected/` (oracles) | corpus authors | `validation/` only | repair, context, llm, prompts |
| `benchmark/artifacts/` (legacy data) | original module | `validation/` only | repair, context, llm, prompts |
| `RepairRequest` | `repair/request.py` | strategies S1–S4 | – (cannot carry extra fields) |
| Candidate code | strategies | integrity checks, sandbox | host interpreter (never executed outside the sandbox) |
| `ValidationReport` | `validation/` | aggregation, storage, reporting | strategies (no feedback loop) |

Enforcement:

- `ingest/benchmark_loader.py` reads only `cases/`; `validation/oracle.py` is the only reader of
  `expected/` and `artifacts/`.
- An import-boundary test fails if `repair`, `context`, `llm`, `ingest`, `analysis` or `rules`
  imports anything from `validation`.
- Hidden files carry canaries; end-to-end tests assert none appears in any prompt or request.
- Strategies are single-shot: validation results are never fed back into generation.

## Validation inside the sandbox

```
host                                         sandbox (Docker: no network, read-only, nobody)
────                                         ───────────────────────────────────────────────
candidate.py ─┐
checks.py  ───┼─ copied to a temp work dir ─► python -I -B harness.py
artifacts/ ───┘   (+ per-run nonce env var)      for each check_*(ctx): PASS / FAIL
                                                 prints CRYPTOAUDIT_RESULT:<nonce>:{json}
GateResult ◄─ parse nonce-tagged line ◄──────── stdout
```

A missing or unparseable result line, a broken oracle or an unavailable sandbox is an `ERROR`
(validator could not evaluate), never a `PASS`.
