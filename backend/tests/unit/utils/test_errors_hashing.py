"""Unit tests for structured errors and deterministic hashing."""

from cryptoaudit.utils.errors import CryptoAuditError, ErrorCode
from cryptoaudit.utils.hashing import stable_hash


def test_error_carries_code_and_details():
    err = CryptoAuditError(ErrorCode.PARSE_ERROR, "bad syntax", {"line": 3})
    assert err.code is ErrorCode.PARSE_ERROR
    assert "PARSE_ERROR" in str(err)
    assert err.to_dict() == {"code": "PARSE_ERROR", "message": "bad syntax", "details": {"line": 3}}


def test_stable_hash_is_order_independent_for_dicts():
    assert stable_hash({"a": 1, "b": 2}) == stable_hash({"b": 2, "a": 1})
