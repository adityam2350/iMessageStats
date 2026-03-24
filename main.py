"""
main.py — CLI entry point for the iMessage Group Chat Analyzer.

This module is the composition root. Its only job is to:
  1. Parse command-line arguments
  2. Coordinate the pipeline: db → parser → stats → display
  3. Handle top-level errors gracefully

No business logic lives here. It only wires the other modules together.

Usage:
  python main.py --list-chats
  python main.py --chat-id 42
  python main.py --chat-id 42 --top 10   # optional cap per leaderboard
  python main.py --chat-id 42 --json out/leaderboards.json
"""

import sys
from pathlib import Path

import click

import db
import display
import export_json
import parser
import stats


@click.command()
@click.option(
    "--chat-id",
    type=int,
    default=None,
    help="The numeric ID of the group chat to analyze. Use --list-chats to discover IDs.",
)
@click.option(
    "--list-chats",
    is_flag=True,
    default=False,
    help="List all available group chats and their IDs, then exit.",
)
@click.option(
    "--top",
    type=int,
    default=None,
    help="Cap how many rows each leaderboard shows (default: show all).",
)
@click.option(
    "--json",
    "json_out",
    type=click.Path(dir_okay=False, writable=True, path_type=Path),
    default=None,
    help="Write chat summary and all leaderboards to this JSON file (UTF-8).",
)
def main(
    chat_id: int | None,
    list_chats: bool,
    top: int | None,
    json_out: Path | None,
) -> None:
    """Analyze reactions and activity in an iMessage group chat."""
    try:
        conn = db.open_readonly_connection()
    except FileNotFoundError as e:
        display.print_error(str(e))
        sys.exit(1)

    with conn:
        if list_chats:
            chats = db.fetch_group_chats(conn)
            display.print_chat_picker(chats)
            return

        if chat_id is None:
            display.print_error(
                "Please provide a --chat-id to analyze, or use --list-chats to discover IDs."
            )
            sys.exit(1)

        run_analysis(conn, chat_id=chat_id, top_n=top, json_out=json_out)


def run_analysis(
    conn,
    chat_id: int,
    top_n: int | None = None,
    json_out: Path | None = None,
) -> None:
    """
    Full analysis pipeline for a single group chat.

    Pipeline:
      1. Fetch raw rows from the database
      2. Parse into clean domain objects
      3. Compute all leaderboards
      4. Display results
    """
    # ── 1. Fetch ───────────────────────────────────────────────────────────────
    raw_chats = db.fetch_group_chats(conn)
    chat = next((c for c in raw_chats if c.chat_id == chat_id), None)
    if chat is None:
        display.print_error(f"No group chat found with ID {chat_id}. Use --list-chats to browse.")
        sys.exit(1)

    raw_handles = db.fetch_handles_for_chat(conn, chat_id)
    raw_messages = db.fetch_messages_for_chat(conn, chat_id)

    # ── 2. Parse ───────────────────────────────────────────────────────────────
    participant_map = parser.build_participant_map(raw_handles)
    messages, reactions = parser.parse_messages_and_reactions(raw_messages, participant_map)
    summary = parser.build_chat_summary(chat, messages, reactions)

    # ── 3. Stats ───────────────────────────────────────────────────────────────
    all_stats = {
        "messages_sent":        stats.messages_sent_leaderboard(messages),
        "reaction_receivers":   stats.reaction_receivers_leaderboard(reactions),
        "reaction_givers":      stats.reaction_givers_leaderboard(reactions),
        "rrpm":                 stats.rrpm_leaderboard(messages, reactions),
        "hahas_received":       stats.hahas_received_leaderboard(reactions),
        "most_haha_messages":   stats.most_haha_messages_leaderboard(messages, reactions),
        "bangers":              stats.bangers_leaderboard(messages, reactions),
        "emphasizes_received":  stats.emphasizes_received_leaderboard(reactions),
        "questions_received":   stats.questions_received_leaderboard(reactions),
    }

    # ── 4. Display ─────────────────────────────────────────────────────────────
    display.print_chat_summary(summary)
    display.print_all_leaderboards(**all_stats, top_n=top_n)

    if json_out is not None:
        export_json.write_leaderboards_json(
            json_out,
            chat_id=chat_id,
            summary=summary,
            all_stats=all_stats,
            top_n=top_n,
        )


if __name__ == "__main__":
    main()
