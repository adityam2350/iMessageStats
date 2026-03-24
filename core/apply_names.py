"""
apply_names.py — Substitute display names in a leaderboard document dict.

Loads a simple JSON object mapping identifier strings to display strings.
Does not merge or re-rank rows; only rewrites participant/sender fields.
"""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any


def load_mapping(path: Path | str) -> dict[str, str]:
    path = Path(path)
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("Names file must be a JSON object mapping strings to strings.")
    out: dict[str, str] = {}
    for k, v in raw.items():
        if not isinstance(k, str) or not isinstance(v, str):
            raise ValueError("Names file must use only string keys and string values.")
        out[k] = v
    return out


def substitute_identifiers(doc: dict[str, Any], mapping: dict[str, str]) -> dict[str, Any]:
    """Return a deep copy of doc with participant/sender identifiers replaced where mapped."""
    out = deepcopy(doc)
    lb = out.get("leaderboards")
    if not isinstance(lb, dict):
        return out

    for _key, rows in lb.items():
        if not isinstance(rows, list):
            continue
        for row in rows:
            if not isinstance(row, dict):
                continue
            if "participant" in row and isinstance(row["participant"], str):
                pid = row["participant"]
                row["participant"] = mapping.get(pid, pid)
            if "sender" in row and isinstance(row["sender"], str):
                sid = row["sender"]
                row["sender"] = mapping.get(sid, sid)
    return out


def apply_names_file(doc: dict[str, Any], names_path: Path | str) -> dict[str, Any]:
    """Load names from path and return a new document with substitutions applied."""
    mapping = load_mapping(names_path)
    return substitute_identifiers(doc, mapping)
