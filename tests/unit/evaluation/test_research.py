"""Research analysis tests on synthetic outcomes."""

import pytest

from cryptoaudit.aggregation import CaseOutcome, Verdict
from cryptoaudit.evaluation import analyze, to_markdown, wilson_interval
from cryptoaudit.repair import RepairStatus, StrategyId
from cryptoaudit.validation import GateStatus

P, F, NA = GateStatus.PASS, GateStatus.FAIL, GateStatus.NOT_APPLICABLE


def _outcome(strategy, rule, verdict, v0, v1, v2, v3, bandit_clean):
    return CaseOutcome(
        case_id=f"{rule}-case",
        module_name="m.py",
        rule_ids=[rule],
        strategy_id=strategy,
        candidate_id="c",
        repair_status=RepairStatus.PRODUCED,
        gates={"V0": v0, "V1": v1, "V2": v2, "V3": v3},
        v3_gating=v3 is not NA,
        scanner_results={"cryptoaudit": v0 is P, "bandit": bandit_clean},
        verdict=verdict,
    )


OUTCOMES = [
    _outcome(StrategyId.S1, "CR1", Verdict.FAILED, F, P, F, P, True),  # bandit silenced, insecure
    _outcome(StrategyId.S2, "CR1", Verdict.FAILED, P, F, P, F, True),
    _outcome(StrategyId.S2, "CR5", Verdict.VERIFIED, P, P, P, NA, True),
    _outcome(StrategyId.S4, "CR1", Verdict.VERIFIED, F, P, P, P, False),  # legacy md5 read still flagged
    _outcome(StrategyId.S3, "CR3", Verdict.FAILED, P, P, P, F, True),  # secure but breaks legacy
]
BASELINES = [
    {"case_id": "a", "module_name": "m.py", "rule_ids": ["CR1"], "evidence": {"cryptoaudit": {"available": True, "relevant_issues": 1}, "bandit": {"available": True, "relevant_issues": 1}}},
    {"case_id": "b", "module_name": "m.py", "rule_ids": ["CR3"], "evidence": {"cryptoaudit": {"available": True, "relevant_issues": 1}, "bandit": {"available": True, "relevant_issues": 0}}},
]


def test_wilson_interval():
    assert wilson_interval(0, 0) is None
    low, high = wilson_interval(5, 10)
    assert low < 0.5 < high
    assert wilson_interval(10, 10)[1] == 1.0


def test_scanner_overestimation_and_underestimation():
    findings = analyze(OUTCOMES, BASELINES, run_id="R1")
    bandit = findings.scanners["bandit"]
    assert bandit.candidates_judged_clean == 4
    assert (bandit.clean_but_not_verified.successes, bandit.clean_but_not_verified.total) == (3, 4)
    assert (bandit.verified_but_still_flagged.successes, bandit.verified_but_still_flagged.total) == (1, 2)
    assert (bandit.original_detection.successes, bandit.original_detection.total) == (1, 2)
    assert findings.scanners["cryptoaudit"].original_detection.rate == 1.0


def test_hardest_category_and_compatibility_breaks():
    findings = analyze(OUTCOMES, BASELINES)
    assert findings.hardest_rules[0] == "CR3"
    assert findings.verified_by_rule["CR1"].successes == 1
    assert (findings.compatibility_breaks.successes, findings.compatibility_breaks.total) == (1, 2)


def test_insights_and_markdown():
    findings = analyze(OUTCOMES, BASELINES, run_id="R1")
    assert any("overestimation" in i for i in findings.insights)
    markdown = to_markdown(findings)
    assert "run R1" in markdown and "| bandit |" in markdown and "Hardest category" in markdown


def test_empty_input():
    findings = analyze([], [])
    assert findings.total_outcomes == 0 and findings.hardest_rules == []
    assert "not enough data" in to_markdown(findings)


def test_tied_hardest_categories_are_all_reported():
    tied = [
        _outcome(StrategyId.S2, "CR1", Verdict.FAILED, P, F, P, P, True),
        _outcome(StrategyId.S2, "CR2", Verdict.FAILED, P, F, P, P, True),
        _outcome(StrategyId.S2, "CR5", Verdict.VERIFIED, P, P, P, NA, True),
    ]
    insight = next(i for i in analyze(tied, []).insights if i.startswith("Hardest"))
    assert insight.startswith("Hardest categories (tied): CR1, CR2")
