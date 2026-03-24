"""Tests for merge_display_names (participant → display name aggregation)."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import merge_display_names as mdn


def test_merge_sums_counts_for_same_display_name():
    doc = {
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
    out = mdn.apply_participant_mapping(doc, mapping)
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
    assert rpm[0]["count"] == 33  # hundredths
    assert rpm[0]["rrpm"] == 0.33


def test_unmapped_participant_unchanged():
    doc = {
        "chat_id": 1,
        "summary": {},
        "leaderboards": {
            "messages_sent": [{"rank": 1, "participant": "only@me.com", "count": 1}],
            "reaction_receivers": [{"rank": 1, "participant": "only@me.com", "count": 4}],
            "reaction_givers": [],
            "rrpm": [],
            "hahas_received": [],
            "most_haha_messages": [],
            "bangers": [],
            "emphasizes_received": [],
            "questions_received": [],
        },
    }
    out = mdn.apply_participant_mapping(doc, {})
    assert out["leaderboards"]["messages_sent"][0]["participant"] == "only@me.com"


def test_most_haha_messages_remaps_sender():
    doc = {
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
    out = mdn.apply_participant_mapping(doc, {"x@y.com": "Pat"})
    rows = out["leaderboards"]["most_haha_messages"]
    assert rows[0]["sender"] == "Pat"
    assert rows[0]["rank"] == 1
