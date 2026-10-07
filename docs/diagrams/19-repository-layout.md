# Repository layout at a glance

Run backend commands from `backend/` (relative paths such as `.env`, `data/` and the test fixtures
resolve from there) and frontend commands from `frontend/`.

| Folder | Contents |
|---|---|
| `frontend/` | React website |
| `backend/` | Python package `cryptoaudit`, tests, benchmark, rule configuration, prompts |
| `docker/` | API and web images, nginx configuration, docker-compose, validation sandbox |
| `docs/` | `architecture/`, `development/` and these diagrams |
| `.github/workflows/` | Backend tests and the frontend preview deployment |

## Diagram

```mermaid
mindmap
  root((Crypto_Audit))
    frontend
      src/pages
      src/components
        ui design system
        code viewer + diff
      src/services API client
      src/context + hooks
      src/layouts
      src/styles tokens + CSS
      src/utils
      public favicon
    backend
      src/cryptoaudit
        cli
        api FastAPI
        ingest
        analysis + rules
        models
        context
        llm
        repair S1-S4
        validation V0-V3
        pipeline
        reporting
        storage
        config + utils
      tests
        unit
        integration
        e2e
        fixtures
      benchmark
        cases public
        expected hidden
        artifacts hidden
        results
      configs/rules.yaml
      prompts repair + explanation
      data runtime, git-ignored
      .env.example
    docker
      api.Dockerfile
      web.Dockerfile + nginx.conf
      docker-compose.yml
      sandbox/Dockerfile
    docs
      architecture
      development
      diagrams
    .github/workflows
      ci.yml backend tests
      deploy.yml frontend preview
```
