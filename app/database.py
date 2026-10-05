import sqlite3
from collections import Counter
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from app.catalog import ensure_master_data
from app.periods import token_for_day

BERLIN = ZoneInfo("Europe/Berlin")

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "customer_state.db"

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
        ensure_master_data(connection)
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


def latest_real_capture_label(board_ids=None):
    connection = connect()
    try:
        board_sql, board_params = _board_clause(board_ids)
        where = "WHERE is_demo = 0"
        if board_sql:
            where += " AND " + board_sql.replace("e.board_id", "board_id")
        row = connection.execute(
            f"""
            SELECT created_at FROM erfassungen
            {where}
            ORDER BY id DESC
            LIMIT 1
            """,
            board_params,
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
                INSERT INTO korrektur_status (korrektur_id, level, parent, position, wert, option_id)
                VALUES (?, 1, NULL, ?, ?, ?)
                """,
                (korrektur_id, index, option["label"], option["id"]),
            )
        for index, block in enumerate(level2):
            connection.execute(
                """
                INSERT INTO korrektur_status (korrektur_id, level, parent, position, wert, option_id)
                VALUES (?, 2, NULL, ?, ?, ?)
                """,
                (korrektur_id, index, block["label"], block["id"]),
            )
            for detail_index, option in enumerate(block["level3"]):
                connection.execute(
                    """
                    INSERT INTO korrektur_status (korrektur_id, level, parent, position, wert, option_id)
                    VALUES (?, 3, ?, ?, ?, ?)
                    """,
                    (korrektur_id, block["label"], detail_index, option["label"], option["id"]),
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


def list_erfassungen(day=None, connection=None, board_ids=None):
    close_connection = connection is None
    if connection is None:
        connection = connect()
    try:
        conditions = []
        params = []
        if day is not None:
            conditions.append("substr(e.created_at, 1, 10) = ?")
            params.append(day.isoformat())
        board_sql, board_params = _board_clause(board_ids)
        if board_sql:
            conditions.append(board_sql)
            params.extend(board_params)
        where = "WHERE " + " AND ".join(conditions) if conditions else ""
        rows = connection.execute(
            f"""
            SELECT e.id, e.created_at, e.started_at, e.level1_completed_at,
                   e.level2_opened_at, e.level2_started_at, e.level2_completed_at,
                   e.level3_opened_at, e.level3_started_at, e.completed_at,
                   COALESCE(ho.label, h.wert), i.id, COALESCE(io.label, i.wert),
                   COALESCE(do.label, d.wert)
            FROM erfassungen AS e
            LEFT JOIN erfassung_herkunft AS h ON h.erfassung_id = e.id
            LEFT JOIN board_options AS ho ON ho.id = h.option_id
            LEFT JOIN erfassung_interesse AS i ON i.erfassung_id = e.id
            LEFT JOIN board_options AS io ON io.id = i.option_id
            LEFT JOIN erfassung_detail AS d ON d.interesse_id = i.id
            LEFT JOIN board_options AS do ON do.id = d.option_id
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


def _option_number(value):
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip().isdigit():
        return int(value.strip())
    return None


def _active_options(connection, board_key, position):
    rows = connection.execute(
        """
        SELECT o.id, o.key, o.label, o.position, o.span, o.grid_row, o.grid_column, o.grid_width
        FROM board_options AS o
        JOIN board_levels AS l ON l.id = o.level_id
        JOIN boards AS b ON b.id = l.board_id
        WHERE b.key = ? AND l.position = ? AND o.aktiv = 1 AND l.aktiv = 1 AND b.aktiv = 1
        ORDER BY o.grid_row, o.grid_column, o.position, o.id
        """,
        (board_key, position),
    ).fetchall()
    return [
        {
            "id": row[0],
            "key": row[1],
            "label": row[2],
            "position": row[3],
            "span": row[4],
            "grid_row": row[5],
            "grid_column": row[6],
            "grid_width": row[7],
        }
        for row in rows
    ]


def _active_children(connection, parent_id):
    rows = connection.execute(
        """
        SELECT child.id, child.key, child.label, link.position, child.span,
               child.grid_row, child.grid_column, child.grid_width
        FROM board_option_parents AS link
        JOIN board_options AS child ON child.id = link.child_option_id
        JOIN board_options AS parent ON parent.id = link.parent_option_id
        WHERE link.parent_option_id = ? AND child.aktiv = 1 AND parent.aktiv = 1
        ORDER BY child.grid_row, child.grid_column, link.position, child.id
        """,
        (parent_id,),
    ).fetchall()
    return [
        {
            "id": row[0],
            "key": row[1],
            "label": row[2],
            "position": row[3],
            "span": row[4],
            "grid_row": row[5],
            "grid_column": row[6],
            "grid_width": row[7],
        }
        for row in rows
    ]


def capture_catalog(board_key="verkauf"):
    connection = connect()
    try:
        board = connection.execute(
            "SELECT key, name FROM boards WHERE key = ? AND aktiv = 1",
            (board_key,),
        ).fetchone()
        if board is None:
            return {"key": board_key, "name": "", "levels": []}
        levels = []
        for position in (1, 2, 3):
            title = connection.execute(
                """
                SELECT l.title
                FROM board_levels AS l
                JOIN boards AS b ON b.id = l.board_id
                WHERE b.key = ? AND l.position = ? AND l.aktiv = 1
                """,
                (board_key, position),
            ).fetchone()
            options = _active_options(connection, board_key, position)
            level = {
                "position": position,
                "title": title[0] if title else "",
                "options": options,
            }
            if position == 3:
                children = {}
                for option in _active_options(connection, board_key, 2):
                    nested = _active_children(connection, option["id"])
                    if nested:
                        children[str(option["id"])] = nested
                level["children"] = children
            levels.append(level)
        return {"key": board[0], "name": board[1], "levels": levels}
    finally:
        connection.close()


def _take_options(raw_ids, allowed, require, message="Die Erfassung ist unvollständig."):
    if not isinstance(raw_ids, list) or (require and not raw_ids):
        raise ValueError(message)
    chosen = []
    seen = set()
    allowed_by_id = {item["id"]: item for item in allowed}
    for raw in raw_ids:
        number = _option_number(raw)
        option = allowed_by_id.get(number)
        if option is None or number in seen:
            raise ValueError(message)
        seen.add(number)
        chosen.append({"id": option["id"], "label": option["label"]})
    return chosen


def prepare_capture(level1_raw, level2_raw, board_key="verkauf"):
    connection = connect()
    try:
        level1 = _take_options(level1_raw, _active_options(connection, board_key, 1), True)
        if not isinstance(level2_raw, list) or not level2_raw:
            raise ValueError("Die Erfassung ist unvollständig.")
        parents = {item["id"]: item for item in _active_options(connection, board_key, 2)}
        level2 = []
        seen = set()
        for block in level2_raw:
            if not isinstance(block, dict):
                raise ValueError("Die Erfassung ist unvollständig.")
            number = _option_number(block.get("id"))
            parent = parents.get(number)
            details = block.get("level3")
            if parent is None or number in seen or not isinstance(details, list) or not details:
                raise ValueError("Die Erfassung ist unvollständig.")
            seen.add(number)
            children = _take_options(details, _active_children(connection, number), True)
            level2.append({"id": parent["id"], "label": parent["label"], "level3": children})
        board = connection.execute(
            "SELECT id FROM boards WHERE key = ? AND aktiv = 1",
            (board_key,),
        ).fetchone()
        if board is None:
            raise ValueError("Die Erfassung ist unvollständig.")
        return board[0], level1, level2
    finally:
        connection.close()


def prepare_korrektur(level1_raw, level2_raw, board_key="verkauf"):
    connection = connect()
    try:
        level1 = _take_options(
            level1_raw or [],
            _active_options(connection, board_key, 1),
            False,
            "Die Korrektur ist unvollständig.",
        )
        if not isinstance(level2_raw, list):
            raise ValueError("Die Korrektur ist unvollständig.")
        parents = {item["id"]: item for item in _active_options(connection, board_key, 2)}
        level2 = []
        seen = set()
        for block in level2_raw:
            if not isinstance(block, dict):
                raise ValueError("Die Korrektur ist unvollständig.")
            number = _option_number(block.get("id"))
            parent = parents.get(number)
            details = block.get("level3") or []
            if parent is None or number in seen or not isinstance(details, list):
                raise ValueError("Die Korrektur ist unvollständig.")
            seen.add(number)
            children = _take_options(
                details,
                _active_children(connection, number),
                False,
                "Die Korrektur ist unvollständig.",
            )
            level2.append({"id": parent["id"], "label": parent["label"], "level3": children})
        return level1, level2
    finally:
        connection.close()


def save_erfassung(
    board_id,
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

    # employee_id wird absichtlich nicht geschrieben. Die Anmeldung darf keine
    # Erfassung, Zeitmessung oder Korrektur einer Person zuordnen.
    connection = connect()
    try:
        cursor = connection.execute(
            """
            INSERT INTO erfassungen (
                created_at, is_demo, board_id, started_at, level1_completed_at,
                level2_opened_at, level2_started_at, level2_completed_at,
                level3_opened_at, level3_started_at, completed_at
            )
            VALUES (?, 0, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                _stamp(completed),
                board_id,
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
            INSERT INTO erfassung_herkunft (erfassung_id, position, wert, option_id)
            VALUES (?, ?, ?, ?)
            """,
            [
                (erfassung_id, index, option["label"], option["id"])
                for index, option in enumerate(level1)
            ],
        )
        for index, block in enumerate(level2):
            interesse_cursor = connection.execute(
                """
                INSERT INTO erfassung_interesse (erfassung_id, position, wert, option_id)
                VALUES (?, ?, ?, ?)
                """,
                (erfassung_id, index, block["label"], block["id"]),
            )
            interesse_id = interesse_cursor.lastrowid
            connection.executemany(
                """
                INSERT INTO erfassung_detail (interesse_id, position, wert, option_id)
                VALUES (?, ?, ?, ?)
                """,
                [
                    (interesse_id, detail_index, option["label"], option["id"])
                    for detail_index, option in enumerate(block["level3"])
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


def _board_clause(board_ids, alias="e"):
    if board_ids is None:
        return "", []
    if not board_ids:
        return "0 = 1", []
    marks = ",".join("?" for _ in board_ids)
    return f"{alias}.board_id IN ({marks})", list(board_ids)


def _modus_clause(modus):
    if modus == "demo":
        return "e.is_demo = 1", []
    if modus == "echt":
        return "e.is_demo = 0", []
    return "1 = 1", []


def _used_options(connection, modus, position, board_ids=None):
    clause, params = _modus_clause(modus)
    board_sql, board_params = _board_clause(board_ids)
    if position == 1:
        usage = """
            JOIN erfassung_herkunft AS used ON used.option_id = o.id
            JOIN erfassungen AS e ON e.id = used.erfassung_id
        """
    elif position == 2:
        usage = """
            JOIN erfassung_interesse AS used ON used.option_id = o.id
            JOIN erfassungen AS e ON e.id = used.erfassung_id
        """
    else:
        usage = """
            JOIN erfassung_detail AS used ON used.option_id = o.id
            JOIN erfassung_interesse AS interest ON interest.id = used.interesse_id
            JOIN erfassungen AS e ON e.id = interest.erfassung_id
        """
    rows = connection.execute(
        f"""
        SELECT DISTINCT o.id, o.key, o.label, o.aktiv, o.position
        FROM board_options AS o
        JOIN board_levels AS l ON l.id = o.level_id
        {usage}
        WHERE l.position = ? AND {clause}{(" AND " + board_sql) if board_sql else ""}
        ORDER BY o.position, o.id
        """,
        [position, *params, *board_params],
    ).fetchall()
    return [
        {"id": row[0], "key": row[1], "label": row[2], "aktiv": row[3], "position": row[4]}
        for row in rows
    ]


def _match_options(options, raw):
    text = (raw or "").strip()
    if not text:
        return []
    if text.isdigit():
        by_id = [option for option in options if str(option["id"]) == text]
        if by_id:
            return by_id
    return [
        option
        for option in options
        if option["label"] == text or option["key"] == text
    ]


def _filter_ids(options, raw):
    text = (raw or "").strip()
    if not text:
        return None, ""
    matched = _match_options(options, text)
    if not matched:
        return None, ""
    if len(matched) == 1:
        return [matched[0]["id"]], str(matched[0]["id"])
    return [option["id"] for option in matched], text


def _load_entries(connection, modus, herkunft, interesse, detail="", board_ids=None):
    clause, params = _modus_clause(modus)
    board_sql, board_params = _board_clause(board_ids)
    level1_options = _used_options(connection, modus, 1, board_ids)
    level2_options = _used_options(connection, modus, 2, board_ids)
    level3_options = _used_options(connection, modus, 3, board_ids)
    herkunft_ids, applied_herkunft = _filter_ids(level1_options, herkunft)
    interesse_ids, applied_interesse = _filter_ids(level2_options, interesse)
    detail_ids, applied_detail = _filter_ids(level3_options, detail)
    if (herkunft or "").strip() and not applied_herkunft:
        herkunft_ids = None
    if (interesse or "").strip() and not applied_interesse:
        interesse_ids = None
    if (detail or "").strip() and not applied_detail:
        detail_ids = None
    sql = f"""
        SELECT e.id, e.created_at, e.started_at, e.level1_completed_at,
               e.level2_opened_at, e.level2_started_at, e.level2_completed_at,
               e.level3_opened_at, e.level3_started_at, e.completed_at,
               h.option_id, COALESCE(ho.label, h.wert),
               i.id, i.option_id, COALESCE(io.label, i.wert),
               d.option_id, COALESCE(do.label, d.wert)
        FROM erfassungen AS e
        LEFT JOIN erfassung_herkunft AS h ON h.erfassung_id = e.id
        LEFT JOIN board_options AS ho ON ho.id = h.option_id
        LEFT JOIN erfassung_interesse AS i ON i.erfassung_id = e.id
        LEFT JOIN board_options AS io ON io.id = i.option_id
        LEFT JOIN erfassung_detail AS d ON d.interesse_id = i.id
        LEFT JOIN board_options AS do ON do.id = d.option_id
        WHERE {clause}{(" AND " + board_sql) if board_sql else ""}
    """
    params.extend(board_params)
    if herkunft_ids:
        marks = ",".join("?" for _ in herkunft_ids)
        sql += f"""
            AND EXISTS (
                SELECT 1 FROM erfassung_herkunft AS hf
                WHERE hf.erfassung_id = e.id AND hf.option_id IN ({marks})
            )
        """
        params.extend(herkunft_ids)
    if interesse_ids:
        marks = ",".join("?" for _ in interesse_ids)
        sql += f"""
            AND EXISTS (
                SELECT 1 FROM erfassung_interesse AS inf
                WHERE inf.erfassung_id = e.id AND inf.option_id IN ({marks})
            )
        """
        params.extend(interesse_ids)
    if detail_ids:
        marks = ",".join("?" for _ in detail_ids)
        sql += f"""
            AND EXISTS (
                SELECT 1 FROM erfassung_detail AS df
                JOIN erfassung_interesse AS inf ON inf.id = df.interesse_id
                WHERE inf.erfassung_id = e.id AND df.option_id IN ({marks})
        """
        params.extend(detail_ids)
        if interesse_ids:
            interest_marks = ",".join("?" for _ in interesse_ids)
            sql += f" AND inf.option_id IN ({interest_marks})"
            params.extend(interesse_ids)
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
            herkunft_option_id,
            herkunft_label,
            interesse_row_id,
            interesse_option_id,
            interesse_label,
            detail_option_id,
            detail_label,
        ) = row
        entry = grouped.get(row_id)
        if entry is None:
            moment = _as_berlin(created_at)
            entry = {
                "id": row_id,
                "herkunft": [],
                "herkunft_ids": [],
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
        if herkunft_option_id and herkunft_option_id not in entry["herkunft_ids"]:
            entry["herkunft_ids"].append(herkunft_option_id)
            entry["herkunft"].append(herkunft_label)
        if interesse_row_id is not None and interesse_row_id not in entry["_interessen"]:
            block = {
                "id": interesse_option_id,
                "value": interesse_label,
                "details": [],
                "detail_ids": [],
            }
            entry["_interessen"][interesse_row_id] = block
            entry["interessen"].append(block)
        if detail_label is not None and interesse_row_id is not None:
            block = entry["_interessen"][interesse_row_id]
            if detail_option_id not in block["detail_ids"]:
                block["detail_ids"].append(detail_option_id)
                block["details"].append(detail_label)
    entries = []
    for entry in grouped.values():
        del entry["_interessen"]
        entries.append(entry)
    return entries


def _known_values(connection, modus, board_ids=None):
    return (
        _used_options(connection, modus, 1, board_ids),
        _used_options(connection, modus, 2, board_ids),
        _used_options(connection, modus, 3, board_ids),
    )


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


def _ranked(options, counts, total):
    items = [
        {"id": option["id"], "name": option["label"], "count": counts.get(option["id"], 0)}
        for option in options
    ]
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
    board_ids=None,
):
    close_connection = connection is None
    if connection is None:
        connection = connect()
    try:
        level1_options, level2_options, level3_options = _known_values(connection, modus, board_ids)
        _herkunft_ids, applied_herkunft = _filter_ids(level1_options, herkunft)
        _interesse_ids, applied_interesse = _filter_ids(level2_options, interesse)
        _detail_ids, applied_detail = _filter_ids(level3_options, detail)
        entries = _load_entries(
            connection,
            modus,
            applied_herkunft,
            applied_interesse,
            applied_detail,
            board_ids,
        )
        timed_entries = _load_entries(
            connection,
            "alle",
            applied_herkunft,
            applied_interesse,
            applied_detail,
            board_ids,
        )
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
        for option_id in entry["herkunft_ids"]:
            by_level1[option_id] += 1
        seen_interest = set()
        for block in entry["interessen"]:
            if block["id"] not in seen_interest:
                by_level2[block["id"]] += 1
                seen_interest.add(block["id"])
        seen_details = set()
        for block in entry["interessen"]:
            for detail_id, detail_label in zip(block["detail_ids"], block["details"]):
                if detail_id not in seen_details:
                    detail_counts[detail_id] += 1
                    seen_details.add(detail_id)
                for origin in entry["herkunft"]:
                    combinations[(origin, block["value"], detail_label)] += 1

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

    herkunft_items = _ranked(level1_options, by_level1, total)
    interesse_items = _ranked(level2_options, by_level2, total)

    def mode_label(items):
        if not items or not items[0]["count"]:
            return "—"
        peak = items[0]["count"]
        names = [item["name"] for item in items if item["count"] == peak]
        return _join_labels(names)

    top_herkunft = mode_label(herkunft_items)
    top_interesse = mode_label(interesse_items)

    detail_labels = {option["id"]: option["label"] for option in level3_options}
    details = [
        {"name": detail_labels.get(option_id, str(option_id)), "count": count}
        for option_id, count in detail_counts.most_common()
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
        "herkunft_options": level1_options,
        "interesse_options": level2_options,
        "detail_options": level3_options,
        "applied_herkunft": applied_herkunft,
        "applied_interesse": applied_interesse,
        "applied_detail": applied_detail,
        "duration": _duration_report(timed_entries),
        "calendar": calendar,
    }


def erfassungen_board(selected, board_ids=None):
    connection = connect()
    try:
        overview = list_erfassungen(selected, connection, board_ids)
        board_sql, board_params = _board_clause(board_ids)
        where = "WHERE " + board_sql if board_sql else ""
        rows = connection.execute(
            f"SELECT substr(created_at, 1, 10), COUNT(*) FROM erfassungen AS e {where} GROUP BY 1",
            board_params,
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


def apply_option_filter(options, raw):
    _ids, applied = _filter_ids(options, raw)
    invalid = bool((raw or "").strip()) and not applied
    return applied, invalid


def filter_names(modus, board_ids=None):
    connection = connect()
    try:
        names = _known_values(connection, modus, board_ids)
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


def compare_periods(modus, herkunft, interesse, left, right, art, board_ids=None):
    connection = connect()
    try:
        entries = _load_entries(connection, modus, herkunft, interesse, "", board_ids)
        level1_options, level2_options, _level3_options = _known_values(connection, modus, board_ids)
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
        [option["label"] for option in level1_options],
    )
    interesse_rows = _aligned_rows(
        _counts_for(left_entries, lambda entry: [block["value"] for block in entry["interessen"]]),
        _counts_for(right_entries, lambda entry: [block["value"] for block in entry["interessen"]]),
        left_summary["total"],
        right_summary["total"],
        [option["label"] for option in level2_options],
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
