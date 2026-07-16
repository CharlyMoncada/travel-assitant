import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path("data/travel_assistant.db")


def save_user_memory(
    thread_id: str,
    memory_key: str,
    memory_value: str,
    category: str | None = None,
) -> None:
    now = datetime.now(timezone.utc).isoformat()

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            INSERT INTO user_memories (
                thread_id, memory_key, memory_value, category, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(thread_id, memory_key)
            DO UPDATE SET
                memory_value = excluded.memory_value,
                category = excluded.category,
                updated_at = excluded.updated_at
            """,
            (thread_id, memory_key, memory_value, category, now, now),
        )
        conn.commit()


def get_user_memories(thread_id: str) -> list[dict]:
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT memory_key, memory_value, category, updated_at
            FROM user_memories
            WHERE thread_id = ?
            ORDER BY updated_at DESC
            """,
            (thread_id,),
        ).fetchall()

    return [
        {
            "memory_key": row["memory_key"],
            "memory_value": row["memory_value"],
            "category": row["category"],
            "updated_at": row["updated_at"],
        }
        for row in rows
    ]


def format_user_memories(thread_id: str) -> str:
    memories = get_user_memories(thread_id)

    if not memories:
        return ""

    lines = []

    for memory in memories:
        key = memory["memory_key"]
        value = memory["memory_value"]
        category = memory["category"] or "general"

        lines.append(f"- {key}: {value} ({category})")

    return "\n".join(lines)