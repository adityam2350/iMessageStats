#!/usr/bin/env python3
"""
run.py — Analyze a group chat: compute leaderboards, write data/leaderboard.json,
and print tables (unless --json-only).
"""

from __future__ import annotations

import sys
from pathlib import Path

import click
from rich.console import Console

import core.apply_names as apply_names
import core.db as db
import core.parser as parser
import core.print_leaderboard as print_leaderboard
import core.serializer as serializer
import core.stats as stats

ROOT = Path(__file__).resolve().parent
DEFAULT_LEADERBOARD_JSON = ROOT / "data" / "leaderboard.json"

console = Console()


def _analyze(conn, chat_id: int):
    raw_chats = db.fetch_group_chats(conn)
    chat = next((c for c in raw_chats if c.chat_id == chat_id), None)
    if chat is None:
        return None

    raw_handles = db.fetch_handles_for_chat(conn, chat_id)
    raw_messages = db.fetch_messages_for_chat(conn, chat_id)
    participant_map = parser.build_participant_map(raw_handles)
    messages, reactions = parser.parse_messages_and_reactions(raw_messages, participant_map)
    summary = parser.build_chat_summary(chat, messages, reactions)

    all_stats = {
        "messages_sent": stats.messages_sent_leaderboard(messages),
        "reaction_receivers": stats.reaction_receivers_leaderboard(reactions),
        "reaction_givers": stats.reaction_givers_leaderboard(reactions),
        "rrpm": stats.rrpm_leaderboard(messages, reactions),
        "hahas_received": stats.hahas_received_leaderboard(reactions),
        "most_haha_messages": stats.most_haha_messages_leaderboard(messages, reactions),
        "bangers": stats.bangers_leaderboard(messages, reactions),
        "emphasizes_received": stats.emphasizes_received_leaderboard(reactions),
        "questions_received": stats.questions_received_leaderboard(reactions),
    }
    return chat_id, summary, all_stats


@click.command()
@click.option("--chat-id", type=int, required=True, help="Group chat ID from discover.py.")
@click.option(
    "--names",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    default=None,
    help="Optional JSON file mapping identifiers to display names.",
)
@click.option(
    "--top",
    type=int,
    default=5,
    show_default=True,
    help="How many rows to show per leaderboard in the terminal.",
)
@click.option(
    "--json-only",
    is_flag=True,
    help="Only write data/leaderboard.json; do not print tables.",
)
def main(
    chat_id: int,
    names: Path | None,
    top: int,
    json_only: bool,
) -> None:
    try:
        conn = db.open_readonly_connection()
    except FileNotFoundError as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        sys.exit(1)

    with conn:
        result = _analyze(conn, chat_id)

    if result is None:
        console.print(
            f"[bold red]Error:[/bold red] No group chat found with ID {chat_id}. "
            "Use [cyan]python discover.py --list-chats[/cyan]."
        )
        sys.exit(1)

    cid, summary, all_stats = result
    doc = serializer.to_dict(cid, summary, all_stats, display_top_n=top)
    if names is not None:
        doc = apply_names.apply_names_file(doc, names)
    serializer.write_json(doc, DEFAULT_LEADERBOARD_JSON)

    if not json_only:
        print_leaderboard.render_leaderboard_file(DEFAULT_LEADERBOARD_JSON, top_n=top)


if __name__ == "__main__":
    main()
