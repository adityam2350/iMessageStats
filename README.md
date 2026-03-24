# iMessage Group Chat Analyzer

Analyze reactions, activity, and "bangers" in an iMessage group chat — all from the command line.

---

## Prerequisites

**macOS only.** This tool reads from `~/Library/Messages/chat.db`.

Your terminal app (Terminal, iTerm2, etc.) must have **Full Disk Access** enabled:

> System Settings → Privacy & Security → Full Disk Access → enable your terminal app

---

## Setup

```bash
/opt/homebrew/bin/python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

---

## Usage

### 1. Discover your group chats

```bash
python main.py --list-chats
```

This prints a table of all group chats with their numeric IDs.

### 2. Analyze a chat

```bash
python main.py --chat-id 42
```

### 3. Limit leaderboard length (optional)

By default every leaderboard lists **all** ranked rows. To cap at e.g. 10 rows per board:

```bash
python main.py --chat-id 42 --top 10
```

### 4. Export leaderboards as JSON

Writes one UTF-8 JSON file with `summary`, `chat_id`, `top_n_applied`, and a `leaderboards` object containing every board (same row cap as `--top` when set):

```bash
python main.py --chat-id 42 --json ./out/leaderboards.json
```

Parent directories are created if needed. RRPM rows include both `count` (stored as hundredths) and `rrpm` (float).

### 5. Merge display names on exported JSON

After exporting, you can fold multiple raw identifiers (phone, email, etc.) into one display name. Counts are summed and ranks recomputed; **RRPM** is recomputed from merged “messages sent” and “reaction receivers” totals.

Mapping file: a JSON object with **string keys and string values** (identifier → name). Identifiers not listed are left as-is.

```bash
python scripts/merge_leaderboard_names.py \
  --leaderboards out/leaderboards.json \
  --mapping mapping.json \
  --out out/leaderboards_merged.json
```

Omit `--out` to print JSON to stdout. The merged document includes `"display_names_merged": true`.

---

## Leaderboards

| Leaderboard | Description |
|---|---|
| 📨 Messages Sent | Who talks the most |
| 🏆 Reaction Receivers | Who gets the most reactions overall |
| 🎁 Reaction Givers | Who gives the most reactions overall |
| 📈 RRPM | Reactions Received Per Message — quality over quantity |
| 😂 HaHas Received | Who gets laughed at the most |
| 😂 Messages with the Most HaHas | Individual messages (3+ HaHas each), ranked by HaHa count; author shown with each line |
| 💥 Bangers | Who authored the most messages that each earned 3+ HaHas |
| ‼️ Emphasizes Received | Who gets the most emphasis reactions |
| ❓ Questions Received | Whose messages generate the most questions |

---

## Running Tests

```bash
python -m pytest -v
```

All tests are pure unit tests — no database or file system required.

---

## Project Structure

```
iMessageStats/
├── main.py          # CLI entry point — wires everything together
├── db.py            # Read-only SQLite access — all queries live here
├── parser.py        # Transforms raw rows into clean domain objects
├── models.py        # Plain data containers shared across the system
├── stats.py         # Leaderboard calculations — pure functions, fully testable
├── display.py       # Rich terminal output — knows nothing about calculations
├── export_json.py   # Optional JSON export for leaderboards
├── merge_display_names.py  # Merge leaderboard rows by display name (used by script below)
├── scripts/
│   └── merge_leaderboard_names.py  # CLI: apply mapping JSON to exported leaderboards
├── tests/
│   ├── test_stats.py
│   ├── test_parser.py
│   ├── test_db.py
│   ├── test_export_json.py
│   └── test_merge_display_names.py
└── requirements.txt
```

`main.py` wires the pipeline together; other modules stay focused on one concern.
