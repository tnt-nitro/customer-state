import sqlite3
from collections import Counter
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from app.periods import token_for_day

BERLIN = ZoneInfo("Europe/Berlin")

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "customer_state.db"

LEVEL1_VALUES = (
    "Empfehlung",
    "KI",
    "Google",
    "Leasingportal",
    "Arbeit",
    "Sonstiges",
    "Stammkunde",
)

LEVEL2_VALUES = (
    "MTB",
    "E-MTB",
    "Gravel",
    "E-Gravel",
    "Rennrad",
    "Triathlon",
    "Kinderrad",
    "Lastenrad",
    "Trekking",
    "Trekking vollgefedert",
    "Bekleidung",
    "Zubehör",
)

INTERESTS = {
    "MTB": ["Specialized", "Produkt fehlte", "Leasing", "Kauf", "Reparatur"],
    "E-MTB": ["Specialized", "PIVOT", "AMFLOW", "Produkt fehlte", "Leasing", "Kauf", "Reparatur"],
    "Gravel": ["PIVOT", "Specialized", "Produkt fehlte", "Leasing", "Kauf", "Reparatur"],
    "E-Gravel": ["Specialized", "PIVOT", "Produkt fehlte", "Leasing", "Kauf", "Reparatur"],
    "Rennrad": ["Specialized", "Produkt fehlte"],
    "Triathlon": ["Specialized", "Produkt fehlte"],
    "Kinderrad": ["woom", "Produkt fehlte", "Leasing", "Kauf", "Reparatur"],
    "Lastenrad": ["Riese & Müller", "Produkt fehlte", "Leasing", "Kauf", "Reparatur"],
    "Trekking": ["Riese & Müller", "Specialized", "Produkt fehlte", "Leasing", "Kauf", "Reparatur"],
    "Trekking vollgefedert": [
        "Riese & Müller",
        "Specialized",
        "AMFLOW",
        "Produkt fehlte",
        "Leasing",
        "Kauf",
        "Reparatur",
    ],
    "Bekleidung": [
        "Helm",
        "Trikot",
        "Radhose",
        "Handschuhe",
        "Schuhe",
        "Regenbekleidung",
        "Jacke/Weste",
        "Brille",
        "Sonstiges",
    ],
    "Zubehör": [
        "Luftpumpe",
        "Beleuchtung",
        "Schutzbleche",
        "Schlösser",
        "Griffe",
        "Pflege und Reinigungsprodukte",
    ],
}

WEEKDAY_NAMES = (
    "Montag",
    "Dienstag",
    "Mittwoch",
    "Donnerstag",
    "Freitag",
    "Samstag",
    "Sonntag",
)

MONTH_NAMES = (
    "Januar",
    "Februar",
    "März",
    "April",
    "Mai",
    "Juni",
    "Juli",
    "August",
    "September",
    "Oktober",
    "November",
    "Dezember",
)

# Mo–Fr 10:00–19:00 sind 9 Stunden, Sa 09:00–14:00 sind 5 Stunden, So geschlossen.
OPENING_HOURS = {0: 9, 1: 9, 2: 9, 3: 9, 4: 9, 5: 5, 6: 0}
WEEKDAY_CLOCK_HOURS = tuple(range(10, 19))
SATURDAY_CLOCK_HOURS = tuple(range(9, 14))

_SCHEMA = """
CREATE TABLE IF NOT EXISTS erfassungen (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    is_demo INTEGER NOT NULL DEFAULT 0,
    started_at TEXT,
    level1_completed_at TEXT,
    level2_started_at TEXT,
    level2_completed_at TEXT,
    level3_started_at TEXT,
    completed_at TEXT
);

CREATE TABLE IF NOT EXISTS erfassung_herkunft (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    erfassung_id INTEGER NOT NULL,
    position INTEGER NOT NULL,
    wert TEXT NOT NULL,
    FOREIGN KEY (erfassung_id) REFERENCES erfassungen(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS erfassung_interesse (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    erfassung_id INTEGER NOT NULL,
    position INTEGER NOT NULL,
    wert TEXT NOT NULL,
    FOREIGN KEY (erfassung_id) REFERENCES erfassungen(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS erfassung_detail (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    interesse_id INTEGER NOT NULL,
    position INTEGER NOT NULL,
    wert TEXT NOT NULL,
    FOREIGN KEY (interesse_id) REFERENCES erfassung_interesse(id) ON DELETE CASCADE
);
"""


def connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def _columns(connection, table):
    return [row[1] for row in connection.execute(f"PRAGMA table_info({table})")]


def init_db():
    connection = connect()
    try:
        names = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        if "erfassungen" not in names:
            connection.executescript(_SCHEMA)
        elif "level1" in _columns(connection, "erfassungen"):
            _ensure_demo_flag(connection)
            _migrate_relational(connection)
        _ensure_stage_marks(connection)
        _ensure_korrektur(connection)
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def _ensure_stage_marks(connection):
    columns = _columns(connection, "erfassungen")
    for name in (
        "level2_started_at",
        "level3_started_at",
        "level2_opened_at",
        "level3_opened_at",
    ):
        if name not in columns:
            connection.execute(f"ALTER TABLE erfassungen ADD COLUMN {name} TEXT")


def _ensure_korrektur(connection):
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS korrektur (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            from_level INTEGER NOT NULL,
            to_level INTEGER NOT NULL,
            elapsed_seconds INTEGER NOT NULL,
            had_selection INTEGER NOT NULL
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS korrektur_status (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            korrektur_id INTEGER NOT NULL REFERENCES korrektur(id) ON DELETE CASCADE,
            level INTEGER NOT NULL,
            parent TEXT,
            position INTEGER NOT NULL,
            wert TEXT NOT NULL
        )
        """
    )


def _ensure_demo_flag(connection):
    if "is_demo" in _columns(connection, "erfassungen"):
        return
    connection.execute(
        "ALTER TABLE erfassungen ADD COLUMN is_demo INTEGER NOT NULL DEFAULT 0"
    )
    connection.execute(
        """
        UPDATE erfassungen
        SET is_demo = 1
        WHERE created_at >= '2025-01-01' AND created_at < '2026-01-01'
        """
    )


def _migrate_relational(connection):
    before = {}
    rows = connection.execute(
        """
        SELECT e.id, e.created_at, e.is_demo, e.level1, e.level2, l.wert
        FROM erfassungen AS e
        LEFT JOIN erfassung_level3 AS l ON l.erfassung_id = e.id
        ORDER BY e.id, l.id
        """
    ).fetchall()
    for row_id, created_at, is_demo, level1, level2, wert in rows:
        entry = before.get(row_id)
        if entry is None:
            entry = {
                "created_at": created_at,
                "is_demo": is_demo,
                "level1": level1,
                "level2": level2,
                "details": [],
            }
            before[row_id] = entry
        if wert is not None:
            entry["details"].append(wert)
    if not before:
        raise RuntimeError("Migration abgebrochen: keine Erfassungen gefunden")

    connection.execute("PRAGMA foreign_keys = OFF")
    connection.execute("BEGIN")
    connection.execute(
        """
        CREATE TABLE erfassungen_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            is_demo INTEGER NOT NULL DEFAULT 0,
            started_at TEXT,
            level1_completed_at TEXT,
            level2_completed_at TEXT,
            completed_at TEXT
        )
        """
    )
    connection.execute(
        """
        INSERT INTO erfassungen_new (id, created_at, is_demo)
        SELECT id, created_at, is_demo FROM erfassungen
        """
    )
    connection.execute(
        """
        CREATE TABLE erfassung_herkunft (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            erfassung_id INTEGER NOT NULL,
            position INTEGER NOT NULL,
            wert TEXT NOT NULL,
            FOREIGN KEY (erfassung_id) REFERENCES erfassungen(id) ON DELETE CASCADE
        )
        """
    )
    connection.execute(
        """
        INSERT INTO erfassung_herkunft (erfassung_id, position, wert)
        SELECT id, 0, level1 FROM erfassungen
        """
    )
    connection.execute(
        """
        CREATE TABLE erfassung_interesse (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            erfassung_id INTEGER NOT NULL,
            position INTEGER NOT NULL,
            wert TEXT NOT NULL,
            FOREIGN KEY (erfassung_id) REFERENCES erfassungen(id) ON DELETE CASCADE
        )
        """
    )
    connection.execute(
        """
        INSERT INTO erfassung_interesse (erfassung_id, position, wert)
        SELECT id, 0, level2 FROM erfassungen
        """
    )
    connection.execute(
        """
        CREATE TABLE erfassung_detail (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            interesse_id INTEGER NOT NULL,
            position INTEGER NOT NULL,
            wert TEXT NOT NULL,
            FOREIGN KEY (interesse_id) REFERENCES erfassung_interesse(id) ON DELETE CASCADE
        )
        """
    )
    connection.execute(
        """
        INSERT INTO erfassung_detail (interesse_id, position, wert)
        SELECT i.id, l.position, l.wert
        FROM (
            SELECT
                id,
                erfassung_id,
                wert,
                ROW_NUMBER() OVER (PARTITION BY erfassung_id ORDER BY id) - 1 AS position
            FROM erfassung_level3
        ) AS l
        JOIN erfassung_interesse AS i ON i.erfassung_id = l.erfassung_id
        """
    )
    _assert_migration(connection, before)
    connection.execute("DROP TABLE erfassung_level3")
    connection.execute("DROP TABLE erfassungen")
    connection.execute("ALTER TABLE erfassungen_new RENAME TO erfassungen")
    max_id = connection.execute("SELECT MAX(id) FROM erfassungen").fetchone()[0] or 0
    connection.execute("DELETE FROM sqlite_sequence WHERE name = 'erfassungen'")
    connection.execute(
        "INSERT INTO sqlite_sequence (name, seq) VALUES ('erfassungen', ?)",
        (max_id,),
    )
    connection.execute("PRAGMA foreign_keys = ON")


def _assert_migration(connection, before):
    after_rows = connection.execute(
        """
        SELECT e.id, e.created_at, e.is_demo, e.started_at, e.level1_completed_at,
               e.level2_completed_at, e.completed_at, h.wert, i.wert, d.wert
        FROM erfassungen_new AS e
        LEFT JOIN erfassung_herkunft AS h ON h.erfassung_id = e.id
        LEFT JOIN erfassung_interesse AS i ON i.erfassung_id = e.id
        LEFT JOIN erfassung_detail AS d ON d.interesse_id = i.id
        ORDER BY e.id, h.position, i.position, d.position, d.id
        """
    ).fetchall()
    after = {}
    for row in after_rows:
        row_id, created_at, is_demo, started, level1_at, level2_at, completed, herkunft, interesse, detail = row
        entry = after.get(row_id)
        if entry is None:
            entry = {
                "created_at": created_at,
                "is_demo": is_demo,
                "times": (started, level1_at, level2_at, completed),
                "herkunft": [],
                "interesse": [],
                "details": [],
            }
            after[row_id] = entry
        if herkunft and herkunft not in entry["herkunft"]:
            entry["herkunft"].append(herkunft)
        if interesse and interesse not in entry["interesse"]:
            entry["interesse"].append(interesse)
        if detail is not None:
            entry["details"].append(detail)
    if set(after) != set(before):
        raise RuntimeError("Migration abgebrochen: IDs weichen ab")
    for row_id, old in before.items():
        new = after[row_id]
        if new["created_at"] != old["created_at"] or new["is_demo"] != old["is_demo"]:
            raise RuntimeError(f"Migration abgebrochen: Kopf von ID {row_id} verändert")
        if new["herkunft"] != [old["level1"]] or new["interesse"] != [old["level2"]]:
            raise RuntimeError(f"Migration abgebrochen: Zuordnung von ID {row_id} verändert")
        if new["details"] != old["details"]:
            raise RuntimeError(f"Migration abgebrochen: Details von ID {row_id} verändert")
        if any(value is not None for value in new["times"]):
            raise RuntimeError(f"Migration abgebrochen: Zeitmessung an ID {row_id} erfunden")
    herkunft_count = connection.execute("SELECT COUNT(*) FROM erfassung_herkunft").fetchone()[0]
    interesse_count = connection.execute("SELECT COUNT(*) FROM erfassung_interesse").fetchone()[0]
    if herkunft_count != len(before) or interesse_count != len(before):
        raise RuntimeError("Migration abgebrochen: doppelte Herkunft oder doppeltes Interesse")


def berlin_timestamp():
    return datetime.now(BERLIN).isoformat(sep=" ", timespec="seconds")


def capture_clock_label(moment):
    local = moment.astimezone(BERLIN) if moment.tzinfo else moment.replace(tzinfo=BERLIN)
    return f"{WEEKDAY_NAMES[local.weekday()]} {local.strftime('%H:%M:%S')} {local.strftime('%d:%m:%Y')}"


def latest_real_capture_label():
    connection = connect()
    try:
        row = connection.execute(
            """
            SELECT created_at FROM erfassungen
            WHERE is_demo = 0
            ORDER BY id DESC
            LIMIT 1
            """
        ).fetchone()
    finally:
        connection.close()
    if not row or not row[0]:
        return ""
    return capture_clock_label(_as_berlin(row[0]))


def save_korrektur(from_level, to_level, elapsed_seconds, had_selection, level1, level2):
    connection = connect()
    try:
        cursor = connection.execute(
            """
            INSERT INTO korrektur (
                created_at, from_level, to_level, elapsed_seconds, had_selection
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                berlin_timestamp(),
                from_level,
                to_level,
                elapsed_seconds,
                1 if had_selection else 0,
            ),
        )
        korrektur_id = cursor.lastrowid
        for index, wert in enumerate(level1):
            connection.execute(
                """
                INSERT INTO korrektur_status (korrektur_id, level, parent, position, wert)
                VALUES (?, 1, NULL, ?, ?)
                """,
                (korrektur_id, index, wert),
            )
        for index, block in enumerate(level2):
            connection.execute(
                """
                INSERT INTO korrektur_status (korrektur_id, level, parent, position, wert)
                VALUES (?, 2, NULL, ?, ?)
                """,
                (korrektur_id, index, block["value"]),
            )
            for detail_index, detail in enumerate(block["level3"]):
                connection.execute(
                    """
                    INSERT INTO korrektur_status (korrektur_id, level, parent, position, wert)
                    VALUES (?, 3, ?, ?, ?)
                    """,
                    (korrektur_id, block["value"], detail_index, detail),
                )
        connection.commit()
        return korrektur_id
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def correction_report(start=None, end=None):
    connection = connect()
    try:
        clauses = []
        params = []
        if start is not None:
            clauses.append("substr(created_at, 1, 10) >= ?")
            params.append(start.isoformat())
        if end is not None:
            clauses.append("substr(created_at, 1, 10) <= ?")
            params.append(end.isoformat())
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = connection.execute(
            f"""
            SELECT id, created_at, from_level, to_level, elapsed_seconds
            FROM korrektur
            {where}
            ORDER BY id
            """,
            params,
        ).fetchall()
        if not rows:
            status_rows = []
        else:
            marks = ",".join("?" for _ in rows)
            status_rows = connection.execute(
                f"""
                SELECT korrektur_id, level, parent, wert
                FROM korrektur_status
                WHERE korrektur_id IN ({marks})
                ORDER BY korrektur_id, level, position, id
                """,
                [row[0] for row in rows],
            ).fetchall()
    finally:
        connection.close()

    by_hour = Counter()
    by_step = Counter()
    by_status = Counter()
    for _row_id, created_at, from_level, to_level, _elapsed in rows:
        moment = _as_berlin(created_at)
        by_hour[moment.hour] += 1
        by_step[(from_level, to_level)] += 1
    for _korrektur_id, level, parent, wert in status_rows:
        if level == 3 and parent:
            by_status[f"{parent}: {wert}"] += 1
        else:
            by_status[wert] += 1
    hours = [
        {"label": f"{hour:02d} Uhr", "count": by_hour[hour]}
        for hour in range(24)
        if by_hour[hour]
    ]
    _bars(hours)
    for item in hours:
        item["count_label"] = _de_int(item["count"])
    steps = []
    for (from_level, to_level), count in by_step.most_common():
        steps.append(
            {
                "label": f"Ebene {from_level} → Ebene {to_level}",
                "count": count,
                "count_label": _de_int(count),
            }
        )
    _bars(steps)
    statuses = [
        {"label": name, "count": count, "count_label": _de_int(count)}
        for name, count in by_status.most_common(8)
    ]
    _bars(statuses)
    return {
        "total": len(rows),
        "total_label": _de_int(len(rows)),
        "hours": hours,
        "steps": steps,
        "statuses": statuses,
    }


def _as_berlin(value):
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=BERLIN)
    return parsed.astimezone(BERLIN)


def _stamp(moment):
    return moment.isoformat(sep=" ", timespec="seconds")


def _parse_client_time(value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("Zeitangabe fehlt")
    parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=BERLIN)
    return parsed.astimezone(BERLIN)


def list_erfassungen(day=None, connection=None):
    close_connection = connection is None
    if connection is None:
        connection = connect()
    try:
        where = ""
        params = []
        if day is not None:
            where = "WHERE substr(e.created_at, 1, 10) = ?"
            params.append(day.isoformat())
        rows = connection.execute(
            f"""
            SELECT e.id, e.created_at, e.started_at, e.level1_completed_at,
                   e.level2_opened_at, e.level2_started_at, e.level2_completed_at,
                   e.level3_opened_at, e.level3_started_at, e.completed_at,
                   h.wert, i.id, i.wert, d.wert
            FROM erfassungen AS e
            LEFT JOIN erfassung_herkunft AS h ON h.erfassung_id = e.id
            LEFT JOIN erfassung_interesse AS i ON i.erfassung_id = e.id
            LEFT JOIN erfassung_detail AS d ON d.interesse_id = i.id
            {where}
            ORDER BY e.id, h.position, h.id, i.position, i.id, d.position, d.id
            """,
            params,
        ).fetchall()
    finally:
        if close_connection:
            connection.close()

    grouped = {}
    for (
        row_id,
        created_at,
        started_at,
        level1_completed_at,
        level2_opened_at,
        level2_started_at,
        level2_completed_at,
        level3_opened_at,
        level3_started_at,
        completed_at,
        herkunft,
        interesse_id,
        interesse,
        detail,
    ) in rows:
        entry = grouped.get(row_id)
        if entry is None:
            moment = _as_berlin(created_at)
            entry = {
                "id": row_id,
                "created_at": created_at,
                "date_label": moment.strftime("%d.%m.%Y"),
                "time_label": moment.strftime("%H:%M"),
                "herkunft": [],
                "interessen": [],
                "_interessen": {},
                "_moment": moment,
                "timing": _timing_view(
                    started_at,
                    level1_completed_at,
                    level2_started_at,
                    level2_completed_at,
                    level3_started_at,
                    completed_at,
                    level2_opened_at,
                    level3_opened_at,
                ),
            }
            grouped[row_id] = entry
        if herkunft and herkunft not in entry["herkunft"]:
            entry["herkunft"].append(herkunft)
        if interesse_id is not None and interesse_id not in entry["_interessen"]:
            block = {"value": interesse, "details": []}
            entry["_interessen"][interesse_id] = block
            entry["interessen"].append(block)
        if detail is not None and interesse_id is not None:
            block = entry["_interessen"][interesse_id]
            if detail not in block["details"]:
                block["details"].append(detail)

    entries = sorted(
        grouped.values(),
        key=lambda entry: (entry["_moment"], entry["id"]),
        reverse=True,
    )
    today = datetime.now(BERLIN).date()
    today_count = sum(1 for entry in entries if entry["_moment"].date() == today)
    for entry in entries:
        del entry["_moment"]
        del entry["_interessen"]

    return {
        "entries": entries,
        "total": len(entries),
        "today": today_count,
    }


def _parse_optional_time(value):
    if value is None or (isinstance(value, str) and not value.strip()):
        return None
    return _parse_client_time(value)


def save_erfassung(
    level1,
    level2,
    started_at,
    level1_completed_at,
    level2_started_at,
    level2_completed_at,
    level3_started_at,
    level2_opened_at=None,
    level3_opened_at=None,
):
    started = _parse_client_time(started_at)
    level1_done = _parse_client_time(level1_completed_at)
    level2_started = _parse_client_time(level2_started_at)
    level2_done = _parse_client_time(level2_completed_at)
    level3_started = _parse_client_time(level3_started_at)
    level2_opened = _parse_optional_time(level2_opened_at)
    level3_opened = _parse_optional_time(level3_opened_at)
    completed = datetime.now(BERLIN)
    if level3_started > completed:
        if level3_started - completed <= timedelta(seconds=120):
            completed = level3_started
        else:
            raise ValueError("Die Zeitangaben sind ungültig.")
    if level2_opened is not None and not (level1_done <= level2_opened <= level2_started):
        raise ValueError("Die Zeitangaben sind ungültig.")
    if level3_opened is not None and not (level2_done <= level3_opened <= level3_started):
        raise ValueError("Die Zeitangaben sind ungültig.")
    if not (
        started
        <= level1_done
        <= level2_started
        <= level2_done
        <= level3_started
        <= completed
    ):
        raise ValueError("Die Zeitangaben sind ungültig.")

    connection = connect()
    try:
        cursor = connection.execute(
            """
            INSERT INTO erfassungen (
                created_at, is_demo, started_at, level1_completed_at,
                level2_opened_at, level2_started_at, level2_completed_at,
                level3_opened_at, level3_started_at, completed_at
            )
            VALUES (?, 0, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                _stamp(completed),
                _stamp(started),
                _stamp(level1_done),
                _stamp(level2_opened) if level2_opened else None,
                _stamp(level2_started),
                _stamp(level2_done),
                _stamp(level3_opened) if level3_opened else None,
                _stamp(level3_started),
                _stamp(completed),
            ),
        )
        erfassung_id = cursor.lastrowid
        connection.executemany(
            """
            INSERT INTO erfassung_herkunft (erfassung_id, position, wert)
            VALUES (?, ?, ?)
            """,
            [(erfassung_id, index, wert) for index, wert in enumerate(level1)],
        )
        for index, block in enumerate(level2):
            interesse_cursor = connection.execute(
                """
                INSERT INTO erfassung_interesse (erfassung_id, position, wert)
                VALUES (?, ?, ?)
                """,
                (erfassung_id, index, block["value"]),
            )
            interesse_id = interesse_cursor.lastrowid
            connection.executemany(
                """
                INSERT INTO erfassung_detail (interesse_id, position, wert)
                VALUES (?, ?, ?)
                """,
                [
                    (interesse_id, detail_index, wert)
                    for detail_index, wert in enumerate(block["level3"])
                ],
            )
        connection.commit()
        return erfassung_id, capture_clock_label(completed)
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def _de_int(value):
    return f"{value:,}".replace(",", ".")


def _de_num(value):
    return f"{value:.1f}".replace(".", ",")


def _de_pct(part, whole):
    if not whole:
        return "0,0 %"
    return _de_num(100 * part / whole) + " %"


def _modus_clause(modus):
    if modus == "demo":
        return "e.is_demo = 1", []
    if modus == "echt":
        return "e.is_demo = 0", []
    return "1 = 1", []


def _load_entries(connection, modus, herkunft, interesse, detail=""):
    clause, params = _modus_clause(modus)
    sql = f"""
        SELECT e.id, e.created_at, e.started_at, e.level1_completed_at,
               e.level2_opened_at, e.level2_started_at, e.level2_completed_at,
               e.level3_opened_at, e.level3_started_at, e.completed_at,
               h.wert, i.id, i.wert, d.wert
        FROM erfassungen AS e
        LEFT JOIN erfassung_herkunft AS h ON h.erfassung_id = e.id
        LEFT JOIN erfassung_interesse AS i ON i.erfassung_id = e.id
        LEFT JOIN erfassung_detail AS d ON d.interesse_id = i.id
        WHERE {clause}
    """
    if herkunft:
        sql += """
            AND EXISTS (
                SELECT 1 FROM erfassung_herkunft AS hf
                WHERE hf.erfassung_id = e.id AND hf.wert = ?
            )
        """
        params.append(herkunft)
    if interesse:
        sql += """
            AND EXISTS (
                SELECT 1 FROM erfassung_interesse AS inf
                WHERE inf.erfassung_id = e.id AND inf.wert = ?
            )
        """
        params.append(interesse)
    if detail:
        sql += """
            AND EXISTS (
                SELECT 1 FROM erfassung_detail AS df
                JOIN erfassung_interesse AS inf ON inf.id = df.interesse_id
                WHERE inf.erfassung_id = e.id AND df.wert = ?
        """
        params.append(detail)
        if interesse:
            sql += " AND inf.wert = ?"
            params.append(interesse)
        sql += ")"
    sql += " ORDER BY e.id, h.position, h.id, i.position, i.id, d.position, d.id"
    rows = connection.execute(sql, params).fetchall()
    grouped = {}
    for row in rows:
        (
            row_id,
            created_at,
            started_at,
            level1_completed_at,
            level2_opened_at,
            level2_started_at,
            level2_completed_at,
            level3_opened_at,
            level3_started_at,
            completed_at,
            herkunft_wert,
            interesse_id,
            interesse_wert,
            detail,
        ) = row
        entry = grouped.get(row_id)
        if entry is None:
            moment = _as_berlin(created_at)
            entry = {
                "id": row_id,
                "herkunft": [],
                "interessen": [],
                "_interessen": {},
                "moment": moment,
                "date": moment.date(),
                "hour": moment.hour,
                "weekday": moment.weekday(),
                "started": _as_berlin(started_at) if started_at else None,
                "level1_completed": _as_berlin(level1_completed_at) if level1_completed_at else None,
                "level2_opened": _as_berlin(level2_opened_at) if level2_opened_at else None,
                "level2_started": _as_berlin(level2_started_at) if level2_started_at else None,
                "level2_completed": _as_berlin(level2_completed_at) if level2_completed_at else None,
                "level3_opened": _as_berlin(level3_opened_at) if level3_opened_at else None,
                "level3_started": _as_berlin(level3_started_at) if level3_started_at else None,
                "completed": _as_berlin(completed_at) if completed_at else None,
            }
            grouped[row_id] = entry
        if herkunft_wert and herkunft_wert not in entry["herkunft"]:
            entry["herkunft"].append(herkunft_wert)
        if interesse_id is not None and interesse_id not in entry["_interessen"]:
            block = {"value": interesse_wert, "details": []}
            entry["_interessen"][interesse_id] = block
            entry["interessen"].append(block)
        if detail is not None and interesse_id is not None:
            block = entry["_interessen"][interesse_id]
            if detail not in block["details"]:
                block["details"].append(detail)
    entries = []
    for entry in grouped.values():
        del entry["_interessen"]
        entries.append(entry)
    return entries


def _known_values(connection, modus):
    clause, params = _modus_clause(modus)
    level1 = list(LEVEL1_VALUES)
    level2 = list(LEVEL2_VALUES)
    for (name,) in connection.execute(
        f"""
        SELECT DISTINCT h.wert
        FROM erfassung_herkunft AS h
        JOIN erfassungen AS e ON e.id = h.erfassung_id
        WHERE {clause}
        """,
        params,
    ):
        if name not in level1:
            level1.append(name)
    for (name,) in connection.execute(
        f"""
        SELECT DISTINCT i.wert
        FROM erfassung_interesse AS i
        JOIN erfassungen AS e ON e.id = i.erfassung_id
        WHERE {clause}
        """,
        params,
    ):
        if name not in level2:
            level2.append(name)
    level3 = []
    for interest in list(LEVEL2_VALUES) + [name for name in INTERESTS if name not in LEVEL2_VALUES]:
        for name in INTERESTS.get(interest, []):
            if name not in level3:
                level3.append(name)
    for (name,) in connection.execute(
        f"""
        SELECT DISTINCT d.wert
        FROM erfassung_detail AS d
        JOIN erfassung_interesse AS i ON i.id = d.interesse_id
        JOIN erfassungen AS e ON e.id = i.erfassung_id
        WHERE {clause}
        """,
        params,
    ):
        if name not in level3:
            level3.append(name)
    return level1, level2, level3


def _weekday_occurrences(start, end):
    counts = [0, 0, 0, 0, 0, 0, 0]
    if start is None or end is None or end < start:
        return counts
    day = start
    while day <= end:
        counts[day.weekday()] += 1
        day += timedelta(days=1)
    return counts


def _bars(items, value_key="count"):
    maximum = max((item[value_key] for item in items), default=0)
    for item in items:
        value = item[value_key]
        item["width"] = 0 if maximum <= 0 else round(100 * value / maximum, 1)
    return items


def _ranked(names, counts, total):
    items = [{"name": name, "count": counts.get(name, 0)} for name in names]
    items.sort(key=lambda item: (-item["count"], item["name"]))
    for item in items:
        item["count_label"] = _de_int(item["count"])
        item["percent"] = _de_pct(item["count"], total)
    return _bars(items)


def _month_keys(start, end, full_years):
    if full_years:
        return [
            (year, month)
            for year in range(start.year, end.year + 1)
            for month in range(1, 13)
        ]
    keys = []
    year, month = start.year, start.month
    while (year, month) <= (end.year, end.month):
        keys.append((year, month))
        month += 1
        if month == 13:
            month = 1
            year += 1
    return keys


def _timeline(entries, start, end, zeitraum):
    if start is None:
        if not entries:
            return {"kind": "leer", "groups": []}
        start = min(entry["date"] for entry in entries)
        end = max(entry["date"] for entry in entries)
    if zeitraum in ("gesamt", "jahr") or (end - start).days >= 31:
        counts = Counter((entry["date"].year, entry["date"].month) for entry in entries)
        grouped = {}
        flat = []
        for year, month in _month_keys(start, end, zeitraum in ("gesamt", "jahr")):
            bar = {
                "label": MONTH_NAMES[month - 1],
                "count": counts.get((year, month), 0),
            }
            grouped.setdefault(year, []).append(bar)
            flat.append(bar)
        _bars(flat)
        groups = []
        for year, bars in grouped.items():
            for bar in bars:
                bar["count_label"] = _de_int(bar["count"])
            groups.append({"title": str(year), "bars": bars})
        return {"kind": "monate", "groups": groups}

    counts = Counter(entry["date"] for entry in entries)
    bars = []
    day = start
    while day <= end:
        bars.append(
            {
                "label": day.strftime("%d.%m."),
                "count": counts.get(day, 0),
            }
        )
        day += timedelta(days=1)
    _bars(bars)
    for bar in bars:
        bar["count_label"] = _de_int(bar["count"])
    return {"kind": "tage", "groups": [{"title": "Tage", "bars": bars}]}


def _join_labels(labels):
    if not labels:
        return "—"
    if len(labels) == 1:
        return labels[0]
    if len(labels) == 2:
        return f"{labels[0]} und {labels[1]}"
    return ", ".join(labels[:-1]) + " und " + labels[-1]


def _format_duration(seconds):
    whole = max(0, int(round(seconds)))
    if whole < 60:
        return f"{whole} s"
    minutes, secs = divmod(whole, 60)
    if minutes < 60:
        if secs:
            return f"{minutes} min {secs} s"
        return f"{minutes} min"
    hours, minutes = divmod(minutes, 60)
    if minutes:
        return f"{hours} h {minutes} min"
    return f"{hours} h"


STAGE_SPECS = (
    ("level1", "Ebene 1, erster Klick bis Weiter", "started", "level1_completed"),
    ("gap2", "Verweildauer ohne Aktion, Ebene 2", "level1_completed", "level2_started"),
    ("level2", "Ebene 2, erster Klick bis Weiter", "level2_started", "level2_completed"),
    ("gap3", "Verweildauer ohne Aktion, Ebene 3", "level2_completed", "level3_started"),
    ("level3", "Ebene 3, erster Klick bis Speichern", "level3_started", "completed"),
    ("total", "Start bis Ende", "started", "completed"),
)


def _moment(value):
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value
    return _as_berlin(value)


def _span_seconds(moments, start_key, end_key):
    start = moments.get(start_key)
    end = moments.get(end_key)
    if start is None or end is None or end < start:
        return None
    return (end - start).total_seconds()


def _stage_seconds(moments, key, start_key, end_key):
    if key == "gap2" and moments.get("level2_opened"):
        start_key = "level2_opened"
    if key == "gap3" and moments.get("level3_opened"):
        start_key = "level3_opened"
    return _span_seconds(moments, start_key, end_key)


def _timing_moments(
    started_at,
    level1_completed_at,
    level2_started_at,
    level2_completed_at,
    level3_started_at,
    completed_at,
    level2_opened_at=None,
    level3_opened_at=None,
):
    return {
        "started": _moment(started_at),
        "level1_completed": _moment(level1_completed_at),
        "level2_opened": _moment(level2_opened_at),
        "level2_started": _moment(level2_started_at),
        "level2_completed": _moment(level2_completed_at),
        "level3_opened": _moment(level3_opened_at),
        "level3_started": _moment(level3_started_at),
        "completed": _moment(completed_at),
    }


def _timing_view(
    started_at,
    level1_completed_at,
    level2_started_at,
    level2_completed_at,
    level3_started_at,
    completed_at,
    level2_opened_at=None,
    level3_opened_at=None,
):
    moments = _timing_moments(
        started_at,
        level1_completed_at,
        level2_started_at,
        level2_completed_at,
        level3_started_at,
        completed_at,
        level2_opened_at,
        level3_opened_at,
    )
    if moments["started"] is None or moments["completed"] is None:
        return {"state": "none", "stages": [], "by_key": {key: None for key, *_rest in STAGE_SPECS}}
    stages = []
    by_key = {}
    missing = False
    for key, label, start_key, end_key in STAGE_SPECS:
        seconds = _stage_seconds(moments, key, start_key, end_key)
        if seconds is None:
            missing = True
            by_key[key] = None
            continue
        duration = _format_duration(seconds)
        by_key[key] = duration
        stages.append({"key": key, "label": label, "duration": duration})
    return {
        "state": "partial" if missing else "complete",
        "stages": stages,
        "by_key": by_key,
    }


def _median(values):
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / 2


def _duration_report(entries):
    stage_samples = {key: [] for key, _label, _start, _end in STAGE_SPECS}
    for entry in entries:
        for key, _label, start_key, end_key in STAGE_SPECS:
            seconds = _stage_seconds(entry, key, start_key, end_key)
            if seconds is not None:
                stage_samples[key].append(seconds)
    totals = stage_samples["total"]
    if not totals:
        return {"available": False, "count": 0, "count_label": "0", "stages": [], "buckets": []}
    bounds = (10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 61)
    labels = (
        "unter 10 Sekunden",
        "10–15 Sekunden",
        "15–20 Sekunden",
        "20–25 Sekunden",
        "25–30 Sekunden",
        "30–35 Sekunden",
        "35–40 Sekunden",
        "40–45 Sekunden",
        "45–50 Sekunden",
        "50–55 Sekunden",
        "55–60 Sekunden",
        "über 1 Minute",
    )
    bucket_counts = [0] * len(labels)
    for total in totals:
        placed = False
        for index, bound in enumerate(bounds):
            if total < bound:
                bucket_counts[index] += 1
                placed = True
                break
        if not placed:
            bucket_counts[-1] += 1
    buckets = [
        {"label": label, "count": count, "count_label": _de_int(count)}
        for label, count in zip(labels, bucket_counts)
    ]
    _bars(buckets)
    stages = []
    for key, label, _start, _end in STAGE_SPECS:
        samples = stage_samples[key]
        if not samples:
            stages.append(
                {
                    "key": key,
                    "label": label,
                    "count": 0,
                    "count_label": "0",
                    "average": "",
                    "median": "",
                    "total": key == "total",
                }
            )
            continue
        stages.append(
            {
                "key": key,
                "label": label,
                "count": len(samples),
                "count_label": _de_int(len(samples)),
                "average": _format_duration(sum(samples) / len(samples)),
                "median": _format_duration(_median(samples)),
                "total": key == "total",
            }
        )
    return {
        "available": True,
        "count": len(totals),
        "count_label": _de_int(len(totals)),
        "stages": stages,
        "buckets": buckets,
    }


def _intensity_levels(counts):
    positive = sorted(count for count in counts if count > 0)
    if not positive:
        return lambda count: 0, []
    def at(quantile):
        index = int(round((len(positive) - 1) * quantile))
        return positive[max(0, min(len(positive) - 1, index))]

    cuts = [at(0.25), at(0.5), at(0.75)]

    def level(count):
        if count <= 0:
            return 0
        if count <= cuts[0]:
            return 1
        if count <= cuts[1]:
            return 2
        if count <= cuts[2]:
            return 3
        return 4

    return level, cuts


def _shift_month(day, months):
    index = day.year * 12 + (day.month - 1) + months
    year, month_index = divmod(index, 12)
    return date(year, month_index + 1, 1)


def _calendar(entries, start, end, zeitraum, mark_start=None, mark_end=None):
    if start is None:
        if not entries:
            return {"weeks": [], "legend": [], "max_count": 0}
        start = min(entry["date"] for entry in entries)
        end = max(entry["date"] for entry in entries)
    if zeitraum in ("gesamt", "jahr"):
        start = start.replace(month=1, day=1)
        end = end.replace(month=12, day=31)
    elif zeitraum == "woche":
        end = start + timedelta(days=6)
    elif zeitraum == "monat":
        end = _shift_month(start, 1) - timedelta(days=1)
    elif zeitraum == "quartal":
        end = _shift_month(start, 3) - timedelta(days=1)
    elif zeitraum == "halbjahr":
        end = _shift_month(start, 6) - timedelta(days=1)
    counts = Counter(
        entry["date"] for entry in entries if start <= entry["date"] <= end
    )
    level_for, _cuts = _intensity_levels(counts.values())
    grid_start = start - timedelta(days=start.weekday())
    grid_end = end + timedelta(days=(6 - end.weekday()))
    weeks = []
    day = grid_start
    while day <= grid_end:
        cells = []
        month_label = ""
        for _offset in range(7):
            in_range = start <= day <= end
            count = counts.get(day, 0) if in_range else 0
            selected = (
                in_range
                and mark_start is not None
                and mark_end is not None
                and mark_start <= day <= mark_end
            )
            if in_range and day.day == 1:
                month_label = MONTH_NAMES[day.month - 1]
            cells.append(
                {
                    "date": day.isoformat(),
                    "label": day.strftime("%d.%m.%Y"),
                    "weekday": WEEKDAY_NAMES[day.weekday()],
                    "count": count,
                    "count_label": _de_int(count),
                    "level": level_for(count) if in_range else 0,
                    "in_range": in_range,
                    "selected": selected,
                }
            )
            day += timedelta(days=1)
        weeks.append({"label": month_label, "days": cells})
    names = {0: "keine", 1: "niedrig", 2: "mittel", 3: "hoch", 4: "sehr hoch"}
    legend = [{"level": level, "label": names[level]} for level in range(5)]
    return {
        "weeks": weeks,
        "legend": legend,
        "max_count": max(counts.values(), default=0),
    }


def build_auswertung(
    modus,
    zeitraum,
    start,
    end,
    herkunft,
    interesse,
    detail="",
    connection=None,
    mark_start=None,
    mark_end=None,
    stufen=None,
    wochentage=None,
):
    close_connection = connection is None
    if connection is None:
        connection = connect()
    try:
        level1_names, level2_names, level3_names = _known_values(connection, modus)
        if herkunft and herkunft not in level1_names:
            herkunft = ""
        if interesse and interesse not in level2_names:
            interesse = ""
        if detail and detail not in level3_names:
            detail = ""
        applied_detail = detail
        entries = _load_entries(connection, modus, herkunft, interesse, detail)
        timed_entries = _load_entries(connection, "alle", herkunft, interesse, detail)
    finally:
        if close_connection:
            connection.close()

    all_entries = entries
    if start is not None and end is not None:
        entries = [entry for entry in entries if start <= entry["date"] <= end]
        timed_entries = [entry for entry in timed_entries if start <= entry["date"] <= end]
        range_start, range_end = start, end
    elif entries:
        range_start = min(entry["date"] for entry in entries)
        range_end = max(entry["date"] for entry in entries)
    else:
        range_start = range_end = None

    calendar = (
        _calendar(all_entries, mark_start, mark_end, "jahr", mark_start, mark_end)
        if mark_start is not None and mark_end is not None
        else _calendar(entries, start, end, zeitraum)
    )
    wanted_levels = set(stufen or [])
    wanted_days = set(wochentage or [])
    if wanted_levels or wanted_days:
        day_level = {
            date.fromisoformat(cell["date"]): cell["level"]
            for week in calendar["weeks"]
            for cell in week["days"]
            if cell["in_range"]
        }

        def matches(entry):
            if wanted_levels and day_level.get(entry["date"]) not in wanted_levels:
                return False
            if wanted_days and entry["weekday"] not in wanted_days:
                return False
            return True

        entries = [entry for entry in entries if matches(entry)]
        timed_entries = [entry for entry in timed_entries if matches(entry)]
        period_marked = mark_start is not None and mark_end is not None
        for week in calendar["weeks"]:
            for cell in week["days"]:
                parsed = date.fromisoformat(cell["date"])
                color_ok = not wanted_levels or cell["level"] in wanted_levels
                day_ok = not wanted_days or parsed.weekday() in wanted_days
                if period_marked:
                    cell["selected"] = cell["selected"] and color_ok and day_ok
                else:
                    cell["selected"] = cell["in_range"] and color_ok and day_ok

    total = len(entries)
    by_date = Counter(entry["date"] for entry in entries)
    active_days = len(by_date)
    by_month = Counter((entry["date"].year, entry["date"].month) for entry in entries)
    by_level1 = Counter()
    by_level2 = Counter()
    by_weekday = Counter(entry["weekday"] for entry in entries)
    detail_counts = Counter()
    combinations = Counter()
    for entry in entries:
        for name in entry["herkunft"]:
            by_level1[name] += 1
        seen_interest = set()
        for block in entry["interessen"]:
            if block["value"] not in seen_interest:
                by_level2[block["value"]] += 1
                seen_interest.add(block["value"])
        seen_details = set()
        for block in entry["interessen"]:
            for detail in block["details"]:
                if detail not in seen_details:
                    detail_counts[detail] += 1
                    seen_details.add(detail)
                for origin in entry["herkunft"]:
                    combinations[(origin, block["value"], detail)] += 1

    weekday_clock = Counter(
        entry["hour"] for entry in entries if entry["weekday"] != 5 and entry["weekday"] != 6
    )
    saturday_clock = Counter(entry["hour"] for entry in entries if entry["weekday"] == 5)
    outside = sum(
        1
        for entry in entries
        if (
            entry["weekday"] == 6
            or (entry["weekday"] == 5 and entry["hour"] not in SATURDAY_CLOCK_HOURS)
            or (entry["weekday"] < 5 and entry["hour"] not in WEEKDAY_CLOCK_HOURS)
        )
    )

    occurrences = _weekday_occurrences(range_start, range_end)
    weekdays = []
    for index, name in enumerate(WEEKDAY_NAMES):
        hours = OPENING_HOURS[index]
        count = by_weekday.get(index, 0)
        rate = None
        if hours and occurrences[index]:
            rate = count / (occurrences[index] * hours)
        weekdays.append(
            {
                "name": name,
                "count": count,
                "count_label": _de_int(count),
                "rate": rate,
                "rate_label": "geschlossen" if hours == 0 else ("—" if rate is None else _de_num(rate)),
                "closed": hours == 0,
            }
        )
    _bars(weekdays)
    rate_items = [item for item in weekdays if item["rate"] is not None]
    rate_max = max((item["rate"] for item in rate_items), default=0)
    for item in weekdays:
        if item["rate"] is None or rate_max <= 0:
            item["rate_width"] = 0
        else:
            item["rate_width"] = round(100 * item["rate"] / rate_max, 1)

    def clock_rows(hours, counts):
        rows = [{"label": f"{hour:02d}:00", "count": counts.get(hour, 0)} for hour in hours]
        _bars(rows)
        for row in rows:
            row["count_label"] = _de_int(row["count"])
        return rows

    if total == 0 or not by_date:
        strongest_day = "—"
        strongest_day_count = ""
    else:
        peak = max(by_date.values())
        days = sorted(day for day, count in by_date.items() if count == peak)
        strongest_day = _join_labels([day.strftime("%d.%m.%Y") for day in days[:3]])
        if len(days) > 3:
            strongest_day += f" (+{len(days) - 3})"
        strongest_day_count = _de_int(peak)

    if total == 0 or not by_month:
        strongest_month = "—"
        strongest_month_count = ""
    else:
        peak = max(by_month.values())
        months = sorted(key for key, count in by_month.items() if count == peak)
        strongest_month = _join_labels(
            [f"{MONTH_NAMES[month - 1]} {year}" for year, month in months]
        )
        strongest_month_count = _de_int(peak)

    herkunft_items = _ranked(level1_names, by_level1, total)
    interesse_items = _ranked(level2_names, by_level2, total)

    def mode_label(items):
        if not items or not items[0]["count"]:
            return "—"
        peak = items[0]["count"]
        names = [item["name"] for item in items if item["count"] == peak]
        return _join_labels(names)

    top_herkunft = mode_label(herkunft_items)
    top_interesse = mode_label(interesse_items)

    details = [
        {"name": name, "count": count}
        for name, count in detail_counts.most_common()
    ]
    for item in details:
        item["count_label"] = _de_int(item["count"])
        item["percent"] = _de_pct(item["count"], total)
    _bars(details)

    combo_rows = []
    for (level1, level2, detail), count in combinations.most_common(12):
        combo_rows.append(
            {
                "label": f"{level1} → {level2} → {detail}",
                "count": count,
                "count_label": _de_int(count),
            }
        )
    _bars(combo_rows)

    return {
        "total": total,
        "total_label": _de_int(total),
        "active_days": active_days,
        "average_label": "—" if not active_days else _de_num(total / active_days),
        "strongest_day": strongest_day,
        "strongest_day_count": strongest_day_count,
        "strongest_month": strongest_month,
        "strongest_month_count": strongest_month_count,
        "top_herkunft": top_herkunft,
        "top_interesse": top_interesse,
        "timeline": _timeline(entries, start, end, zeitraum),
        "weekdays": weekdays,
        "weekday_hours": clock_rows(WEEKDAY_CLOCK_HOURS, weekday_clock),
        "saturday_hours": clock_rows(SATURDAY_CLOCK_HOURS, saturday_clock),
        "outside": outside,
        "herkunft": herkunft_items,
        "interesse": interesse_items,
        "details": details,
        "combinations": combo_rows,
        "herkunft_options": level1_names,
        "interesse_options": level2_names,
        "detail_options": level3_names,
        "applied_herkunft": herkunft,
        "applied_interesse": interesse,
        "applied_detail": applied_detail,
        "duration": _duration_report(timed_entries),
        "calendar": calendar,
    }


def erfassungen_board(selected):
    connection = connect()
    try:
        overview = list_erfassungen(selected, connection)
        rows = connection.execute(
            "SELECT substr(created_at, 1, 10), COUNT(*) FROM erfassungen GROUP BY 1"
        ).fetchall()
    finally:
        connection.close()

    counts = {}
    years = set()
    for text, count in rows:
        try:
            parsed = date.fromisoformat(text)
        except ValueError:
            continue
        counts[parsed] = count
        years.add(parsed.year)
    years.add(selected.year)
    start = date(selected.year, 1, 1)
    end = date(selected.year, 12, 31)
    stubs = [
        {"date": day}
        for day, count in counts.items()
        if start <= day <= end
        for _index in range(count)
    ]
    calendar = _calendar(stubs, start, end, "jahr")
    return {
        "entries": overview["entries"],
        "total": overview["total"],
        "selected": selected,
        "selected_label": selected.strftime("%d.%m.%Y"),
        "selected_iso": selected.isoformat(),
        "weekday": WEEKDAY_NAMES[selected.weekday()],
        "calendar": calendar,
        "years": sorted(years),
    }


def _counts_for(entries, names):
    counts = Counter()
    for entry in entries:
        for name in names(entry):
            counts[name] += 1
    return counts


def _aligned_rows(left_counts, right_counts, left_total, right_total, order):
    names = [name for name in order if left_counts[name] or right_counts[name]]
    extra = sorted((set(left_counts) | set(right_counts)) - set(names))
    rows = []
    for name in names + extra:
        left = left_counts[name]
        right = right_counts[name]
        if not left and not right:
            continue
        delta = right - left
        sign = "+" if delta > 0 else ""
        rows.append(
            {
                "name": name,
                "left_label": _de_int(left),
                "right_label": _de_int(right),
                "left_percent": _de_pct(left, left_total),
                "right_percent": _de_pct(right, right_total),
                "delta_label": f"{sign}{delta}".replace("+-", "-"),
            }
        )
    return rows


def _side_summary(entries, period):
    total = len(entries)
    active_days = len({entry["date"] for entry in entries})
    return {
        "title": period["title"] if period else "Zeitraum nicht erkannt",
        "detail": period["detail"] if period else "",
        "total": total,
        "total_label": _de_int(total),
        "active_days": active_days,
        "average_label": "—" if not active_days else _de_num(total / active_days),
        "duration": _duration_report(entries),
    }


def filter_names(modus):
    connection = connect()
    try:
        names = _known_values(connection, modus)
        return names[0], names[1]
    finally:
        connection.close()


def _period_heatmap(entries, period, art):
    if period is None:
        return {"weeks": [], "legend": [], "max_count": 0}
    start = date(period["start"].year, 1, 1)
    end = date(period["end"].year, 12, 31)
    calendar = _calendar(
        [entry for entry in entries if start <= entry["date"] <= end],
        start,
        end,
        "jahr",
    )
    for week in calendar["weeks"]:
        for cell in week["days"]:
            if not cell["in_range"]:
                cell["selected"] = False
                cell["token"] = ""
                continue
            parsed = date.fromisoformat(cell["date"])
            cell["selected"] = period["start"] <= parsed <= period["end"]
            cell["token"] = token_for_day(art, parsed) or ""
    return calendar


def suggest_compare_days(modus, herkunft, interesse, today):
    connection = connect()
    try:
        entries = _load_entries(connection, modus, herkunft, interesse)
    finally:
        connection.close()
    days = sorted({entry["date"] for entry in entries})
    if not days:
        return today, today
    left = today if today in set(days) else days[-1]
    try:
        previous = left.replace(year=left.year - 1)
    except ValueError:
        previous = left.replace(year=left.year - 1, day=28)
    if previous in set(days) and previous != left:
        return left, previous
    earlier = [day for day in days if day < left]
    return left, earlier[-1] if earlier else left


def compare_periods(modus, herkunft, interesse, left, right, art):
    connection = connect()
    try:
        entries = _load_entries(connection, modus, herkunft, interesse)
    finally:
        connection.close()

    def within(period):
        if period is None:
            return []
        return [entry for entry in entries if period["start"] <= entry["date"] <= period["end"]]

    left_entries = within(left)
    right_entries = within(right)
    left_summary = _side_summary(left_entries, left)
    right_summary = _side_summary(right_entries, right)
    left_summary["calendar"] = _period_heatmap(entries, left, art)
    right_summary["calendar"] = _period_heatmap(entries, right, art)
    delta = right_summary["total"] - left_summary["total"]
    sign = "+" if delta > 0 else ""
    herkunft_rows = _aligned_rows(
        _counts_for(left_entries, lambda entry: entry["herkunft"]),
        _counts_for(right_entries, lambda entry: entry["herkunft"]),
        left_summary["total"],
        right_summary["total"],
        LEVEL1_VALUES,
    )
    interesse_rows = _aligned_rows(
        _counts_for(left_entries, lambda entry: [block["value"] for block in entry["interessen"]]),
        _counts_for(right_entries, lambda entry: [block["value"] for block in entry["interessen"]]),
        left_summary["total"],
        right_summary["total"],
        LEVEL2_VALUES,
    )
    duration_rows = []
    left_stages = {stage["key"]: stage for stage in left_summary["duration"]["stages"]}
    right_stages = {stage["key"]: stage for stage in right_summary["duration"]["stages"]}
    for key, label, _start, _end in STAGE_SPECS:
        left_stage = left_stages.get(key)
        right_stage = right_stages.get(key)
        duration_rows.append(
            {
                "label": label,
                "left": left_stage["average"] if left_stage and left_stage["count"] else "—",
                "right": right_stage["average"] if right_stage and right_stage["count"] else "—",
            }
        )
    return {
        "left": left_summary,
        "right": right_summary,
        "delta_label": f"{sign}{delta}",
        "herkunft": herkunft_rows,
        "interesse": interesse_rows,
        "duration": duration_rows,
    }
