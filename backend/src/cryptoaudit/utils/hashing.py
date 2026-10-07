"""Deterministic hashing used for IDs and reproducibility metadata."""

import hashlib
import json
from typing import Any


def stable_hash(payload: Any) -> str:
    """SHA-256 over a canonical JSON encoding of payload."""
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()
