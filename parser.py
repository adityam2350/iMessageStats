"""
parser.py — Transforms raw database rows into clean domain objects.

Responsible for:
  - Resolving handle IDs to Participant objects
  - Separating messages from reactions
  - Linking each reaction back to the original message's sender (the recipient)
  - Filtering out reaction removals (3000-series types)

Association GUID prefixes (``bp:``, ``p:n/``) are normalized in ``db.fetch_messages_for_chat``;
``associated_message_guid`` on ``RawMessage`` is already the lookup key for ``message.guid``.
Everything downstream works with clean Message and Reaction objects.
"""

from datetime import datetime, timezone

from db import ME_HANDLE_ID, RawMessage, RawHandle, RawChat
from models import ChatSummary, Message, Participant, Reaction, ReactionType


def build_participant_map(handles: list[RawHandle]) -> dict[int, Participant]:
    """Map handle_id → Participant for quick lookup during parsing."""
    participant_map = {ME_HANDLE_ID: Participant(identifier="Me")}
    participant_map.update(
        {h.handle_id: Participant(identifier=h.identifier) for h in handles}
    )
    return participant_map


def parse_messages_and_reactions(
    raw_messages: list[RawMessage],
    participant_map: dict[int, Participant],
) -> tuple[list[Message], list[Reaction]]:
    """
    Split raw rows into regular messages and reactions.

    Strategy:
      1. First pass: build a guid → Message index from all non-reaction rows.
      2. Second pass: replay reaction add/remove events in chronological order
         to compute the net active reactions.
    """
    messages = _parse_regular_messages(raw_messages, participant_map)
    message_by_guid = {m.guid: m for m in messages}

    reactions = _resolve_net_reactions(raw_messages, participant_map, message_by_guid)

    return messages, reactions


def build_chat_summary(
    chat: RawChat,
    messages: list[Message],
    reactions: list[Reaction],
) -> ChatSummary:
    participants = {m.sender for m in messages} | \
                   {r.reactor for r in reactions} | \
                   {r.recipient for r in reactions}

    timestamps = [m.timestamp for m in messages]

    return ChatSummary(
        display_name=chat.display_name or chat.guid,
        participant_count=len(participants),
        message_count=len(messages),
        reaction_count=len(reactions),
        earliest_message=min(timestamps) if timestamps else None,
        latest_message=max(timestamps) if timestamps else None,
    )


# ── Private helpers ────────────────────────────────────────────────────────────

def _resolve_sender(handle_id: int, participant_map: dict[int, Participant]) -> Participant:
    """Unknown handle IDs (e.g. from deleted contacts) fall back gracefully."""
    return participant_map.get(handle_id, Participant(identifier=f"Unknown ({handle_id})"))


def _to_datetime(unix_timestamp: float) -> datetime:
    return datetime.fromtimestamp(unix_timestamp, tz=timezone.utc)


def _is_reaction_addition(associated_message_type: int) -> bool:
    return associated_message_type in ReactionType.additions()


def _is_reaction_removal(associated_message_type: int) -> bool:
    return associated_message_type in ReactionType.removals()


def _is_regular_message(associated_message_type: int) -> bool:
    return associated_message_type == 0


def _parse_regular_messages(
    raw_messages: list[RawMessage],
    participant_map: dict[int, Participant],
) -> list[Message]:
    messages = []
    for raw in raw_messages:
        if not _is_regular_message(raw.associated_message_type):
            continue
        if not raw.text:
            continue  # Skip empty/attachment-only messages

        messages.append(Message(
            message_id=raw.message_id,
            guid=raw.guid,
            sender=_resolve_sender(raw.handle_id, participant_map),
            text=raw.text.strip(),
            timestamp=_to_datetime(raw.date_seconds),
        ))
    return messages


def _resolve_net_reactions(
    raw_messages: list[RawMessage],
    participant_map: dict[int, Participant],
    message_by_guid: dict[str, Message],
) -> list[Reaction]:
    """
    Build the net active reaction set by replaying additions and removals
    in chronological order. The final state of each unique
    (reactor, message_guid, reaction_type) triple determines whether
    the reaction counts.
    """
    ReactionKey = tuple[Participant, int, ReactionType]
    net: dict[ReactionKey, Reaction | None] = {}

    for raw in sorted(raw_messages, key=lambda r: r.date_seconds):
        if not (
            _is_reaction_addition(raw.associated_message_type)
            or _is_reaction_removal(raw.associated_message_type)
        ):
            continue

        original_message = message_by_guid.get(raw.associated_message_guid or "")
        if original_message is None:
            continue  # Reaction targets a message we don't have (e.g. deleted)

        reactor = _resolve_sender(raw.handle_id, participant_map)
        base_reaction_type = (
            raw.associated_message_type
            if _is_reaction_addition(raw.associated_message_type)
            else raw.associated_message_type - 1000
        )
        reaction_type = ReactionType(base_reaction_type)
        key: ReactionKey = (reactor, original_message.message_id, reaction_type)

        if _is_reaction_addition(raw.associated_message_type):
            net[key] = Reaction(
                reactor=reactor,
                recipient=original_message.sender,
                reaction_type=reaction_type,
                original_message_id=original_message.message_id,
            )
        else:
            net[key] = None

    return [reaction for reaction in net.values() if reaction is not None]
