"""
stats.py — All leaderboard calculations for the group chat analyzer.

Every function here is pure: it takes messages/reactions as input and
returns a sorted list of (Participant, count) pairs. No I/O, no side effects.

This makes each leaderboard independently testable and easy to extend.
"""

from collections import Counter, defaultdict
from dataclasses import dataclass

from models import Message, Participant, Reaction, ReactionType


BANGER_HAHA_THRESHOLD = 3  # A message needs this many HaHas to be a "banger"


@dataclass(frozen=True)
class LeaderboardEntry:
    rank: int
    participant: Participant
    count: int


@dataclass(frozen=True)
class BangerEntry:
    rank: int
    sender: Participant
    text: str
    haha_count: int


def reaction_receivers_leaderboard(reactions: list[Reaction]) -> list[LeaderboardEntry]:
    """Who receives the most reactions of any type."""
    counts = Counter(r.recipient for r in reactions)
    return _to_leaderboard(counts)


def reaction_givers_leaderboard(reactions: list[Reaction]) -> list[LeaderboardEntry]:
    """Who gives the most reactions of any type."""
    counts = Counter(r.reactor for r in reactions)
    return _to_leaderboard(counts)


def rrpm_leaderboard(
    messages: list[Message],
    reactions: list[Reaction],
) -> list[LeaderboardEntry]:
    """
    Reactions Received Per Message — a measure of message quality over quantity.

    Calculated as: total reactions received / total messages sent.
    Participants with zero messages sent are excluded to avoid division by zero.
    The count field here holds the RRPM × 100 (i.e. as a percentage integer)
    for clean display; callers should format it as a decimal.
    """
    messages_sent = Counter(m.sender for m in messages)
    reactions_received = Counter(r.recipient for r in reactions)

    rrpm_scores: dict[Participant, float] = {}
    for participant, sent_count in messages_sent.items():
        if sent_count == 0:
            continue
        received = reactions_received.get(participant, 0)
        rrpm_scores[participant] = received / sent_count

    sorted_entries = sorted(rrpm_scores.items(), key=lambda item: item[1], reverse=True)
    return [
        LeaderboardEntry(rank=i + 1, participant=p, count=int(score * 100))
        for i, (p, score) in enumerate(sorted_entries)
    ]


def hahas_received_leaderboard(reactions: list[Reaction]) -> list[LeaderboardEntry]:
    """Who receives the most HaHa reactions."""
    return _reactions_received_by_type(reactions, ReactionType.HAHA)


def most_haha_messages_leaderboard(
    messages: list[Message],
    reactions: list[Reaction],
) -> list[BangerEntry]:
    """
    Messages that received at least BANGER_HAHA_THRESHOLD HaHas,
    ranked by HaHa count (ties broken by sort order of message ids).
    """
    haha_counts_by_message = _count_reactions_by_message_id(reactions, ReactionType.HAHA)
    message_by_id = {m.message_id: m for m in messages}

    ranked = [
        (message_id, count)
        for message_id, count in haha_counts_by_message.items()
        if count >= BANGER_HAHA_THRESHOLD
    ]
    ranked.sort(key=lambda item: item[1], reverse=True)

    entries = []
    for rank, (message_id, haha_count) in enumerate(ranked, start=1):
        message = message_by_id.get(message_id)
        if message is None:
            continue
        entries.append(BangerEntry(
            rank=rank,
            sender=message.sender,
            text=_truncate(message.text, max_length=60),
            haha_count=haha_count,
        ))
    return entries


def bangers_leaderboard(
    messages: list[Message],
    reactions: list[Reaction],
) -> list[LeaderboardEntry]:
    """
    Participants ranked by how many distinct messages they sent that received
    at least BANGER_HAHA_THRESHOLD HaHa reactions each.
    """
    haha_counts_by_message = _count_reactions_by_message_id(reactions, ReactionType.HAHA)
    message_by_id = {m.message_id: m for m in messages}

    bangers_per_sender: Counter[Participant] = Counter()
    for message_id, count in haha_counts_by_message.items():
        if count < BANGER_HAHA_THRESHOLD:
            continue
        message = message_by_id.get(message_id)
        if message is None:
            continue
        bangers_per_sender[message.sender] += 1

    return _to_leaderboard(bangers_per_sender)


def emphasizes_received_leaderboard(reactions: list[Reaction]) -> list[LeaderboardEntry]:
    """Who receives the most Emphasize (!!) reactions."""
    return _reactions_received_by_type(reactions, ReactionType.EMPHASIZE)


def questions_received_leaderboard(reactions: list[Reaction]) -> list[LeaderboardEntry]:
    """Who receives the most Question (?) reactions."""
    return _reactions_received_by_type(reactions, ReactionType.QUESTION)


def messages_sent_leaderboard(messages: list[Message]) -> list[LeaderboardEntry]:
    """Who sends the most messages."""
    counts = Counter(m.sender for m in messages)
    return _to_leaderboard(counts)


# ── Private helpers ────────────────────────────────────────────────────────────

def _reactions_received_by_type(
    reactions: list[Reaction],
    reaction_type: ReactionType,
) -> list[LeaderboardEntry]:
    filtered = [r for r in reactions if r.reaction_type == reaction_type]
    counts = Counter(r.recipient for r in filtered)
    return _to_leaderboard(counts)


def _count_reactions_by_message_id(
    reactions: list[Reaction],
    reaction_type: ReactionType,
) -> dict[int, int]:
    counts: dict[int, int] = defaultdict(int)
    for r in reactions:
        if r.reaction_type == reaction_type:
            counts[r.original_message_id] += 1
    return dict(counts)


def _to_leaderboard(counts: Counter) -> list[LeaderboardEntry]:
    return [
        LeaderboardEntry(rank=i + 1, participant=participant, count=count)
        for i, (participant, count) in enumerate(counts.most_common())
    ]


def _truncate(text: str, max_length: int) -> str:
    return text if len(text) <= max_length else text[:max_length - 1] + "…"
