"""Structured error codes shared by every CryptoAudit pipeline stage."""

from enum import Enum
from typing import Any, Dict, Optional


class ErrorCode(str, Enum):
    """Canonical error codes. Stages must surface failures with one of these codes."""

    INVALID_INPUT = "INVALID_INPUT"
    PARSE_ERROR = "PARSE_ERROR"
    ANALYSIS_ERROR = "ANALYSIS_ERROR"
    CONTEXT_ERROR = "CONTEXT_ERROR"
    REPAIR_ERROR = "REPAIR_ERROR"
    LLM_ERROR = "LLM_ERROR"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    SANDBOX_ERROR = "SANDBOX_ERROR"
    TOOL_UNAVAILABLE = "TOOL_UNAVAILABLE"
    STORAGE_ERROR = "STORAGE_ERROR"
    TIMEOUT = "TIMEOUT"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    NO_REPAIR = "NO_REPAIR"
    AUTHENTICATION_ERROR = "AUTHENTICATION_ERROR"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    NOT_FOUND = "NOT_FOUND"
    RATE_LIMITED = "RATE_LIMITED"
    LIMIT_EXCEEDED = "LIMIT_EXCEEDED"
    EXTERNAL_SERVICE_ERROR = "EXTERNAL_SERVICE_ERROR"


class CryptoAuditError(Exception):
    """Base exception carrying a structured error code and debugging metadata."""

    def __init__(self, code: ErrorCode, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(f"[{code.value}] {message}")
        self.code = code
        self.message = message
        self.details: Dict[str, Any] = dict(details or {})

    def to_dict(self) -> Dict[str, Any]:
        return {"code": self.code.value, "message": self.message, "details": self.details}
