# CryptoAudit backend

Python package `cryptoaudit`: deterministic CR1–CR5 detection, bounded repair context, S1–S4
candidate repairs, sandboxed V0–V3 validation, aggregation, experiment storage, research analysis,
and the website API (FastAPI, served under `/api`).

Run every command below from this `backend/` directory: relative paths such as `.env`, `data/`
and the test fixtures resolve from here.

```sh
pip install -e ".[dev,web,scanners]"
cp .env.example .env                  # website settings (GitHub OAuth App, session secret)

cryptoaudit serve                     # website API on http://127.0.0.1:8000
cryptoaudit analyze path/to/file.py   # Analyzer only
cryptoaudit repair path/to/file.py -s S1,S2
cryptoaudit bench run -s S1,S2,S3,S4  # benchmark experiments
cryptoaudit bench report
python -m pytest
```

| Path | Contents |
|---|---|
| `src/cryptoaudit/` | the package (see `../docs/architecture/system-design.md`) |
| `tests/` | `unit/<package>/`, `integration/`, `e2e/`, `fixtures/` |
| `configs/rules.yaml` | CR1–CR5 rule configuration |
| `prompts/` | versioned LLM prompts (`repair/`, `explanation/`) |
| `benchmark/` | research corpus: `cases/` (public), `expected/` + `artifacts/` (validation only), `results/` |
| `data/` | local runtime output: web store, experiment databases (git-ignored) |
