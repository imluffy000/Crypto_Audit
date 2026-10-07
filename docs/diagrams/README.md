# CryptoAudit diagrams

Each page explains one part of CryptoAudit in prose and tables, followed by a
[Mermaid](https://mermaid.js.org) diagram. GitHub and VS Code (with a Mermaid-enabled Markdown
preview) render the diagrams directly.

## Start here

| # | Page | What it explains |
|---|---|---|
| 01 | [System architecture](01-system-architecture.md) | Every major component and how they connect; the design rules |
| 02 | [Website scan, end to end](02-website-scan-sequence.md) | From choosing a repository to reading results |
| 19 | [Repository layout](19-repository-layout.md) | Where everything lives |

## How it works

| # | Page | What it explains |
|---|---|---|
| 03 | [Sign-in, switch account, sign-out](03-auth-sequence.md) | GitHub OAuth flow, sessions, token storage and revocation |
| 04 | [Scan lifecycle](04-scan-lifecycle.md) | Scan states and the eight pipeline stages |
| 05 | [Repository ingestion](05-ingestion.md) | Reading the tarball and `.zip` archives safely, limits and skip reasons |
| 06 | [Deterministic analyzer](06-analyzer.md) | How CR1–CR5 findings are detected |
| 07 | [Repair strategies S1–S4](07-repair-strategies.md) | Scanner hints, templates, LLM repairs and their statuses |
| 08 | [Language model routing](08-llm-routing.md) | Ollama / OpenRouter selection and the context budget |
| 09 | [Validation and verdict](09-validation-and-verdict.md) | Integrity checks, V0–V3 gates and how the verdict is decided |
| 10 | [Benchmark and hidden tests](10-benchmark-information-boundary.md) | Why generation never sees the tests, and how that is enforced |
| 11 | [Sandboxed execution](11-sandbox-execution.md) | How benchmark checks run in Docker |
| 12 | [Data model](12-data-model.md) | The shared types from input to verdict |
| 16 | [Deployment](16-deployment.md) | Local development, Docker Compose and CI |

## Every file

| # | Page | Covers |
|---|---|---|
| 13 | [Backend files 1/3](13-backend-files-input-analysis.md) | `ingest/`, `analysis/`, `rules/`, `context/`, `models/`, `config/`, `utils/` |
| 14 | [Backend files 2/3](14-backend-files-repair-validation.md) | `repair/`, `llm/`, `validation/`, `prompts/` |
| 15 | [Backend files 3/3](15-backend-files-api-pipeline.md) | `api/` (with every endpoint), `pipeline/`, `reporting/`, `storage/`, `cli/` |
| 17 | [Frontend files](17-frontend-files.md) | Every file in `frontend/src/` |
| 18 | [Frontend routes](18-frontend-navigation.md) | Routes, pages and the API calls each page makes |

For more detail see [architecture/system-design.md](../architecture/system-design.md),
[architecture/data-flow.md](../architecture/data-flow.md) and
[development/website.md](../development/website.md).
