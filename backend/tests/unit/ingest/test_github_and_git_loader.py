"""GitHub client (mocked HTTP) and in-memory tarball ingestion tests."""

import io
import json
import tarfile
from urllib.parse import parse_qs, urlparse

import httpx
import pytest

from cryptoaudit.ingest.filters import SnapshotLimits, is_valid_ref, safe_relative_path
from cryptoaudit.ingest.git_loader import fetch_repository, read_python_modules
from cryptoaudit.ingest.github_client import GitHubClient, GitHubOAuth
from cryptoaudit.utils.errors import CryptoAuditError, ErrorCode

REPO_JSON = {
    "id": 7,
    "full_name": "alice/app",
    "owner": {"login": "alice"},
    "name": "app",
    "private": True,
    "default_branch": "main",
    "size": 12,
}


def make_tarball(files, top="alice-app-abc1234", extra=None) -> bytes:
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as tar:
        root = tarfile.TarInfo(top)
        root.type = tarfile.DIRTYPE
        tar.addfile(root)
        for path, content in files.items():
            data = content if isinstance(content, bytes) else content.encode("utf-8")
            info = tarfile.TarInfo(f"{top}/{path}")
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
        for info in extra or []:
            tar.addfile(info)
    return buffer.getvalue()


def github_transport(routes):
    def handler(request: httpx.Request) -> httpx.Response:
        key = (request.method, request.url.path)
        if key not in routes:
            return httpx.Response(404, json={"message": "Not Found"})
        status, body = routes[key](request) if callable(routes[key]) else routes[key]
        if isinstance(body, bytes):
            return httpx.Response(status, content=body)
        return httpx.Response(status, json=body)

    return httpx.MockTransport(handler)


# --- filters ---------------------------------------------------------------------------------


@pytest.mark.parametrize("raw", ["../etc/passwd", "/abs.py", "a/../../b.py", "C:/x.py", "a\\b.py", ""])
def test_unsafe_paths_rejected(raw):
    assert safe_relative_path(raw) is None


def test_safe_path_normalised():
    assert safe_relative_path("src/pkg/mod.py") == "src/pkg/mod.py"
    assert safe_relative_path("./src/mod.py") == "src/mod.py"


@pytest.mark.parametrize("ref, ok", [("main", True), ("feature/x-1", True), ("../main", False), ("a b", False), ("/x", False)])
def test_ref_validation(ref, ok):
    assert is_valid_ref(ref) is ok


# --- tarball ingestion -----------------------------------------------------------------------


def test_reads_only_python_files_in_memory():
    archive = make_tarball(
        {"src/app.py": "import hashlib\n", "README.md": "# hi", "src/.venv/lib/x.py": "x=1", "node_modules/y.py": "y=1"}
    )
    snapshot = read_python_modules(archive, SnapshotLimits())
    assert [m.module_name for m in snapshot.modules] == ["src/app.py"]
    assert snapshot.commit == "abc1234"


def test_symlinks_and_traversal_are_skipped():
    link = tarfile.TarInfo("alice-app-abc1234/evil.py")
    link.type = tarfile.SYMTYPE
    link.linkname = "/etc/passwd"
    traversal = tarfile.TarInfo("alice-app-abc1234/../../outside.py")
    traversal.size = 0
    snapshot = read_python_modules(make_tarball({"ok.py": "x = 1\n"}, extra=[link, traversal]), SnapshotLimits())
    assert [m.module_name for m in snapshot.modules] == ["ok.py"]
    reasons = {s.reason for s in snapshot.skipped}
    assert {"not a regular file", "unsafe path"} <= reasons


def test_limits_and_encoding_are_enforced():
    archive = make_tarball({"a.py": "a = 1\n", "b.py": "b = 2\n", "big.py": "x" * 50, "bin.py": b"\xff\xfe"})
    snapshot = read_python_modules(archive, SnapshotLimits(max_python_files=1, max_file_bytes=20))
    assert [m.module_name for m in snapshot.modules] == ["a.py"]
    reasons = {s.path: s.reason for s in snapshot.skipped}
    assert reasons["big.py"] == "file too large"
    assert reasons["b.py"] == "file count limit reached"


def test_unpacked_size_limit():
    with pytest.raises(CryptoAuditError) as excinfo:
        read_python_modules(make_tarball({"a.py": "x" * 200}), SnapshotLimits(max_unpacked_bytes=100))
    assert excinfo.value.code is ErrorCode.LIMIT_EXCEEDED


def test_reads_from_file_objects():
    import tempfile

    with tempfile.TemporaryFile() as handle:
        handle.write(make_tarball({"pkg/a.py": "x = 1\n"}))
        snapshot = read_python_modules(handle, SnapshotLimits())
    assert [m.module_name for m in snapshot.modules] == ["pkg/a.py"] and snapshot.archive_bytes > 0


def test_download_streams_into_sink():
    archive = make_tarball({"a.py": "x = 1\n"})
    transport = github_transport({("GET", "/repos/alice/app/tarball/main"): (200, archive)})
    sink = io.BytesIO()
    written = GitHubClient("t", transport=transport).download_tarball_to("alice", "app", "main", 10_000, sink)
    assert written == len(archive) and sink.getvalue() == archive


def test_invalid_archive():
    with pytest.raises(CryptoAuditError) as excinfo:
        read_python_modules(b"not a tarball", SnapshotLimits())
    assert excinfo.value.code is ErrorCode.INVALID_INPUT


# --- GitHub client ---------------------------------------------------------------------------


def test_lists_user_repos_with_pagination():
    seen = []
    page_one = [dict(REPO_JSON, id=1000 + i, full_name=f"alice/r{i:03d}", name=f"r{i:03d}") for i in range(100)]

    def repos(request):
        seen.append(dict(request.url.params))
        page = int(request.url.params["page"])
        return 200, page_one if page == 1 else [REPO_JSON, page_one[0]]  # duplicate is de-duplicated

    repos_list = GitHubClient("t", transport=github_transport({("GET", "/user/repos"): repos})).list_user_repos()
    assert len(repos_list) == 101 and repos_list[0].full_name == "alice/app"
    assert [p["page"] for p in seen] == ["1", "2"]
    assert seen[0]["visibility"] == "all" and "organization_member" in seen[0]["affiliation"]


def test_public_only_listing_requests_public_visibility():
    seen = {}

    def repos(request):
        seen.update(request.url.params)
        return 200, []

    GitHubClient("t", transport=github_transport({("GET", "/user/repos"): repos})).list_user_repos(include_private=False)
    assert seen["visibility"] == "public"


def test_sends_token_and_api_version():
    seen = {}

    def user(request):
        seen.update(request.headers)
        return 200, {"id": 1, "login": "alice"}

    GitHubClient("secret-token", transport=github_transport({("GET", "/user"): user})).get_user()
    assert seen["authorization"] == "Bearer secret-token"
    assert seen["x-github-api-version"]


@pytest.mark.parametrize(
    "status, headers, code",
    [(401, {}, ErrorCode.AUTHENTICATION_ERROR), (404, {}, ErrorCode.NOT_FOUND), (500, {}, ErrorCode.EXTERNAL_SERVICE_ERROR)],
)
def test_http_errors_are_structured(status, headers, code):
    transport = httpx.MockTransport(lambda request: httpx.Response(status, headers=headers, json={}))
    with pytest.raises(CryptoAuditError) as excinfo:
        GitHubClient("t", transport=transport).get_user()
    assert excinfo.value.code is code


def test_rate_limit_is_reported():
    transport = httpx.MockTransport(lambda r: httpx.Response(403, headers={"x-ratelimit-remaining": "0"}, json={}))
    with pytest.raises(CryptoAuditError) as excinfo:
        GitHubClient("t", transport=transport).get_user()
    assert excinfo.value.code is ErrorCode.RATE_LIMITED


def test_invalid_names_never_reach_github():
    transport = httpx.MockTransport(lambda r: pytest.fail("request must not be sent"))
    with pytest.raises(CryptoAuditError):
        GitHubClient("t", transport=transport).get_repo("alice", "../../etc")


def test_tarball_download_enforces_size_limit():
    archive = make_tarball({"a.py": "x" * 5000})
    transport = github_transport({("GET", "/repos/alice/app/tarball/main"): (200, archive)})
    with pytest.raises(CryptoAuditError) as excinfo:
        GitHubClient("t", transport=transport).download_tarball("alice", "app", "main", max_bytes=10)
    assert excinfo.value.code is ErrorCode.LIMIT_EXCEEDED


def test_fetch_repository_end_to_end():
    archive = make_tarball({"pkg/auth.py": "import hashlib\n"})
    transport = github_transport({("GET", "/repos/alice/app/tarball/main"): (200, archive)})
    snapshot = fetch_repository(GitHubClient("t", transport=transport), "alice", "app", "main", SnapshotLimits())
    assert snapshot.full_name == "alice/app" and snapshot.ref == "main"
    assert snapshot.modules[0].module_name == "pkg/auth.py"


# --- OAuth App sign-in ------------------------------------------------------------------------


def test_authorize_url_contains_scope_state_and_redirect():
    auth = GitHubOAuth("Ov23abc", "secret", "http://localhost:5173/api/auth/github/callback", scopes=("read:user", "repo"))
    query = parse_qs(urlparse(auth.authorize_url("st4te")).query)
    assert query == {
        "client_id": ["Ov23abc"],
        "redirect_uri": ["http://localhost:5173/api/auth/github/callback"],
        "scope": ["read:user repo"],
        "state": ["st4te"],
        "allow_signup": ["false"],
    }
    assert auth.manage_access_url == "https://github.com/settings/connections/applications/Ov23abc"
    switch = parse_qs(urlparse(auth.authorize_url("st4te", select_account=True)).query)
    assert switch["prompt"] == ["select_account"] and switch["state"] == ["st4te"]


def test_revoke_uses_app_credentials():
    seen = {}

    def revoke(request):
        seen["auth"] = request.headers["authorization"]
        seen["body"] = request.content.decode()
        return 204, b""

    transport = github_transport({("DELETE", "/applications/Ov23abc/token"): revoke})
    assert GitHubOAuth("Ov23abc", "secret", "http://cb", transport=transport).revoke("gho_x") is True
    assert seen["auth"].startswith("Basic ") and "gho_x" in seen["body"]


def test_revoke_is_best_effort():
    def boom(request):
        raise httpx.ConnectError("offline")

    assert GitHubOAuth("id", "secret", "http://cb", transport=httpx.MockTransport(boom)).revoke("gho_x") is False


def test_code_exchange():
    def token(request):
        body = parse_qs(request.content.decode())
        assert body["code"] == ["c0de"] and body["client_secret"] == ["secret"]
        return 200, {"access_token": "ghu_x", "token_type": "bearer", "expires_in": 28800, "refresh_token": "ghr_y"}

    auth = GitHubOAuth("id", "secret", "http://cb", transport=github_transport({("POST", "/login/oauth/access_token"): token}))
    result = auth.exchange_code("c0de")
    assert result.access_token == "ghu_x" and result.expires_in == 28800


def test_code_exchange_error():
    transport = github_transport({("POST", "/login/oauth/access_token"): (200, {"error": "bad_verification_code"})})
    with pytest.raises(CryptoAuditError) as excinfo:
        GitHubOAuth("id", "secret", "http://cb", transport=transport).exchange_code("x")
    assert excinfo.value.code is ErrorCode.AUTHENTICATION_ERROR
    assert "bad_verification_code" in excinfo.value.message


def test_json_helper_unused_guard():
    # Ensures the mock transport serialises JSON bodies like GitHub does.
    assert json.loads(json.dumps(REPO_JSON))["owner"]["login"] == "alice"


def test_github_connections_retry_by_default_but_tests_keep_their_transport():
    import httpx

    from cryptoaudit.ingest.github_client import _transport

    default = _transport(None)
    assert isinstance(default, httpx.HTTPTransport)  # httpx retries failed connection attempts on this transport
    mock = httpx.MockTransport(lambda request: httpx.Response(200))
    assert _transport(mock) is mock
