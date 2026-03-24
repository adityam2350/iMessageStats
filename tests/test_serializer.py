"""Unit tests for core.serializer."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import json
import tempfile

import pytest

from core.models import ChatSummary, Participant
from core.stats import BangerEntry, LeaderboardEntry
from core import serializer


def test_to_dict_includes_version():
    summary = ChatSummary("G", 2, 1, 0, None, None)
    p = Participant("a@x.com")
    all_stats = {
        "messages_sent": [LeaderboardEntry(1, p, 5)],
        "reaction_receivers": [],
        "reaction_givers": [],
        "rrpm": [],
        "hahas_received": [],
        "most_haha_messages": [],
        "bangers": [],
        "emphasizes_received": [],
        "questions_received": [],
    }
    doc = serializer.to_dict(7, summary, all_stats, display_top_n=5)
    assert doc["version"] == serializer.CURRENT_VERSION
    assert doc["chat_id"] == 7
    assert doc["display_top_n"] == 5
    assert doc["leaderboards"]["messages_sent"][0]["participant"] == "a@x.com"


def test_from_dict_missing_version():
    with pytest.raises(ValueError, match="missing required"):
        serializer.from_dict({"leaderboards": {}})


def test_from_dict_unknown_version():
    with pytest.raises(ValueError, match="Unsupported leaderboard format"):
        serializer.from_dict({"version": 999, "leaderboards": {}})


def test_round_trip_dict_equivalence():
    summary = ChatSummary(
        display_name="Test",
        participant_count=2,
        message_count=10,
        reaction_count=5,
        earliest_message=datetime(2024, 1, 1, tzinfo=timezone.utc),
        latest_message=datetime(2024, 2, 1, tzinfo=timezone.utc),
    )
    alice = Participant("alice@example.com")
    all_stats = {
        "messages_sent": [LeaderboardEntry(1, alice, 5)],
        "reaction_receivers": [],
        "reaction_givers": [],
        "rrpm": [LeaderboardEntry(1, alice, 250)],
        "hahas_received": [],
        "most_haha_messages": [BangerEntry(1, alice, "hi", 4)],
        "bangers": [LeaderboardEntry(1, alice, 2)],
        "emphasizes_received": [],
        "questions_received": [],
    }
    original = serializer.to_dict(99, summary, all_stats)
    normalized = serializer.from_dict(original)
    assert normalized == original


def test_write_read_json_round_trip():
    summary = ChatSummary("G", 1, 1, 0, None, None)
    p = Participant("me@example.com")
    all_stats = {
        "messages_sent": [LeaderboardEntry(1, p, 1)],
        "reaction_receivers": [],
        "reaction_givers": [],
        "rrpm": [],
        "hahas_received": [],
        "most_haha_messages": [],
        "bangers": [],
        "emphasizes_received": [],
        "questions_received": [],
    }
    doc = serializer.to_dict(3, summary, all_stats)
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "nested" / "lb.json"
        serializer.write_json(doc, path)
        raw = serializer.read_json(path)
        assert raw == json.loads(path.read_text(encoding="utf-8"))
        again = serializer.from_dict(raw)
        assert again == doc
