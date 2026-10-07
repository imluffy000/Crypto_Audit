"""Python files inside .zip archives committed to a repository are read in memory, safely and bounded."""

import io
import zipfile

import pytest

from cryptoaudit.analysis.analyzer import AnalyzerEngine
from cryptoaudit.ingest.filters import SnapshotLimits
from cryptoaudit.ingest.git_loader import read_python_modules
from cryptoaudit.pipeline.stages import analysis_stage
from cryptoaudit.utils.errors import CryptoAuditError, ErrorCode
from tests.unit.ingest.test_github_and_git_loader import make_tarball

MISUSE = 'import hashlib\n\n\ndef store_password(password):\n    return hashlib.md5(password.encode()).hexdigest()\n'


def make_zip(files, compression=zipfile.ZIP_DEFLATED) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=compression) as zf:
        for name, content in files.items():
            zf.writestr(name, content)
    return buffer.getvalue()


def test_python_files_inside_a_zip_are_scanned():
    archive = make_tarball(
        {
            "demo/CryptoAudit_DemoRepo (1).zip": make_zip(
                {"DemoRepo/auth.py": MISUSE, "DemoRepo/README.md": "# demo", "DemoRepo/": ""}
            ),
            "app.py": "x = 1\n",
        }
    )
    snapshot = read_python_modules(archive, SnapshotLimits())
    names = [m.module_name for m in snapshot.modules]
    assert names == ["app.py", "demo/CryptoAudit_DemoRepo (1).zip/DemoRepo/auth.py"]


def test_findings_in_zipped_files_carry_the_archive_path():
    archive = make_tarball({"code.zip": make_zip({"auth.py": MISUSE})})
    module = read_python_modules(archive, SnapshotLimits()).modules[0]
    findings = analysis_stage(AnalyzerEngine(), module)
    assert {f.rule_id for f in findings} == {"CR1"}
    assert all(f.file == "code.zip/auth.py" for f in findings)


def test_unsafe_nested_and_excluded_members_are_skipped():
    inner = make_zip({"evil.py": "x = 1\n"})
    data = make_zip(
        {
            "../escape.py": "x = 1\n",
            "/abs.py": "x = 1\n",
            "inner.zip": inner,
            "__MACOSX/._auth.py": "junk",
            "ok.py": "y = 2\n",
        }
    )
    snapshot = read_python_modules(make_tarball({"a.zip": data}), SnapshotLimits())
    assert [m.module_name for m in snapshot.modules] == ["a.zip/ok.py"]
    reasons = {s.path: s.reason for s in snapshot.skipped}
    assert reasons["a.zip/inner.zip"] == "nested archive not scanned"
    assert sum(r == "unsafe path" for r in reasons.values()) == 2


def test_zip_limits_are_enforced():
    big_member = make_zip({"big.py": "#" * 5000, "small.py": "x = 1\n"})
    snapshot = read_python_modules(make_tarball({"a.zip": big_member}), SnapshotLimits(max_file_bytes=1000))
    assert [m.module_name for m in snapshot.modules] == ["a.zip/small.py"]
    assert {s.path: s.reason for s in snapshot.skipped}["a.zip/big.py"] == "file too large"

    too_big_archive = read_python_modules(make_tarball({"a.zip": big_member}), SnapshotLimits(max_archive_bytes=10))
    assert too_big_archive.modules == [] and too_big_archive.skipped[0].reason == "archive too large"

    two_files = make_tarball({"a.zip": make_zip({"1.py": "a=1", "2.py": "b=2"})})
    limited = read_python_modules(two_files, SnapshotLimits(max_python_files=1))
    assert len(limited.modules) == 1 and limited.skipped[0].reason == "file count limit reached"


def test_zip_bomb_counts_towards_the_unpacked_limit():
    bomb = make_zip({f"f{i}.py": "#" * 50_000 for i in range(10)})  # ~500 KB unpacked, a few KB compressed
    with pytest.raises(CryptoAuditError) as excinfo:
        read_python_modules(make_tarball({"bomb.zip": bomb}), SnapshotLimits(max_unpacked_bytes=200_000))
    assert excinfo.value.code is ErrorCode.LIMIT_EXCEEDED


def test_corrupt_zip_is_skipped_not_fatal():
    archive = make_tarball({"broken.zip": b"PK\x03\x04 not really", "ok.py": "x = 1\n"})
    snapshot = read_python_modules(archive, SnapshotLimits())
    assert [m.module_name for m in snapshot.modules] == ["ok.py"]
    assert snapshot.skipped[0].path == "broken.zip" and snapshot.skipped[0].reason.startswith("unreadable zip archive")


def test_archive_scanning_can_be_turned_off():
    archive = make_tarball({"code.zip": make_zip({"auth.py": MISUSE})})
    assert read_python_modules(archive, SnapshotLimits(scan_archives=False)).modules == []
