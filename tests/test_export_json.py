"""Tests for JSON export of leaderboards."""

import json
import sys
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from models import ChatSummary, Participant
from stats import BangerEntry, LeaderboardEntry
import export_json


def test_build_leaderboards_document_rrpm_and_bangers():
    summary = ChatSummary(
        display_name="Test",
        participant_count=2,
        message_count=10,
        reaction_count=5,
        earliest_message=datetime(2024, 1, 1, tzinfo=timezone.utc),
        latest_message=datetime(2024, 2, 1, tzinfo=timezone.utc),
    )
    alice = Participant("alice@example.com")
    bob = Participant("bob@example.com")
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
    doc = export_json.build_leaderboards_document(
        99, summary, all_stats, top_n=None
    )
    assert doc["chat_id"] == 99
    assert doc["summary"]["display_name"] == "Test"
    assert doc["summary"]["earliest_message"].startswith("2024-01-01")
    assert doc["leaderboards"]["rrpm"][0]["rrpm"] == 2.5
    assert doc["leaderboards"]["rrpm"][0]["count"] == 250
    assert doc["leaderboards"]["most_haha_messages"][0]["sender"] == "alice@example.com"
    assert doc["leaderboards"]["bangers"][0]["participant"] == "alice@example.com"


def test_top_n_slices_export():
    entries = [
        LeaderboardEntry(1, Participant("a"), 10),
        LeaderboardEntry(2, Participant("b"), 9),
    ]
    all_stats = {
        "messages_sent": entries,
        "reaction_receivers": [],
        "reaction_givers": [],
        "rrpm": [],
        "hahas_received": [],
        "most_haha_messages": [],
        "bangers": [],
        "emphasizes_received": [],
        "questions_received": [],
    }
    summary = ChatSummary("x", 0, 0, 0, None, None)
    doc = export_json.build_leaderboards_document(1, summary, all_stats, top_n=1)
    assert len(doc["leaderboards"]["messages_sent"]) == 1
    assert doc["top_n_applied"] == 1


def test_write_leaderboards_json_roundtrip():
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
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "nested" / "out.json"
        export_json.write_leaderboards_json(path, 3, summary, all_stats)
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["chat_id"] == 3
        assert data["leaderboards"]["messages_sent"][0]["participant"] == "me@example.com"
