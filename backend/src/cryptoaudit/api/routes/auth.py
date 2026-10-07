"""GitHub OAuth App sign-in: redirect to GitHub, handle the callback, issue a session cookie, revoke on logout."""

import logging
from typing import Optional
from urllib.parse import quote

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import RedirectResponse

from cryptoaudit.api.dependencies import SESSION_COOKIE, STATE_COOKIE, current_session, get_services
from cryptoaudit.api.schemas import UserOut
from cryptoaudit.api.services import Services
from cryptoaudit.storage.web_store import SessionInfo
from cryptoaudit.utils.errors import CryptoAuditError, ErrorCode

router = APIRouter(prefix="/auth", tags=["auth"])
logger = logging.getLogger("cryptoaudit.api.auth")


def _frontend(services: Services, route: str) -> str:
    return f"{services.settings.public_url.rstrip('/')}/#{route}"


@router.get("/github/login")
def github_login(select_account: bool = False, services: Services = Depends(get_services)) -> RedirectResponse:
    """Start sign-in. ``select_account=true`` asks GitHub to let the user pick a different account."""
    if services.auth is None:
        raise CryptoAuditError(ErrorCode.EXTERNAL_SERVICE_ERROR, "GitHub sign-in is not configured on this server")
    state = services.store.create_oauth_state()
    response = RedirectResponse(services.auth.authorize_url(state, select_account=select_account), status_code=302)
    # Bind the state to this browser as well as to the server (login-CSRF protection).
    response.set_cookie(
        STATE_COOKIE, state, max_age=600, httponly=True, samesite="lax", secure=services.settings.cookie_secure, path="/api/auth"
    )
    return response


@router.get("/github/callback")
def github_callback(request: Request, code: str = "", state: str = "", services: Services = Depends(get_services)) -> RedirectResponse:
    def fail(reason: str) -> RedirectResponse:
        response = RedirectResponse(_frontend(services, f"/login?error={quote(reason)}"), status_code=302)
        response.delete_cookie(STATE_COOKIE, path="/api/auth")
        return response

    if services.auth is None:
        return fail("not_configured")
    cookie_state = request.cookies.get(STATE_COOKIE, "")
    # Consume the server-side state first so it can never be replayed, then compare with the browser's copy.
    state_valid = services.store.consume_oauth_state(state)
    if not code or not state_valid or not cookie_state or cookie_state != state:
        return fail("invalid_state")
    try:
        token = services.auth.exchange_code(code)
        with services.github(token.access_token) as client:
            user = client.get_user()
    except CryptoAuditError as exc:
        logger.warning("GitHub sign-in failed: %s", exc.code.value)
        return fail(exc.code.value.lower())
    except Exception:  # never show a bare 500 page mid sign-in; details go to the server log
        logger.exception("Unexpected error while completing GitHub sign-in")
        return fail("server_error")

    _end_session(services, request.cookies.get(SESSION_COOKIE), keep_token=token.access_token)
    session_id = services.store.create_session(user, token.access_token, services.settings.session_ttl_hours)
    response = RedirectResponse(_frontend(services, "/dashboard"), status_code=302)
    response.delete_cookie(STATE_COOKIE, path="/api/auth")
    response.set_cookie(
        SESSION_COOKIE,
        session_id,
        max_age=int(services.settings.session_ttl_hours * 3600),
        httponly=True,
        samesite="lax",
        secure=services.settings.cookie_secure,
        path="/",
    )
    return response


def _end_session(services: Services, session_id: Optional[str], keep_token: Optional[str] = None) -> None:
    """Delete a session and revoke its GitHub token (best effort). Used on logout and when switching accounts."""
    if not session_id:
        return
    session = services.store.get_session(session_id)
    services.store.delete_session(session_id)
    # OAuth App tokens never expire on their own: revoke this one at GitHub.
    if session is None or services.auth is None or session.access_token == keep_token:
        return
    if not services.auth.revoke(session.access_token):
        logger.warning("Could not revoke a GitHub token; the user can revoke it in GitHub settings")


@router.get("/me", response_model=UserOut)
def me(session: SessionInfo = Depends(current_session)) -> UserOut:
    return UserOut(**session.user.model_dump())


@router.post("/logout", status_code=204)
def logout(request: Request, services: Services = Depends(get_services)) -> Response:
    _end_session(services, request.cookies.get(SESSION_COOKIE))
    response = Response(status_code=204)
    response.delete_cookie(SESSION_COOKIE, path="/")
    return response
