#!/usr/bin/env python3
"""
Merge participant identifiers to display names in leaderboard JSON.

Reads the file produced by:  python main.py --chat-id N --json out.json
and a mapping JSON object (string keys → string values). Writes merged JSON.

Example mapping.json:
  {
    "+15551234567": "Alice",
    "alice@icloud.com": "Alice",
    "bob@example.com": "Bob"
  }

Unmapped identifiers are left unchanged. Multiple raw IDs mapping to the same
name have counts summed and ranks recomputed (RRPM uses merged totals).

Usage:
  python scripts/merge_leaderboard_names.py \\
    --leaderboards out/leaderboards.json \\
    --mapping mapping.json \\
    --out out/leaderboards_merged.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import click

import merge_display_names as mdn


def _validate_mapping(obj: object) -> dict[str, str]:
    if not isinstance(obj, dict):
        raise click.ClickException("mapping JSON must be a JSON object (string → string).")
    out: dict[str, str] = {}
    for k, v in obj.items():
        if not isinstance(k, str) or not isinstance(v, str):
            raise click.ClickException(
                "mapping JSON must use only string keys and string values."
            )
        out[k] = v
    return out


@click.command()
@click.option(
    "--leaderboards",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    required=True,
    help="Leaderboards JSON from main.py --json",
)
@click.option(
    "--mapping",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    required=True,
    help="JSON object: participant identifier → display name",
)
@click.option(
    "--out",
    type=click.Path(dir_okay=False, path_type=Path),
    default=None,
    help="Write result here (default: print to stdout)",
)
def cli(leaderboards: Path, mapping: Path, out: Path | None) -> None:
    doc = json.loads(leaderboards.read_text(encoding="utf-8"))
    raw_map = json.loads(mapping.read_text(encoding="utf-8"))
    m = _validate_mapping(raw_map)
    merged = mdn.apply_participant_mapping(doc, m)
    text = json.dumps(merged, indent=2, ensure_ascii=False) + "\n"
    if out is not None:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8")
    else:
        click.echo(text, nl=False)


if __name__ == "__main__":
    cli()
