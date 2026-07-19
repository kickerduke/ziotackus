"""
Seed the ziotackus database from a Telegram chat export JSON file.

Usage:
    python seed_from_export.py --export result.json --chat-id -100xxxxxxxxxx [--db data/ziotackus.db]

How to export:
    Telegram Desktop → Settings → Advanced → Export Telegram data
    → Select the group → Format: JSON → Only messages (no media)
    → Export

The script inserts each unique link as first occurrence (INSERT OR IGNORE).
If the same link appears multiple times in the export, subsequent occurrences
are recorded in the duplicates table.
"""

import argparse
import json
import os
import re
import sqlite3
import sys
from datetime import datetime

from bot.normalizer import extract_and_normalize_urls

_URL_ENTITY_TYPES = {"link", "text_link"}


def _extract_urls_from_message(msg: dict) -> list[tuple[str, str]]:
    """Return (original_url, normalized_url) pairs from a message dict."""
    found: list[tuple[str, str]] = []
    seen_normalized: set[str] = set()

    # Prefer structured text_entities to avoid false positives from regex
    entities = msg.get("text_entities", [])
    raw_urls_from_entities: list[str] = []
    for ent in entities:
        if ent.get("type") in _URL_ENTITY_TYPES:
            url = ent.get("href") or ent.get("text", "")
            if url.startswith("http"):
                raw_urls_from_entities.append(url)

    # Fallback: run normalizer on full text (handles cases with no entity data)
    text = msg.get("text", "")
    if isinstance(text, list):
        # Telegram sometimes exports text as array of segments
        text = "".join(
            seg if isinstance(seg, str) else seg.get("text", "")
            for seg in text
        )

    pairs_from_text = extract_and_normalize_urls(text)

    # Merge: entity-extracted URLs take priority, then text-extracted
    all_raw = raw_urls_from_entities + [orig for orig, _ in pairs_from_text]
    for raw in all_raw:
        pairs = extract_and_normalize_urls(raw)
        for orig, norm in pairs:
            if norm not in seen_normalized:
                seen_normalized.add(norm)
                found.append((orig, norm))

    return found


def _parse_date(date_str: str) -> str:
    """Convert Telegram export date to ISO-8601 UTC string."""
    # Telegram exports dates as "2023-01-15T10:30:00" (no timezone, local time)
    try:
        dt = datetime.fromisoformat(date_str)
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_user_id(from_id: str | int) -> int:
    """Telegram exports user IDs as 'user123456789' strings."""
    if isinstance(from_id, int):
        return from_id
    return int(re.sub(r"^user", "", str(from_id)))


def seed(export_path: str, chat_id: int, db_path: str) -> None:
    with open(export_path, encoding="utf-8") as f:
        data = json.load(f)

    messages = data.get("messages", [])
    if not messages:
        print("No messages found in export.")
        return

    os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    # Ensure schema exists (in case DB is fresh)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS links (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id        INTEGER NOT NULL,
            normalized_url TEXT    NOT NULL,
            original_url   TEXT    NOT NULL,
            user_id        INTEGER NOT NULL,
            username       TEXT,
            first_name     TEXT    NOT NULL,
            message_id     INTEGER NOT NULL,
            posted_at      TEXT    NOT NULL,
            seeded         INTEGER NOT NULL DEFAULT 0
        );
        CREATE UNIQUE INDEX IF NOT EXISTS idx_links_chat_url ON links (chat_id, normalized_url);
        CREATE INDEX        IF NOT EXISTS idx_links_user     ON links (chat_id, user_id);

        CREATE TABLE IF NOT EXISTS duplicates (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            original_link_id INTEGER NOT NULL REFERENCES links(id),
            chat_id          INTEGER NOT NULL,
            user_id          INTEGER NOT NULL,
            username         TEXT,
            first_name       TEXT    NOT NULL,
            message_id       INTEGER NOT NULL,
            posted_at        TEXT    NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_duplicates_user ON duplicates (chat_id, user_id);
    """)
    conn.commit()

    inserted = 0
    duplicates = 0
    skipped = 0

    for msg in messages:
        if msg.get("type") != "message":
            continue

        from_id = msg.get("from_id")
        from_name = msg.get("from") or "Unknown"
        if not from_id:
            skipped += 1
            continue

        try:
            user_id = _parse_user_id(from_id)
        except (ValueError, TypeError):
            skipped += 1
            continue

        msg_id = msg.get("id", 0)
        posted_at = _parse_date(msg.get("date", ""))
        url_pairs = _extract_urls_from_message(msg)

        for original_url, normalized_url in url_pairs:
            existing = conn.execute(
                "SELECT id FROM links WHERE chat_id = ? AND normalized_url = ?",
                (chat_id, normalized_url),
            ).fetchone()

            if existing is None:
                conn.execute(
                    "INSERT OR IGNORE INTO links "
                    "(chat_id, normalized_url, original_url, user_id, username, first_name, message_id, posted_at, seeded) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)",
                    (chat_id, normalized_url, original_url, user_id, None, from_name, msg_id, posted_at),
                )
                inserted += 1
            else:
                conn.execute(
                    "INSERT INTO duplicates "
                    "(original_link_id, chat_id, user_id, username, first_name, message_id, posted_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (existing["id"], chat_id, user_id, None, from_name, msg_id, posted_at),
                )
                duplicates += 1

    conn.commit()
    conn.close()

    print(f"Seeding completato!")
    print(f"  Link unici importati : {inserted}")
    print(f"  Duplicati trovati    : {duplicates}")
    print(f"  Messaggi saltati     : {skipped}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed ziotackus DB from Telegram chat export JSON")
    parser.add_argument("--export", required=True, help="Path to the Telegram export result.json")
    parser.add_argument("--chat-id", required=True, type=int, help="Telegram chat ID (e.g. -100xxxxxxxxxx)")
    parser.add_argument("--db", default="data/ziotackus.db", help="Path to the SQLite database")
    args = parser.parse_args()

    if not os.path.isfile(args.export):
        print(f"Error: export file not found: {args.export}", file=sys.stderr)
        sys.exit(1)

    seed(args.export, args.chat_id, args.db)


if __name__ == "__main__":
    main()
