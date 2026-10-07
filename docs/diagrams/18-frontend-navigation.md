# Frontend routes, pages and API calls

The website uses hash routes (`frontend/src/App.jsx`). Every route except `/login` is wrapped in
`ProtectedRoute`, which waits for `GET /api/auth/me` and sends signed-out users to the login page.
`/` goes to `/login` (which forwards signed-in users to the dashboard) and unknown routes go to
`/dashboard`.

| Route | Page | Purpose |
|---|---|---|
| `/login` | `Login.jsx` | Sign in with GitHub, or with a different GitHub account |
| `/dashboard` | `Dashboard.jsx` | Metrics from your scans, recent scans, findings by rule, environment |
| `/repositories/github`, `/repositories/upload`, `/repository/add` | `RepositoryUpload.jsx` | Choose a GitHub repository, or review local files (the tab follows the URL) |
| `/repositories/review` | `RepositoryDetails.jsx` | Check the repository and start a scan |
| `/scans/:scanId` | `ScanResults.jsx` | Progress, summary, findings table, strategy outcomes, report |
| `/scans/:scanId/findings/:findingId` | `FindingDetail.jsx` | Original vs repaired code, why, gates, scanner comparison |
| `/reports` | `Reports.jsx` | Scan history and Markdown reports |
| `/findings` | `Findings.jsx` | Every finding from the latest completed scan of each repository, with search and filters |

## Diagram

```mermaid
flowchart LR
    root["/#/"] --> login
    login["/login<br/>Login.jsx"] -- "Continue with GitHub" --> oauth[["/api/auth/github/login"]]
    login -- "Use a different GitHub account" --> oauthsel[["/api/auth/github/login?select_account=true"]]
    oauth & oauthsel -. "GitHub → callback → session cookie" .-> dash

    dash["/dashboard<br/>Dashboard.jsx"]
    repos["/repositories/github<br/>/repositories/upload · /repository/add<br/>RepositoryUpload.jsx (tab follows URL)"]
    review["/repositories/review<br/>RepositoryDetails.jsx"]
    scan["/scans/:scanId<br/>ScanResults.jsx"]
    finding["/scans/:scanId/findings/:findingId<br/>FindingDetail.jsx"]
    reports["/reports<br/>Reports.jsx"]
    latest["/findings<br/>Findings.jsx"]

    dash -- "New scan" --> repos
    dash -- "row" --> scan
    repos -- "Select repository" --> review
    review -- "Start scan" --> scan
    scan -- "row" --> finding
    reports -- "row" --> scan
    latest -- "row" --> finding

    dash -.-> e1[("GET /api/scans<br/>GET /api/scans/{id} (latest per repo)<br/>GET /api/health")]
    repos -.-> e2[("GET /api/repos<br/>GET /api/repos/{owner}/{name}/tree<br/>GET /api/health")]
    review -.-> e3[("POST /api/scans")]
    scan -.-> e4[("GET /api/scans/{id} every 1.5 s<br/>GET /api/scans/{id}/findings<br/>GET /api/reports/{id}.md")]
    finding -.-> e5[("GET /api/scans/{id}/findings/{fid}<br/>POST …/candidates/{cid}/ai-explanation")]
    reports -.-> e6[("GET /api/scans<br/>GET /api/reports/{id}.md")]
    latest -.-> e8[("GET /api/scans<br/>GET /api/scans/{id}/findings (latest per repo)")]
    login -.-> e7[("GET /api/health<br/>GET /api/auth/me")]

    menu["Sidebar account menu"] -- "Switch account" --> sw[["POST /api/auth/logout →<br/>/api/auth/github/login?select_account=true"]]
    menu -- "Sign out" --> so[["POST /api/auth/logout → /login"]]

    classDef page fill:#ebf1fd,stroke:#2557d6,color:#0f2a6b
    classDef api fill:#eef2f7,stroke:#8a96a8,color:#1b2430
    class login,dash,repos,review,scan,finding,reports,latest page
    class e1,e2,e3,e4,e5,e6,e7,e8 api
```
