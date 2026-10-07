"""Repair contract tests: status semantics, leakage-proof request, strategy wrapper."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from cryptoaudit.analysis.analyzer import AnalyzerEngine
from cryptoaudit.repair import (
    RepairRequest,
    RepairResult,
    RepairStatus,
    RepairStrategy,
    StrategyId,
    StrategyRegistry,
    build_repair_request,
)
from cryptoaudit.utils.errors import CryptoAuditError, ErrorCode

FIXTURE = Path("tests/fixtures/cr5/vulnerable.py")


@pytest.fixture(scope="module")
def request_obj() -> RepairRequest:
    source = FIXTURE.read_text(encoding="utf-8")
    findings = AnalyzerEngine().analyze_file(FIXTURE).findings
    return build_repair_request("vulnerable.py", source, findings)


def test_produced_requires_candidate_code():
    with pytest.raises(ValidationError):
        RepairResult(strategy_id=StrategyId.S2, status=RepairStatus.PRODUCED)


@pytest.mark.parametrize("status", [RepairStatus.NO_REPAIR, RepairStatus.NOT_APPLICABLE, RepairStatus.PARSE_ERROR])
def test_failure_statuses_cannot_carry_code(status):
    with pytest.raises(ValidationError):
        RepairResult(strategy_id=StrategyId.S2, status=status, candidate_code="x = 1", failure_reason="r")


@pytest.mark.parametrize("status", [RepairStatus.NO_REPAIR, RepairStatus.NOT_APPLICABLE, RepairStatus.PARSE_ERROR])
def test_failure_statuses_require_reason(status):
    with pytest.raises(ValidationError):
        RepairResult(strategy_id=StrategyId.S2, status=status)


def test_request_rejects_extra_fields(request_obj):
    data = request_obj.model_dump()
    data["oracle_tests"] = "def check(): ..."
    with pytest.raises(ValidationError):
        RepairRequest(**data)


def test_request_is_immutable(request_obj):
    with pytest.raises(ValidationError):
        request_obj.source = "changed"


def test_request_requires_findings(request_obj):
    with pytest.raises(CryptoAuditError) as excinfo:
        build_repair_request("m.py", request_obj.source, [])
    assert excinfo.value.code is ErrorCode.INVALID_INPUT


class _Exploding(RepairStrategy):
    strategy_id = StrategyId.S2

    def _repair(self, request):
        raise RuntimeError("boom")


class _Echo(RepairStrategy):
    strategy_id = StrategyId.S1

    def _repair(self, request):
        return RepairResult(strategy_id=self.strategy_id, status=RepairStatus.PRODUCED, candidate_code=request.source)


def test_strategy_exceptions_become_explicit_no_repair(request_obj):
    result = _Exploding().repair(request_obj)
    assert result.status is RepairStatus.NO_REPAIR
    assert result.error_code is ErrorCode.REPAIR_ERROR
    assert "boom" in result.failure_reason
    assert result.candidate_code is None


def test_strategy_records_duration(request_obj):
    assert _Echo().repair(request_obj).duration_seconds >= 0


def test_registry_rejects_duplicates_and_unknown():
    registry = StrategyRegistry([_Echo()])
    with pytest.raises(CryptoAuditError):
        registry.register(_Echo())
    with pytest.raises(CryptoAuditError):
        registry.get(StrategyId.S3)
    assert registry.ids() == [StrategyId.S1]
