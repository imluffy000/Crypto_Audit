# Backend files (3/3): API, pipeline, reporting, storage and CLI

Every file in `api/`, `pipeline/`, `reporting/`, `storage/` and `cli/`. All HTTP routes are mounted
under `/api` by `api/app.py`.

| Package | Responsibility |
|---|---|
| `cli/` | `cryptoaudit analyze`, `repair`, `bench list/run/report` and `serve` |
| `api/` | FastAPI app, dependency container, session handling, background scan jobs, response schemas, routes |
| `pipeline/` | Stage functions, one-module pipeline, repository scanner, benchmark runner, wiring from settings |
| `reporting/` | Evidence-based explanations, optional AI narrative, Markdown/JSON/console reports, research statistics |
| `storage/` | Web store (users, sessions, OAuth state, scans, AI texts) and the append-only experiment database |

## API endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/health` | Server, GitHub and language model status |
| GET | `/api/auth/github/login` | Start sign-in (`?select_account=true` to switch account) |
| GET | `/api/auth/github/callback` | Finish sign-in, set the session cookie |
| GET | `/api/auth/me` | Signed-in user |
| POST | `/api/auth/logout` | End the session and revoke the token |
| GET | `/api/repos` | Repositories you can scan |
| GET | `/api/repos/{owner}/{name}/tree` | File tree and counts |
| POST | `/api/scans` | Start a scan |
| GET | `/api/scans`, `/api/scans/{id}` | Scan list, progress and summary |
| GET | `/api/scans/{id}/findings`, `/api/scans/{id}/findings/{fid}` | Findings and per-finding detail |
| POST | `/api/scans/{id}/candidates/{cid}/ai-explanation` | Optional plain-language summary |
| GET | `/api/reports/{id}.md` | Markdown report |

## Diagram

```mermaid
flowchart LR
    subgraph CLI["cli/"]
        cli_main["main.py<br/>analyze · repair · bench list|run|report · serve"]
    end

    subgraph API["api/ — FastAPI website backend"]
        direction TB
        a_app["app.py<br/>create_app: routers, error handlers,<br/>GET /api/health"]
        a_services["services.py<br/>Services container: settings, store, OAuth,<br/>GitHub client, LLM, pipeline factory, executor, limits"]
        a_deps["dependencies.py<br/>get_services, current_session (cookie → session)"]
        a_jobs["jobs.py<br/>run_scan in a worker thread"]
        a_schemas["schemas.py<br/>response shapes: HealthOut, RepoOut, RepoTreeOut,<br/>ScanOut, FindingOut, FindingDetailOut, AIExplanationOut"]
        subgraph ROUTES["routes/"]
            r_auth["auth.py<br/>GET github/login · GET github/callback<br/>GET me · POST logout"]
            r_repos["repos.py<br/>GET /repos · GET /repos/{owner}/{name}/tree"]
            r_scan["scan.py<br/>POST /scans · GET /scans · GET /scans/{id}"]
            r_find["findings.py<br/>GET …/findings · GET …/findings/{fid}<br/>POST …/candidates/{cid}/ai-explanation"]
            r_rep["reports.py<br/>GET /reports/{id}.md"]
        end
        a_app --> ROUTES
        ROUTES --> a_deps --> a_services
        r_scan --> a_jobs
    end

    subgraph PIPELINE["pipeline/ — orchestration"]
        direction TB
        p_stages["stages.py<br/>analysis_stage · candidate_stage · validation_stage"]
        p_orch["orchestrator.py<br/>RepairPipeline for one module"]
        p_repo["repository_scan.py<br/>RepositoryScanner: 8 stages, progress,<br/>parallel per file, select_web_strategies"]
        p_bench["benchmark_runner.py<br/>every case × strategy → one run"]
        p_factory["factory.py<br/>build analyzer, strategies, LLM router,<br/>sandbox, scanners from Settings"]
        p_result["pipeline_result.py<br/>ModuleRun, StrategyRun"]
        p_orch --> p_stages
        p_repo --> p_stages
        p_bench --> p_orch
        p_orch --> p_result
    end

    subgraph REPORTING["reporting/"]
        direction TB
        rep_expl["explanation.py<br/>evidence-based why: headline, sections, limitations"]
        rep_ai["ai_explanation.py<br/>optional LLM narrative of that evidence (labelled)"]
        rep_md["markdown_report.py<br/>scan report + research report"]
        rep_json["json_report.py<br/>JSON output"]
        rep_console["console_report.py<br/>Rich console output for the CLI"]
        rep_research["research.py<br/>StrategyStats, compare strategies"]
    end

    subgraph STORAGE["storage/"]
        direction TB
        s_web["web_store.py<br/>users, sessions (hashed ids, encrypted tokens),<br/>OAuth state, scans, AI explanations"]
        s_sql["sqlite.py<br/>append-only experiment DB (no UPDATE / DELETE)"]
        s_jsonl["jsonl.py<br/>export experiment records"]
    end

    a_services --> s_web
    a_services --> p_factory
    a_jobs --> p_repo
    a_jobs --> s_web
    r_find --> rep_ai
    r_rep --> rep_md
    p_repo --> rep_expl
    p_orch --> s_sql
    s_sql --> s_jsonl
    cli_main --> p_orch & p_bench & rep_console & rep_research & a_app
    rep_research --> s_sql
```
