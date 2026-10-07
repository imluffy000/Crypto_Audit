"""GitHub API access for the web flow: GitHub App user authorisation, repositories, trees, tarballs."""

from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlencode

import httpx
from pydantic import BaseModel

from cryptoaudit.ingest.filters import is_valid_github_name, is_valid_ref
from cryptoaudit.utils.errors import CryptoAuditError, ErrorCode

GITHUB_API_URL = "https://api.github.com"
GITHUB_WEB_URL = "https://github.com"
API_VERSION = "2022-11-28"
MAX_PAGES = 10


class GitHubUser(BaseModel):
    id: int
    login: str
    name: Optional[str] = None
    email: Optional[str] = None
    avatar_url: Optional[str] = None


class GitHubRepo(BaseModel):
    id: int
    full_name: str
    owner: str
    name: str
    private: bool
    default_branch: str
    size_kb: int = 0
    description: Optional[str] = None
    language: Optional[str] = None
    updated_at: Optional[str] = None
    html_url: Optional[str] = None


class TreeEntry(BaseModel):
    path: str
    type: str  # "blob" | "tree"
    size: Optional[int] = None


class OAuthToken(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: Optional[int] = None
    refresh_token: Optional[str] = None


def _repo(data: Dict[str, Any]) -> GitHubRepo:
    return GitHubRepo(
        id=data["id"],
        full_name=data["full_name"],
        owner=data["owner"]["login"],
        name=data["name"],
        private=bool(data.get("private")),
        default_branch=data.get("default_branch") or "main",
        size_kb=int(data.get("size") or 0),
        description=data.get("description"),
        language=data.get("language"),
        updated_at=data.get("updated_at"),
        html_url=data.get("html_url"),
    )


def _check_repo_ref(owner: str, name: str, ref: Optional[str] = None) -> None:
    if not (is_valid_github_name(owner) and is_valid_github_name(name)):
        raise CryptoAuditError(ErrorCode.INVALID_INPUT, "Invalid repository owner or name")
    if ref is not None and not is_valid_ref(ref):
        raise CryptoAuditError(ErrorCode.INVALID_INPUT, "Invalid git ref")


def _raise_for_status(response: httpx.Response, what: str) -> None:
    if response.status_code < 400:
        return
    if response.status_code == 401:
        raise CryptoAuditError(ErrorCode.AUTHENTICATION_ERROR, "GitHub rejected the access token; please sign in again")
    if response.status_code == 403 and response.headers.get("x-ratelimit-remaining") == "0":
        raise CryptoAuditError(ErrorCode.RATE_LIMITED, "GitHub API rate limit reached; try again later")
    if response.status_code in (403, 404):
        raise CryptoAuditError(ErrorCode.NOT_FOUND, f"{what} not found or not accessible to the CryptoAudit GitHub App")
    raise CryptoAuditError(ErrorCode.EXTERNAL_SERVICE_ERROR, f"GitHub returned HTTP {response.status_code} for {what}")


class GitHubClient:
    """User-to-server client. Holds the user's token only for the duration of a request or scan."""

    def __init__(
        self,
        token: str,
        transport: Optional[httpx.BaseTransport] = None,
        api_url: str = GITHUB_API_URL,
        timeout: float = 30.0,
    ) -> None:
        self._http = httpx.Client(
            base_url=api_url,
            transport=transport,
            timeout=timeout,
            follow_redirects=True,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": API_VERSION,
                "User-Agent": "CryptoAudit",
            },
        )

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> "GitHubClient":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def _get(self, path: str, what: str, params: Optional[Dict[str, Any]] = None) -> Any:
        try:
            response = self._http.get(path, params=params)
        except httpx.HTTPError as exc:
            raise CryptoAuditError(ErrorCode.EXTERNAL_SERVICE_ERROR, f"Cannot reach GitHub: {type(exc).__name__}") from exc
        _raise_for_status(response, what)
        return response.json()

    def get_user(self) -> GitHubUser:
        data = self._get("/user", "user")
        return GitHubUser(
            id=data["id"], login=data["login"], name=data.get("name"), email=data.get("email"), avatar_url=data.get("avatar_url")
        )

    def list_installation_repos(self) -> List[GitHubRepo]:
        """Repositories the user can access through installations of the CryptoAudit GitHub App."""
        repos: Dict[int, GitHubRepo] = {}
        installations = []
        for page in range(1, MAX_PAGES + 1):
            data = self._get("/user/installations", "installations", {"per_page": 100, "page": page})
            installations.extend(data.get("installations", []))
            if len(data.get("installations", [])) < 100:
                break
        for installation in installations:
            for page in range(1, MAX_PAGES + 1):
                data = self._get(
                    f"/user/installations/{int(installation['id'])}/repositories",
                    "installation repositories",
                    {"per_page": 100, "page": page},
                )
                for item in data.get("repositories", []):
                    repos[item["id"]] = _repo(item)
                if len(data.get("repositories", [])) < 100:
                    break
        return sorted(repos.values(), key=lambda r: r.full_name.lower())

    def get_repo(self, owner: str, name: str) -> GitHubRepo:
        _check_repo_ref(owner, name)
        return _repo(self._get(f"/repos/{owner}/{name}", f"repository {owner}/{name}"))

    def get_tree(self, owner: str, name: str, ref: str) -> Tuple[List[TreeEntry], bool]:
        _check_repo_ref(owner, name, ref)
        data = self._get(f"/repos/{owner}/{name}/git/trees/{ref}", f"tree {owner}/{name}@{ref}", {"recursive": 1})
        entries = [TreeEntry(path=e["path"], type=e["type"], size=e.get("size")) for e in data.get("tree", [])]
        return entries, bool(data.get("truncated"))

    def download_tarball(self, owner: str, name: str, ref: str, max_bytes: int) -> bytes:
        """Stream the repository tarball, aborting once it exceeds max_bytes."""
        _check_repo_ref(owner, name, ref)
        chunks: List[bytes] = []
        total = 0
        try:
            with self._http.stream("GET", f"/repos/{owner}/{name}/tarball/{ref}") as response:
                if response.status_code >= 400:
                    response.read()
                    _raise_for_status(response, f"tarball {owner}/{name}@{ref}")
                for chunk in response.iter_bytes():
                    total += len(chunk)
                    if total > max_bytes:
                        raise CryptoAuditError(
                            ErrorCode.LIMIT_EXCEEDED, f"Repository archive exceeds {max_bytes // (1024 * 1024)} MB"
                        )
                    chunks.append(chunk)
        except httpx.HTTPError as exc:
            raise CryptoAuditError(ErrorCode.EXTERNAL_SERVICE_ERROR, f"Repository download failed: {type(exc).__name__}") from exc
        return b"".join(chunks)


class GitHubAppAuth:
    """User authorisation for a GitHub App (web application flow)."""

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        transport: Optional[httpx.BaseTransport] = None,
        web_url: str = GITHUB_WEB_URL,
    ) -> None:
        self.client_id = client_id
        self._client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.web_url = web_url.rstrip("/")
        self._transport = transport

    def authorize_url(self, state: str) -> str:
        query = urlencode({"client_id": self.client_id, "redirect_uri": self.redirect_uri, "state": state})
        return f"{self.web_url}/login/oauth/authorize?{query}"

    def exchange_code(self, code: str) -> OAuthToken:
        try:
            with httpx.Client(transport=self._transport, timeout=30.0) as http:
                response = http.post(
                    f"{self.web_url}/login/oauth/access_token",
                    data={
                        "client_id": self.client_id,
                        "client_secret": self._client_secret,
                        "code": code,
                        "redirect_uri": self.redirect_uri,
                    },
                    headers={"Accept": "application/json"},
                )
        except httpx.HTTPError as exc:
            raise CryptoAuditError(ErrorCode.EXTERNAL_SERVICE_ERROR, "Cannot reach GitHub to complete sign-in") from exc
        data = response.json() if response.content else {}
        if response.status_code >= 400 or "access_token" not in data:
            reason = data.get("error_description") or data.get("error") or f"HTTP {response.status_code}"
            raise CryptoAuditError(ErrorCode.AUTHENTICATION_ERROR, f"GitHub sign-in failed: {reason}")
        return OAuthToken(**{k: data[k] for k in ("access_token", "token_type", "expires_in", "refresh_token") if k in data})
