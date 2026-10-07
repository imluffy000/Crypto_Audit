# CryptoAudit

CryptoAudit finds cryptographic misuse in Python code, proposes repairs and validates each repair
independently. Every result comes with the reason it was or was not accepted.

It runs as a website: sign in with GitHub, choose a repository and review the findings, the repaired
code and the validation evidence side by side. The same engine is also available as a command-line
tool and a research benchmark.

```
GitHub sign-in → fetch (read-only) → parse → CR1–CR5 analysis → context → repair (S1–S4)
              → candidate integrity → validation (V0–V3) → comparison + explanation → results
```

The design principle is **generate ≠ validate ≠ accept**. A repair is never accepted just because a
language model produced it, or because a scanner no longer complains about it.

---

## Contents

- [What it detects](#what-it-detects)
- [How a repair is judged](#how-a-repair-is-judged)
- [Quick start (website)](#quick-start-website)
- [Language models for S3/S4](#language-models-for-s3s4)
- [Configuration](#configuration)
- [Command-line and research benchmark](#command-line-and-research-benchmark)
- [Repository structure](#repository-structure)
- [Frontend](#frontend)
- [Testing](#testing)
- [Security and privacy](#security-and-privacy)
- [Known limitations](#known-limitations)
- [Documentation](#documentation)
- [License](#license)

---

## What it detects

A deterministic, AST-based analyzer checks five rules. No language model is involved in detection.

| Rule | Misuse | Example |
|---|---|---|
| **CR1** | Weak hashing for stored credentials | `hashlib.md5(password.encode())` |
| **CR2** | Weak or unauthenticated encryption mode | AES in ECB mode |
| **CR3** | Static or reused IV / nonce | a constant IV passed to `modes.CBC(...)` |
| **CR4** | Weak KDF parameters or static salt | PBKDF2 with 1,000 iterations or a hard-coded salt |
| **CR5** | Weak randomness for security tokens | `random.choice` used to build a session token |

Rules are configured in [`backend/configs/rules.yaml`](backend/configs/rules.yaml). Each finding
records its rule, severity, confidence, location, matched API, evidence and remediation guidance.

## How a repair is judged

### Repair strategies

| Id | Strategy | Behaviour |
|---|---|---|
| **S1** | Scanner hint | Applies a scanner's own machine-applicable fix (e.g. Bandit B324) when it matches a CryptoAudit finding |
| **S2** | Template | Deterministic AST transformations per rule (CR1, CR3, CR4, CR5) |
| **S3** | LLM | Single-shot, temperature 0, fixed seed, versioned prompt, strict output parser |
| **S4** | Migration-aware LLM | S3 plus guidance to keep legacy data readable |

S1 and S2 always run. S3 and S4 run when a language model is available (see
[Language models](#language-models-for-s3s4)). A strategy that cannot produce code reports
`NO_REPAIR`, `NOT_APPLICABLE` or `PARSE_ERROR`. Those results become **No candidate** and are never
counted as success.

### Validation gates

| Gate | What runs | Decides the verdict? |
|---|---|---|
| **V0** | Re-scan of the candidate with CryptoAudit, Bandit and Semgrep | No, evidence only |
| **V1** | Syntax, public-interface preservation, functional checks | Yes |
| **V2** | Executable security-property checks (salting and KDF cost, authenticated encryption, unique IVs, CSPRNG) | Yes |
| **V3** | Compatibility with data written by the original code | Where applicable |

Before anything is executed, each candidate must pass integrity checks: it must parse, use only allowed
dependencies, and contain no process, network or dynamic-code surfaces. Benchmark validation runs in a
Docker sandbox with no network, a read-only filesystem, resource limits and no capabilities.

### Verdicts

| Verdict | Meaning |
|---|---|
| **Verified** | V1, V2 and applicable V3 checks passed |
| **Unverified** | Plausible repair (integrity, syntax and interface checks passed) but security properties were not tested |
| **Failed** | An integrity check or a gating validation gate failed |
| **No candidate** | The strategy produced no code |

> **Repositories scanned through the website are never executed.** They have no hidden
> security-property tests (those exist only for the benchmark), so V2/V3 cannot run and
> **Unverified is the best possible verdict** for repository code. A clean scanner result is
> shown for comparison, but it is not proof that the code is secure.

---

## Quick start (website)

### Prerequisites

- Python **3.11+** (the CI tests 3.11 and 3.12)
- Node.js **20.19+ or 22.12+** (required by Vite 8)
- A GitHub account to register an OAuth App
- Optional: [Ollama](https://ollama.com) or an [OpenRouter](https://openrouter.ai) key for S3/S4
- Optional: Docker, for the validation sandbox and the compose setup

### 1. Register a GitHub OAuth App (one time)

GitHub → **Settings → Developer settings → OAuth Apps → New OAuth App**

| Field | Value |
|---|---|
| Homepage URL | `http://localhost:5173` |
| Authorization callback URL | `http://localhost:5173/api/auth/github/callback` |

Copy the **Client ID** and generate a **client secret**.

### 2. Configure the backend

```sh
cd backend
cp .env.example .env
python -c "import secrets; print(secrets.token_urlsafe(48))"   # use as CRYPTOAUDIT_SESSION_SECRET
```

Fill in `CRYPTOAUDIT_GITHUB_CLIENT_ID`, `CRYPTOAUDIT_GITHUB_CLIENT_SECRET` and
`CRYPTOAUDIT_SESSION_SECRET` in `backend/.env`. The file is git-ignored; never commit it.

### 3. Run

```sh
# Terminal 1: API on http://127.0.0.1:8000 (run from backend/ so .env is found)
cd backend
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -e ".[web,scanners]"
cryptoaudit serve

# Terminal 2: website on http://localhost:5173 (proxies /api to the backend)
cd frontend
npm install
npm run dev
```

Open <http://localhost:5173>, sign in with GitHub, choose a repository and start a scan.

If the API runs on another port, point the dev proxy at it, for example
`CRYPTOAUDIT_API_URL=http://localhost:8001 npm run dev`.

### Run with Docker instead

```sh
docker compose -f docker/docker-compose.yml up --build                   # http://localhost:5173
docker compose -f docker/docker-compose.yml --profile llm up --build     # also starts Ollama
```

### Repository access

| `CRYPTOAUDIT_GITHUB_REPO_ACCESS` | Scopes requested | What can be scanned |
|---|---|---|
| `private` (default) | `read:user repo` | Public and private repositories, collaborations, organisation repositories |
| `public` | `read:user` | Public repositories only |

GitHub has no read-only scope for private repositories, so the consent screen for `private` says
"Full control of private repositories". CryptoAudit only ever sends read requests (repository list,
file tree, archive download), and signing out revokes the token at GitHub.

---

## Language models for S3/S4

S3, S4 and the optional plain-language summary on a finding need a language model. Without one, scans
run S1 and S2 and the results page lists S3/S4 as skipped.

| `CRYPTOAUDIT_LLM_PROVIDER` | Behaviour |
|---|---|
| `ollama` | Local model only. Code never leaves the machine. |
| `openrouter` | Hosted model through OpenRouter. |
| `auto` (default) | Ollama when its model is available, otherwise OpenRouter if a key is set. |

```sh
# Local
ollama pull qwen2.5-coder:7b             # default CRYPTOAUDIT_LLM_MODEL

# Hosted fallback, in backend/.env
CRYPTOAUDIT_OPENROUTER_API_KEY=sk-or-...
CRYPTOAUDIT_OPENROUTER_MODEL=qwen/qwen-2.5-coder-32b-instruct
```

> **Privacy:** with OpenRouter, the files being repaired, including private repository code, are
> sent to OpenRouter and the model provider it routes to. Every LLM result records which provider
> and model produced it.

The prompt plus the complete repaired file must fit in the context window
(`CRYPTOAUDIT_LLM_NUM_CTX`, default 8192 for Ollama). Files that don't fit are recorded as
`NO_REPAIR` and are never truncated. Prompts are versioned in [`backend/prompts/`](backend/prompts/).

---

## Configuration

All settings are `CRYPTOAUDIT_*` environment variables, read from the environment or from
`backend/.env`. [`backend/.env.example`](backend/.env.example) documents every one. The most
important:

| Setting | Default | Purpose |
|---|---|---|
| `CRYPTOAUDIT_PUBLIC_URL` | `http://localhost:5173` | Browser-facing origin; the OAuth callback is `<public_url>/api/auth/github/callback` |
| `CRYPTOAUDIT_COOKIE_SECURE` | `false` | Set to `true` behind HTTPS |
| `CRYPTOAUDIT_ENABLE_BANDIT` / `_SEMGREP` | `true` / `false` | Baseline scanners for S1 hints and V0 |
| `CRYPTOAUDIT_MAX_REPO_MB` | `500` | Compressed archive of the scanned commit (no git history) |
| `CRYPTOAUDIT_MAX_UNPACKED_MB` | `4096` | Everything in the archive, including non-Python files |
| `CRYPTOAUDIT_MAX_PYTHON_FILES` | `5000` | Files beyond the limit are listed as skipped |
| `CRYPTOAUDIT_MAX_FILE_KB` | `1024` | Larger `.py` files (usually generated) are skipped and listed |
| `CRYPTOAUDIT_SCAN_ARCHIVES` | `true` | Also scan `.py` files inside `.zip` archives in the repository (in memory, one level deep) |
| `CRYPTOAUDIT_MAX_ARCHIVE_MB` | `100` | Larger `.zip` archives are skipped and listed |
| `CRYPTOAUDIT_SCAN_PARALLELISM` | `4` | Files repaired and validated concurrently within one scan |
| `CRYPTOAUDIT_SCAN_WORKERS` | `2` | Scans running at the same time |
| `CRYPTOAUDIT_LLM_TIMEOUT` | `600` | Seconds allowed for one generation |

For large repositories, turning Semgrep off and raising `CRYPTOAUDIT_SCAN_PARALLELISM` help most.
Analysis is fast; most of the time is spent on files that have findings.

---

## Command-line and research benchmark

From `backend/`:

```sh
pip install -e ".[dev,web,scanners]"
uv tool install semgrep==1.163.0                              # optional; kept in its own environment
docker build -t cryptoaudit-sandbox:latest ../docker/sandbox  # validation sandbox for V1–V3

cryptoaudit analyze path/to/file.py                           # analyzer only
cryptoaudit repair path/to/file.py -s S1,S2,S3,S4 --show-code # repair + validate one file
cryptoaudit bench list                                        # benchmark cases
cryptoaudit bench run -s S1,S2,S3,S4                          # run experiments
cryptoaudit bench report --markdown benchmark/results/report.md
cryptoaudit serve --port 8000                                 # website API
```

The benchmark in [`backend/benchmark/`](backend/benchmark/) separates public inputs from hidden
validation data:

| Path | Visible to repair? | Contents |
|---|---|---|
| `cases/<rule>/<id>/` | Yes | Vulnerable `module.py` and `case.yaml` |
| `expected/<rule>/<id>/` | No | Oracle and V1/V2/V3 checks |
| `artifacts/<rule>/<id>/` | No | Legacy data written by the original code |
| `results/` | | Local run output (git-ignored) |

An import-boundary test makes sure no generation-side package can import the hidden oracles. Each
run is stored in an append-only SQLite database with its configuration hash, version, git commit,
strategy parameters (model, seed, prompt id and hash), raw LLM output, candidate code, diff and
validation reports.

---

## Repository structure

```
Crypto_Audit/
├── frontend/                React 19 + Vite website
│   └── src/
│       ├── pages/           Login, Dashboard, Repositories, Review, Scan results, Finding, Scans
│       ├── components/      domain components (code compare, gates, stages, explanation, tree)
│       │   ├── ui/          design-system components (Button, DataTable, Tabs, Toast, …)
│       │   └── code/        code viewer and diff viewer
│       ├── styles/          tokens, base, components, layout, code, pages
│       ├── services/        API client (all calls go to /api)
│       ├── context/, hooks/, layouts/, utils/
├── backend/                 Python package `cryptoaudit`; run backend commands from here
│   ├── src/cryptoaudit/
│   │   ├── cli/             analyze, repair, bench, serve
│   │   ├── api/             FastAPI app and routes (auth, repos, scans, findings, reports)
│   │   ├── ingest/          GitHub OAuth + read-only client, in-memory archive loading, benchmark loader
│   │   ├── analysis/, rules/ deterministic CR1–CR5 analyzer
│   │   ├── models/          shared Pydantic models (one finding schema)
│   │   ├── context/         bounded repair context
│   │   ├── llm/             Ollama, OpenRouter, routing, context budget, prompts
│   │   ├── repair/          S1–S4
│   │   ├── validation/      integrity, V0–V3, sandbox, scanners, hidden oracle loader
│   │   ├── pipeline/        orchestration, benchmark runner, repository scan
│   │   ├── reporting/       console, JSON, Markdown, research analysis, explanations
│   │   ├── storage/         experiment DB, web store (sessions, scans)
│   │   └── config/, utils/
│   ├── tests/               unit/, integration/, e2e/, fixtures/
│   ├── benchmark/, configs/, prompts/
│   └── data/                runtime output (git-ignored)
├── docker/                  api and web images, nginx, docker-compose, validation sandbox
├── docs/                    architecture/, development/ and diagrams/
└── .github/workflows/       ci.yml (backend tests), deploy.yml (frontend preview)
```

---

## Frontend

The website is a React 19 single-page app (Vite, React Router, `lucide-react` icons, plain CSS).
It talks to the backend only through `src/services/`, and every call goes to `/api`.

- **Design system:** colour, type and spacing tokens in `src/styles/tokens.css`, one accent colour,
  semantic success/warning/danger/info colours, light and dark themes that follow the operating
  system, and reduced-motion support.
- **Pages:** dashboard metrics from your own scans; repositories, findings and scan history with
  search, filters, sorting and pagination; a finding view with the original and repaired code side by
  side or as a unified diff, the validation gates, a scanners-versus-validation comparison and the
  evidence-based explanation.
- **Code viewer:** line numbers, Python syntax highlighting, flagged/removed/added lines, rule
  markers, collapsible context and copy.
- **Responsive and accessible:** sidebar on desktop, navigation drawer on small screens, tables that
  turn into cards on phones, keyboard-operable tabs, menus and tables, visible focus states and a
  skip link.

```sh
cd frontend
npm run dev       # development server with /api proxy
npm run build     # production build in dist/
npm run lint      # oxlint
```

A [static preview](https://imluffy000.github.io/Crypto_Audit/) is published from `main` by
`deploy.yml`. It is the frontend only, so sign-in and scans need a running backend.

---

## Testing

```sh
cd backend
python -m pytest            # unit, integration and end-to-end tests
cd ../frontend
npm run lint && npm run build
```

CI runs the backend tests on Python 3.11 and 3.12. Tests run with isolated settings, so a local
`backend/.env` does not affect them.

---

## Security and privacy

- **Read-only GitHub access.** Sign-in uses the OAuth web flow with a single-use `state` bound to both
  the server and an HttpOnly cookie. Tokens are stored encrypted on the server (never in the browser)
  and revoked at GitHub on sign-out. Session IDs are stored hashed.
- **Repository code is never executed.** Archives are size-limited and read in memory: only `.py`
  files, no symlinks, no path traversal. One active scan per user.
- **Sandboxed validation.** Benchmark candidates run only in the Docker sandbox. The local sandbox is
  for trusted code and needs an explicit opt-in.
- **The LLM is not the detector or the judge.** Detection is deterministic, and acceptance is decided
  by validation gates. AI summaries are labelled as such and never change a verdict.
- **Local by default.** The API binds to `127.0.0.1`. Put it behind a reverse proxy with HTTPS (and set
  `CRYPTOAUDIT_COOKIE_SECURE=true`) before exposing it.
- Never commit `backend/.env`. If you use OpenRouter, the code being repaired leaves your machine.

---

## Known limitations

- Website scans cannot reach **Verified**: arbitrary repositories have no security-property oracles,
  so V2/V3 do not run there.
- A clean scanner result means no known pattern matched. It does not mean the code is secure.
- The benchmark currently has one case per rule; extend `backend/benchmark/` for statistical power.
- Known analyzer precision issues: CR5 flags `random.SystemRandom`, keyword matching works on
  substrings (e.g. "auth" in "author"), and CR3/CR4 resolve scope by function name.
- Semgrep registry configs are fetched over the network and can change over time; the config and
  version are recorded per run.
- Local file upload on the website is for review only; scans need a GitHub repository so results are
  tied to a commit.
- Not yet built: risk scoring, SARIF/HTML reports, dependency graphs, a hosted deployment.

---

## Documentation

| Document | Contents |
|---|---|
| [docs/diagrams/](docs/diagrams/README.md) | Illustrated explanations: architecture, scan flow, sign-in, ingestion, analyzer, strategies, validation, data model, every backend and frontend file |
| [docs/development/website.md](docs/development/website.md) | Website setup, OAuth scopes, LLM options, large repositories, security notes |
| [docs/architecture/system-design.md](docs/architecture/system-design.md) | Components, strategies, gates, reproducibility |
| [docs/architecture/data-flow.md](docs/architecture/data-flow.md) | How data moves between stages and across the hidden-oracle boundary |
| [docs/development/analyzer-phase1.md](docs/development/analyzer-phase1.md) | Analyzer design notes |
| [backend/README.md](backend/README.md) | Backend commands and layout |

## License

[MIT](LICENSE) © 2026 Prasanth changala
