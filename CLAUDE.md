# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Environment

Python project with a local virtual environment at `.venv/`. Activate it before running anything:

```bash
# Windows
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the bot locally (requires .env with BOT_TOKEN and ALLOWED_CHAT_ID)
python main.py
```

## Architecture

The bot uses `python-telegram-bot` v20+ (async) with `aiosqlite` for SQLite persistence.

```
bot/
├── app.py          — builds ApplicationBuilder, registers all handlers, starts polling
├── config.py       — Config dataclass populated from env vars; fails fast if BOT_TOKEN or ALLOWED_CHAT_ID missing
├── database.py     — all SQL lives here: init_db, find_existing_link, record_link, record_duplicate, get_user_stats, get_hall_of_shame
├── normalizer.py   — extract_and_normalize_urls(text) → list[tuple[original, normalized]]
├── messages.py     — shame message pool, pick_shame_message(), display_name(), format_time_ago()
└── handlers/
    ├── filters.py  — AllowedChatFilter: gates all handlers to ALLOWED_CHAT_ID
    ├── message.py  — core loop: extract URLs → find_existing_link → shame+record_duplicate OR record_link
    ├── commands.py — /start /stats /hall_of_shame
    └── member.py   — sends welcome message when bot is added to the group
```

`seed_from_export.py` is a standalone CLI script (uses sync `sqlite3`, not aiosqlite) for importing a Telegram Desktop JSON export into the database before the bot starts.

### Core data flow

1. Message arrives → `AllowedChatFilter` rejects any chat not matching `ALLOWED_CHAT_ID`
2. `normalizer.extract_and_normalize_urls` extracts `(original_url, normalized_url)` pairs
3. For each pair: `database.find_existing_link` checks the `links` table by `(chat_id, normalized_url)`
4. If found → reply with random shame message + `record_duplicate` in `duplicates` table; stop after first duplicate per message
5. If not found → `record_link` in `links` table

### Database schema

Two tables: `links` (first occurrence, UNIQUE on `chat_id + normalized_url`) and `duplicates` (each repost). Stats are derived by LEFT JOINing them per user.

### URL normalization strategy

Each platform has a dedicated normalizer in `bot/normalizer.py`:
- **YouTube**: extracts bare video ID → `https://www.youtube.com/watch?v={id}` (handles youtu.be, shorts, embed, m.youtube.com, extra query params)
- **Instagram**: extracts content type + ID → `https://www.instagram.com/{type}/{id}/`
- **Facebook**: structured extraction for watch/videos/photo/permalink; `fb.watch` short links kept as-is
- **9gag**: extracts gag ID → `https://9gag.com/gag/{id}`
- **Fallback**: normalizes scheme to https, lowercases domain, strips known tracking params (utm_*, fbclid, gclid, igshid…), sorts remaining query params

## Docker

```bash
# Build and start
docker compose up -d --build

# Logs
docker compose logs -f
```

Requires a `.env` file (copy from `.env.example`). The SQLite database is persisted in a named Docker volume (`db_data`).
