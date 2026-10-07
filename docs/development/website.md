# Running the CryptoAudit website

```
GitHub sign-in → pick a repository → fetch (read-only) → parse → CR1–CR5 analysis → context →
repair (S1, S2, + S3/S4 with a local LLM) → candidates → validation (V0–V3) → comparison + why → results
```

The website is the React app in `frontend/` talking to the FastAPI backend (`cryptoaudit serve`,
routes under `/api`). Repository code is fetched as a tarball, read in memory, analysed and repaired
— **never executed**.

## 1. Create a GitHub OAuth App (one time)

GitHub → **Settings → Developer settings → OAuth Apps → New OAuth App**:

| Field | Value |
|---|---|
| Application name | e.g. `CryptoAudit (local)` |
| Homepage URL | `http://localhost:5173` |
| Authorization callback URL | `http://localhost:5173/api/auth/github/callback` |
| Enable Device Flow | unchecked |

Register the app, copy the **Client ID** and generate a **client secret**.

OAuth Apps accept a single callback URL, so the dev server and `docker compose` both serve the site on
`http://localhost:5173`. If you deploy elsewhere, register a separate OAuth App for that origin and set
`CRYPTOAUDIT_PUBLIC_URL` to it.

### Repository access

| `CRYPTOAUDIT_GITHUB_REPO_ACCESS` | Scopes requested | What can be scanned |
|---|---|---|
| `private` (default) | `read:user repo` | Your public and private repositories, collaborations, organisation repositories |
| `public` | `read:user` | Public repositories only |

GitHub has no read-only scope for private repositories, so `private` shows **“Full control of private
repositories”** on the consent screen. CryptoAudit only ever makes read requests (repository list,
file tree, tarball download), and **signing out revokes the token** at GitHub. You can also review or
revoke access at any time under GitHub → Settings → Applications → Authorized OAuth Apps (the
website's “Manage GitHub access” button opens it). Organisations that restrict third-party access
must approve the app there before their repositories appear.

## 2. Configure

```sh
cd backend
cp .env.example .env
python -c "import secrets; print(secrets.token_urlsafe(48))"   # paste as CRYPTOAUDIT_SESSION_SECRET
```

Fill in `CRYPTOAUDIT_GITHUB_CLIENT_ID` and `CRYPTOAUDIT_GITHUB_CLIENT_SECRET` (and optionally
`CRYPTOAUDIT_GITHUB_REPO_ACCESS`) in `backend/.env`. `.env` is git-ignored — never commit it.

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
docker compose -f docker/docker-compose.yml up --build          # http://localhost:5173
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

- Sign-in uses the GitHub OAuth web flow with a single-use `state` bound to both the server and an
  HttpOnly browser cookie. Tokens are revoked at GitHub on logout (OAuth App tokens never expire on their own). Sessions are HttpOnly, SameSite=Lax cookies; set
  `CRYPTOAUDIT_COOKIE_SECURE=true` behind HTTPS.
- Access tokens are encrypted at rest in `backend/data/web/cryptoaudit.sqlite`; session IDs are stored hashed.
- Repository archives are size-limited and read in memory (only `.py` files, no symlinks, no path
  traversal). One active scan per user.
- The API binds to `127.0.0.1` by default. Put it behind a reverse proxy with HTTPS before exposing it.
