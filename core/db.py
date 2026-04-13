"""
db.py — Read-only access to the iMessage SQLite database.

Responsible for:
  - Opening a safe, read-only connection to chat.db
  - Fetching raw rows for a specific group chat
  - Listing available group chats for discovery

Fetches only (read-only). At the boundary we still adjust a few columns for downstream use:
  - Apple epoch → Unix seconds on message dates
  - NULL handle_id → ME_HANDLE_ID for self-sent messages
  - associated_message_guid → normalized to match message.guid (strip bp: / p:n/ prefixes)
"""

import re
import sqlite3
from pathlib import Path
from typing import NamedTuple


CHAT_DB_PATH = Path.home() / "Library" / "Messages" / "chat.db"

# iMessage timestamps are nanoseconds since 2001-01-01 (Apple epoch).
# This offset converts them to standard Unix timestamps.
APPLE_EPOCH_OFFSET_SECONDS = 978307200
ME_HANDLE_ID = -1  # Sentinel that can never collide with SQLite ROWID values.

_PART_INDEX_PREFIX = re.compile(r"^p:\d+/")


def normalize_reaction_target_guid(associated: str | None) -> str:
    """
    Map Apple's association reference to the key stored in message.guid.

    Raw values look like ``bp:<uuid>`` (balloon) or ``p:<n>/<uuid>`` (message part);
    ``message.guid`` is typically the bare suffix only.
    """
    if not associated:
        return ""
    s = associated.strip()
    if not s:
        return ""
    if s.startswith("bp:"):
        return s[3:]
    m = _PART_INDEX_PREFIX.match(s)
    if m:
        return s[m.end():]
    return s


class RawMessage(NamedTuple):
    message_id: int
    guid: str
    handle_id: int              # Always an int; self-sent messages use ME_HANDLE_ID.
    text: str | None
    associated_message_type: int
    associated_message_guid: str | None
    date_seconds: float         # Already converted from Apple epoch to Unix


class RawHandle(NamedTuple):
    handle_id: int
    identifier: str             # Phone number or Apple ID


class RawChat(NamedTuple):
    chat_id: int
    guid: str
    display_name: str


def open_readonly_connection(path: Path = CHAT_DB_PATH) -> sqlite3.Connection:
    """Open chat.db in strict read-only mode to prevent any accidental writes."""
    if not path.exists():
        raise FileNotFoundError(
            f"chat.db not found at {path}.\n"
            "Make sure your terminal has Full Disk Access enabled in:\n"
            "  System Settings → Privacy & Security → Full Disk Access"
        )
    uri = f"file:{path}?mode=ro"
    return sqlite3.connect(uri, uri=True)


def fetch_group_chats(conn: sqlite3.Connection) -> list[RawChat]:
    """Return all group chats (chats with more than one participant)."""
    query = """
        SELECT c.ROWID, c.guid, COALESCE(c.display_name, '') AS display_name
        FROM chat c
        INNER JOIN chat_handle_join chj ON chj.chat_id = c.ROWID
        GROUP BY c.ROWID
        HAVING COUNT(DISTINCT chj.handle_id) > 1
        ORDER BY display_name
    """
    rows = conn.execute(query).fetchall()
    return [RawChat(*row) for row in rows]


def fetch_handles_for_chat(conn: sqlite3.Connection, chat_id: int) -> list[RawHandle]:
    """Return all participants (handles) in a given chat via chat_handle_join."""
    query = """
        SELECT h.ROWID, h.id
        FROM handle h
        INNER JOIN chat_handle_join chj ON chj.handle_id = h.ROWID
        WHERE chj.chat_id = ?
    """
    rows = conn.execute(query, (chat_id,)).fetchall()
    return [RawHandle(*row) for row in rows]


def fetch_all_participants_for_chat(
    conn: sqlite3.Connection, chat_id: int,
) -> list[RawHandle]:
    """
    Return every identifier that sent a message in this chat.

    Unlike fetch_handles_for_chat this includes orphan handles (not in
    chat_handle_join) and the local user (is_from_me). The local user
    is returned as RawHandle(ME_HANDLE_ID, "Me").
    """
    query = """
        WITH owner_handles AS (
            SELECT DISTINCT m2.handle_id
            FROM message m2
            INNER JOIN chat_message_join cmj2 ON cmj2.message_id = m2.ROWID
            WHERE cmj2.chat_id = :chat_id AND m2.is_from_me = 1
        )
        SELECT DISTINCT
            CASE WHEN m.is_from_me = 1 OR m.handle_id IN owner_handles
                 THEN :me_handle_id
                 ELSE m.handle_id
            END AS hid,
            CASE WHEN m.is_from_me = 1 OR m.handle_id IN owner_handles
                 THEN 'Me'
                 ELSE COALESCE(h.id, 'Unknown (' || m.handle_id || ')')
            END AS identifier
        FROM message m
        INNER JOIN chat_message_join cmj ON cmj.message_id = m.ROWID
        LEFT JOIN handle h ON h.ROWID = m.handle_id
        WHERE cmj.chat_id = :chat_id
          AND m.handle_id IS NOT NULL
        ORDER BY identifier
    """
    rows = conn.execute(query, {
        "chat_id": chat_id,
        "me_handle_id": ME_HANDLE_ID,
    }).fetchall()
    return [RawHandle(*row) for row in rows]


def fetch_messages_for_chat(conn: sqlite3.Connection, chat_id: int) -> list[RawMessage]:
    """
    Return all messages (both regular and reactions) for a given chat.

    Date conversion: Apple stores dates as nanoseconds since 2001-01-01.
    We divide by 1e9 to get seconds, then add the epoch offset to get Unix time.
    """
    query = """
        SELECT
            m.ROWID,
            m.guid,
            CASE WHEN m.is_from_me = 1 THEN :me_handle_id
                 ELSE COALESCE(m.handle_id, :me_handle_id)
            END AS handle_id,
            m.text,
            m.associated_message_type,
            m.associated_message_guid,
            (m.date / 1000000000.0) + :epoch_offset AS date_seconds
        FROM message m
        INNER JOIN chat_message_join cmj ON cmj.message_id = m.ROWID
        WHERE cmj.chat_id = :chat_id
        ORDER BY m.date ASC
    """
    rows = conn.execute(query, {
        "chat_id": chat_id,
        "epoch_offset": APPLE_EPOCH_OFFSET_SECONDS,
        "me_handle_id": ME_HANDLE_ID,
    }).fetchall()
    return [
        RawMessage(
            message_id=mid,
            guid=guid,
            handle_id=hid,
            text=text,
            associated_message_type=amt,
            associated_message_guid=normalize_reaction_target_guid(aguid) if aguid else None,
            date_seconds=ds,
        )
        for mid, guid, hid, text, amt, aguid, ds in rows
    ]
