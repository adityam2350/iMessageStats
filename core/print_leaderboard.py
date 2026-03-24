"""
print_leaderboard.py — Render a validated leaderboard JSON document to the terminal.

Reads JSON via serializer, converts rows to domain entry types, and prints Rich tables.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from rich import box
from rich.columns import Columns
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from core.models import ChatSummary, Participant, ReactionType
from core.serializer import from_dict, read_json
from core.stats import BangerEntry, LeaderboardEntry

console = Console()
RANK_MEDALS = {1: "🥇", 2: "🥈", 3: "🥉"}


def _leaderboard_slice(entries: list, top_n: int | None) -> list:
    if top_n is None:
        return entries
    return entries[:top_n]


def _format_date_range(earliest: datetime | None, latest: datetime | None) -> str:
    if not earliest or not latest:
        return "No messages"
    fmt = "%b %Y"
    if earliest.month == latest.month and earliest.year == latest.year:
        return earliest.strftime(fmt)
    return f"{earliest.strftime(fmt)} – {latest.strftime(fmt)}"


def print_chat_summary(summary: ChatSummary) -> None:
    date_range = _format_date_range(summary.earliest_message, summary.latest_message)
    content = (
        f"[bold]{summary.display_name}[/bold]\n"
        f"[dim]{summary.participant_count} participants  ·  "
        f"{summary.message_count:,} messages  ·  "
        f"{summary.reaction_count:,} reactions  ·  "
        f"{date_range}[/dim]"
    )
    console.print(Panel(content, title="📱 iMessage Group Chat Analyzer", border_style="cyan"))
    console.print()


def print_leaderboard(
    title: str,
    emoji: str,
    entries: list[LeaderboardEntry],
    top_n: int | None = None,
    value_label: str = "",
    value_formatter: Callable[[int], str] = str,
) -> Table:
    table = Table(
        title=f"{emoji} {title}",
        box=box.SIMPLE_HEAD,
        title_style="bold white",
        header_style="dim",
        show_footer=False,
        expand=False,
    )
    table.add_column("#", style="dim", width=3, justify="right")
    table.add_column("Participant", min_width=16)
    table.add_column(value_label or "Count", justify="right", style="cyan bold")

    shown = _leaderboard_slice(entries, top_n)
    if not shown:
        table.add_row("—", "[dim]No data[/dim]", "—")
    else:
        for entry in shown:
            medal = RANK_MEDALS.get(entry.rank, str(entry.rank))
            table.add_row(
                medal,
                entry.participant.display_name,
                value_formatter(entry.count),
            )

    return table


def print_most_haha_messages_table(entries: list[BangerEntry], top_n: int | None = None) -> Table:
    table = Table(
        title="😂 Messages with the Most HaHas",
        box=box.SIMPLE_HEAD,
        title_style="bold white",
        header_style="dim",
        show_footer=False,
        expand=True,
    )
    table.add_column("#", style="dim", width=3, justify="right")
    table.add_column("Author & message", min_width=40)
    table.add_column("😂", justify="right", style="cyan bold", width=5)

    shown = _leaderboard_slice(entries, top_n)
    if not shown:
        table.add_row("—", "[dim]No data[/dim]", "—")
    else:
        for entry in shown:
            medal = RANK_MEDALS.get(entry.rank, str(entry.rank))
            author = entry.sender.display_name
            body = f'[bold]{author}[/bold]  [italic]"{entry.text}"[/italic]'
            table.add_row(medal, body, str(entry.haha_count))

    return table


def print_all_leaderboards(
    messages_sent: list[LeaderboardEntry],
    reaction_receivers: list[LeaderboardEntry],
    reaction_givers: list[LeaderboardEntry],
    rrpm: list[LeaderboardEntry],
    hahas_received: list[LeaderboardEntry],
    most_haha_messages: list[BangerEntry],
    bangers: list[LeaderboardEntry],
    emphasizes_received: list[LeaderboardEntry],
    questions_received: list[LeaderboardEntry],
    top_n: int | None = None,
) -> None:
    def rrpm_formatter(count: int) -> str:
        return f"{count / 100:.2f}"

    table_messages = print_leaderboard(
        "Messages Sent", "📨", messages_sent, top_n, value_label="Messages"
    )
    table_receivers = print_leaderboard(
        "Reaction Receivers", "🏆", reaction_receivers, top_n
    )
    table_givers = print_leaderboard(
        "Reaction Givers", "🎁", reaction_givers, top_n
    )
    table_rrpm = print_leaderboard(
        "RRPM", "📈", rrpm, top_n,
        value_label="Per Msg",
        value_formatter=rrpm_formatter,
    )
    table_hahas = print_leaderboard(
        "HaHas Received", "😂", hahas_received, top_n,
        value_label=ReactionType.HAHA.label,
    )
    table_emphasizes = print_leaderboard(
        "Emphasizes Received", "‼️ ", emphasizes_received, top_n,
        value_label=ReactionType.EMPHASIZE.label,
    )
    table_questions = print_leaderboard(
        "Questions Received", "❓", questions_received, top_n,
        value_label=ReactionType.QUESTION.label,
    )
    table_most_hahas = print_most_haha_messages_table(most_haha_messages, top_n)
    table_bangers = print_leaderboard(
        "Bangers", "💥", bangers, top_n,
        value_label="Msgs w/ 3+ 😂",
    )

    console.print(Columns([table_messages, table_receivers]))
    console.print(Columns([table_givers, table_rrpm]))
    console.print(Columns([table_hahas, table_emphasizes]))
    console.print(table_questions)
    console.print()
    console.print(table_most_hahas)
    console.print()
    console.print(table_bangers)


def _parse_summary_block(s: object) -> ChatSummary:
    if not isinstance(s, dict):
        s = {}
    def _dt(key: str) -> datetime | None:
        v = s.get(key)
        if not v:
            return None
        return datetime.fromisoformat(str(v))

    return ChatSummary(
        display_name=str(s.get("display_name", "")),
        participant_count=int(s.get("participant_count", 0)),
        message_count=int(s.get("message_count", 0)),
        reaction_count=int(s.get("reaction_count", 0)),
        earliest_message=_dt("earliest_message"),
        latest_message=_dt("latest_message"),
    )


def _rows_to_leaderboard_entries(rows: object) -> list[LeaderboardEntry]:
    if not isinstance(rows, list):
        return []
    out: list[LeaderboardEntry] = []
    for r in rows:
        if not isinstance(r, dict):
            continue
        out.append(
            LeaderboardEntry(
                rank=int(r["rank"]),
                participant=Participant(str(r["participant"])),
                count=int(r["count"]),
            )
        )
    return out


def _rows_to_banger_entries(rows: object) -> list[BangerEntry]:
    if not isinstance(rows, list):
        return []
    out: list[BangerEntry] = []
    for r in rows:
        if not isinstance(r, dict):
            continue
        out.append(
            BangerEntry(
                rank=int(r["rank"]),
                sender=Participant(str(r["sender"])),
                text=str(r.get("text", "")),
                haha_count=int(r["haha_count"]),
            )
        )
    return out


def render_leaderboard_file(path: Path | str, top_n: int | None = 5) -> None:
    """
    Read a leaderboard JSON file from disk, validate it, and print all tables.

    ``top_n`` limits how many rows are shown per leaderboard (``None`` = show all).
    """
    raw = read_json(path)
    doc = from_dict(raw)
    summary = _parse_summary_block(doc.get("summary"))
    lb = doc["leaderboards"]

    print_chat_summary(summary)
    print_all_leaderboards(
        messages_sent=_rows_to_leaderboard_entries(lb.get("messages_sent")),
        reaction_receivers=_rows_to_leaderboard_entries(lb.get("reaction_receivers")),
        reaction_givers=_rows_to_leaderboard_entries(lb.get("reaction_givers")),
        rrpm=_rows_to_leaderboard_entries(lb.get("rrpm")),
        hahas_received=_rows_to_leaderboard_entries(lb.get("hahas_received")),
        most_haha_messages=_rows_to_banger_entries(lb.get("most_haha_messages")),
        bangers=_rows_to_leaderboard_entries(lb.get("bangers")),
        emphasizes_received=_rows_to_leaderboard_entries(lb.get("emphasizes_received")),
        questions_received=_rows_to_leaderboard_entries(lb.get("questions_received")),
        top_n=top_n,
    )
