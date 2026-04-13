#!/usr/bin/env python3
"""
discover.py — List group chats and chat members (discovery phase).
"""

from __future__ import annotations

import sys

import click
from rich import box
from rich.console import Console
from rich.table import Table

import core.db as db

console = Console()


@click.command()
@click.option(
    "--list-chats",
    is_flag=True,
    help="Print all group chats and their numeric IDs, then exit.",
)
@click.option(
    "--list-members",
    is_flag=True,
    help="Print one participant identifier per line for the given chat.",
)
@click.option(
    "--chat-id",
    type=int,
    default=None,
    help="Required with --list-members: which chat to inspect.",
)
def main(list_chats: bool, list_members: bool, chat_id: int | None) -> None:
    if not list_chats and not list_members:
        raise click.UsageError("Specify --list-chats and/or --list-members.")
    if list_members and chat_id is None:
        raise click.UsageError("--list-members requires --chat-id <ID>.")

    try:
        conn = db.open_readonly_connection()
    except FileNotFoundError as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        sys.exit(1)

    with conn:
        if list_chats:
            chats = db.fetch_group_chats(conn)
            table = Table(
                title="Available Group Chats",
                box=box.SIMPLE_HEAD,
                title_style="bold white",
                header_style="dim",
            )
            table.add_column("ID", style="dim", width=6, justify="right")
            table.add_column("Name / GUID")
            for chat in chats:
                name = chat.display_name or f"[dim]{chat.guid}[/dim]"
                table.add_row(str(chat.chat_id), name)
            console.print(table)
            console.print(
                "\nUse [bold cyan]python run.py --chat-id <ID>[/bold cyan] to analyze a chat."
            )

        if list_members:
            handles = db.fetch_all_participants_for_chat(conn, chat_id)
            for h in handles:
                console.print(h.identifier)


if __name__ == "__main__":
    main()
