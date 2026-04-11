import sqlite3
from config import DB_PATH


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    with get_conn() as conn:
        conn.execute("PRAGMA journal_mode = WAL")
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS guests (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                name          TEXT NOT NULL,
                email         TEXT NOT NULL UNIQUE,
                token         TEXT NOT NULL UNIQUE,
                selfie_path   TEXT NOT NULL,
                embedding     BLOB NOT NULL,
                registered_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                email_sent    INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS wedding_photos (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                filename    TEXT NOT NULL UNIQUE,
                file_path   TEXT NOT NULL,
                uploaded_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                processed   INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS guest_photo_matches (
                id       INTEGER PRIMARY KEY AUTOINCREMENT,
                guest_id INTEGER REFERENCES guests(id),
                photo_id INTEGER REFERENCES wedding_photos(id),
                distance REAL NOT NULL,
                UNIQUE(guest_id, photo_id)
            );
        """)
