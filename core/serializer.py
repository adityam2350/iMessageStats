"""
serializer.py — Versioned leaderboard documents as plain dicts and JSON files.

Name mapping is handled elsewhere; identifiers are stored as raw strings.
"""

from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any

from core.models import ChatSummary
from core.stats import BangerEntry, LeaderboardEntry

CURRENT_VERSION = 1

LEADERBOARD_KEYS = (
    "messages_sent",
    "reaction_receivers",
    "reaction_givers",
    "rrpm",
    "hahas_received",
    "most_haha_messages",
    "bangers",
    "emphasizes_received",
    "questions_received",
)


def _iso(dt: datetime | None) -> str | None:
    return dt.isoformat() if dt else None


def chat_summary_to_dict(summary: ChatSummary) -> dict[str, Any]:
    return {
        "display_name": summary.display_name,
        "participant_count": summary.participant_count,
        "message_count": summary.message_count,
        "reaction_count": summary.reaction_count,
        "earliest_message": _iso(summary.earliest_message),
        "latest_message": _iso(summary.latest_message),
    }


def leaderboard_rows_to_dicts(
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


def banger_rows_to_dicts(entries: list[BangerEntry]) -> list[dict[str, Any]]:
    return [
        {
            "rank": e.rank,
            "sender": e.sender.identifier,
            "text": e.text,
            "haha_count": e.haha_count,
        }
        for e in entries
    ]


def to_dict(
    chat_id: int,
    summary: ChatSummary,
    all_stats: dict[str, Any],
    *,
    display_top_n: int | None = None,
) -> dict[str, Any]:
    """Build a versioned document with all leaderboard tables (full data, not sliced)."""
    lb = {
        key: leaderboard_rows_to_dicts(all_stats[key], rrpm=(key == "rrpm"))
        for key in LEADERBOARD_KEYS
        if key != "most_haha_messages"
    }
    lb["most_haha_messages"] = banger_rows_to_dicts(all_stats["most_haha_messages"])

    return {
        "version": CURRENT_VERSION,
        "chat_id": chat_id,
        "summary": chat_summary_to_dict(summary),
        "display_top_n": display_top_n,
        "leaderboards": lb,
    }


def from_dict(data: dict[str, Any]) -> dict[str, Any]:
    """
    Validate a parsed leaderboard document and return a normalized copy.

    Raises ValueError with a clear message if the version is missing or unsupported.
    """
    if not isinstance(data, dict):
        raise ValueError("Leaderboard document must be a JSON object.")

    ver = data.get("version")
    if ver is None:
        raise ValueError(
            'Leaderboard JSON is missing required "version" key; refusing to load.'
        )
    if ver != CURRENT_VERSION:
        raise ValueError(
            f"Unsupported leaderboard format version {ver!r}; "
            f"this tool only supports version {CURRENT_VERSION}."
        )

    lb = data.get("leaderboards")
    if not isinstance(lb, dict):
        raise ValueError('Leaderboard JSON must contain a "leaderboards" object.')

    out = deepcopy(data)
    lb_out = out.setdefault("leaderboards", {})
    for key in LEADERBOARD_KEYS:
        if key not in lb_out:
            lb_out[key] = []
        elif not isinstance(lb_out[key], list):
            raise ValueError(f'Leaderboards key "{key}" must be a JSON array.')
    return out


def write_json(data: dict[str, Any], path: Path | str) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def read_json(path: Path | str) -> dict[str, Any]:
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"Leaderboard file not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))
