# CryptoAudit

CryptoAudit finds cryptographic misuse in Python repositories, generates candidate repairs and
validates them independently, explaining why each repair was or was not accepted.

## Website

Sign in with GitHub, pick a repository, and CryptoAudit runs: fetch → parse → CR1–CR5 analysis →
context → repair (S1–S4) → validation (V0–V3) → comparison and explanation → results.

```sh
cp .env.example .env                    # add your GitHub App credentials (see docs/development/website.md)
pip install -e ".[web,scanners]"
cryptoaudit serve                       # API on :8000
cd frontend && npm install && npm run dev   # website on http://localhost:5173
```

Setup guide, GitHub App permissions and what the verdicts mean: [docs/development/website.md](docs/development/website.md).

## Research pipeline (Python)

The `cryptoaudit` Python package implements the full pipeline: deterministic CR1–CR5 detection,
bounded context, S1–S4 candidate repairs, sandboxed V0–V3 validation, aggregation, an append-only
experiment database and research analysis. See [docs/architecture/system-design.md](docs/architecture/system-design.md)
and [docs/architecture/data-flow.md](docs/architecture/data-flow.md).

```sh
pip install -e ".[dev,web,scanners]"
uv tool install semgrep==1.163.0   # optional baseline scanner, kept in its own environment
cryptoaudit repair path/to/file.py -s S1,S2
cryptoaudit bench run -s S1,S2,S3,S4
cryptoaudit bench report
python -m pytest
```

## Preview

Open the [CryptoAudit preview](https://imluffy000.github.io/Crypto_Audit/). GitHub Actions publishes the preview whenever changes are pushed to `main`.

The GitHub Pages preview is the static frontend only: it has no backend, so sign-in and scans need a locally running `cryptoaudit serve`.

## Run locally

```sh
cd frontend
npm install
npm run dev
```

Create a production build with `cd frontend && npm run build`.

This template provides a minimal setup to get React working in Vite with HMR and some Oxlint rules.

Currently, two official plugins are available:

- [@vitejs/plugin-react](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react) uses [Oxc](https://oxc.rs)
- [@vitejs/plugin-react-swc](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react-swc) uses [SWC](https://swc.rs/)

## React Compiler

The React Compiler is not enabled on this template because of its impact on dev & build performances. To add it, see [this documentation](https://react.dev/learn/react-compiler/installation).

## Expanding the Oxlint configuration

If you are developing a production application, we recommend using TypeScript with type-aware lint rules enabled. Check out the [TS template](https://github.com/vitejs/vite/tree/main/packages/create-vite/template-react-ts) for information on how to integrate TypeScript and Oxlint's TypeScript related rules in your project.
