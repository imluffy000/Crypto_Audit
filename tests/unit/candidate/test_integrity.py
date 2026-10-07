"""Candidate integrity check tests."""

import pytest

from cryptoaudit.candidate import IntegrityChecker, make_candidate
from cryptoaudit.repair import RepairResult, RepairStatus, StrategyId

ALLOWED = ("hashlib", "hmac", "secrets", "os")


def check(code, allowed=ALLOWED, original=None):
    return IntegrityChecker().check(code, allowed, original)


def test_clean_candidate_passes():
    report = check("import hashlib\nimport os\n\ndef f(p):\n    return hashlib.pbkdf2_hmac('sha256', p, os.urandom(16), 600000)\n")
    assert report.passed and report.syntax_ok
    assert report.imports == ["hashlib", "os"]


def test_syntax_error_fails():
    report = check("def broken(:\n")
    assert not report.passed and not report.syntax_ok
    assert report.issues_of("syntax")[0].line == 1


def test_disallowed_dependency_fails():
    report = check("import bcrypt\n")
    assert not report.passed
    assert "bcrypt" in report.issues_of("dependency")[0].message


def test_original_imports_are_allowed():
    assert check("import random\n", original="import random\n").passed


def test_helper_stdlib_is_allowed():
    assert check("from typing import Optional\nimport string\n").passed


@pytest.mark.parametrize(
    "code",
    [
        "import subprocess\n",
        "import socket\n",
        "from urllib import request\n",
        "eval('1')\n",
        "exec('x = 1')\n",
        "__import__('os')\n",
        "import os\nos.system('ls')\n",
        "import os\nos.execv('/bin/sh', [])\n",
        "import os\nos.remove('x')\n",
        "open('f', 'w')\n",
        "open('f', mode='ab')\n",
    ],
)
def test_dangerous_constructs_fail(code):
    report = check(code)
    assert not report.passed
    assert report.issues_of("dangerous_call")


def test_denied_module_cannot_be_allowed_by_original():
    assert not check("import subprocess\n", original="import subprocess\n").passed


def test_reading_files_is_allowed():
    assert check("open('f')\nopen('f', 'rb')\n").passed


def test_relative_import_fails():
    assert not check("from . import helper\n").passed


def test_size_limit():
    assert not IntegrityChecker(max_chars=10).check("x = 1\n" * 10).passed


def test_default_crypto_stdlib_when_no_allowed_libraries():
    assert check("import secrets\n", allowed=()).passed
    assert not check("import cryptography\n", allowed=()).passed


def test_candidate_executable_only_when_produced_and_clean():
    produced = RepairResult(strategy_id=StrategyId.S2, status=RepairStatus.PRODUCED, candidate_code="x = 2\n")
    candidate = make_candidate("m.py", "x = 1\n", produced, check("x = 2\n"))
    assert candidate.executable
    assert "-x = 1" in candidate.diff and "+x = 2" in candidate.diff

    bad = make_candidate("m.py", "x = 1\n", produced, check("import subprocess\n"))
    assert not bad.executable

    failed = RepairResult(strategy_id=StrategyId.S2, status=RepairStatus.NO_REPAIR, failure_reason="none")
    none_candidate = make_candidate("m.py", "x = 1\n", failed, None)
    assert not none_candidate.executable and none_candidate.diff == ""


def test_candidate_id_is_deterministic():
    produced = RepairResult(strategy_id=StrategyId.S2, status=RepairStatus.PRODUCED, candidate_code="x = 2\n")
    assert make_candidate("m.py", "", produced, None).candidate_id == make_candidate("m.py", "", produced, None).candidate_id
