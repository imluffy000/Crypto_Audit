"""
CryptoAudit check harness. Executed INSIDE the validation sandbox.

Standard library only: it is copied verbatim into the sandbox work directory and run as a
script. It imports a candidate module from a file, runs every check_*(ctx) function from a
check file, and prints one marker-prefixed JSON line with the results.
"""

import argparse
import importlib.util
import itertools
import json
import os
import sys
import time
from pathlib import Path

MARKER = "CRYPTOAUDIT_RESULT:"
NONCE_ENV = "CRYPTOAUDIT_RESULT_NONCE"


class CheckContext:
    def __init__(self, candidate_path: Path, artifacts_dir: Path) -> None:
        self.candidate_path = candidate_path
        self.artifacts_dir = artifacts_dir
        self._counter = itertools.count()

    def load_candidate(self):
        """Import a fresh copy of the candidate so patches applied before loading take effect."""
        name = f"cryptoaudit_candidate_{next(self._counter)}"
        spec = importlib.util.spec_from_file_location(name, self.candidate_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def artifact(self, name: str) -> Path:
        path = (self.artifacts_dir / name).resolve()
        if self.artifacts_dir.resolve() not in path.parents:
            raise ValueError(f"artifact path escapes artifacts directory: {name}")
        return path

    def load_json(self, name: str):
        return json.loads(self.artifact(name).read_text(encoding="utf-8"))


def _load_checks(checks_path: Path):
    spec = importlib.util.spec_from_file_location("cryptoaudit_checks", checks_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run(checks_path: Path, candidate_path: Path, artifacts_dir: Path) -> dict:
    try:
        checks = _load_checks(checks_path)
    except BaseException as exc:  # an oracle that cannot load is a validator error, not a candidate failure
        return {"harness_error": f"check module failed to load: {type(exc).__name__}: {exc}", "results": []}

    ctx = CheckContext(candidate_path, artifacts_dir)
    results = []
    names = sorted(n for n in dir(checks) if n.startswith("check_") and callable(getattr(checks, n)))
    for name in names:
        started = time.perf_counter()
        try:
            getattr(checks, name)(ctx)
            status, message = "PASS", ""
        except AssertionError as exc:
            status, message = "FAIL", str(exc) or "assertion failed"
        except BaseException as exc:  # candidate raised: a behavioural failure of the candidate
            status, message = "FAIL", f"candidate raised {type(exc).__name__}: {exc}"
        results.append(
            {"name": name, "status": status, "message": message[:500], "duration": round(time.perf_counter() - started, 4)}
        )
    return {"harness_error": None, "results": results}


def main() -> int:
    # Read and remove the per-run nonce before any candidate code is imported, so a candidate
    # cannot trivially forge a result line. (Best effort: in-process code is not fully contained.)
    nonce = os.environ.pop(NONCE_ENV, "")
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--checks", required=True)
    parser.add_argument("--artifacts", required=True)
    args = parser.parse_args()
    outcome = run(Path(args.checks), Path(args.candidate), Path(args.artifacts))
    sys.stdout.write("\n" + MARKER + nonce + ":" + json.dumps(outcome) + "\n")
    sys.stdout.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main())
