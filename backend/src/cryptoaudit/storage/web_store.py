"""
Operational store for the website: users, sessions, OAuth state, scan jobs and AI explanations.

Separate from the append-only research experiment database. Session IDs are stored only as
SHA-256 hashes and GitHub access tokens are encrypted at rest (Fernet, key derived from the
configured session secret), so a copied database file does not grant access.
"""

import base64
import hashlib
import json
import secrets
import sqlite3
from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from cryptography.fernet import Fernet, InvalidToken
from pydantic import BaseModel

from cryptoaudit.ingest.github_client import GitHubUser
from cryptoaudit.models.scan import RepositoryScanResult, ScanRecord, ScanStatus, StageProgress
from cryptoaudit.utils.errors import CryptoAuditError, ErrorCode

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    github_id INTEGER PRIMARY KEY,
    login TEXT NOT NULL,
    profile_json TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS sessions (
    session_hash TEXT PRIMARY KEY,
    github_id INTEGER NOT NULL REFERENCES users(github_id),
    token_encrypted TEXT NOT NULL,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS oauth_states (
    state_hash TEXT PRIMARY KEY,
    expires_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS scans (
    scan_id TEXT PRIMARY KEY,
    github_id INTEGER NOT NULL REFERENCES users(github_id),
    repository TEXT NOT NULL,
    ref TEXT NOT NULL,
    status TEXT NOT NULL,
    stages_json TEXT NOT NULL,
    error_json TEXT,
    result_json TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_scans_user ON scans(github_id, created_at);
CREATE TABLE IF NOT EXISTS ai_explanations (
    scan_id TEXT NOT NULL REFERENCES scans(scan_id),
    candidate_id TEXT NOT NULL,
    explanation_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (scan_id, candidate_id)
);
"""


class SessionInfo(BaseModel):
    user: GitHubUser
    access_token: str
    expires_at: str


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(moment: datetime) -> str:
    return moment.isoformat(timespec="seconds")


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


class WebStore:
    def __init__(self, path: Union[str, Path], secret: str) -> None:
        if not secret or len(secret) < 32:
            raise CryptoAuditError(ErrorCode.INVALID_INPUT, "Session secret must be at least 32 characters")
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._fernet = Fernet(base64.urlsafe_b64encode(hashlib.sha256(secret.encode("utf-8")).digest()))
        with closing(self._connect()) as conn, conn:
            conn.executescript(SCHEMA)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        return conn

    def _exec(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        try:
            with closing(self._connect()) as conn, conn:
                return conn.execute(sql, params)
        except sqlite3.Error as exc:
            raise CryptoAuditError(ErrorCode.STORAGE_ERROR, f"Web store write failed: {exc}") from exc

    def _one(self, sql: str, params: tuple = ()) -> Optional[sqlite3.Row]:
        with closing(self._connect()) as conn:
            return conn.execute(sql, params).fetchone()

    def _all(self, sql: str, params: tuple = ()) -> List[sqlite3.Row]:
        with closing(self._connect()) as conn:
            return conn.execute(sql, params).fetchall()

    # -- OAuth state (CSRF protection for the sign-in redirect) -------------------------------

    def create_oauth_state(self, ttl_minutes: int = 10) -> str:
        state = secrets.token_urlsafe(32)
        self._exec("DELETE FROM oauth_states WHERE expires_at < ?", (_iso(_now()),))
        self._exec("INSERT INTO oauth_states(state_hash, expires_at) VALUES (?, ?)", (_hash(state), _iso(_now() + timedelta(minutes=ttl_minutes))))
        return state

    def consume_oauth_state(self, state: str) -> bool:
        """Single use: a state is valid once, and only before it expires."""
        if not state:
            return False
        cursor = self._exec("DELETE FROM oauth_states WHERE state_hash = ? AND expires_at >= ?", (_hash(state), _iso(_now())))
        return cursor.rowcount == 1

    # -- users and sessions ---------------------------------------------------------------------

    def upsert_user(self, user: GitHubUser) -> None:
        self._exec(
            "INSERT INTO users(github_id, login, profile_json, updated_at) VALUES (?, ?, ?, ?) "
            "ON CONFLICT(github_id) DO UPDATE SET login=excluded.login, profile_json=excluded.profile_json, updated_at=excluded.updated_at",
            (user.id, user.login, user.model_dump_json(), _iso(_now())),
        )

    def create_session(self, user: GitHubUser, access_token: str, ttl_hours: float = 8.0) -> str:
        self.upsert_user(user)
        session_id = secrets.token_urlsafe(32)
        encrypted = self._fernet.encrypt(access_token.encode("utf-8")).decode("ascii")
        self._exec(
            "INSERT INTO sessions(session_hash, github_id, token_encrypted, created_at, expires_at) VALUES (?, ?, ?, ?, ?)",
            (_hash(session_id), user.id, encrypted, _iso(_now()), _iso(_now() + timedelta(hours=ttl_hours))),
        )
        return session_id

    def get_session(self, session_id: Optional[str]) -> Optional[SessionInfo]:
        if not session_id:
            return None
        row = self._one(
            "SELECT s.token_encrypted, s.expires_at, u.profile_json FROM sessions s JOIN users u USING (github_id) "
            "WHERE s.session_hash = ?",
            (_hash(session_id),),
        )
        if row is None:
            return None
        if row["expires_at"] < _iso(_now()):
            self.delete_session(session_id)
            return None
        try:
            token = self._fernet.decrypt(row["token_encrypted"].encode("ascii")).decode("utf-8")
        except InvalidToken:
            return None  # secret rotated: force a new sign-in
        return SessionInfo(user=GitHubUser.model_validate_json(row["profile_json"]), access_token=token, expires_at=row["expires_at"])

    def delete_session(self, session_id: str) -> None:
        self._exec("DELETE FROM sessions WHERE session_hash = ?", (_hash(session_id),))

    # -- scans ------------------------------------------------------------------------------------

    def create_scan(self, github_id: int, repository: str, ref: str, stages: List[StageProgress]) -> str:
        scan_id = "S-" + secrets.token_hex(8)
        now = _iso(_now())
        self._exec(
            "INSERT INTO scans(scan_id, github_id, repository, ref, status, stages_json, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?)",
            (scan_id, github_id, repository, ref, ScanStatus.QUEUED.value, _dump_stages(stages), now, now),
        )
        return scan_id

    def update_progress(self, scan_id: str, stages: List[StageProgress]) -> None:
        self._exec(
            "UPDATE scans SET status = ?, stages_json = ?, updated_at = ? WHERE scan_id = ? AND status IN (?, ?)",
            (ScanStatus.RUNNING.value, _dump_stages(stages), _iso(_now()), scan_id, ScanStatus.QUEUED.value, ScanStatus.RUNNING.value),
        )

    def complete_scan(self, scan_id: str, result: RepositoryScanResult) -> None:
        self._exec(
            "UPDATE scans SET status = ?, result_json = ?, updated_at = ? WHERE scan_id = ?",
            (ScanStatus.COMPLETED.value, result.model_dump_json(), _iso(_now()), scan_id),
        )

    def fail_scan(self, scan_id: str, error: Dict[str, Any], stages: Optional[List[StageProgress]] = None) -> None:
        if stages is None:
            self._exec(
                "UPDATE scans SET status = ?, error_json = ?, updated_at = ? WHERE scan_id = ?",
                (ScanStatus.FAILED.value, json.dumps(error), _iso(_now()), scan_id),
            )
        else:
            self._exec(
                "UPDATE scans SET status = ?, error_json = ?, stages_json = ?, updated_at = ? WHERE scan_id = ?",
                (ScanStatus.FAILED.value, json.dumps(error), _dump_stages(stages), _iso(_now()), scan_id),
            )

    def get_scan(self, scan_id: str, github_id: int, include_result: bool = True) -> Optional[ScanRecord]:
        """Scans are only visible to the user who started them."""
        row = self._one("SELECT * FROM scans WHERE scan_id = ? AND github_id = ?", (scan_id, github_id))
        return _record(row, include_result) if row is not None else None

    def list_scans(self, github_id: int, limit: int = 50) -> List[ScanRecord]:
        rows = self._all("SELECT * FROM scans WHERE github_id = ? ORDER BY created_at DESC, scan_id LIMIT ?", (github_id, limit))
        return [_record(row, include_result=False) for row in rows]

    def active_scan_count(self, github_id: int) -> int:
        row = self._one(
            "SELECT COUNT(*) AS n FROM scans WHERE github_id = ? AND status IN (?, ?)",
            (github_id, ScanStatus.QUEUED.value, ScanStatus.RUNNING.value),
        )
        return int(row["n"]) if row else 0

    def fail_interrupted_scans(self) -> int:
        """At startup, scans left QUEUED/RUNNING by a previous process can never finish: mark them FAILED."""
        cursor = self._exec(
            "UPDATE scans SET status = ?, error_json = ?, updated_at = ? WHERE status IN (?, ?)",
            (
                ScanStatus.FAILED.value,
                json.dumps({"code": "INTERRUPTED", "message": "The server restarted before this scan finished"}),
                _iso(_now()),
                ScanStatus.QUEUED.value,
                ScanStatus.RUNNING.value,
            ),
        )
        return cursor.rowcount

    # -- AI explanations --------------------------------------------------------------------------

    def save_ai_explanation(self, scan_id: str, candidate_id: str, explanation_json: str) -> None:
        self._exec(
            "INSERT OR REPLACE INTO ai_explanations(scan_id, candidate_id, explanation_json, created_at) VALUES (?,?,?,?)",
            (scan_id, candidate_id, explanation_json, _iso(_now())),
        )

    def get_ai_explanation(self, scan_id: str, candidate_id: str) -> Optional[str]:
        row = self._one("SELECT explanation_json FROM ai_explanations WHERE scan_id = ? AND candidate_id = ?", (scan_id, candidate_id))
        return row["explanation_json"] if row else None


def _dump_stages(stages: List[StageProgress]) -> str:
    return json.dumps([s.model_dump(mode="json") for s in stages])


def _record(row: sqlite3.Row, include_result: bool) -> ScanRecord:
    return ScanRecord(
        scan_id=row["scan_id"],
        repository=row["repository"],
        ref=row["ref"],
        status=ScanStatus(row["status"]),
        stages=[StageProgress(**s) for s in json.loads(row["stages_json"])],
        error=json.loads(row["error_json"]) if row["error_json"] else None,
        result=RepositoryScanResult.model_validate_json(row["result_json"]) if include_result and row["result_json"] else None,
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )
