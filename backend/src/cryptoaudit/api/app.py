"""FastAPI application: the website backend. All routes are served under /api."""

import logging
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from cryptoaudit import __version__
from cryptoaudit.api.routes import auth, findings, reports, repos, scan
from cryptoaudit.api.schemas import HealthOut
from cryptoaudit.api.services import Services, default_services
from cryptoaudit.utils.errors import CryptoAuditError, ErrorCode

logger = logging.getLogger("cryptoaudit.api")

STATUS_BY_CODE = {
    ErrorCode.INVALID_INPUT: 400,
    ErrorCode.AUTHENTICATION_ERROR: 401,
    ErrorCode.PERMISSION_DENIED: 403,
    ErrorCode.NOT_FOUND: 404,
    ErrorCode.LIMIT_EXCEEDED: 413,
    ErrorCode.RATE_LIMITED: 429,
    ErrorCode.EXTERNAL_SERVICE_ERROR: 502,
    ErrorCode.LLM_ERROR: 503,
    ErrorCode.TIMEOUT: 504,
}


def create_app(services: Optional[Services] = None) -> FastAPI:
    services = services or default_services()
    app = FastAPI(title="CryptoAudit", version=__version__, docs_url="/api/docs", openapi_url="/api/openapi.json")
    app.state.services = services

    if services.settings.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=services.settings.cors_origins,
            allow_credentials=True,
            allow_methods=["GET", "POST"],
            allow_headers=["Content-Type"],
        )

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault("Cache-Control", "no-store")
        return response

    @app.exception_handler(CryptoAuditError)
    async def handle_error(request: Request, exc: CryptoAuditError) -> JSONResponse:
        status = STATUS_BY_CODE.get(exc.code, 500)
        if status >= 500:
            logger.warning("%s %s -> %s: %s", request.method, request.url.path, exc.code.value, exc.message)
        return JSONResponse(status_code=status, content={"error": {"code": exc.code.value, "message": exc.message}})

    @app.exception_handler(RequestValidationError)
    async def handle_validation(request: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(status_code=422, content={"error": {"code": ErrorCode.INVALID_INPUT.value, "message": "Invalid request"}})

    @app.get("/api/health", response_model=HealthOut, tags=["system"])
    def health() -> HealthOut:
        settings = services.settings
        return HealthOut(
            status="ok",
            version=__version__,
            github_configured=services.auth is not None,
            manage_access_url=services.auth.manage_access_url if services.auth else None,
            repo_access=settings.github_repo_access,
            llm_model=settings.llm_model,
            llm_available=bool(services.llm is not None and services.llm_available()),
        )

    for router in (auth.router, repos.router, scan.router, findings.router, reports.router):
        app.include_router(router, prefix="/api")

    interrupted = services.store.fail_interrupted_scans()
    if interrupted:
        logger.warning("Marked %d interrupted scan(s) as failed", interrupted)
    return app
