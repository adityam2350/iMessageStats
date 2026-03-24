"""
apply_names.py — Map identifiers to display names and merge leaderboard rows.

When several raw identifiers map to the same display name, counts are summed,
ranks recomputed, and RRPM is derived from merged messages-sent and
reaction-receiver totals (same definition as stats.rrpm_leaderboard).

most_haha_messages only remaps senders and re-sorts by HaHa count (rows are not merged).
"""

from __future__ import annotations

import json
from collections import defaultdict
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


def _as_row_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _resolve_name(identifier: str, mapping: dict[str, str]) -> str:
    return mapping.get(identifier, identifier)


def _merge_counts(
    entries: list[dict[str, Any]],
    mapping: dict[str, str],
    *,
    id_field: str = "participant",
    count_field: str = "count",
) -> dict[str, int]:
    totals: dict[str, int] = defaultdict(int)
    for row in entries:
        if not isinstance(row, dict):
            continue
        raw_id = str(row.get(id_field, ""))
        name = _resolve_name(raw_id, mapping)
        totals[name] += int(row.get(count_field, 0))
    return dict(totals)


def _rank_by_count_desc(totals: dict[str, int]) -> list[dict[str, Any]]:
    pairs = sorted(totals.items(), key=lambda item: (-item[1], item[0]))
    return [
        {"rank": i + 1, "participant": name, "count": count}
        for i, (name, count) in enumerate(pairs)
    ]


def _merge_participant_board(
    entries: list[dict[str, Any]],
    mapping: dict[str, str],
) -> list[dict[str, Any]]:
    return _rank_by_count_desc(_merge_counts(entries, mapping, id_field="participant"))


def merge_rrpm_from_totals(
    messages_by_name: dict[str, int],
    receivers_by_name: dict[str, int],
) -> list[dict[str, Any]]:
    """
    RRPM = reactions received (any type) / messages sent.
    Excludes names with zero messages (matches stats behavior).
    """
    rows: list[tuple[str, int, float]] = []
    for name, sent in messages_by_name.items():
        if sent <= 0:
            continue
        recv = receivers_by_name.get(name, 0)
        rrpm = recv / sent
        hundredths = int(round(rrpm * 100))
        rows.append((name, hundredths, rrpm))
    rows.sort(key=lambda item: (-item[2], item[0]))
    return [
        {
            "rank": i + 1,
            "participant": name,
            "count": h,
            "rrpm": round(r, 2),
        }
        for i, (name, h, r) in enumerate(rows)
    ]


def merge_most_haha_messages(
    entries: list[dict[str, Any]],
    mapping: dict[str, str],
) -> list[dict[str, Any]]:
    """Remap senders; re-sort by haha_count and re-rank (rows are not merged)."""
    rows: list[dict[str, Any]] = []
    for row in entries:
        if not isinstance(row, dict):
            continue
        raw = str(row.get("sender", ""))
        rows.append({
            "sender": _resolve_name(raw, mapping),
            "text": row.get("text", ""),
            "haha_count": int(row.get("haha_count", 0)),
        })
    rows.sort(key=lambda r: (-r["haha_count"], r["sender"], str(r["text"])))
    return [
        {**r, "rank": i + 1}
        for i, r in enumerate(rows)
    ]


def merge_by_display_name(doc: dict[str, Any], mapping: dict[str, str]) -> dict[str, Any]:
    """
    Return a new document with leaderboards merged by mapped display name.

    Expects the structure produced by serializer.to_dict.
    """
    out = deepcopy(doc)
    lb = out.get("leaderboards")
    if not isinstance(lb, dict):
        return out

    messages_sent = _as_row_list(lb.get("messages_sent"))
    reaction_receivers = _as_row_list(lb.get("reaction_receivers"))

    merged_messages = _merge_counts(messages_sent, mapping, id_field="participant")
    merged_receivers = _merge_counts(reaction_receivers, mapping, id_field="participant")

    new_lb: dict[str, Any] = {
        "messages_sent": _rank_by_count_desc(merged_messages),
        "reaction_receivers": _rank_by_count_desc(merged_receivers),
        "reaction_givers": _merge_participant_board(
            _as_row_list(lb.get("reaction_givers")), mapping
        ),
        "rrpm": merge_rrpm_from_totals(merged_messages, merged_receivers),
        "hahas_received": _merge_participant_board(
            _as_row_list(lb.get("hahas_received")), mapping
        ),
        "most_haha_messages": merge_most_haha_messages(
            _as_row_list(lb.get("most_haha_messages")), mapping
        ),
        "bangers": _merge_participant_board(
            _as_row_list(lb.get("bangers")), mapping
        ),
        "emphasizes_received": _merge_participant_board(
            _as_row_list(lb.get("emphasizes_received")), mapping
        ),
        "questions_received": _merge_participant_board(
            _as_row_list(lb.get("questions_received")), mapping
        ),
    }

    out["leaderboards"] = new_lb
    out["display_names_merged"] = True
    return out


def apply_names_file(doc: dict[str, Any], names_path: Path | str) -> dict[str, Any]:
    """Load names from path and return a document with merged display names."""
    mapping = load_mapping(names_path)
    return merge_by_display_name(doc, mapping)
