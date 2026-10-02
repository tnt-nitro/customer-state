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


def _as_berlin(value):
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=BERLIN)
    return parsed.astimezone(BERLIN)


def list_erfassungen(connection=None):
    close_connection = connection is None
    if connection is None:
        connection = connect()
    try:
        rows = connection.execute(
            """
            SELECT e.id, e.created_at, e.level1, e.level2, l.wert
            FROM erfassungen AS e
            LEFT JOIN erfassung_level3 AS l ON l.erfassung_id = e.id
            ORDER BY e.id, l.id
            """
        ).fetchall()
    finally:
        if close_connection:
            connection.close()

    grouped = {}
    for row_id, created_at, level1, level2, wert in rows:
        entry = grouped.get(row_id)
        if entry is None:
            moment = _as_berlin(created_at)
            entry = {
                "id": row_id,
                "created_at": created_at,
                "date_label": moment.strftime("%d.%m.%Y"),
                "time_label": moment.strftime("%H:%M"),
                "herkunft": level1,
                "interesse": level2,
                "details": [],
                "_moment": moment,
            }
            grouped[row_id] = entry
        if wert is not None:
            entry["details"].append(wert)

    entries = sorted(
        grouped.values(),
        key=lambda entry: (entry["_moment"], entry["id"]),
        reverse=True,
    )
    today = datetime.now(BERLIN).date()
    today_count = sum(1 for entry in entries if entry["_moment"].date() == today)
    for entry in entries:
        del entry["_moment"]

    return {
        "entries": entries,
        "total": len(entries),
        "today": today_count,
    }


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
