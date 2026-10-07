"""Experiment store tests: append-only guarantees, round-trips and reproducibility metadata."""

import json
import sqlite3

import pytest

from cryptoaudit.aggregation import build_outcome
from cryptoaudit.candidate import IntegrityChecker, make_candidate
from cryptoaudit.repair import RepairResult, RepairStatus, StrategyId
from cryptoaudit.storage import ExperimentStore
from cryptoaudit.validation import GateId, GateResult, GateStatus, ValidationReport


def _sample():
    repair = RepairResult(strategy_id=StrategyId.S2, status=RepairStatus.PRODUCED, candidate_code="x = 2\n")
    candidate = make_candidate("m.py", "x = 1\n", repair, IntegrityChecker().check("x = 2\n"))
    report = ValidationReport(
        candidate_id=candidate.candidate_id,
        gates=[GateResult(gate=g, status=GateStatus.PASS, gating=g is not GateId.V0) for g in GateId],
    )
    return candidate, report, build_outcome(candidate, report, ["CR5"], "case1")


def test_round_trip(tmp_path):
    store = ExperimentStore(tmp_path / "exp.sqlite")
    run = store.start_run({"strategies": ["S2"], "seed": 0}, git_commit="abc123")
    candidate, report, outcome = _sample()
    store.record(run.run_id, outcome, candidate, report)
    store.record_baseline(run.run_id, "case1", "m.py", ["CR5"], {"bandit": {"available": True}})

    assert store.outcomes(run.run_id) == [outcome]
    row = store.records(run.run_id)[0]
    assert row["candidate_code"] == "x = 2\n" and "+x = 2" in row["diff"]
    assert json.loads(row["validation_json"])["candidate_id"] == candidate.candidate_id
    assert store.baselines(run.run_id)[0]["evidence"]["bandit"]["available"] is True
    info = store.runs()[0]
    assert info.git_commit == "abc123" and info.config == {"strategies": ["S2"], "seed": 0}
    assert len(info.config_hash) == 64


@pytest.mark.parametrize("sql", ["UPDATE records SET verdict = 'VERIFIED'", "DELETE FROM records", "DELETE FROM runs", "UPDATE runs SET git_commit = 'x'"])
def test_store_is_append_only(tmp_path, sql):
    path = tmp_path / "exp.sqlite"
    store = ExperimentStore(path)
    run = store.start_run({})
    candidate, report, outcome = _sample()
    store.record(run.run_id, outcome, candidate, report)
    with sqlite3.connect(path) as conn, pytest.raises(sqlite3.IntegrityError, match="append-only"):
        conn.execute(sql)


def test_runs_are_never_overwritten(tmp_path):
    store = ExperimentStore(tmp_path / "exp.sqlite")
    first = store.start_run({"a": 1})
    second = store.start_run({"a": 1})
    assert first.run_id != second.run_id
    assert first.config_hash == second.config_hash
    assert len(store.runs()) == 2


def test_records_require_existing_run(tmp_path):
    store = ExperimentStore(tmp_path / "exp.sqlite")
    candidate, report, outcome = _sample()
    from cryptoaudit.core.errors import CryptoAuditError

    with pytest.raises(CryptoAuditError):
        store.record("R-missing", outcome, candidate, report)


def test_reopening_existing_database(tmp_path):
    path = tmp_path / "exp.sqlite"
    ExperimentStore(path).start_run({})
    assert len(ExperimentStore(path).runs()) == 1


def test_export_jsonl(tmp_path):
    store = ExperimentStore(tmp_path / "exp.sqlite")
    run = store.start_run({})
    candidate, report, outcome = _sample()
    store.record(run.run_id, outcome, candidate, report)
    out = tmp_path / "records.jsonl"
    assert store.export_jsonl(out, run.run_id) == 1
    assert json.loads(out.read_text(encoding="utf-8").splitlines()[0])["strategy_id"] == "S2"
