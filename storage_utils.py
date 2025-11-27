# json 覆盖写入

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, List, Dict, Any, Sequence


def load_records(json_path: str | Path) -> List[Dict[str, Any]]:
    path = Path(json_path)
    if not path.exists():
        return []
    try:
        with path.open("r", encoding="utf-8") as f:
            existing = json.load(f)
    except Exception:
        return []
    if isinstance(existing, list):
        return existing
    if isinstance(existing, dict):
        return [existing]
    return []


def upsert_record(
    records: Iterable[Dict[str, Any]],
    new_record: Dict[str, Any],
    key_fields: Sequence[str] = ("item", "name"),
) -> List[Dict[str, Any]]:
    key = tuple(new_record.get(field) for field in key_fields)
    updated = []
    found = False
    for record in records:
        record_key = tuple(record.get(field) for field in key_fields)
        if not found and record_key == key:
            updated.append(new_record)
            found = True
        else:
            updated.append(record)
    if not found:
        updated.append(new_record)
    return updated


def write_records(json_path: str | Path, records: Iterable[Dict[str, Any]]) -> None:
    path = Path(json_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(list(records), f, indent=2, ensure_ascii=False)
