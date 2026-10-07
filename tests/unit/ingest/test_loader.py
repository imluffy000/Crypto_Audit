"""Input ingestion tests."""

import pytest

from cryptoaudit.core.errors import CryptoAuditError, ErrorCode
from cryptoaudit.ingest import iter_python_files, load_module


def test_load_module(tmp_path):
    path = tmp_path / "m.py"
    path.write_text("x = 1\n", encoding="utf-8")
    module = load_module(path, ["hashlib"], "3.12")
    assert (module.module_name, module.source, module.allowed_libraries, module.target_python) == ("m.py", "x = 1\n", ("hashlib",), "3.12")


@pytest.mark.parametrize("name, content", [("m.txt", b"x"), ("big.py", b"x" * 20), ("bad.py", b"\xff\xfe\x00")])
def test_load_module_rejects_invalid_input(tmp_path, name, content):
    path = tmp_path / name
    path.write_bytes(content)
    with pytest.raises(CryptoAuditError) as excinfo:
        load_module(path, max_bytes=10)
    assert excinfo.value.code is ErrorCode.INVALID_INPUT


def test_iter_python_files_skips_excluded_dirs(tmp_path):
    for rel in ("a.py", "pkg/b.py", ".venv/lib/c.py", "node_modules/d.py", "pkg/__pycache__/e.py"):
        path = tmp_path / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("", encoding="utf-8")
    assert [p.relative_to(tmp_path).as_posix() for p in iter_python_files(tmp_path)] == ["a.py", "pkg/b.py"]
