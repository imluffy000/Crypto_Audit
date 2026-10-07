# How a website scan works, end to end

This sequence follows one scan from choosing a repository to reading the results.

## Steps

1. **Review.** The review page asks the API for the repository's file tree (GitHub trees API) so
   you can check it before scanning. The response also counts Python files and `.zip` archives.
2. **Start.** `POST /api/scans` stores a new scan as `QUEUED` with eight pending stages and hands it
   to a background worker. The response (`202`) contains only the scan id. Your GitHub token stays
   in the worker's memory for the duration of the job; it is never written into the scan.
3. **Run.** `RepositoryScanner` downloads the commit's archive and runs the eight stages
   (fetch, parse, analyze, context, repair, validate, explain, report). After every status change it
   writes progress to the web store; on large repositories in-stage progress is throttled.
4. **Follow.** The scan page polls `GET /api/scans/{id}` every 1.5 seconds until the scan is
   `COMPLETED` or `FAILED`.
5. **Results.** The page loads the findings list. Opening a finding loads the original file, every
   strategy's candidate and diff, the validation gates, the scanner baseline and the explanation.
6. **Optional.** A plain-language summary can be requested per candidate (needs a language model).
   It is labelled as AI-written and never changes a verdict. A Markdown report can be downloaded.

## What never happens

- Your repository code is never executed. Without hidden security tests, V2/V3 are `NOT_RUN`, so
  **Unverified is the best possible verdict** for repository code.
- Nothing is written back to GitHub: every GitHub request is a read.

Related: [04 scan lifecycle](04-scan-lifecycle.md) · [05 ingestion](05-ingestion.md) ·
[18 frontend navigation](18-frontend-navigation.md)

## Diagram

```mermaid
sequenceDiagram
    autonumber
    actor U as Developer
    participant FE as Frontend (React)
    participant API as FastAPI /api
    participant ST as Web store (SQLite)
    participant JOB as Scan worker (api/jobs.py)
    participant GH as GitHub API
    participant PL as RepositoryScanner

    U->>FE: Choose repository
    FE->>API: GET /api/repos/{owner}/{name}/tree
    API->>GH: GET repo + git tree (read-only)
    GH-->>API: tree entries
    API-->>FE: tree, file counts, zip archive count
    U->>FE: Start scan
    FE->>API: POST /api/scans {owner, name, ref}
    API->>ST: create scan (QUEUED, 8 pending stages)
    API->>JOB: submit to thread pool
    API-->>FE: 202 {scan_id}
    FE->>FE: navigate to /scans/{scan_id}

    JOB->>PL: run(fetch)
    PL->>GH: download tarball (size-capped stream)
    GH-->>PL: archive (temp file)
    Note over PL: FETCH → PARSE → ANALYZE → CONTEXT →<br/>REPAIR → VALIDATE → EXPLAIN → REPORT
    loop each stage change
        PL->>ST: update_progress(stages)
    end

    loop every 1.5 s until COMPLETED or FAILED
        FE->>API: GET /api/scans/{scan_id}
        API->>ST: read scan
        API-->>FE: status + stages (+ summary when done)
    end

    alt completed
        PL-->>JOB: RepositoryScanResult
        JOB->>ST: complete_scan(result)
        FE->>API: GET /api/scans/{id}/findings
        API-->>FE: findings + best verdict + per-strategy verdicts
        U->>FE: open a finding
        FE->>API: GET /api/scans/{id}/findings/{finding_id}
        API-->>FE: source, candidates, diffs, gates, baseline, explanation
        opt plain-language summary (needs an LLM)
            FE->>API: POST /api/scans/{id}/candidates/{cid}/ai-explanation
            API-->>FE: labelled text (never changes the verdict)
        end
        FE->>API: GET /api/reports/{id}.md
        API-->>FE: Markdown report
    else failed
        JOB->>ST: fail_scan(error code + message, stages)
        API-->>FE: status FAILED with the failing stage
    end
```
