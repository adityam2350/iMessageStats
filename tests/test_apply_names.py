"""Tests for core.apply_names (merge rows by display name)."""

from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core import apply_names as an


def test_merge_sums_two_ids_to_same_display_name():
    doc = {
        "version": 1,
        "chat_id": 1,
        "summary": {},
        "leaderboards": {
            "messages_sent": [
                {"rank": 1, "participant": "a@x.com", "count": 10},
                {"rank": 2, "participant": "+1999", "count": 5},
            ],
            "reaction_receivers": [
                {"rank": 1, "participant": "a@x.com", "count": 3},
                {"rank": 2, "participant": "+1999", "count": 2},
            ],
            "reaction_givers": [],
            "rrpm": [],
            "hahas_received": [],
            "most_haha_messages": [],
            "bangers": [],
            "emphasizes_received": [],
            "questions_received": [],
        },
    }
    mapping = {"a@x.com": "Alice", "+1999": "Alice"}
    out = an.merge_by_display_name(doc, mapping)
    assert out["display_names_merged"] is True
    ms = out["leaderboards"]["messages_sent"]
    assert len(ms) == 1
    assert ms[0]["participant"] == "Alice"
    assert ms[0]["count"] == 15
    rr = out["leaderboards"]["reaction_receivers"]
    assert len(rr) == 1
    assert rr[0]["participant"] == "Alice"
    assert rr[0]["count"] == 5
    rpm = out["leaderboards"]["rrpm"]
    assert len(rpm) == 1
    assert rpm[0]["participant"] == "Alice"
    assert rpm[0]["rrpm"] == round(5 / 15, 2)


def test_unmapped_participant_unchanged_and_separate_row():
    doc = {
        "version": 1,
        "chat_id": 1,
        "summary": {},
        "leaderboards": {
            "messages_sent": [
                {"rank": 1, "participant": "a@x.com", "count": 10},
                {"rank": 2, "participant": "bob@x.com", "count": 3},
            ],
            "reaction_receivers": [
                {"rank": 1, "participant": "a@x.com", "count": 1},
                {"rank": 2, "participant": "bob@x.com", "count": 1},
            ],
            "reaction_givers": [],
            "rrpm": [],
            "hahas_received": [],
            "most_haha_messages": [],
            "bangers": [],
            "emphasizes_received": [],
            "questions_received": [],
        },
    }
    out = an.merge_by_display_name(doc, {"a@x.com": "Alice"})
    ms = out["leaderboards"]["messages_sent"]
    assert len(ms) == 2
    alice_row = next(r for r in ms if r["participant"] == "Alice")
    bob_row = next(r for r in ms if r["participant"] == "bob@x.com")
    assert alice_row["count"] == 10
    assert bob_row["count"] == 3


def test_most_haha_messages_remaps_sender_and_reranks():
    doc = {
        "version": 1,
        "chat_id": 1,
        "summary": {},
        "leaderboards": {
            "messages_sent": [],
            "reaction_receivers": [],
            "reaction_givers": [],
            "rrpm": [],
            "hahas_received": [],
            "most_haha_messages": [
                {"rank": 1, "sender": "x@y.com", "text": "hi", "haha_count": 5},
            ],
            "bangers": [],
            "emphasizes_received": [],
            "questions_received": [],
        },
    }
    out = an.merge_by_display_name(doc, {"x@y.com": "Pat"})
    rows = out["leaderboards"]["most_haha_messages"]
    assert rows[0]["sender"] == "Pat"
    assert rows[0]["rank"] == 1
