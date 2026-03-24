"""
models.py — Core domain objects for the iMessage analyzer.

These are plain data containers. No logic lives here.
They are the shared language between parsing, stats, and display.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import IntEnum


class ReactionType(IntEnum):
    """
    iMessage reaction types as stored in associated_message_type.
    The 2000-series are additions; 3000-series are removals of the same reaction.
    """
    HEART      = 2000
    THUMBS_UP  = 2001
    THUMBS_DOWN = 2002
    HAHA       = 2003
    EMPHASIZE  = 2004
    QUESTION   = 2005

    @classmethod
    def additions(cls) -> set[int]:
        return {r.value for r in cls}

    @classmethod
    def removals(cls) -> set[int]:
        return {r.value + 1000 for r in cls}

    @property
    def emoji(self) -> str:
        return {
            ReactionType.HEART:       "❤️",
            ReactionType.THUMBS_UP:   "👍",
            ReactionType.THUMBS_DOWN: "👎",
            ReactionType.HAHA:        "😂",
            ReactionType.EMPHASIZE:   "‼️",
            ReactionType.QUESTION:    "❓",
        }[self]

    @property
    def label(self) -> str:
        return {
            ReactionType.HEART:       "Hearts",
            ReactionType.THUMBS_UP:   "Thumbs Up",
            ReactionType.THUMBS_DOWN: "Thumbs Down",
            ReactionType.HAHA:        "HaHas",
            ReactionType.EMPHASIZE:   "Emphasizes",
            ReactionType.QUESTION:    "Questions",
        }[self]


@dataclass(frozen=True)
class Participant:
    """A person in the group chat, identified by their handle or as the local user."""
    identifier: str     # Phone number, Apple ID, or "Me"

    @property
    def display_name(self) -> str:
        return self.identifier


@dataclass(frozen=True)
class Message:
    """A regular (non-reaction) message sent in the chat."""
    message_id: int
    guid: str
    sender: Participant
    text: str
    timestamp: datetime


@dataclass(frozen=True)
class Reaction:
    """
    A single reaction event — who reacted, to whose message, and with what.

    reactor:   the person who gave the reaction
    recipient: the person who sent the original message being reacted to
    """
    reactor: Participant
    recipient: Participant
    reaction_type: ReactionType
    original_message_id: int


@dataclass
class ChatSummary:
    """Metadata about the loaded chat, shown in the output header."""
    display_name: str
    participant_count: int
    message_count: int
    reaction_count: int
    earliest_message: datetime | None
    latest_message: datetime | None
