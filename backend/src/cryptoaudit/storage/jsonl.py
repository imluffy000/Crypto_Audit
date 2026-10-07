"""JSONL export of experiment records for analysis outside CryptoAudit."""

import json
from pathlib import Path
from typing import Optional, Union

from cryptoaudit.storage.sqlite import ExperimentStore


def export_jsonl(store: ExperimentStore, destination: Union[str, Path], run_id: Optional[str] = None) -> int:
    """Write one JSON object per stored record; returns the number of records written."""
    rows = store.records(run_id)
    with open(destination, "w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True, default=str) + "\n")
    return len(rows)
