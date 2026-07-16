import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path("data/travel_assistant.db")


def save_message(thread_id: str, role: str, content: str) -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            INSERT INTO conversation_messages (thread_id, role, content, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (thread_id, role, content, datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()


def get_recent_messages(thread_id: str, limit: int = 6) -> list[dict]:
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT role, content, created_at
            FROM conversation_messages
            WHERE thread_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (thread_id, limit),
        ).fetchall()

    return [
        {
            "role": row["role"],
            "content": row["content"],
            "created_at": row["created_at"],
        }
        for row in reversed(rows)
    ]