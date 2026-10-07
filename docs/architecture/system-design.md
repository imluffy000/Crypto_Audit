# CryptoAudit system design

```
Input ─► Analyzer ─► Findings ─► Context ─► Repair Engine (S1–S4) ─► Candidate code
                                                                         │
            Research findings ◄─ Experiment DB ◄─ Aggregation ◄─ Validation V0–V3
```

Principle: **GENERATE ≠ VALIDATE ≠ ACCEPT.** A repair is accepted (VERIFIED) only when
V1 PASS ∧ V2 PASS ∧ (V3 PASS where the case defines gating legacy artifacts). Scanner
results (V0) are recorded and analysed but never decide acceptance.

How data moves between stages and across the information boundary is described in
[data-flow.md](data-flow.md).

## Repository layout

```
.github/workflows/          ci.yml (Python tests), deploy.yml (frontend Pages)
benchmark/
├── cases/<rule>/<id>/      PUBLIC: vulnerable module.py + case.yaml
├── expected/<rule>/<id>/   HIDDEN: oracle.yaml + V1/V2/V3 check files
├── artifacts/<rule>/<id>/  HIDDEN: legacy data persisted by the original code
└── results/                local run output (git-ignored)
configs/rules.yaml          CR1–CR5 rule configuration
prompts/repair/             versioned LLM prompts (s3_v1.yaml, s4_v1.yaml)
docker/                     sandbox/ (validation runtime), api + web images, docker-compose, nginx
docs/                       architecture/, development/
frontend/                   React/Vite UI
src/cryptoaudit/
├── cli/          main.py: analyze, repair, bench list|run|report, serve
├── api/          app, services, jobs, dependencies, schemas, routes/ (auth, repos, scan, findings, reports)
├── ingest/       file_loader, directory_loader, filters, benchmark_loader (public views only),
│                 github_client (GitHub App API), git_loader (in-memory tarball ingestion)
├── analysis/     ast_parser, import_analyzer, call_analyzer, context_analyzer, literals, analyzer
├── rules/        base, registry, cr1_weak_hash … cr5_insecure_random
├── models/       finding, analysis, enums, context, scan, repair, validation, benchmark, experiment
├── context/      context_builder, context_budget, extractor, symbol_resolver, call_graph
├── llm/          client (protocol), ollama_client, schemas
├── repair/       base, registry, request, edits, s1_hint, s2_template, s3_llm, s4_migration,
│                 prompt_builder, parser
├── validation/   v0_scanner, v1_functional, v2_security, v3_compatibility, gates, runner,
│   │             checks, integrity, oracle (hidden loader)
│   ├── sandbox/  runners (Docker / local), harness (runs inside the sandbox)
│   └── scanners/ bandit, semgrep, process
├── pipeline/     orchestrator, stages, pipeline_result, factory, benchmark_runner
├── reporting/    console_report, json_report, markdown_report, research
├── storage/      sqlite (append-only experiment DB), jsonl (export), web_store (sessions, scan jobs)
├── config/       settings (CRYPTOAUDIT_* environment variables)
└── utils/        errors, hashing
tests/
├── unit/<package>/         mirrors src/cryptoaudit
├── integration/            analysis, validation (oracle validity) pipelines
├── e2e/                    full scan → repair → validate → store
└── fixtures/               analyzer fixtures, context fixtures, reference repairs (tests only)
```

Runtime output (`data/`, e.g. `data/experiments/experiments.sqlite`) is git-ignored.

## Components

| # | Component | Package | Key types |
|---|---|---|---|
| 1 | Input / ingestion | `ingest` | `load_module`, `iter_python_files`, `BenchmarkRepository` |
| 2 | Analyzer (CR1–CR5) | `analysis`, `rules` | `AnalyzerEngine`, `BaseRule`, `load_default_rules` |
| – | Shared models | `models` | `Finding`, `AnalysisResult`, `RepairRequest`, `ValidationReport`, `CaseOutcome` |
| – | Context Engine | `context` | `ContextBuilder`, `ContextBudget` |
| 3 | Repair Engine | `repair`, `llm` | `RepairStrategy`, S1–S4, `render_prompt`, `parse_llm_output` |
| 4 | Candidate + integrity | `models.repair`, `validation.integrity` | `Candidate`, `IntegrityChecker` |
| 5 | Validation V0–V3 | `validation` | `ValidationPipeline`, `ScannerValidator`, `FunctionalValidator`, `SecurityValidator`, `CompatibilityValidator` |
| 6 | Aggregation | `validation.gates`, `reporting.research` | `decide`, `build_outcome`, `compare_strategies` |
| 7 | Experiment database | `storage` | `ExperimentStore`, `export_jsonl` |
| 8 | Research analysis | `reporting` | `analyze`, `to_markdown` |
| 9 | User interface / output | `cli`, `api`, `frontend/`, `reporting` | website, `cryptoaudit repair`, `cryptoaudit bench …` |
| – | Website scan | `pipeline.repository_scan`, `api` | `RepositoryScanner`, staged progress, explanations |
| – | Orchestration | `pipeline` | `RepairPipeline`, stage functions, `BenchmarkRunner` |

## Repair strategies

| Id | Module | Behaviour |
|---|---|---|
| S1 | `repair/s1_hint.py` | Applies only a scanner's own machine-applicable fix (Bandit B324 `usedforsecurity=False`, Semgrep autofix) aligned with a CryptoAudit finding. Otherwise `NOT_APPLICABLE`. |
| S2 | `repair/s2_template.py` | Deterministic per-category AST transformations (CR1/CR3/CR4/CR5). No template ⇒ `NO_REPAIR` (e.g. CR2). |
| S3 | `repair/s3_llm.py` | Single-shot, temperature 0, fixed seed, versioned prompt, strict one-block parser (`PARSE_ERROR` otherwise). |
| S4 | `repair/s4_migration.py` | S3 plus a generic migration section (keep legacy reads, self-describing new format). |

Statuses: `PRODUCED`, `NO_REPAIR`, `NOT_APPLICABLE`, `PARSE_ERROR`. Only `PRODUCED` carries code;
the others become `NO_CANDIDATE` and are never counted as success.

## Validation gates

| Gate | Module | What runs | Gating |
|---|---|---|---|
| V0 | `v0_scanner.py` | CryptoAudit, Bandit, Semgrep re-scan of the candidate | Never |
| V1 | `v1_functional.py` | Syntax, public-interface preservation, functional checks | Yes |
| V2 | `v2_security.py` | Executable security-property checks (salting/KDF cost, no ECB/authenticated encryption, unique IVs, CSPRNG) | Yes |
| V3 | `v3_compatibility.py` | Legacy-artifact checks (CR1–CR4) | Where the case says so; `NOT_APPLICABLE` for CR5 |

Candidates must pass integrity checks (syntax, dependency allow-list, no process/network/dynamic
code surfaces) before they are executed. Execution happens in the sandbox: Docker by default
(`--network none`, read-only, memory/CPU/pids limits, no capabilities, user nobody). The local
sandbox is for trusted code only and requires an explicit opt-in.

## Reproducibility

Each benchmark run stores the configuration and its hash, CryptoAudit version, git commit, strategy
parameters (model, seed, temperature, prompt id and hash), raw LLM output, integrity and validation
reports, candidate code and diff. The store rejects UPDATE/DELETE.

## Usage

```sh
pip install -e ".[dev,web,scanners]"
uv tool install semgrep==1.163.0                              # isolated: conflicts with web deps
docker build -t cryptoaudit-sandbox:latest docker/sandbox     # isolated validation runtime
ollama pull codellama:7b-instruct                             # for S3/S4 (CRYPTOAUDIT_LLM_MODEL to change)

cryptoaudit analyze path/to/file.py
cryptoaudit repair path/to/file.py -s S1,S2,S3,S4 --show-code
cryptoaudit bench list
cryptoaudit bench run -s S1,S2,S3,S4
cryptoaudit bench report --markdown benchmark/results/report.md
```

Settings are environment variables with the `CRYPTOAUDIT_` prefix (see `cryptoaudit.config.settings.Settings`),
e.g. `CRYPTOAUDIT_SANDBOX=docker`, `CRYPTOAUDIT_SEMGREP_CONFIG=p/python`, `CRYPTOAUDIT_ENABLE_SEMGREP=false`.

## Known limitations

- The local sandbox is not an isolation boundary; use Docker for any LLM-generated or user code.
- The harness result nonce resists accidental or naive forgery, but code running in-process can
  still interfere with the harness; the Docker boundary protects the host, not result integrity
  against deliberately adversarial candidates.
- Semgrep registry configs (e.g. `p/python`) are fetched over the network and can change over time;
  the config and Semgrep version are recorded per run.
- The benchmark currently has one case per category; extend `benchmark/` for statistical power.
- Known analyzer precision issues (unchanged): CR5 flags `random.SystemRandom`, keyword matching on
  substrings (e.g. "auth" in "author"), and CR3/CR4 scope resolution by function name.
- Not yet built: risk scoring, SARIF/HTML reports, dependency graphs, a hosted deployment.
- Website scans of user repositories cannot reach Verified: there are no security-property oracles for
  arbitrary code, so V2/V3 are NOT_RUN and the code is never executed.
