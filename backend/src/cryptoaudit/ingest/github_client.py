"""GitHub API access for the web flow: OAuth App sign-in, repositories, trees, tarballs. Read-only use."""

import io
from typing import Any, BinaryIO, Dict, List, Optional, Sequence, Tuple
from urllib.parse import urlencode

import httpx
from pydantic import BaseModel

from cryptoaudit.ingest.filters import is_valid_github_name, is_valid_ref
from cryptoaudit.utils.errors import CryptoAuditError, ErrorCode

GITHUB_API_URL = "https://api.github.com"
GITHUB_WEB_URL = "https://github.com"
API_VERSION = "2022-11-28"
MAX_PAGES = 10
CONNECT_RETRIES = 2  # extra attempts when a connection to GitHub cannot be opened


def _transport(transport: Optional[httpx.BaseTransport]) -> httpx.BaseTransport:
    """
    The given transport (tests), or the default one with retries. httpx only retries when the
    connection itself fails (connect error or timeout), so nothing was sent and a retry is always safe.
    """
    return transport if transport is not None else httpx.HTTPTransport(retries=CONNECT_RETRIES)


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
        raise CryptoAuditError(ErrorCode.NOT_FOUND, f"{what} not found or not accessible with your GitHub authorisation")
    raise CryptoAuditError(ErrorCode.EXTERNAL_SERVICE_ERROR, f"GitHub returned HTTP {response.status_code} for {what}")


class GitHubClient:
    """
    Client acting as the signed-in user. Holds the token only for the duration of a request or scan,
    and only ever issues read requests (even when the OAuth scope would allow writes).
    """

    def __init__(
        self,
        token: str,
        transport: Optional[httpx.BaseTransport] = None,
        api_url: str = GITHUB_API_URL,
        timeout: float = 30.0,
    ) -> None:
        self._http = httpx.Client(
            base_url=api_url,
            transport=_transport(transport),
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

    def list_user_repos(self, include_private: bool = True) -> List[GitHubRepo]:
        """Repositories the user owns, collaborates on or can see through organisation membership."""
        repos: Dict[int, GitHubRepo] = {}
        params: Dict[str, Any] = {
            "per_page": 100,
            "sort": "updated",
            "affiliation": "owner,collaborator,organization_member",
            "visibility": "all" if include_private else "public",
        }
        for page in range(1, MAX_PAGES + 1):
            items = self._get("/user/repos", "repositories", {**params, "page": page})
            for item in items:
                repos[item["id"]] = _repo(item)
            if len(items) < 100:
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
        """Download the repository tarball into memory (small repositories and tests)."""
        buffer = io.BytesIO()
        self.download_tarball_to(owner, name, ref, max_bytes, buffer)
        return buffer.getvalue()

    def download_tarball_to(self, owner: str, name: str, ref: str, max_bytes: int, sink: BinaryIO) -> int:
        """Stream the repository tarball into sink, aborting once it exceeds max_bytes. Returns bytes written."""
        _check_repo_ref(owner, name, ref)
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
                    sink.write(chunk)
        except httpx.HTTPError as exc:
            raise CryptoAuditError(ErrorCode.EXTERNAL_SERVICE_ERROR, f"Repository download failed: {type(exc).__name__}") from exc
        return total


class GitHubOAuth:
    """OAuth App sign-in (web application flow) and token revocation."""

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        scopes: Sequence[str] = ("read:user",),
        transport: Optional[httpx.BaseTransport] = None,
        web_url: str = GITHUB_WEB_URL,
        api_url: str = GITHUB_API_URL,
    ) -> None:
        self.client_id = client_id
        self._client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.scopes = tuple(scopes)
        self.web_url = web_url.rstrip("/")
        self.api_url = api_url.rstrip("/")
        self._transport = transport

    @property
    def manage_access_url(self) -> str:
        """Where a user reviews or revokes this app's access (and requests organisation approval)."""
        return f"{self.web_url}/settings/connections/applications/{self.client_id}"

    def authorize_url(self, state: str, select_account: bool = False) -> str:
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "scope": " ".join(self.scopes),
            "state": state,
            "allow_signup": "false",
        }
        if select_account:
            # Show GitHub's account picker instead of silently reusing the account signed in to github.com.
            params["prompt"] = "select_account"
        return f"{self.web_url}/login/oauth/authorize?{urlencode(params)}"

    def exchange_code(self, code: str) -> OAuthToken:
        try:
            with httpx.Client(transport=_transport(self._transport), timeout=30.0) as http:
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

    def revoke(self, access_token: str) -> bool:
        """
        Revoke a user token at GitHub. OAuth App tokens do not expire, so this runs on logout.
        Best effort: returns False instead of raising when GitHub cannot be reached.
        """
        try:
            with httpx.Client(transport=_transport(self._transport), timeout=15.0) as http:
                response = http.request(
                    "DELETE",
                    f"{self.api_url}/applications/{self.client_id}/token",
                    auth=(self.client_id, self._client_secret),
                    json={"access_token": access_token},
                    headers={"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": API_VERSION},
                )
        except httpx.HTTPError:
            return False
        return response.status_code in (204, 404)
