# CryptoAudit

CryptoAudit finds cryptographic misuse in Python repositories, generates candidate repairs and
validates them independently, explaining why each repair was or was not accepted.

Sign in with GitHub, pick a repository, and CryptoAudit runs: fetch → parse → CR1–CR5 analysis →
context → repair (S1–S4) → validation (V0–V3) → comparison and explanation → results.

## Repository structure

```
Crypto_Audit/
├── frontend/   React + Vite website (pages, components, services → /api)
├── backend/    Python package `cryptoaudit`: analyzer, repair, validation, website API,
│               tests, rule configs, LLM prompts and the research benchmark
├── docker/     container images (api, web, validation sandbox) and docker-compose
├── docs/       architecture/ (system design, data flow) and development/ (setup guides)
└── .github/    CI (backend tests) and frontend preview deployment
```

Each side is self-contained: run backend commands from `backend/` and frontend commands from
`frontend/`.

## Run the website locally

```sh
# backend: API on http://127.0.0.1:8000
cd backend
cp .env.example .env              # GitHub OAuth App credentials, see docs/development/website.md
pip install -e ".[web,scanners]"
cryptoaudit serve

# frontend (second terminal, from the repository root): website on http://localhost:5173
cd frontend
npm install
npm run dev
```

Or run both with Docker: `docker compose -f docker/docker-compose.yml up --build` (http://localhost:5173).

Setup guide, GitHub OAuth scopes and what the verdicts mean:
[docs/development/website.md](docs/development/website.md).

## Research pipeline

From `backend/`:

```sh
pip install -e ".[dev,web,scanners]"
uv tool install semgrep==1.163.0   # optional baseline scanner, kept in its own environment
cryptoaudit repair path/to/file.py -s S1,S2
cryptoaudit bench run -s S1,S2,S3,S4
cryptoaudit bench report
python -m pytest
```

Architecture: [docs/architecture/system-design.md](docs/architecture/system-design.md) and
[docs/architecture/data-flow.md](docs/architecture/data-flow.md). Backend details:
[backend/README.md](backend/README.md).

## Frontend preview

The [GitHub Pages preview](https://imluffy000.github.io/Crypto_Audit/) is published from `main` and is
the static frontend only: sign-in and scans need a running backend. Production build:
`cd frontend && npm run build`.
