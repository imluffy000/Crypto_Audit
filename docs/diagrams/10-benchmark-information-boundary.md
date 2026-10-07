# Research benchmark and the hidden-test boundary

Generation must never see how it will be judged, otherwise a strategy (especially a language model)
could overfit to the tests. The benchmark therefore splits every case into public and hidden parts.

## Layout (`backend/benchmark/`)

| Path | Visibility | Contents |
|---|---|---|
| `cases/<rule>/<id>/` | Public | Vulnerable `module.py` and `case.yaml` (allowed libraries, target Python) |
| `expected/<rule>/<id>/` | Hidden | `oracle.yaml` and the V1/V2/V3 check files |
| `artifacts/<rule>/<id>/` | Hidden | Legacy data written by the original code, used by V3 |
| `results/` | Local | Run output (git-ignored) |

## How the boundary is enforced

- `ingest/benchmark_loader.py` reads only `cases/` and returns a `PublicCase`.
- `validation/oracle.py` is the **only** reader of `expected/` and `artifacts/`.
- An import-boundary test fails if `repair`, `context`, `llm`, `ingest`, `analysis` or `rules`
  imports anything from `validation`.
- Hidden files contain canary strings; tests assert that none reaches a prompt or `RepairRequest`.
- Strategies are single-shot: no validation result is ever fed back to generation.

## Running it

`cryptoaudit bench run -s S1,S2,S3,S4` runs every case with every strategy as one run.
Results go to an append-only SQLite database (`storage/sqlite.py` rejects `UPDATE`/`DELETE`) with
the configuration hash, version, git commit, model, seed, prompt hash, raw model output, candidate
code, diff and gate reports. `cryptoaudit bench report` turns them into per-strategy statistics.

## Diagram

```mermaid
flowchart LR
    subgraph PUBLIC["Public side — may be read by generation"]
        cases[("benchmark/cases/<br/>module.py · case.yaml")]
        loader["ingest/benchmark_loader.py<br/>PublicCase only"]
        analyzer["analysis/ + rules/"]
        request["repair/request.py<br/>frozen RepairRequest<br/>(extra fields forbidden)"]
        strategies["repair/ S1–S4<br/>+ llm/ + prompts/"]
        cases --> loader --> analyzer --> request --> strategies
    end

    subgraph HIDDEN["Hidden side — validation only"]
        expected[("benchmark/expected/<br/>oracle.yaml · V1/V2/V3 checks")]
        artifacts[("benchmark/artifacts/<br/>legacy data")]
        oracle["validation/oracle.py<br/>HiddenOracle"]
        runner["validation/runner.py<br/>V0–V3 + sandbox"]
        expected & artifacts --> oracle --> runner
    end

    strategies -- "Candidate (untrusted code)" --> integrity["validation/integrity.py"] --> runner
    runner --> gates{"validation/gates.py<br/>verdict"}
    gates --> store[("storage/sqlite.py<br/>append-only experiment DB")]
    store --> research["reporting/research.py<br/>StrategyStats per strategy × rule"]
    research --> report[/"cryptoaudit bench report<br/>console / Markdown"/]

    runner -. "NO feedback to generation" .-x strategies
    oracle -. "never imported by public packages<br/>(import-boundary test)" .-x request

    cli["cli: cryptoaudit bench run -s S1,S2,S3,S4"] --> runnerjob["pipeline/benchmark_runner.py<br/>every case × every strategy = one run"]
    runnerjob --> loader

    classDef pub fill:#e7f4ed,stroke:#17784a,color:#0b3320
    classDef hid fill:#fbe9e6,stroke:#bf3120,color:#4a120b
    class cases,loader,analyzer,request,strategies pub
    class expected,artifacts,oracle,runner hid
```
