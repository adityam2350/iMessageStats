"""
tests/test_parser.py — Unit tests for raw data parsing logic.

Tests verify that RawMessage rows are correctly classified as messages
vs. reactions, that senders are resolved properly, and that reactions
are correctly linked back to their original message's sender.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from core.db import ME_HANDLE_ID, RawHandle, RawMessage, normalize_reaction_target_guid
from core.models import ReactionType
from core.parser import build_participant_map, parse_messages_and_reactions


# ── Helpers ────────────────────────────────────────────────────────────────────

def make_raw_message(
    message_id: int,
    guid: str,
    handle_id: int,
    text: str | None,
    associated_message_type: int = 0,
    associated_message_guid: str | None = None,
    date_seconds: float = 1700000000.0,
) -> RawMessage:
    return RawMessage(
        message_id=message_id,
        guid=guid,
        handle_id=handle_id,
        text=text,
        associated_message_type=associated_message_type,
        associated_message_guid=associated_message_guid,
        date_seconds=date_seconds,
    )


# ── Participant Map ────────────────────────────────────────────────────────────

def test_build_participant_map():
    handles = [
        RawHandle(handle_id=1, identifier="alice@example.com"),
        RawHandle(handle_id=2, identifier="+15551234567"),
    ]
    participant_map = build_participant_map(handles)
    assert participant_map[ME_HANDLE_ID].identifier == "Me"
    assert participant_map[1].identifier == "alice@example.com"
    assert participant_map[2].identifier == "+15551234567"


# ── Message Parsing ────────────────────────────────────────────────────────────

def test_regular_message_is_parsed():
    handles = [RawHandle(1, "alice@example.com")]
    participant_map = build_participant_map(handles)

    raw = [make_raw_message(
        message_id=1, guid="guid-1", handle_id=1,
        text="Hello!", associated_message_type=0,
    )]
    messages, reactions = parse_messages_and_reactions(raw, participant_map)

    assert len(messages) == 1
    assert messages[0].text == "Hello!"
    assert messages[0].sender.identifier == "alice@example.com"
    assert len(reactions) == 0


def test_message_with_me_handle_id_resolves_to_me():
    participant_map = build_participant_map([])
    raw = [make_raw_message(
        message_id=1, guid="guid-1", handle_id=ME_HANDLE_ID,
        text="Sent by me", associated_message_type=0,
    )]
    messages, _ = parse_messages_and_reactions(raw, participant_map)
    assert messages[0].sender.identifier == "Me"


def test_empty_text_messages_are_skipped():
    raw = [make_raw_message(
        message_id=1, guid="guid-1", handle_id=ME_HANDLE_ID,
        text=None, associated_message_type=0,
    )]
    messages, _ = parse_messages_and_reactions(raw, {})
    assert len(messages) == 0


# ── Reaction Parsing ───────────────────────────────────────────────────────────

def test_reaction_links_to_original_sender_with_bp_prefix():
    handles = [
        RawHandle(1, "alice@example.com"),
        RawHandle(2, "bob@example.com"),
    ]
    participant_map = build_participant_map(handles)
    msg_uuid = "AAAABBBB-CCCC-DDDD-EEEE-FFFFFFFFFFFF"

    original = make_raw_message(
        message_id=1, guid=msg_uuid, handle_id=1,
        text="link preview", associated_message_type=0,
    )
    reaction = make_raw_message(
        message_id=2, guid="reaction-guid-2", handle_id=2,
        text="Loved an image",
        associated_message_type=ReactionType.HEART,
        associated_message_guid=normalize_reaction_target_guid(f"bp:{msg_uuid}"),
    )

    messages, reactions = parse_messages_and_reactions([original, reaction], participant_map)

    assert len(messages) == 1
    assert len(reactions) == 1
    assert reactions[0].reactor.identifier == "bob@example.com"
    assert reactions[0].recipient.identifier == "alice@example.com"
    assert reactions[0].reaction_type == ReactionType.HEART


def test_reaction_links_to_original_sender_with_p0_prefix():
    handles = [
        RawHandle(1, "alice@example.com"),
        RawHandle(2, "bob@example.com"),
    ]
    participant_map = build_participant_map(handles)
    msg_uuid = "11112222-3333-4444-5555-666666666666"

    original = make_raw_message(
        message_id=1, guid=msg_uuid, handle_id=1,
        text="plain text", associated_message_type=0,
    )
    reaction = make_raw_message(
        message_id=2, guid="reaction-guid-2", handle_id=2,
        text='Laughed at "plain text"',
        associated_message_type=ReactionType.HAHA,
        associated_message_guid=normalize_reaction_target_guid(f"p:0/{msg_uuid}"),
    )

    messages, reactions = parse_messages_and_reactions([original, reaction], participant_map)

    assert len(messages) == 1
    assert len(reactions) == 1
    assert reactions[0].reactor.identifier == "bob@example.com"
    assert reactions[0].recipient.identifier == "alice@example.com"
    assert reactions[0].reaction_type == ReactionType.HAHA


def test_reaction_links_to_original_sender():
    handles = [
        RawHandle(1, "alice@example.com"),
        RawHandle(2, "bob@example.com"),
    ]
    participant_map = build_participant_map(handles)

    # Alice sends a message with guid "guid-1"
    original = make_raw_message(
        message_id=1, guid="guid-1", handle_id=1,
        text="funny message", associated_message_type=0,
    )
    # Bob reacts with HaHa to Alice's message
    reaction = make_raw_message(
        message_id=2, guid="guid-2", handle_id=2,
        text='Laughed at \u201cfunny message\u201d',
        associated_message_type=ReactionType.HAHA,
        associated_message_guid="guid-1",
    )

    messages, reactions = parse_messages_and_reactions([original, reaction], participant_map)

    assert len(messages) == 1
    assert len(reactions) == 1
    assert reactions[0].reactor.identifier == "bob@example.com"
    assert reactions[0].recipient.identifier == "alice@example.com"
    assert reactions[0].reaction_type == ReactionType.HAHA


def test_reaction_removal_is_discarded():
    handles = [RawHandle(1, "alice@example.com"), RawHandle(2, "bob@example.com")]
    participant_map = build_participant_map(handles)

    original = make_raw_message(1, "guid-1", handle_id=1, text="hi")
    removal = make_raw_message(
        2, "guid-2", handle_id=2, text=None,
        associated_message_type=ReactionType.HAHA + 1000,  # removal type
        associated_message_guid="guid-1",
    )

    _, reactions = parse_messages_and_reactions([original, removal], participant_map)
    assert len(reactions) == 0


def test_reaction_add_then_remove_results_in_no_active_reaction():
    handles = [RawHandle(1, "alice@example.com"), RawHandle(2, "bob@example.com")]
    participant_map = build_participant_map(handles)

    original = make_raw_message(
        1, "guid-1", handle_id=1, text="hi", date_seconds=10.0
    )
    addition = make_raw_message(
        2, "guid-2", handle_id=2, text="Loved “hi”",
        associated_message_type=ReactionType.HEART,
        associated_message_guid="guid-1",
        date_seconds=20.0,
    )
    removal = make_raw_message(
        3, "guid-3", handle_id=2, text=None,
        associated_message_type=ReactionType.HEART + 1000,
        associated_message_guid="guid-1",
        date_seconds=30.0,
    )

    _, reactions = parse_messages_and_reactions(
        [original, addition, removal], participant_map
    )
    assert len(reactions) == 0


def test_reaction_remove_then_add_leaves_reaction_active():
    handles = [RawHandle(1, "alice@example.com"), RawHandle(2, "bob@example.com")]
    participant_map = build_participant_map(handles)

    original = make_raw_message(
        1, "guid-1", handle_id=1, text="hi", date_seconds=10.0
    )
    removal = make_raw_message(
        2, "guid-2", handle_id=2, text=None,
        associated_message_type=ReactionType.HEART + 1000,
        associated_message_guid="guid-1",
        date_seconds=20.0,
    )
    addition = make_raw_message(
        3, "guid-3", handle_id=2, text="Loved “hi”",
        associated_message_type=ReactionType.HEART,
        associated_message_guid="guid-1",
        date_seconds=30.0,
    )

    _, reactions = parse_messages_and_reactions(
        [original, removal, addition], participant_map
    )
    assert len(reactions) == 1
    assert reactions[0].reaction_type == ReactionType.HEART
    assert reactions[0].reactor.identifier == "bob@example.com"
    assert reactions[0].recipient.identifier == "alice@example.com"


def test_reaction_to_unknown_message_is_skipped():
    """If the original message isn't in our dataset, skip the reaction gracefully."""
    handles = [RawHandle(1, "alice@example.com")]
    participant_map = build_participant_map(handles)

    orphaned_reaction = make_raw_message(
        1, "guid-1", handle_id=1, text="Laughed at something",
        associated_message_type=ReactionType.HAHA,
        associated_message_guid="guid-does-not-exist",
    )

    _, reactions = parse_messages_and_reactions([orphaned_reaction], participant_map)
    assert len(reactions) == 0
