import sqlite3
from config import DB_PATH


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _migrate(conn):
    """Drop email/email_sent columns from guests if they exist (old schema)."""
    cols = {row[1] for row in conn.execute("PRAGMA table_info(guests)")}
    if "email" in cols:
        conn.executescript("""
            PRAGMA foreign_keys = OFF;
            DROP TABLE IF EXISTS guests_new;
            CREATE TABLE guests_new (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                name          TEXT NOT NULL,
                token         TEXT NOT NULL UNIQUE,
                selfie_path   TEXT NOT NULL,
                embedding     BLOB NOT NULL,
                registered_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            INSERT INTO guests_new (id, name, token, selfie_path, embedding, registered_at)
                SELECT id, name, token, selfie_path, embedding, registered_at FROM guests;
            DROP TABLE guests;
            ALTER TABLE guests_new RENAME TO guests;
            PRAGMA foreign_keys = ON;
        """)


def init_db():
    with get_conn() as conn:
        conn.execute("PRAGMA journal_mode = WAL")
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS guests (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                name          TEXT NOT NULL,
                token         TEXT NOT NULL UNIQUE,
                selfie_path   TEXT NOT NULL,
                embedding     BLOB NOT NULL,
                registered_at DATETIME DEFAULT CURRENT_TIMESTAMP
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
        _migrate(conn)
