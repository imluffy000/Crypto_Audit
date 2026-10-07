"""Acceptance truth-table and comparison tests."""

import itertools

import pytest

from cryptoaudit.aggregation import Verdict, build_outcome, compare_strategies, decide
from cryptoaudit.candidate import IntegrityChecker, make_candidate
from cryptoaudit.repair import RepairResult, RepairStatus, StrategyId
from cryptoaudit.validation import GateId, GateResult, GateStatus, ValidationReport

P, F, E, NR, NA = GateStatus.PASS, GateStatus.FAIL, GateStatus.ERROR, GateStatus.NOT_RUN, GateStatus.NOT_APPLICABLE


def _candidate(code="x = 1\n", status=RepairStatus.PRODUCED, strategy=StrategyId.S2):
    if status is RepairStatus.PRODUCED:
        repair = RepairResult(strategy_id=strategy, status=status, candidate_code=code)
        return make_candidate("m.py", "x = 0\n", repair, IntegrityChecker().check(code))
    repair = RepairResult(strategy_id=strategy, status=status, failure_reason="reason")
    return make_candidate("m.py", "x = 0\n", repair, None)


def _report(v0, v1, v2, v3, v3_gating=True):
    gates = [
        GateResult(gate=GateId.V0, status=v0, gating=False, evidence={"bandit": {"available": True, "relevant_issues": 0 if v0 is P else 1}}),
        GateResult(gate=GateId.V1, status=v1, gating=True),
        GateResult(gate=GateId.V2, status=v2, gating=True),
        GateResult(gate=GateId.V3, status=v3, gating=v3_gating and v3 is not NA),
    ]
    return ValidationReport(candidate_id="c", gates=gates)


def _expected(v1, v2, v3, v3_gating):
    gating = [v1, v2] + ([v3] if v3_gating and v3 is not NA else [])
    if F in gating:
        return Verdict.FAILED
    if any(s in (E, NR) for s in gating):
        return Verdict.UNVERIFIED
    return Verdict.VERIFIED


@pytest.mark.parametrize(
    "v0,v1,v2,v3,v3_gating",
    list(itertools.product([P, F], [P, F, E, NR], [P, F, E, NR], [P, F, E, NR, NA], [True, False])),
)
def test_full_truth_table(v0, v1, v2, v3, v3_gating):
    verdict, _ = decide(_candidate(), _report(v0, v1, v2, v3, v3_gating))
    assert verdict is _expected(v1, v2, v3, v3_gating)


@pytest.mark.parametrize("v1,v2,v3", list(itertools.product([P, F, E, NR], [P, F, E, NR], [P, F, NA])))
def test_v0_never_changes_the_verdict(v1, v2, v3):
    clean, _ = decide(_candidate(), _report(P, v1, v2, v3))
    dirty, _ = decide(_candidate(), _report(F, v1, v2, v3))
    assert clean is dirty


def test_scanner_clean_but_insecure_is_flagged():
    verdict, reasons = decide(_candidate(), _report(P, P, F, P))
    assert verdict is Verdict.FAILED
    assert any("Scanners report the candidate clean" in r for r in reasons)


@pytest.mark.parametrize("status", [RepairStatus.NO_REPAIR, RepairStatus.NOT_APPLICABLE, RepairStatus.PARSE_ERROR])
def test_non_produced_statuses_never_succeed(status):
    verdict, reasons = decide(_candidate(status=status), _report(P, P, P, P))
    assert verdict is Verdict.NO_CANDIDATE
    assert status.value in reasons[0]


def test_integrity_failure_is_failed_even_if_gates_pass():
    verdict, _ = decide(_candidate(code="import subprocess\n"), _report(P, P, P, P))
    assert verdict is Verdict.FAILED


def test_missing_v1_or_v2_cannot_verify():
    report = ValidationReport(candidate_id="c", gates=[GateResult(gate=GateId.V2, status=P, gating=True)])
    assert decide(_candidate(), report)[0] is Verdict.UNVERIFIED


def test_non_gating_v3_failure_is_reported_but_does_not_block():
    verdict, reasons = decide(_candidate(), _report(P, P, P, F, v3_gating=False))
    assert verdict is Verdict.VERIFIED
    assert any("non-gating" in r for r in reasons)


def test_comparison_counts():
    outcomes = [
        build_outcome(_candidate(strategy=StrategyId.S2), _report(P, P, P, P), ["CR1"], "c1"),
        build_outcome(_candidate(strategy=StrategyId.S2), _report(P, P, F, P), ["CR2"], "c2"),
        build_outcome(_candidate(status=RepairStatus.NO_REPAIR, strategy=StrategyId.S1), _report(NR, NR, NR, NR), ["CR1"], "c1"),
    ]
    stats = {(s.strategy_id.value, s.rule_id): s for s in compare_strategies(outcomes)}
    s2 = stats[("S2", "ALL")]
    assert (s2.attempts, s2.verified, s2.failed, s2.v0_clean, s2.scanner_clean_not_verified) == (2, 1, 1, 2, 1)
    assert s2.rate(s2.verified) == 0.5
    s1 = stats[("S1", "ALL")]
    assert (s1.no_candidate, s1.produced) == (1, 0)
    assert list(stats) == sorted(stats)


def test_outcome_records_scanner_results():
    outcome = build_outcome(_candidate(), _report(F, P, P, NA), ["CR5"], "c5")
    assert outcome.scanner_results == {"bandit": False}
    assert outcome.scanner_clean is False
