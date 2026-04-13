# iMessage Group Chat Analyzer

Analyze reactions and activity in an iMessage group chat from the command line.

---

## Prerequisites

**macOS only.** This tool reads `~/Library/Messages/chat.db`.

Enable **Full Disk Access** for your terminal app:

**System Settings → Privacy & Security → Full Disk Access** → add Terminal, iTerm2, etc.

---

## Setup

```bash
/opt/homebrew/bin/python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

---

## Two-phase workflow

### Phase 1: Discovery (`discover.py`)

See what chats exist and who is in a chat **before** running analysis.

| Flag | Description |
|------|-------------|
| `--list-chats` | Print a table of all group chats and their numeric IDs. |
| `--list-members` | Print one participant identifier (phone or Apple ID) per line. **Requires** `--chat-id`. |
| `--chat-id <ID>` | Chat to inspect when using `--list-members`. |

```bash
python discover.py --list-chats
python discover.py --list-members --chat-id 42
```

You can combine both flags in one run (chats table first, then members).

### Phase 2: Analysis (`run.py`)

Computes leaderboards from the database, writes **`data/leaderboard.json`**, then prints Rich tables by re-reading that file (unless `--json-only`).

| Flag | Description |
|------|-------------|
| `--chat-id <ID>` | **Required.** Group chat to analyze. |
| `--config <PATH>` | JSON config with your name and identifier mappings. **Default:** `data/config.json` if it exists. |
| `--top <N>` | Max rows per leaderboard in the terminal. **Default: 15.** |
| `--json-only` | Only write `data/leaderboard.json`; do not print tables. |

**Config file** (`data/config.json`):

```json
{
  "me": "Your Name",
  "names": {
    "+15551234567": "Alice",
    "alice@icloud.com": "Alice",
    "bob@example.com": "Bob"
  }
}
```

- `"me"` — your display name. Replaces "Me" in all leaderboards so you don't have to map yourself.
- `"names"` — identifier-to-name mappings. Multiple identifiers mapping to the same name have their counts **merged**, ranks and RRPM recomputed.

Both keys are optional. A legacy flat mapping (no `me`/`names` keys) is also accepted.

### First-time workflow

```bash
# Phase 1: discovery
python discover.py --list-chats
python discover.py --list-members --chat-id 42

# Create data/config.json from the member list output (see format above)

# Phase 2: analysis
ç

# JSON only (e.g. for scripting)
python run.py --chat-id 42 --json-only
```

---

## Leaderboards

| Board | Meaning |
|-------|---------|
| Messages Sent | Who sends the most messages |
| Reaction Receivers / Givers | Who receives or gives the most reactions |
| RRPM | Reactions received per message |
| HaHas Received | Who gets the most HaHa reactions |
| Messages with the Most HaHas | Pretty self-explanatory methinks |
| Bangers | Who has the most messages that each earned 3+ HaHas |
| Emphasizes / Questions Received | Emphasis and question reactions received |

---

## Project layout

```
iMessageStats/
├── discover.py
├── run.py
├── core/
│   ├── db.py
│   ├── parser.py
│   ├── models.py
│   ├── stats.py
│   ├── serializer.py
│   ├── apply_names.py
│   └── print_leaderboard.py
├── data/
│   └── .gitkeep          # JSON outputs are gitignored (data/*.json)
├── scripts/
│   └── clean.py          # remove __pycache__, tool caches (see below)
├── tests/
└── requirements.txt
```

---

## Tests

```bash
python -m pytest -v
```

Unit tests for `stats`, `parser`, `serializer`, and `db` helpers — no real `chat.db` required for most tests.

---

## Clean up bytecode and tool caches

Removes `__pycache__/`, `*.pyc` / `*.pyo`, and (by default) `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/`, `htmlcov/`, etc. Skips `.git` and top-level `.venv` / `venv` / `env`.

```bash
python scripts/clean.py              # delete
python scripts/clean.py --dry-run    # preview
python scripts/clean.py --only-bytecode   # only __pycache__ + .pyc files
```
