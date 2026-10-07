# CryptoAudit architecture

```
Input ─► Analyzer ─► Findings ─► Context ─► Repair Engine (S1–S4) ─► Candidate code
                                                                         │
            Research findings ◄─ Experiment DB ◄─ Aggregation ◄─ Validation V0–V3
```

Principle: **GENERATE ≠ VALIDATE ≠ ACCEPT.** A repair is accepted (VERIFIED) only when
V1 PASS ∧ V2 PASS ∧ (V3 PASS where the case defines gating legacy artifacts). Scanner
results (V0) are recorded and analysed but never decide acceptance.

## Components

| # | Component | Package | Key types |
|---|---|---|---|
| 1 | Input / ingestion | `cryptoaudit.ingest`, `cryptoaudit.benchmark` | `ModuleInput`, `PublicCase`, `BenchmarkRepository` |
| 2 | Analyzer (CR1–CR5) | `cryptoaudit.analyzer` | `AnalyzerEngine`, `Finding`, `AnalysisResult` (unchanged contracts) |
| – | Context Engine | `cryptoaudit.context` | `ContextBuilder`, `CodeContext` |
| 3 | Repair Engine | `cryptoaudit.repair`, `cryptoaudit.llm` | `RepairStrategy`, `RepairRequest`, `RepairResult`, `RepairStatus` |
| 4 | Candidate + integrity checks | `cryptoaudit.candidate` | `Candidate`, `IntegrityChecker`, `IntegrityReport` |
| 5 | Validation V0–V3 | `cryptoaudit.validation`, `cryptoaudit.scanners` | `ValidationPipeline`, `GateResult`, `DockerSandbox` |
| 6 | Results aggregation | `cryptoaudit.aggregation` | `decide()`, `CaseOutcome`, `Verdict`, `StrategyStats` |
| 7 | Experiment database | `cryptoaudit.storage` | `ExperimentStore` (append-only SQLite) |
| 8 | Research analysis | `cryptoaudit.evaluation` | `analyze()`, `ResearchFindings` |
| 9 | User interface / output | `cryptoaudit.cli`, `cryptoaudit.reporting` | `cryptoaudit repair`, `cryptoaudit bench …` |
| – | Orchestration | `cryptoaudit.pipeline` | `RepairPipeline`, `BenchmarkRunner` |

## Repair strategies

| Id | Strategy | Behaviour |
|---|---|---|
| S1 | Tool-guided | Applies only a scanner's own machine-applicable fix (Bandit B324 `usedforsecurity=False`, Semgrep autofix) aligned with a CryptoAudit finding. Otherwise `NOT_APPLICABLE`. |
| S2 | Template | Deterministic per-category AST transformations (CR1/CR3/CR4/CR5). No template ⇒ `NO_REPAIR` (e.g. CR2). |
| S3 | Local LLM | Single-shot, temperature 0, fixed seed, versioned prompt, strict one-block parser (`PARSE_ERROR` otherwise). |
| S4 | Migration-aware LLM | S3 plus a generic migration section (keep legacy reads, self-describing new format). |

Statuses: `PRODUCED`, `NO_REPAIR`, `NOT_APPLICABLE`, `PARSE_ERROR`. Only `PRODUCED` carries code;
the others become `NO_CANDIDATE` and are never counted as success.

## Validation gates

| Gate | What runs | Gating |
|---|---|---|
| V0 | CryptoAudit, Bandit, Semgrep re-scan of the candidate | Never |
| V1 | Syntax, public-interface preservation, hidden functional checks | Yes |
| V2 | Hidden executable security-property checks (salting/KDF cost, no ECB/authenticated encryption, unique IVs, CSPRNG) | Yes |
| V3 | Hidden legacy-artifact checks (CR1–CR4) | Where the case says so; `NOT_APPLICABLE` for CR5 |

Candidates must pass integrity checks (syntax, dependency allow-list, no process/network/dynamic
code surfaces) before they are executed. Execution happens in the sandbox: Docker by default
(`--network none`, read-only, memory/CPU/pids limits, no capabilities, user nobody). The local
sandbox is for trusted code only and requires an explicit opt-in.

## Information boundary

- Strategies receive a frozen `RepairRequest` (`extra="forbid"`) built from public input only.
- `benchmark/cases/*/hidden/` is read only by `cryptoaudit.benchmark.oracle`; an import-boundary test
  keeps `repair`, `context`, `llm` and `scanners` from importing it.
- Hidden files carry canaries; end-to-end tests assert no canary reaches any prompt or request.
- Reference repairs live only in `tests/fixtures/reference_repairs/` to prove oracle validity.

## Reproducibility

Each benchmark run stores the configuration and its hash, CryptoAudit version, git commit, strategy
parameters (model, seed, temperature, prompt version/hash), raw LLM output, integrity and validation
reports, candidate code and diff. The store rejects UPDATE/DELETE.

## Usage

```sh
pip install -e ".[dev,scanners]"
docker build -t cryptoaudit-sandbox:latest docker/sandbox     # isolated validation runtime
ollama pull codellama:7b-instruct                             # for S3/S4 (CRYPTOAUDIT_LLM_MODEL to change)

cryptoaudit analyze path/to/file.py
cryptoaudit repair path/to/file.py -s S1,S2,S3,S4 --show-code
cryptoaudit bench list
cryptoaudit bench run -s S1,S2,S3,S4 --db data/experiments.sqlite
cryptoaudit bench report --db data/experiments.sqlite --markdown results.md
```

Settings are environment variables with the `CRYPTOAUDIT_` prefix (see `cryptoaudit.core.config.Settings`),
e.g. `CRYPTOAUDIT_SANDBOX=docker`, `CRYPTOAUDIT_SEMGREP_CONFIG=p/python`, `CRYPTOAUDIT_ENABLE_SEMGREP=false`.

## Known limitations

- The local sandbox is not an isolation boundary; use Docker for any LLM-generated or user code.
- The harness result nonce resists accidental or naive forgery, but code running in-process can
  still interfere with the harness; the Docker boundary protects the host, not result integrity
  against deliberately adversarial candidates.
- Semgrep registry configs (e.g. `p/python`) are fetched over the network and can change over time;
  the config and Semgrep version are recorded per run.
- The benchmark currently has one case per category; extend `benchmark/cases/` for statistical power.
- Known analyzer precision issues (unchanged here): CR5 flags `random.SystemRandom`, keyword
  matching on substrings (e.g. "auth" in "author"), and CR3/CR4 scope resolution by function name.
