"""
merge_display_names.py — Merge leaderboard JSON rows by display name.

Maps raw participant identifiers (phone, email, etc.) to human-readable names
via a string→string JSON object. Multiple identifiers mapping to the same
name have their numeric stats summed and ranks recomputed.

RRPM is recomputed as total reactions received / total messages sent for each
merged name (same definition as stats.rrpm_leaderboard).
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any


def resolve_display_name(identifier: str, mapping: dict[str, str]) -> str:
    """Return mapped name, or the original identifier if unmapped."""
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
        raw_id = row[id_field]
        name = resolve_display_name(str(raw_id), mapping)
        totals[name] += int(row[count_field])
    return dict(totals)


def _rank_by_count_desc(totals: dict[str, int]) -> list[dict[str, Any]]:
    pairs = sorted(totals.items(), key=lambda item: (-item[1], item[0]))
    return [
        {"rank": i + 1, "participant": name, "count": count}
        for i, (name, count) in enumerate(pairs)
    ]


def _merge_leaderboard_participant(
    entries: list[dict[str, Any]],
    mapping: dict[str, str],
) -> list[dict[str, Any]]:
    return _rank_by_count_desc(_merge_counts(entries, mapping, id_field="participant"))


def merge_most_haha_messages(
    entries: list[dict[str, Any]],
    mapping: dict[str, str],
) -> list[dict[str, Any]]:
    """Remap senders; re-sort by haha_count and re-rank (rows are not merged)."""
    rows = []
    for row in entries:
        raw = str(row["sender"])
        rows.append({
            "sender": resolve_display_name(raw, mapping),
            "text": row["text"],
            "haha_count": int(row["haha_count"]),
        })
    rows.sort(key=lambda r: (-r["haha_count"], r["sender"], r["text"]))
    return [
        {**r, "rank": i + 1}
        for i, r in enumerate(rows)
    ]


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


def apply_participant_mapping(
    doc: dict[str, Any],
    mapping: dict[str, str],
) -> dict[str, Any]:
    """
    Return a new document with leaderboards merged by display name.

    Expects the structure produced by export_json.build_leaderboards_document.
    """
    lb = doc.get("leaderboards") or {}
    if not isinstance(lb, dict):
        raise ValueError("document missing leaderboards object")

    messages_sent = lb.get("messages_sent") or []
    reaction_receivers = lb.get("reaction_receivers") or []

    merged_messages = _merge_counts(messages_sent, mapping, id_field="participant")
    merged_receivers = _merge_counts(reaction_receivers, mapping, id_field="participant")

    new_lb = {
        "messages_sent": _rank_by_count_desc(merged_messages),
        "reaction_receivers": _rank_by_count_desc(merged_receivers),
        "reaction_givers": _merge_leaderboard_participant(
            lb.get("reaction_givers") or [], mapping
        ),
        "rrpm": merge_rrpm_from_totals(merged_messages, merged_receivers),
        "hahas_received": _merge_leaderboard_participant(
            lb.get("hahas_received") or [], mapping
        ),
        "most_haha_messages": merge_most_haha_messages(
            lb.get("most_haha_messages") or [], mapping
        ),
        "bangers": _merge_leaderboard_participant(
            lb.get("bangers") or [], mapping
        ),
        "emphasizes_received": _merge_leaderboard_participant(
            lb.get("emphasizes_received") or [], mapping
        ),
        "questions_received": _merge_leaderboard_participant(
            lb.get("questions_received") or [], mapping
        ),
    }

    out = {
        **doc,
        "display_names_merged": True,
        "leaderboards": new_lb,
    }
    return out
