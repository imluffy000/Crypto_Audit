"""Web store tests: OAuth state, sessions (hashed IDs, encrypted tokens), scan jobs and isolation between users."""


import pytest

from cryptoaudit.ingest.github_client import GitHubUser
from cryptoaudit.models.scan import (
    STAGE_LABELS,
    RepositoryScanResult,
    ScanStage,
    ScanStatus,
    StageProgress,
    StageStatus,
)
from cryptoaudit.storage.web_store import WebStore
from cryptoaudit.utils.errors import CryptoAuditError

SECRET = "s" * 40
ALICE = GitHubUser(id=1, login="alice", name="Alice")
BOB = GitHubUser(id=2, login="bob")


@pytest.fixture()
def store(tmp_path):
    return WebStore(tmp_path / "web.sqlite", SECRET)


def stages():
    return [StageProgress(stage=s, label=STAGE_LABELS[s]) for s in ScanStage]


def test_secret_must_be_strong(tmp_path):
    with pytest.raises(CryptoAuditError):
        WebStore(tmp_path / "w.sqlite", "short")


def test_oauth_state_is_single_use(store):
    state = store.create_oauth_state()
    assert store.consume_oauth_state(state) is True
    assert store.consume_oauth_state(state) is False
    assert store.consume_oauth_state("forged") is False
    assert store.consume_oauth_state("") is False


def test_expired_oauth_state_is_rejected(store):
    state = store.create_oauth_state(ttl_minutes=-1)
    assert store.consume_oauth_state(state) is False


def test_session_round_trip_and_logout(store):
    session_id = store.create_session(ALICE, "ghu_secret")
    info = store.get_session(session_id)
    assert info.user.login == "alice" and info.access_token == "ghu_secret"
    store.delete_session(session_id)
    assert store.get_session(session_id) is None
    assert store.get_session(None) is None


def test_session_ids_hashed_and_tokens_encrypted_at_rest(store):
    session_id = store.create_session(ALICE, "ghu_secret_token")
    raw = store.path.read_bytes() + (store.path.with_name(store.path.name + "-wal").read_bytes() if store.path.with_name(store.path.name + "-wal").exists() else b"")
    assert b"ghu_secret_token" not in raw
    assert session_id.encode() not in raw


def test_expired_session_is_rejected(store):
    session_id = store.create_session(ALICE, "t", ttl_hours=-1)
    assert store.get_session(session_id) is None


def test_rotated_secret_invalidates_tokens(tmp_path):
    path = tmp_path / "web.sqlite"
    session_id = WebStore(path, SECRET).create_session(ALICE, "t")
    assert WebStore(path, "x" * 40).get_session(session_id) is None


def test_scan_lifecycle(store):
    store.upsert_user(ALICE)
    scan_id = store.create_scan(ALICE.id, "alice/app", "main", stages())
    assert store.get_scan(scan_id, ALICE.id).status is ScanStatus.QUEUED
    assert store.active_scan_count(ALICE.id) == 1

    progress = stages()
    progress[0] = progress[0].model_copy(update={"status": StageStatus.RUNNING})
    store.update_progress(scan_id, progress)
    record = store.get_scan(scan_id, ALICE.id)
    assert record.status is ScanStatus.RUNNING and record.stages[0].status is StageStatus.RUNNING

    store.complete_scan(scan_id, RepositoryScanResult(repository="alice/app", ref="main"))
    record = store.get_scan(scan_id, ALICE.id)
    assert record.status is ScanStatus.COMPLETED and record.result.repository == "alice/app"
    assert store.active_scan_count(ALICE.id) == 0
    assert store.list_scans(ALICE.id)[0].result is None  # list view omits large results


def test_progress_cannot_resurrect_finished_scan(store):
    store.upsert_user(ALICE)
    scan_id = store.create_scan(ALICE.id, "alice/app", "main", stages())
    store.fail_scan(scan_id, {"code": "NOT_FOUND", "message": "gone"})
    store.update_progress(scan_id, stages())
    assert store.get_scan(scan_id, ALICE.id).status is ScanStatus.FAILED


def test_scans_are_private_to_their_owner(store):
    store.upsert_user(ALICE)
    store.upsert_user(BOB)
    scan_id = store.create_scan(ALICE.id, "alice/app", "main", stages())
    assert store.get_scan(scan_id, BOB.id) is None
    assert store.list_scans(BOB.id) == []


def test_interrupted_scans_fail_on_restart(store):
    store.upsert_user(ALICE)
    scan_id = store.create_scan(ALICE.id, "alice/app", "main", stages())
    assert store.fail_interrupted_scans() == 1
    record = store.get_scan(scan_id, ALICE.id)
    assert record.status is ScanStatus.FAILED and record.error["code"] == "INTERRUPTED"


def test_ai_explanation_cache(store):
    store.upsert_user(ALICE)
    scan_id = store.create_scan(ALICE.id, "alice/app", "main", stages())
    assert store.get_ai_explanation(scan_id, "C-1") is None
    store.save_ai_explanation(scan_id, "C-1", '{"text": "x"}')
    assert store.get_ai_explanation(scan_id, "C-1") == '{"text": "x"}'


def test_foreign_keys_enforced(store):
    with pytest.raises(CryptoAuditError):
        store.create_scan(999, "x/y", "main", stages())
