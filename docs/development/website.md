# Running the CryptoAudit website

```
GitHub sign-in → pick a repository → fetch (read-only) → parse → CR1–CR5 analysis → context →
repair (S1, S2, + S3/S4 with a local LLM) → candidates → validation (V0–V3) → comparison + why → results
```

The website is the React app in `frontend/` talking to the FastAPI backend (`cryptoaudit serve`,
routes under `/api`). Repository code is fetched as a tarball, read in memory, analysed and repaired
— **never executed**.

## 1. Create a GitHub App (one time)

GitHub → **Settings → Developer settings → GitHub Apps → New GitHub App**:

| Field | Value |
|---|---|
| GitHub App name | e.g. `CryptoAudit (local)` — its URL slug becomes `CRYPTOAUDIT_GITHUB_APP_SLUG` |
| Homepage URL | `http://localhost:5173` |
| Callback URL | `http://localhost:5173/api/auth/github/callback` (add `http://localhost:8080/api/auth/github/callback` too if you use docker compose) |
| Expire user authorization tokens | leave checked |
| Request user authorization (OAuth) during installation | **unchecked** (sign in from the website instead) |
| Webhook → Active | **unchecked** (not used) |
| Repository permissions → Contents | **Read-only** (Metadata read-only is added automatically) |
| Account permissions | none |
| Where can this app be installed | Only on this account (or any account) |

Create the app, copy the **Client ID**, generate a **client secret**, then **Install App** on the
repositories you want to scan. CryptoAudit can only see repositories the app is installed on;
the website's “Grant repositories” button links to the installation page.

## 2. Configure

```sh
cd backend
cp .env.example .env
python -c "import secrets; print(secrets.token_urlsafe(48))"   # paste as CRYPTOAUDIT_SESSION_SECRET
```

Fill in `CRYPTOAUDIT_GITHUB_CLIENT_ID`, `CRYPTOAUDIT_GITHUB_CLIENT_SECRET` and
`CRYPTOAUDIT_GITHUB_APP_SLUG` in `backend/.env`. `.env` is git-ignored — never commit it.

## 3. Run (development)

```sh
cd backend
pip install -e ".[web,scanners]"
cryptoaudit serve                      # API on http://127.0.0.1:8000 (run from backend/ so .env is found)

# second terminal, from the repository root
cd frontend && npm install && npm run dev   # website on http://localhost:5173 (proxies /api to :8000)
```

Optional local LLM (enables S3/S4 and the “Explain in plain language (AI)” button):

```sh
ollama pull codellama:7b-instruct       # or set CRYPTOAUDIT_LLM_MODEL to another code model
```

Without it, scans run S1 and S2 and the results page says S3/S4 were skipped.

## 3b. Run with Docker

```sh
docker compose -f docker/docker-compose.yml up --build          # http://localhost:8080
docker compose -f docker/docker-compose.yml --profile llm up --build   # + Ollama
```

## What the results mean

| Verdict | Meaning |
|---|---|
| **Verified** | V1 functional, V2 security-property and applicable V3 compatibility checks passed |
| **Unverified** | Plausible repair: integrity, syntax and interface checks passed and scanners may be clean, but security properties were not tested |
| **Failed** | An integrity check or a gating validation gate failed |
| **No candidate** | The strategy produced no code (no template, no applicable hint, or unparseable LLM output) |

Your repositories have no hidden security-property tests (those exist only for the benchmark), so
**Unverified is the best possible verdict for repository code**. The website says so on every
result. Scanner results (V0) are shown for comparison but never decide the verdict.

## Security notes

- Sign-in uses the GitHub App web flow with a single-use `state` bound to both the server and an
  HttpOnly browser cookie. Sessions are HttpOnly, SameSite=Lax cookies; set
  `CRYPTOAUDIT_COOKIE_SECURE=true` behind HTTPS.
- Access tokens are encrypted at rest in `backend/data/web/cryptoaudit.sqlite`; session IDs are stored hashed.
- Repository archives are size-limited and read in memory (only `.py` files, no symlinks, no path
  traversal). One active scan per user.
- The API binds to `127.0.0.1` by default. Put it behind a reverse proxy with HTTPS before exposing it.
