"""
display.py — Terminal output using the Rich library.

Responsible for:
  - Rendering leaderboards as styled tables
  - Formatting the summary header
  - Formatting the chat picker list

This module knows nothing about how stats are calculated.
It only knows how to display data it receives.
"""

from datetime import datetime, timezone

from rich import box
from rich.columns import Columns
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from models import ChatSummary, ReactionType
from stats import BangerEntry, LeaderboardEntry


console = Console()

RANK_MEDALS = {1: "🥇", 2: "🥈", 3: "🥉"}


def _leaderboard_slice(entries: list, top_n: int | None) -> list:
    """All entries when top_n is None; otherwise first top_n rows."""
    if top_n is None:
        return entries
    return entries[:top_n]


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
    value_formatter: callable = str,
) -> Table:
    """
    Render a generic leaderboard table.

    value_formatter lets callers control how the count is displayed,
    e.g. for RRPM which should display as a decimal rather than an integer.
    """
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
    """Messages with the most HaHas (3+); author shown with each quote."""
    table = Table(
        title="😂 Messages with the Most HaHas  (3+ per message)",
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
    """
    Print all leaderboards in a two-column layout where possible,
    with wide tables for message-level HaHa leaders and participant bangers.
    """
    def rrpm_formatter(count: int) -> str:
        # RRPM is stored as count × 100 for integer storage; reverse here for display.
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


def print_chat_picker(chats: list) -> None:
    """Display available group chats for the user to choose from."""
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
    console.print("\nUse [bold cyan]--chat-id <ID>[/bold cyan] to analyze a chat.")


def print_error(message: str) -> None:
    console.print(f"\n[bold red]Error:[/bold red] {message}\n")


# ── Private helpers ────────────────────────────────────────────────────────────

def _format_date_range(earliest: datetime | None, latest: datetime | None) -> str:
    if not earliest or not latest:
        return "No messages"
    fmt = "%b %Y"
    if earliest.month == latest.month and earliest.year == latest.year:
        return earliest.strftime(fmt)
    return f"{earliest.strftime(fmt)} – {latest.strftime(fmt)}"
