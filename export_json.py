"""
export_json.py — Serialize chat summary and leaderboards to JSON.

Used when the CLI is run with --json PATH. Applies the same top_n cap as
terminal output when provided.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from models import ChatSummary
from stats import BangerEntry, LeaderboardEntry


def _slice(items: list, top_n: int | None) -> list:
    if top_n is None:
        return items
    return items[:top_n]


def chat_summary_to_dict(summary: ChatSummary) -> dict[str, Any]:
    def iso(dt: datetime | None) -> str | None:
        return dt.isoformat() if dt else None

    return {
        "display_name": summary.display_name,
        "participant_count": summary.participant_count,
        "message_count": summary.message_count,
        "reaction_count": summary.reaction_count,
        "earliest_message": iso(summary.earliest_message),
        "latest_message": iso(summary.latest_message),
    }


def leaderboard_entries_to_dicts(
    entries: list[LeaderboardEntry],
    *,
    rrpm: bool = False,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for e in entries:
        row: dict[str, Any] = {
            "rank": e.rank,
            "participant": e.participant.identifier,
            "count": e.count,
        }
        if rrpm:
            row["rrpm"] = round(e.count / 100.0, 2)
        rows.append(row)
    return rows


def banger_entries_to_dicts(entries: list[BangerEntry]) -> list[dict[str, Any]]:
    return [
        {
            "rank": e.rank,
            "sender": e.sender.identifier,
            "text": e.text,
            "haha_count": e.haha_count,
        }
        for e in entries
    ]


def build_leaderboards_document(
    chat_id: int,
    summary: ChatSummary,
    all_stats: dict[str, Any],
    *,
    top_n: int | None = None,
) -> dict[str, Any]:
    """Assemble one JSON-serializable object for all leaderboards."""
    ms = all_stats["messages_sent"]
    rr = all_stats["reaction_receivers"]
    rg = all_stats["reaction_givers"]
    rpm = all_stats["rrpm"]
    hh = all_stats["hahas_received"]
    mhm = all_stats["most_haha_messages"]
    bang = all_stats["bangers"]
    em = all_stats["emphasizes_received"]
    qu = all_stats["questions_received"]

    return {
        "chat_id": chat_id,
        "summary": chat_summary_to_dict(summary),
        "top_n_applied": top_n,
        "leaderboards": {
            "messages_sent": leaderboard_entries_to_dicts(_slice(ms, top_n)),
            "reaction_receivers": leaderboard_entries_to_dicts(_slice(rr, top_n)),
            "reaction_givers": leaderboard_entries_to_dicts(_slice(rg, top_n)),
            "rrpm": leaderboard_entries_to_dicts(_slice(rpm, top_n), rrpm=True),
            "hahas_received": leaderboard_entries_to_dicts(_slice(hh, top_n)),
            "most_haha_messages": banger_entries_to_dicts(_slice(mhm, top_n)),
            "bangers": leaderboard_entries_to_dicts(_slice(bang, top_n)),
            "emphasizes_received": leaderboard_entries_to_dicts(_slice(em, top_n)),
            "questions_received": leaderboard_entries_to_dicts(_slice(qu, top_n)),
        },
    }


def write_leaderboards_json(
    path: Path | str,
    chat_id: int,
    summary: ChatSummary,
    all_stats: dict[str, Any],
    *,
    top_n: int | None = None,
) -> None:
    path = Path(path)
    doc = build_leaderboards_document(
        chat_id, summary, all_stats, top_n=top_n
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(doc, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
