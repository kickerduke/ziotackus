import os
from dataclasses import dataclass
from typing import Optional

import aiosqlite

_SCHEMA = """
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
"""


@dataclass
class LinkRow:
    id: int
    chat_id: int
    normalized_url: str
    original_url: str
    user_id: int
    username: Optional[str]
    first_name: str
    message_id: int
    posted_at: str


@dataclass
class UserStat:
    user_id: int
    username: Optional[str]
    first_name: str
    link_count: int
    duplicate_count: int


async def init_db(db_path: str) -> None:
    os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
    async with aiosqlite.connect(db_path) as db:
        await db.executescript(_SCHEMA)
        await db.commit()


async def find_existing_link(db_path: str, chat_id: int, normalized_url: str) -> Optional[LinkRow]:
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT id, chat_id, normalized_url, original_url, user_id, username, first_name, message_id, posted_at "
            "FROM links WHERE chat_id = ? AND normalized_url = ?",
            (chat_id, normalized_url),
        ) as cursor:
            row = await cursor.fetchone()
            if row is None:
                return None
            return LinkRow(
                id=row["id"],
                chat_id=row["chat_id"],
                normalized_url=row["normalized_url"],
                original_url=row["original_url"],
                user_id=row["user_id"],
                username=row["username"],
                first_name=row["first_name"],
                message_id=row["message_id"],
                posted_at=row["posted_at"],
            )


async def record_link(
    db_path: str,
    chat_id: int,
    normalized_url: str,
    original_url: str,
    user_id: int,
    username: Optional[str],
    first_name: str,
    message_id: int,
    posted_at: str,
    seeded: bool = False,
) -> None:
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            "INSERT OR IGNORE INTO links "
            "(chat_id, normalized_url, original_url, user_id, username, first_name, message_id, posted_at, seeded) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (chat_id, normalized_url, original_url, user_id, username, first_name, message_id, posted_at, int(seeded)),
        )
        await db.commit()


async def record_duplicate(
    db_path: str,
    original_link_id: int,
    chat_id: int,
    user_id: int,
    username: Optional[str],
    first_name: str,
    message_id: int,
    posted_at: str,
) -> None:
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            "INSERT INTO duplicates "
            "(original_link_id, chat_id, user_id, username, first_name, message_id, posted_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (original_link_id, chat_id, user_id, username, first_name, message_id, posted_at),
        )
        await db.commit()


async def get_user_stats(db_path: str, chat_id: int) -> list[UserStat]:
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """
            SELECT
                l.user_id,
                l.username,
                l.first_name,
                COUNT(l.id)                    AS link_count,
                COALESCE(d.duplicate_count, 0) AS duplicate_count
            FROM links l
            LEFT JOIN (
                SELECT user_id, chat_id, COUNT(*) AS duplicate_count
                FROM duplicates
                GROUP BY user_id, chat_id
            ) d ON d.user_id = l.user_id AND d.chat_id = l.chat_id
            WHERE l.chat_id = ?
            GROUP BY l.user_id
            ORDER BY link_count DESC
            """,
            (chat_id,),
        ) as cursor:
            rows = await cursor.fetchall()
            return [
                UserStat(
                    user_id=r["user_id"],
                    username=r["username"],
                    first_name=r["first_name"],
                    link_count=r["link_count"],
                    duplicate_count=r["duplicate_count"],
                )
                for r in rows
            ]


async def get_hall_of_shame(db_path: str, chat_id: int) -> list[UserStat]:
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """
            SELECT
                d.user_id,
                d.username,
                d.first_name,
                COALESCE(l.link_count, 0) AS link_count,
                COUNT(d.id)               AS duplicate_count
            FROM duplicates d
            LEFT JOIN (
                SELECT user_id, chat_id, COUNT(*) AS link_count
                FROM links
                GROUP BY user_id, chat_id
            ) l ON l.user_id = d.user_id AND l.chat_id = d.chat_id
            WHERE d.chat_id = ?
            GROUP BY d.user_id
            HAVING duplicate_count > 0
            ORDER BY duplicate_count DESC
            """,
            (chat_id,),
        ) as cursor:
            rows = await cursor.fetchall()
            return [
                UserStat(
                    user_id=r["user_id"],
                    username=r["username"],
                    first_name=r["first_name"],
                    link_count=r["link_count"],
                    duplicate_count=r["duplicate_count"],
                )
                for r in rows
            ]
