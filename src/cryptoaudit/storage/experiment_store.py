"""Append-only SQLite experiment database."""

import json
import sqlite3
import uuid
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel

from cryptoaudit import __version__
from cryptoaudit.aggregation.models import CaseOutcome
from cryptoaudit.candidate.models import Candidate
from cryptoaudit.core.errors import CryptoAuditError, ErrorCode
from cryptoaudit.core.identity import stable_hash
from cryptoaudit.validation.models import ValidationReport

SCHEMA_VERSION = 1
TABLES = ("runs", "baselines", "records")

SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS runs (
    run_id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    cryptoaudit_version TEXT NOT NULL,
    git_commit TEXT,
    config_hash TEXT NOT NULL,
    config_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS baselines (
    baseline_id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL REFERENCES runs(run_id),
    case_id TEXT,
    module_name TEXT NOT NULL,
    rule_ids TEXT NOT NULL,
    created_at TEXT NOT NULL,
    evidence_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS records (
    record_id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL REFERENCES runs(run_id),
    case_id TEXT,
    module_name TEXT NOT NULL,
    strategy_id TEXT NOT NULL,
    candidate_id TEXT NOT NULL,
    repair_status TEXT NOT NULL,
    verdict TEXT NOT NULL,
    created_at TEXT NOT NULL,
    outcome_json TEXT NOT NULL,
    repair_json TEXT NOT NULL,
    integrity_json TEXT,
    validation_json TEXT NOT NULL,
    candidate_code TEXT,
    diff TEXT
);
CREATE INDEX IF NOT EXISTS idx_records_run ON records(run_id);
"""


class RunInfo(BaseModel):
    run_id: str
    created_at: str
    cryptoaudit_version: str
    git_commit: Optional[str]
    config_hash: str
    config: Dict[str, Any]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class ExperimentStore:
    """
    Every write is an INSERT; triggers reject UPDATE and DELETE so results cannot be
    silently overwritten. A new run gets a new run_id.
    """

    def __init__(self, path: Union[str, Path]) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as conn, conn:
            conn.executescript(SCHEMA)
            for table in TABLES:
                for action in ("UPDATE", "DELETE"):
                    conn.execute(
                        f"CREATE TRIGGER IF NOT EXISTS {table}_no_{action.lower()} BEFORE {action} ON {table} "
                        "BEGIN SELECT RAISE(ABORT, 'experiment store is append-only'); END"
                    )
            conn.execute("INSERT OR IGNORE INTO meta(key, value) VALUES ('schema_version', ?)", (str(SCHEMA_VERSION),))

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _write(self, sql: str, params: tuple) -> None:
        try:
            with closing(self._connect()) as conn, conn:
                conn.execute(sql, params)
        except sqlite3.Error as exc:
            raise CryptoAuditError(ErrorCode.STORAGE_ERROR, f"Experiment store write failed: {exc}") from exc

    def start_run(self, config: Dict[str, Any], git_commit: Optional[str] = None) -> RunInfo:
        info = RunInfo(
            run_id=f"R-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{uuid.uuid4().hex[:8]}",
            created_at=_now(),
            cryptoaudit_version=__version__,
            git_commit=git_commit,
            config_hash=stable_hash(config),
            config=config,
        )
        self._write(
            "INSERT INTO runs(run_id, created_at, cryptoaudit_version, git_commit, config_hash, config_json) VALUES (?,?,?,?,?,?)",
            (info.run_id, info.created_at, info.cryptoaudit_version, git_commit, info.config_hash, json.dumps(config, sort_keys=True, default=str)),
        )
        return info

    def record_baseline(self, run_id: str, case_id: Optional[str], module_name: str, rule_ids: List[str], evidence: Dict[str, Any]) -> None:
        self._write(
            "INSERT INTO baselines(run_id, case_id, module_name, rule_ids, created_at, evidence_json) VALUES (?,?,?,?,?,?)",
            (run_id, case_id, module_name, json.dumps(sorted(rule_ids)), _now(), json.dumps(evidence, sort_keys=True, default=str)),
        )

    def record(self, run_id: str, outcome: CaseOutcome, candidate: Candidate, report: ValidationReport) -> None:
        self._write(
            "INSERT INTO records(run_id, case_id, module_name, strategy_id, candidate_id, repair_status, verdict, created_at,"
            " outcome_json, repair_json, integrity_json, validation_json, candidate_code, diff) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                run_id,
                outcome.case_id,
                outcome.module_name,
                outcome.strategy_id.value,
                outcome.candidate_id,
                outcome.repair_status.value,
                outcome.verdict.value,
                _now(),
                outcome.model_dump_json(),
                candidate.repair.model_dump_json(),
                candidate.integrity.model_dump_json() if candidate.integrity else None,
                report.model_dump_json(),
                candidate.code,
                candidate.diff,
            ),
        )

    def runs(self) -> List[RunInfo]:
        with closing(self._connect()) as conn:
            rows = conn.execute("SELECT * FROM runs ORDER BY created_at, run_id").fetchall()
        return [
            RunInfo(
                run_id=r["run_id"], created_at=r["created_at"], cryptoaudit_version=r["cryptoaudit_version"],
                git_commit=r["git_commit"], config_hash=r["config_hash"], config=json.loads(r["config_json"]),
            )
            for r in rows
        ]

    def latest_run_id(self) -> Optional[str]:
        runs = self.runs()
        return runs[-1].run_id if runs else None

    def outcomes(self, run_id: Optional[str] = None) -> List[CaseOutcome]:
        return [CaseOutcome.model_validate_json(r["outcome_json"]) for r in self._rows("records", run_id)]

    def records(self, run_id: Optional[str] = None) -> List[Dict[str, Any]]:
        return [dict(r) for r in self._rows("records", run_id)]

    def baselines(self, run_id: Optional[str] = None) -> List[Dict[str, Any]]:
        rows = self._rows("baselines", run_id)
        return [
            {"case_id": r["case_id"], "module_name": r["module_name"], "rule_ids": json.loads(r["rule_ids"]),
             "evidence": json.loads(r["evidence_json"])}
            for r in rows
        ]

    def _rows(self, table: str, run_id: Optional[str]) -> List[sqlite3.Row]:
        order = "baseline_id" if table == "baselines" else "record_id"
        with closing(self._connect()) as conn:
            if run_id is None:
                return conn.execute(f"SELECT * FROM {table} ORDER BY {order}").fetchall()
            return conn.execute(f"SELECT * FROM {table} WHERE run_id = ? ORDER BY {order}", (run_id,)).fetchall()

    def export_jsonl(self, destination: Union[str, Path], run_id: Optional[str] = None) -> int:
        rows = self.records(run_id)
        with open(destination, "w", encoding="utf-8") as handle:
            for row in rows:
                handle.write(json.dumps(row, sort_keys=True, default=str) + "\n")
        return len(rows)
