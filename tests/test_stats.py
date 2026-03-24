"""
tests/test_stats.py — Unit tests for the leaderboard calculations in stats.py.

All tests here are pure: they construct in-memory Message and Reaction objects
and verify the output of each leaderboard function independently.
No database, no file system, no network.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from datetime import datetime, timezone

import pytest

from core.models import Message, Participant, Reaction, ReactionType
from core.stats import (
    bangers_leaderboard,
    emphasizes_received_leaderboard,
    most_haha_messages_leaderboard,
    hahas_received_leaderboard,
    messages_sent_leaderboard,
    questions_received_leaderboard,
    reaction_givers_leaderboard,
    reaction_receivers_leaderboard,
    rrpm_leaderboard,
)


# ── Fixtures ───────────────────────────────────────────────────────────────────

ALICE = Participant("alice@example.com")
BOB   = Participant("bob@example.com")
CAROL = Participant("carol@example.com")

NOW = datetime(2024, 1, 1, tzinfo=timezone.utc)


def make_message(message_id: int, sender: Participant, text: str = "hello") -> Message:
    return Message(
        message_id=message_id,
        guid=f"guid-{message_id}",
        sender=sender,
        text=text,
        timestamp=NOW,
    )


def make_reaction(
    reactor: Participant,
    recipient: Participant,
    reaction_type: ReactionType,
    message_id: int = 1,
) -> Reaction:
    return Reaction(
        reactor=reactor,
        recipient=recipient,
        reaction_type=reaction_type,
        original_message_id=message_id,
    )


# ── Messages Sent ──────────────────────────────────────────────────────────────

def test_messages_sent_ranks_by_count():
    messages = [
        make_message(1, ALICE),
        make_message(2, ALICE),
        make_message(3, BOB),
    ]
    result = messages_sent_leaderboard(messages)
    assert result[0].participant == ALICE
    assert result[0].count == 2
    assert result[1].participant == BOB
    assert result[1].count == 1


def test_messages_sent_empty():
    assert messages_sent_leaderboard([]) == []


# ── Reaction Receivers ─────────────────────────────────────────────────────────

def test_reaction_receivers_counts_correctly():
    reactions = [
        make_reaction(BOB,   ALICE, ReactionType.HEART),
        make_reaction(CAROL, ALICE, ReactionType.HAHA),
        make_reaction(ALICE, BOB,   ReactionType.THUMBS_UP),
    ]
    result = reaction_receivers_leaderboard(reactions)
    assert result[0].participant == ALICE
    assert result[0].count == 2


def test_reaction_receivers_empty():
    assert reaction_receivers_leaderboard([]) == []


# ── Reaction Givers ────────────────────────────────────────────────────────────

def test_reaction_givers_counts_correctly():
    reactions = [
        make_reaction(ALICE, BOB,   ReactionType.HEART),
        make_reaction(ALICE, CAROL, ReactionType.HAHA),
        make_reaction(BOB,   CAROL, ReactionType.HEART),
    ]
    result = reaction_givers_leaderboard(reactions)
    assert result[0].participant == ALICE
    assert result[0].count == 2


# ── RRPM ───────────────────────────────────────────────────────────────────────

def test_rrpm_calculates_correctly():
    messages = [
        make_message(1, ALICE),  # Alice sends 1 message
        make_message(2, BOB),    # Bob sends 1 message
        make_message(3, BOB),    # Bob sends 2 messages
    ]
    reactions = [
        make_reaction(BOB, ALICE, ReactionType.HAHA),  # Alice gets 1 reaction
        make_reaction(BOB, ALICE, ReactionType.HEART), # Alice gets 2 reactions
    ]
    result = rrpm_leaderboard(messages, reactions)
    # Alice: 2 reactions / 1 message = 2.00 RRPM → stored as 200
    # Bob:   0 reactions / 2 messages = 0.00 RRPM → stored as 0
    assert result[0].participant == ALICE
    assert result[0].count == 200


def test_rrpm_excludes_zero_message_senders():
    # CAROL appears as a reaction recipient but never sends a message
    messages = [make_message(1, ALICE)]
    reactions = [make_reaction(ALICE, CAROL, ReactionType.HEART)]
    result = rrpm_leaderboard(messages, reactions)
    participants = [e.participant for e in result]
    assert CAROL not in participants


# ── HaHas Received ─────────────────────────────────────────────────────────────

def test_hahas_received_filters_by_type():
    reactions = [
        make_reaction(BOB,   ALICE, ReactionType.HAHA),
        make_reaction(CAROL, ALICE, ReactionType.HAHA),
        make_reaction(BOB,   ALICE, ReactionType.HEART),  # should not count
        make_reaction(ALICE, BOB,   ReactionType.HAHA),
    ]
    result = hahas_received_leaderboard(reactions)
    assert result[0].participant == ALICE
    assert result[0].count == 2
    assert result[1].participant == BOB
    assert result[1].count == 1


# ── Most HaHa messages & participant Bangers ─────────────────────────────────

def test_most_haha_messages_requires_threshold_hahas():
    messages = [
        make_message(1, ALICE, text="this is a banger"),
        make_message(2, BOB,   text="not a banger"),
    ]
    reactions = [
        make_reaction(BOB,   ALICE, ReactionType.HAHA, message_id=1),
        make_reaction(CAROL, ALICE, ReactionType.HAHA, message_id=1),
        make_reaction(BOB,   ALICE, ReactionType.HAHA, message_id=1),  # 3 HaHas → qualifies
        make_reaction(CAROL, BOB,   ReactionType.HAHA, message_id=2),  # only 1 HaHa → not listed
    ]
    result = most_haha_messages_leaderboard(messages, reactions)
    assert len(result) == 1
    assert result[0].sender == ALICE
    assert result[0].haha_count == 3


def test_most_haha_messages_empty_when_no_threshold_met():
    messages = [make_message(1, ALICE)]
    reactions = [
        make_reaction(BOB, ALICE, ReactionType.HAHA, message_id=1),
        make_reaction(BOB, ALICE, ReactionType.HAHA, message_id=1),
        # only 2 HaHas, threshold is 3
    ]
    result = most_haha_messages_leaderboard(messages, reactions)
    assert len(result) == 0


def test_bangers_leaderboard_counts_messages_per_sender():
    """Bangers: how many of each participant's messages hit 3+ HaHas."""
    messages = [
        make_message(1, ALICE, text="a1"),
        make_message(2, ALICE, text="a2"),
        make_message(3, BOB,   text="b1"),
        make_message(4, BOB,   text="b2"),
    ]
    reactions = [
        make_reaction(BOB, ALICE, ReactionType.HAHA, message_id=1),
        make_reaction(CAROL, ALICE, ReactionType.HAHA, message_id=1),
        make_reaction(BOB, ALICE, ReactionType.HAHA, message_id=1),
        make_reaction(BOB, ALICE, ReactionType.HAHA, message_id=2),
        make_reaction(CAROL, ALICE, ReactionType.HAHA, message_id=2),
        make_reaction(BOB, ALICE, ReactionType.HAHA, message_id=2),
        make_reaction(ALICE, BOB, ReactionType.HAHA, message_id=3),
        make_reaction(CAROL, BOB, ReactionType.HAHA, message_id=3),
        make_reaction(ALICE, BOB, ReactionType.HAHA, message_id=3),
        make_reaction(ALICE, BOB, ReactionType.HAHA, message_id=4),
    ]
    result = bangers_leaderboard(messages, reactions)
    assert len(result) == 2
    assert result[0].participant == ALICE
    assert result[0].count == 2
    assert result[1].participant == BOB
    assert result[1].count == 1


def test_bangers_participant_leaderboard_empty_when_no_threshold_met():
    messages = [make_message(1, ALICE)]
    reactions = [
        make_reaction(BOB, ALICE, ReactionType.HAHA, message_id=1),
        make_reaction(BOB, ALICE, ReactionType.HAHA, message_id=1),
    ]
    result = bangers_leaderboard(messages, reactions)
    assert len(result) == 0


# ── Emphasizes & Questions ─────────────────────────────────────────────────────

def test_emphasizes_received():
    reactions = [
        make_reaction(BOB, ALICE, ReactionType.EMPHASIZE),
        make_reaction(BOB, ALICE, ReactionType.HEART),    # should not count
    ]
    result = emphasizes_received_leaderboard(reactions)
    assert result[0].participant == ALICE
    assert result[0].count == 1


def test_questions_received():
    reactions = [
        make_reaction(BOB, CAROL, ReactionType.QUESTION),
        make_reaction(BOB, CAROL, ReactionType.QUESTION),
    ]
    result = questions_received_leaderboard(reactions)
    assert result[0].participant == CAROL
    assert result[0].count == 2
