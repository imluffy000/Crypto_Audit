"""Stable identifiers derived from existing domain models (the Finding schema is unchanged)."""

import hashlib
import json
from typing import Any

from cryptoaudit.core.models import Finding


def finding_id(finding: Finding) -> str:
    """
    Deterministic identifier for a finding.

    Uses the same key the AnalyzerEngine deduplicates on, so two findings the
    engine treats as distinct (e.g. CR4 salt + iterations on one line) get distinct IDs.
    """
    key = [
        finding.file.replace("\\", "/"),
        finding.line,
        finding.column,
        finding.rule_id,
        finding.matched_api,
        finding.explanation,
    ]
    return "F-" + stable_hash(key)[:16]


def stable_hash(payload: Any) -> str:
    """SHA-256 over a canonical JSON encoding of payload."""
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()
