import sqlite3
from pathlib import Path

DB_PATH = Path("travel_assistant.db")
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Query messages in the database
cursor.execute(
    "SELECT id, thread_id, role, content, created_at FROM conversation_messages WHERE thread_id = '8226067620' ORDER BY id ASC"
)
rows = cursor.fetchall()

print("=== MESSAGES IN DB FOR THREAD 8226067620 ===")
for r in rows:
    print(f"ID: {r[0]} | Role: {r[2]} | Content: '{r[3][:100].strip().replace('\n', ' ')}...' | CreatedAt: {r[4]}")
