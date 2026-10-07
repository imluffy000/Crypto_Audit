"""API tests with a simulated GitHub: sign-in, repositories, scans, findings, AI explanations, reports."""

import io
import tarfile
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
from fastapi.testclient import TestClient

from cryptoaudit.analysis.analyzer import AnalyzerEngine
from cryptoaudit.api.app import create_app
from cryptoaudit.api.dependencies import SESSION_COOKIE, STATE_COOKIE
from cryptoaudit.api.services import InlineExecutor, Services
from cryptoaudit.config.settings import Settings
from cryptoaudit.ingest.filters import SnapshotLimits
from cryptoaudit.ingest.github_client import GitHubClient, GitHubOAuth
from cryptoaudit.llm.schemas import LLMRequest, LLMResponse
from cryptoaudit.models.scan import ScanStage, StageProgress
from cryptoaudit.pipeline.orchestrator import RepairPipeline
from cryptoaudit.repair.s2_template import TemplateRepairStrategy
from cryptoaudit.storage.web_store import WebStore
from cryptoaudit.validation.runner import ValidationPipeline
from cryptoaudit.validation.sandbox import Sandbox
from cryptoaudit.validation.v0_scanner import ScannerValidator

FIXTURES = Path("tests/fixtures")
REPO = {"id": 7, "full_name": "alice/app", "owner": {"login": "alice"}, "name": "app", "private": True, "default_branch": "main", "size": 40}


def tarball() -> bytes:
    files = {
        "app/tokens.py": (FIXTURES / "cr5" / "vulnerable.py").read_text(encoding="utf-8"),
        "app/auth.py": (FIXTURES / "cr1" / "vulnerable.py").read_text(encoding="utf-8"),
        "README.md": "# app",
    }
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as tar:
        for path, content in files.items():
            data = content.encode("utf-8")
            info = tarfile.TarInfo(f"alice-app-abc1234/{path}")
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
    return buffer.getvalue()


class FakeGitHub:
    def __init__(self):
        self.users = {"ghu_alice": {"id": 1, "login": "alice", "name": "Alice"}, "ghu_bob": {"id": 2, "login": "bob"}}
        self.codes = {"code-alice": "ghu_alice", "code-bob": "ghu_bob"}
        self.repo = dict(REPO)
        self.tarball_status = 200
        self.revoked = []

    def handler(self, request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if request.url.host == "github.com" and path == "/login/oauth/access_token":
            code = parse_qs(request.content.decode())["code"][0]
            if code not in self.codes:
                return httpx.Response(200, json={"error": "bad_verification_code"})
            return httpx.Response(200, json={"access_token": self.codes[code], "token_type": "bearer"})
        if request.method == "DELETE" and path == "/applications/Ov23test/token":
            self.revoked.append(request.content.decode())
            return httpx.Response(204)
        token = request.headers.get("authorization", "").removeprefix("Bearer ")
        if token not in self.users:
            return httpx.Response(401, json={})
        routes = {
            "/user": self.users[token],
            "/user/repos": [self.repo],
            "/repos/alice/app": self.repo,
            "/repos/alice/app/git/trees/main": {
                "tree": [
                    {"path": "app", "type": "tree"},
                    {"path": "app/tokens.py", "type": "blob", "size": 300},
                    {"path": "app/auth.py", "type": "blob", "size": 400},
                    {"path": "README.md", "type": "blob", "size": 5},
                ],
                "truncated": False,
            },
        }
        if path == "/repos/alice/app/tarball/main":
            return httpx.Response(self.tarball_status, content=tarball() if self.tarball_status == 200 else b"")
        if path in routes:
            return httpx.Response(200, json=routes[path])
        return httpx.Response(404, json={})


class ForbiddenSandbox(Sandbox):
    name = "forbidden"

    def _execute(self, work, argv, nonce):
        raise AssertionError("web scans must never execute repository code")


class FakeLLM:
    def __init__(self):
        self.available = True
        self.calls = 0

    def generate(self, request: LLMRequest) -> LLMResponse:
        self.calls += 1
        return LLMResponse(text="Plain-language narrative.", model=request.model)


@pytest.fixture()
def env(tmp_path):
    settings = Settings(
        github_client_id="Ov23test",
        github_client_secret="client-secret",
        session_secret="s" * 40,
        web_db=tmp_path / "web.sqlite",
        public_url="http://localhost:5173",
        enable_bandit=False,
        enable_semgrep=False,
    )
    github = FakeGitHub()
    transport = httpx.MockTransport(github.handler)
    llm = FakeLLM()
    analyzer = AnalyzerEngine()

    def pipeline_factory(strategy_ids):
        return RepairPipeline(
            analyzer=analyzer,
            strategies=[TemplateRepairStrategy()],
            validator=ValidationPipeline(ForbiddenSandbox(), ScannerValidator(analyzer)),
        )

    services = Services(
        settings=settings,
        store=WebStore(settings.web_db, "s" * 40),
        auth=GitHubOAuth("Ov23test", "client-secret", settings.oauth_redirect_uri, settings.github_oauth_scopes, transport=transport),
        github=lambda token: GitHubClient(token, transport=transport),
        llm=llm,
        llm_available=lambda: llm.available,
        pipeline_factory=pipeline_factory,
        executor=InlineExecutor(),
        limits=SnapshotLimits(),
    )
    client = TestClient(create_app(services), follow_redirects=False)
    return client, services, github, llm


def sign_in(client, code="code-alice"):
    login = client.get("/api/auth/github/login")
    state = parse_qs(urlparse(login.headers["location"]).query)["state"][0]
    return client.get(f"/api/auth/github/callback?code={code}&state={state}")


def start_scan(client):
    response = client.post("/api/scans", json={"owner": "alice", "name": "app"})
    assert response.status_code == 202, response.text
    return response.json()["scan_id"]


# --- system & auth -----------------------------------------------------------------------------


def test_health_reports_capabilities(env):
    client, *_ = env
    body = client.get("/api/health").json()
    assert body["github_configured"] is True and body["llm_available"] is True
    assert body["manage_access_url"] == "https://github.com/settings/connections/applications/Ov23test"
    assert body["repo_access"] == "private"


def test_login_redirects_to_github_with_state_cookie(env):
    client, *_ = env
    response = client.get("/api/auth/github/login")
    assert response.status_code == 302
    location = urlparse(response.headers["location"])
    query = parse_qs(location.query)
    assert location.netloc == "github.com" and query["client_id"] == ["Ov23test"]
    assert query["scope"] == ["read:user repo"]
    assert query["redirect_uri"] == ["http://localhost:5173/api/auth/github/callback"]
    cookie = response.headers["set-cookie"]
    assert STATE_COOKIE in cookie and "HttpOnly" in cookie and query["state"][0] in cookie


def test_callback_creates_http_only_session(env):
    client, *_ = env
    response = sign_in(client)
    assert response.status_code == 302 and response.headers["location"] == "http://localhost:5173/#/dashboard"
    cookies = response.headers.get_list("set-cookie")
    session_cookie = next(c for c in cookies if c.startswith(SESSION_COOKIE))
    assert "HttpOnly" in session_cookie and "samesite=lax" in session_cookie.lower()
    assert client.get("/api/auth/me").json()["login"] == "alice"


def test_callback_rejects_mismatched_or_replayed_state(env):
    client, services, *_ = env
    forged = services.store.create_oauth_state()  # valid on the server but never issued to this browser
    response = client.get(f"/api/auth/github/callback?code=code-alice&state={forged}")
    assert response.headers["location"].endswith("/#/login?error=invalid_state")
    assert client.get("/api/auth/me").status_code == 401

    login = client.get("/api/auth/github/login")
    state = parse_qs(urlparse(login.headers["location"]).query)["state"][0]
    client.get(f"/api/auth/github/callback?code=code-alice&state={state}")
    client.cookies.set(STATE_COOKIE, state, path="/api/auth")
    replay = client.get(f"/api/auth/github/callback?code=code-alice&state={state}")
    assert "invalid_state" in replay.headers["location"]


def test_bad_code_redirects_with_error(env):
    client, *_ = env
    response = sign_in(client, code="nope")
    assert response.headers["location"].endswith("/#/login?error=authentication_error")


def test_logout_ends_session_and_revokes_token(env):
    client, services, github, _ = env
    sign_in(client)
    assert client.post("/api/auth/logout").status_code == 204
    assert client.get("/api/auth/me").status_code == 401
    assert len(github.revoked) == 1 and "ghu_alice" in github.revoked[0]


def test_protected_routes_require_sign_in(env):
    client, *_ = env
    response = client.get("/api/repos")
    assert response.status_code == 401
    assert response.json() == {"error": {"code": "AUTHENTICATION_ERROR", "message": "Sign in with GitHub to continue"}}


def test_github_not_configured(env):
    client, services, *_ = env
    services.auth = None
    response = client.get("/api/auth/github/login")
    assert response.status_code == 502 and response.json()["error"]["code"] == "EXTERNAL_SERVICE_ERROR"


# --- repositories --------------------------------------------------------------------------------


def test_lists_repos_and_nested_tree(env):
    client, *_ = env
    sign_in(client)
    repos = client.get("/api/repos").json()
    assert [r["full_name"] for r in repos] == ["alice/app"]
    tree = client.get("/api/repos/alice/app/tree").json()
    assert tree["ref"] == "main" and tree["python_files"] == 2 and tree["files"] == 3
    root = tree["tree"]
    assert [c["name"] for c in root["children"]] == ["app", "README.md"]  # folders first
    assert [c["name"] for c in root["children"][0]["children"]] == ["auth.py", "tokens.py"]


# --- scans ---------------------------------------------------------------------------------------


def test_full_scan_flow(env):
    client, *_ = env
    sign_in(client)
    scan_id = start_scan(client)
    scan = client.get(f"/api/scans/{scan_id}").json()
    assert scan["status"] == "COMPLETED", scan
    assert scan["commit"] == "abc1234" and all(s["status"] == "DONE" for s in scan["stages"])
    assert scan["summary"]["files_scanned"] == 2 and scan["summary"]["findings"] >= 3

    findings = client.get(f"/api/scans/{scan_id}/findings").json()
    rules = {f["finding"]["rule_id"] for f in findings}
    assert {"CR1", "CR5"} <= rules

    token_finding = next(f for f in findings if f["finding"]["rule_id"] == "CR5")
    detail = client.get(f"/api/scans/{scan_id}/findings/{token_finding['finding_id']}").json()
    assert detail["file_path"] == "app/tokens.py" and "random" in detail["original_source"]
    run = detail["runs"][0]
    assert run["strategy_id"] == "S2" and run["verdict"] == "UNVERIFIED" and run["targets_finding"]
    assert "secrets.choice" in run["candidate_code"] and run["diff"].startswith("---")
    assert run["explanation"]["limitations"] and {g["gate"] for g in run["gates"]} == {"V0", "V1", "V2", "V3"}

    assert [s["scan_id"] for s in client.get("/api/scans").json()] == [scan_id]
    report = client.get(f"/api/reports/{scan_id}.md")
    assert report.status_code == 200 and "attachment" in report.headers["content-disposition"]
    assert "# CryptoAudit report: alice/app" in report.text


def test_scans_are_private(env):
    client, services, github, _ = env
    sign_in(client)
    scan_id = start_scan(client)
    other = TestClient(client.app, follow_redirects=False)
    sign_in(other, code="code-bob")
    assert other.get(f"/api/scans/{scan_id}").status_code == 404
    assert other.get(f"/api/scans/{scan_id}/findings").status_code == 404


def test_scan_input_validation_and_limits(env):
    client, services, github, _ = env
    sign_in(client)
    assert client.post("/api/scans", json={"owner": "alice", "name": "../etc"}).status_code == 400
    github.repo["size"] = 10_000_000
    assert client.post("/api/scans", json={"owner": "alice", "name": "app"}).status_code == 413
    github.repo["size"] = 40
    stages = [StageProgress(stage=s, label=s.value) for s in ScanStage]
    services.store.create_scan(1, "alice/app", "main", stages)  # an already-queued scan
    assert client.post("/api/scans", json={"owner": "alice", "name": "app"}).status_code == 429


def test_failed_fetch_is_reported(env):
    client, services, github, _ = env
    github.tarball_status = 404
    sign_in(client)
    scan_id = start_scan(client)
    scan = client.get(f"/api/scans/{scan_id}").json()
    assert scan["status"] == "FAILED" and scan["error"]["code"] == "NOT_FOUND"
    assert scan["stages"][0]["status"] == "FAILED"
    assert client.get(f"/api/scans/{scan_id}/findings").status_code == 400


def test_ai_explanation_is_cached_and_labelled(env):
    client, services, github, llm = env
    sign_in(client)
    scan_id = start_scan(client)
    finding = client.get(f"/api/scans/{scan_id}/findings").json()[0]
    candidate_id = client.get(f"/api/scans/{scan_id}/findings/{finding['finding_id']}").json()["runs"][0]["candidate_id"]
    first = client.post(f"/api/scans/{scan_id}/candidates/{candidate_id}/ai-explanation")
    assert first.status_code == 200 and "not a security verdict" in first.json()["disclaimer"]
    client.post(f"/api/scans/{scan_id}/candidates/{candidate_id}/ai-explanation")
    assert llm.calls == 1


def test_ai_explanation_unavailable(env):
    client, services, github, llm = env
    sign_in(client)
    scan_id = start_scan(client)
    finding = client.get(f"/api/scans/{scan_id}/findings").json()[0]
    candidate_id = client.get(f"/api/scans/{scan_id}/findings/{finding['finding_id']}").json()["runs"][0]["candidate_id"]
    llm.available = False
    response = client.post(f"/api/scans/{scan_id}/candidates/{candidate_id}/ai-explanation")
    assert response.status_code == 503 and response.json()["error"]["code"] == "LLM_ERROR"


def test_security_headers(env):
    client, *_ = env
    response = client.get("/api/health")
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["cache-control"] == "no-store"
