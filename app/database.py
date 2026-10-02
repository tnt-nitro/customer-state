import sqlite3
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

BERLIN = ZoneInfo("Europe/Berlin")

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "customer_state.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS erfassungen (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    level1 TEXT NOT NULL,
    level2 TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS erfassung_level3 (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    erfassung_id INTEGER NOT NULL,
    wert TEXT NOT NULL,
    FOREIGN KEY (erfassung_id) REFERENCES erfassungen(id) ON DELETE CASCADE
);
"""


def connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def init_db():
    with connect() as connection:
        connection.executescript(_SCHEMA)


def berlin_timestamp():
    return datetime.now(BERLIN).isoformat(sep=" ", timespec="seconds")


def save_erfassung(level1, level2, level3):
    connection = connect()
    try:
        cursor = connection.execute(
            "INSERT INTO erfassungen (created_at, level1, level2) VALUES (?, ?, ?)",
            (berlin_timestamp(), level1, level2),
        )
        erfassung_id = cursor.lastrowid
        connection.executemany(
            "INSERT INTO erfassung_level3 (erfassung_id, wert) VALUES (?, ?)",
            [(erfassung_id, wert) for wert in level3],
        )
        connection.commit()
        return erfassung_id
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()
