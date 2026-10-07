"""Request dependencies: service lookup and the signed-in session."""

from fastapi import Depends, Request

from cryptoaudit.api.services import Services
from cryptoaudit.storage.web_store import SessionInfo
from cryptoaudit.utils.errors import CryptoAuditError, ErrorCode

SESSION_COOKIE = "ca_session"
STATE_COOKIE = "ca_oauth_state"


def get_services(request: Request) -> Services:
    return request.app.state.services


def current_session(request: Request, services: Services = Depends(get_services)) -> SessionInfo:
    session = services.store.get_session(request.cookies.get(SESSION_COOKIE))
    if session is None:
        raise CryptoAuditError(ErrorCode.AUTHENTICATION_ERROR, "Sign in with GitHub to continue")
    return session
