from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker

BASE_DIR = Path(__file__).resolve().parents[3]
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "travel_assistant.db"
DATABASE_URL = f"sqlite:///{DB_PATH.as_posix()}"

# If the expected SQLite path exists as a directory, handle it gracefully.
if DB_PATH.exists() and DB_PATH.is_dir():
    if any(DB_PATH.iterdir()):
        raise RuntimeError(
            f"Expected SQLite database file at {DB_PATH}, but a non-empty directory exists. "
            "Please remove or rename it before starting the application."
        )
    DB_PATH.rmdir()

DATA_DIR.mkdir(parents=True, exist_ok=True)

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
Base = declarative_base()


def init_db():
    Base.metadata.create_all(bind=engine)

    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS conversation_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                thread_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """))

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS user_memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                thread_id TEXT NOT NULL,
                memory_key TEXT NOT NULL,
                memory_value TEXT NOT NULL,
                category TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(thread_id, memory_key)
            )
        """))