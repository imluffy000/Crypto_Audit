# Frontend files

Every file in `frontend/src/` and what it does. The website uses React 19, Vite, React Router
(hash routes), `lucide-react` icons and plain CSS.

## Layering

| Layer | Folder | Rule |
|---|---|---|
| Pages | `pages/` | One per route; compose components and call services |
| Domain components | `components/` | CryptoAudit-specific UI (code compare, gates, verdicts, tree, explanation) |
| Design system | `components/ui/` | Generic, reusable building blocks with no API knowledge |
| Code viewing | `components/code/` | Code viewer and diff viewer |
| Services | `services/` | The only code that talks to the backend; every call goes to `/api` |
| State | `context/`, `hooks/` | Signed-in user, selected repository, sign-in / switch / sign-out |
| Styles | `styles/` | Design tokens, base, components, layout, code and page CSS (light and dark) |
| Utilities | `utils/` | Formatting, syntax highlighting, diff parsing, local file helpers |

`utils/sizeUtils.js` is a legacy helper that no page imports.

## Diagram

```mermaid
flowchart LR
    subgraph ENTRY["entry"]
        direction TB
        f_main["main.jsx<br/>mount React, import styles/*.css"]
        f_app["App.jsx<br/>providers + HashRouter routes"]
        f_main --> f_app
    end

    subgraph STATE["context/ + hooks/"]
        direction TB
        f_ctx["context/AppContext.jsx<br/>user, authLoading, selectedRepository (localStorage),<br/>loginWithGithub, switchAccount, logout"]
        f_hauth["hooks/useAuth.js<br/>thin wrapper"]
        f_hrepo["hooks/useRepository.js<br/>selected repository wrapper"]
    end

    subgraph SERVICES["services/ — the only code that calls the API"]
        direction TB
        f_api["api.js<br/>fetch wrapper: /api base, cookies, ApiError(status, code, message)"]
        f_auth["authService.js<br/>login redirect (+select_account), me, logout, health"]
        f_repo["repositoryService.js<br/>list repos, repo tree, local review"]
        f_scan["scanService.js<br/>start / get / list scans, findings,<br/>finding detail, AI summary, report URL"]
        f_auth & f_repo & f_scan --> f_api
    end

    subgraph LAYOUTS["layouts/"]
        direction TB
        f_dash["DashboardLayout.jsx<br/>skip link, sidebar, mobile top bar + drawer, main"]
        f_authl["AuthLayout.jsx<br/>centred sign-in shell"]
    end

    subgraph PAGES["pages/"]
        direction TB
        pg_login["Login.jsx<br/>GitHub sign-in, server status, error codes,<br/>use a different account"]
        pg_dash["Dashboard.jsx<br/>real metrics, recent scans, findings by rule, environment"]
        pg_repos["RepositoryUpload.jsx<br/>GitHub list (search, filter, sort) + local review tab"]
        pg_review["RepositoryDetails.jsx<br/>metadata, file tree, zip note, start scan"]
        pg_scan["ScanResults.jsx<br/>polling progress, metrics, findings table,<br/>strategy outcomes, skipped files, report"]
        pg_find["FindingDetail.jsx<br/>finding, strategy tabs, code compare,<br/>why, gates, scanners vs validation"]
        pg_reports["Reports.jsx<br/>scan history with search, status filter, sort"]
        pg_latest["LatestFindings.jsx<br/>redirect to newest completed scan"]
    end

    subgraph DOMAIN["components/ — domain"]
        direction TB
        d_side["Sidebar.jsx<br/>nav + account menu (switch account, sign out)"]
        d_protect["ProtectedRoute.jsx<br/>session check → login redirect"]
        d_brand["BrandMark.jsx<br/>logo"]
        d_compare["CodeCompare.jsx<br/>side by side / unified diff tabs"]
        d_expl["ExplanationPanel.jsx<br/>evidence why + optional AI summary"]
        d_gates["GateTable.jsx<br/>V0–V3 status, role, failing checks"]
        d_stages["StageList.jsx<br/>scan progress timeline"]
        d_verdict["VerdictBadge.jsx<br/>verdict → tone (only VERIFIED is green)"]
        d_tree["RepositoryTree.jsx<br/>filterable file tree"]
        d_upload["FileUpload.jsx<br/>drag and drop files / folder"]
        subgraph CODE["code/"]
            d_viewer["CodeViewer.jsx<br/>line numbers, highlighting, marks, markers,<br/>collapse, copy"]
            d_diff["DiffViewer.jsx<br/>unified diff with old/new numbers"]
        end
    end

    subgraph UI["components/ui/ — design system"]
        direction TB
        ui_btn["Button.jsx"]
        ui_badge["Badge.jsx<br/>+ SeverityBadge"]
        ui_status["StatusIndicator.jsx"]
        ui_header["PageHeader.jsx<br/>+ SectionHeader, breadcrumbs"]
        ui_panel["Panel.jsx"]
        ui_tabs["Tabs.jsx<br/>ARIA tabs + TabPanel"]
        ui_states["States.jsx<br/>Alert, Empty, Error, Loading, Skeleton"]
        ui_table["DataTable.jsx<br/>sort, paginate, mobile cards"]
        ui_filter["FilterBar.jsx<br/>SearchBar, Select"]
        ui_drawer["Drawer.jsx<br/>focus-trapped off-canvas"]
        ui_drop["Dropdown.jsx<br/>menu button"]
        ui_tip["Tooltip.jsx"]
        ui_toast["ToastProvider.jsx + toastContext.js<br/>notifications, useToast()"]
    end

    subgraph UTILS["utils/"]
        direction TB
        u_format["format.js<br/>dates, sizes, rule names, sort orders"]
        u_hl["highlight.js<br/>dependency-free Python tokenizer"]
        u_diff["diff.js<br/>changed line numbers from a unified diff"]
        u_file["fileUtils.js<br/>local file entries + tree"]
        u_val["validation.js<br/>local upload checks"]
        u_size["sizeUtils.js<br/>readable sizes (legacy)"]
    end

    subgraph STYLES["styles/"]
        direction TB
        st["tokens.css · base.css · components.css<br/>layout.css · code.css · pages.css"]
    end

    f_app --> f_ctx & ui_toast & d_protect & PAGES
    PAGES --> SERVICES
    PAGES --> f_dash & f_authl
    f_dash --> d_side & ui_drawer
    pg_find --> d_compare & d_expl & d_gates
    pg_scan --> d_stages & ui_table
    d_compare --> d_viewer & d_diff & u_diff
    d_viewer --> u_hl
    f_ctx --> f_auth
    f_main --> st
```
