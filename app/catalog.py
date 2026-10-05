"""Stammdaten für Boards, Ebenen und Auswahloptionen.

Sichtbare Namen dürfen sich ändern. Schlüssel und IDs bleiben.
Ein Neustart legt fehlende Stammdaten an und überschreibt keine Bezeichnungen.
"""

from datetime import datetime
from zoneinfo import ZoneInfo

BERLIN = ZoneInfo("Europe/Berlin")

SALES_LEVELS = (
    (1, "Wie ist der Kunde auf uns aufmerksam geworden?"),
    (2, "Für was interessierte sich der Kunde?"),
    (3, "Wofür interessiert sich der Kunde?"),
)

SALES_LEVEL1 = (
    ("empfehlung", "Empfehlung", 1),
    ("ki", "KI", 1),
    ("google", "Google", 1),
    ("leasingportal", "Leasingportal", 1),
    ("arbeit", "Arbeit", 1),
    ("sonstiges", "Sonstiges", 1),
    ("stammkunde", "Stammkunde", 2),
)

SALES_LEVEL2 = (
    ("mtb", "MTB"),
    ("e-mtb", "E-MTB"),
    ("gravel", "Gravel"),
    ("e-gravel", "E-Gravel"),
    ("rennrad", "Rennrad"),
    ("triathlon", "Triathlon"),
    ("kinderrad", "Kinderrad"),
    ("lastenrad", "Lastenrad"),
    ("trekking", "Trekking"),
    ("trekking-vollgefedert", "Trekking vollgefedert"),
    ("bekleidung", "Bekleidung"),
    ("zubehoer", "Zubehör"),
)

SALES_LEVEL3 = (
    ("specialized", "Specialized"),
    ("produkt-fehlte", "Produkt fehlte"),
    ("leasing", "Leasing"),
    ("kauf", "Kauf"),
    ("reparatur", "Reparatur"),
    ("pivot", "PIVOT"),
    ("amflow", "AMFLOW"),
    ("woom", "woom"),
    ("riese-mueller", "Riese & Müller"),
    ("helm", "Helm"),
    ("trikot", "Trikot"),
    ("radhose", "Radhose"),
    ("handschuhe", "Handschuhe"),
    ("schuhe", "Schuhe"),
    ("regenbekleidung", "Regenbekleidung"),
    ("jacke-weste", "Jacke/Weste"),
    ("brille", "Brille"),
    ("bekleidung-sonstiges", "Sonstiges"),
    ("luftpumpe", "Luftpumpe"),
    ("beleuchtung", "Beleuchtung"),
    ("schutzbleche", "Schutzbleche"),
    ("schloesser", "Schlösser"),
    ("griffe", "Griffe"),
    ("pflege-und-reinigungsprodukte", "Pflege und Reinigungsprodukte"),
)

SALES_LINKS = {
    "mtb": ["specialized", "produkt-fehlte", "leasing", "kauf", "reparatur"],
    "e-mtb": ["specialized", "pivot", "amflow", "produkt-fehlte", "leasing", "kauf", "reparatur"],
    "gravel": ["pivot", "specialized", "produkt-fehlte", "leasing", "kauf", "reparatur"],
    "e-gravel": ["specialized", "pivot", "produkt-fehlte", "leasing", "kauf", "reparatur"],
    "rennrad": ["specialized", "produkt-fehlte"],
    "triathlon": ["specialized", "produkt-fehlte"],
    "kinderrad": ["woom", "produkt-fehlte", "leasing", "kauf", "reparatur"],
    "lastenrad": ["riese-mueller", "produkt-fehlte", "leasing", "kauf", "reparatur"],
    "trekking": ["riese-mueller", "specialized", "produkt-fehlte", "leasing", "kauf", "reparatur"],
    "trekking-vollgefedert": [
        "riese-mueller",
        "specialized",
        "amflow",
        "produkt-fehlte",
        "leasing",
        "kauf",
        "reparatur",
    ],
    "bekleidung": [
        "helm",
        "trikot",
        "radhose",
        "handschuhe",
        "schuhe",
        "regenbekleidung",
        "jacke-weste",
        "brille",
        "bekleidung-sonstiges",
    ],
    "zubehoer": [
        "luftpumpe",
        "beleuchtung",
        "schutzbleche",
        "schloesser",
        "griffe",
        "pflege-und-reinigungsprodukte",
    ],
}

_MASTER_SCHEMA = """
CREATE TABLE IF NOT EXISTS boards (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    position INTEGER NOT NULL,
    aktiv INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS board_levels (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    board_id INTEGER NOT NULL REFERENCES boards(id),
    position INTEGER NOT NULL,
    title TEXT NOT NULL,
    sort_order INTEGER NOT NULL,
    aktiv INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE (board_id, position)
);

CREATE TABLE IF NOT EXISTS board_options (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    level_id INTEGER NOT NULL REFERENCES board_levels(id),
    key TEXT NOT NULL,
    label TEXT NOT NULL,
    position INTEGER NOT NULL,
    span INTEGER NOT NULL DEFAULT 1,
    grid_row INTEGER NOT NULL DEFAULT 1,
    grid_column INTEGER NOT NULL DEFAULT 1,
    grid_width INTEGER NOT NULL DEFAULT 1,
    aktiv INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE (level_id, key)
);

CREATE TABLE IF NOT EXISTS board_option_parents (
    parent_option_id INTEGER NOT NULL REFERENCES board_options(id),
    child_option_id INTEGER NOT NULL REFERENCES board_options(id),
    position INTEGER NOT NULL,
    PRIMARY KEY (parent_option_id, child_option_id)
);

CREATE TABLE IF NOT EXISTS employees (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    login_name TEXT UNIQUE,
    pin_hash TEXT,
    status TEXT NOT NULL,
    is_admin INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    CHECK (status IN ('aktiv', 'gesperrt', 'ausgeschieden'))
);

CREATE TABLE IF NOT EXISTS employee_boards (
    employee_id INTEGER NOT NULL REFERENCES employees(id),
    board_id INTEGER NOT NULL REFERENCES boards(id),
    PRIMARY KEY (employee_id, board_id)
);
"""


def _stamp():
    return datetime.now(BERLIN).isoformat(sep=" ", timespec="seconds")


def _columns(connection, table):
    return [row[1] for row in connection.execute(f"PRAGMA table_info({table})")]


def _add_column(connection, table, name, definition):
    if name not in _columns(connection, table):
        connection.execute(f"ALTER TABLE {table} ADD COLUMN {name} {definition}")


def _slug(label):
    translated = label.translate(
        str.maketrans(
            {
                "ä": "ae",
                "ö": "oe",
                "ü": "ue",
                "ß": "ss",
                "Ä": "ae",
                "Ö": "oe",
                "Ü": "ue",
            }
        )
    ).lower()
    chars = []
    dash = False
    for char in translated:
        if char.isalnum():
            chars.append(char)
            dash = False
        elif not dash:
            chars.append("-")
            dash = True
    return "".join(chars).strip("-") or "option"


def _board_id(connection, key, name, position, stamp):
    row = connection.execute("SELECT id FROM boards WHERE key = ?", (key,)).fetchone()
    if row:
        return row[0]
    cursor = connection.execute(
        """
        INSERT INTO boards (key, name, position, aktiv, created_at, updated_at)
        VALUES (?, ?, ?, 1, ?, ?)
        """,
        (key, name, position, stamp, stamp),
    )
    return cursor.lastrowid


def _level_id(connection, board_id, position, title, stamp):
    row = connection.execute(
        """
        SELECT id FROM board_levels
        WHERE board_id = ? AND position = ?
        """,
        (board_id, position),
    ).fetchone()
    if row:
        return row[0]
    cursor = connection.execute(
        """
        INSERT INTO board_levels (
            board_id, position, title, sort_order, aktiv, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, 1, ?, ?)
        """,
        (board_id, position, title, position, stamp, stamp),
    )
    return cursor.lastrowid


def _option_id(connection, level_id, key, label, position, span, aktiv, stamp):
    row = connection.execute(
        """
        SELECT id FROM board_options
        WHERE level_id = ? AND key = ?
        """,
        (level_id, key),
    ).fetchone()
    if row:
        return row[0]
    cursor = connection.execute(
        """
        INSERT INTO board_options (
            level_id, key, label, position, span, aktiv, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (level_id, key, label, position, span, aktiv, stamp, stamp),
    )
    return cursor.lastrowid


def _link(connection, parent_id, child_id, position):
    connection.execute(
        """
        INSERT INTO board_option_parents (parent_option_id, child_option_id, position)
        VALUES (?, ?, ?)
        ON CONFLICT (parent_option_id, child_option_id) DO NOTHING
        """,
        (parent_id, child_id, position),
    )


def _level_of(connection, board_key, position):
    row = connection.execute(
        """
        SELECT l.id
        FROM board_levels AS l
        JOIN boards AS b ON b.id = l.board_id
        WHERE b.key = ? AND l.position = ?
        """,
        (board_key, position),
    ).fetchone()
    if row is None:
        raise RuntimeError(f"Ebene {position} auf Board {board_key} fehlt")
    return row[0]


def _option_by_label(connection, level_id, label):
    return connection.execute(
        """
        SELECT id, key FROM board_options
        WHERE level_id = ? AND label = ?
        ORDER BY id
        LIMIT 1
        """,
        (level_id, label),
    ).fetchone()


def _child_by_label(connection, parent_id, label):
    return connection.execute(
        """
        SELECT child.id
        FROM board_option_parents AS link
        JOIN board_options AS child ON child.id = link.child_option_id
        WHERE link.parent_option_id = ? AND child.label = ?
        ORDER BY child.id
        LIMIT 1
        """,
        (parent_id, label),
    ).fetchone()


def _fresh_key(connection, level_id, base):
    key = base
    number = 2
    while connection.execute(
        "SELECT 1 FROM board_options WHERE level_id = ? AND key = ?",
        (level_id, key),
    ).fetchone():
        key = f"{base}-{number}"
        number += 1
    return key


def _next_position(connection, level_id):
    row = connection.execute(
        "SELECT COALESCE(MAX(position), 0) FROM board_options WHERE level_id = ?",
        (level_id,),
    ).fetchone()
    return row[0] + 1


def _historical_option(connection, level_id, label, parent_key, stamp):
    base = _slug(label)
    if connection.execute(
        "SELECT 1 FROM board_options WHERE level_id = ? AND key = ?",
        (level_id, base),
    ).fetchone():
        base = _fresh_key(connection, level_id, f"{parent_key}-{base}" if parent_key else base)
    else:
        base = _fresh_key(connection, level_id, base)
    return _option_id(
        connection,
        level_id,
        base,
        label,
        _next_position(connection, level_id),
        1,
        0,
        stamp,
    )


def _seed_sales(connection, stamp):
    verkauf = _board_id(connection, "verkauf", "Verkauf", 1, stamp)
    werkstatt = _board_id(connection, "werkstatt", "Werkstatt", 2, stamp)
    for position, title in SALES_LEVELS:
        _level_id(connection, verkauf, position, title, stamp)
        _level_id(connection, werkstatt, position, f"Ebene {position}", stamp)
    level1 = _level_of(connection, "verkauf", 1)
    level2 = _level_of(connection, "verkauf", 2)
    level3 = _level_of(connection, "verkauf", 3)
    for index, (key, label, span) in enumerate(SALES_LEVEL1, start=1):
        _option_id(connection, level1, key, label, index, span, 1, stamp)
    parents = {}
    for index, (key, label) in enumerate(SALES_LEVEL2, start=1):
        parents[key] = _option_id(connection, level2, key, label, index, 1, 1, stamp)
    children = {}
    for index, (key, label) in enumerate(SALES_LEVEL3, start=1):
        children[key] = _option_id(connection, level3, key, label, index, 1, 1, stamp)
    for parent_key, child_keys in SALES_LINKS.items():
        for index, child_key in enumerate(child_keys, start=1):
            _link(connection, parents[parent_key], children[child_key], index)
    return verkauf


def _option_for_level_label(connection, board_key, position, label, parent_key, stamp):
    level_id = _level_of(connection, board_key, position)
    found = _option_by_label(connection, level_id, label)
    if found:
        return found[0]
    return _historical_option(connection, level_id, label, parent_key, stamp)


def _child_for_parent(connection, parent_id, label, stamp):
    found = _child_by_label(connection, parent_id, label)
    if found:
        return found[0]
    parent = connection.execute(
        """
        SELECT o.key, o.level_id, l.board_id, l.position
        FROM board_options AS o
        JOIN board_levels AS l ON l.id = o.level_id
        WHERE o.id = ?
        """,
        (parent_id,),
    ).fetchone()
    if parent is None:
        raise RuntimeError("Interesse ohne Stammdaten")
    child_level = connection.execute(
        """
        SELECT id FROM board_levels
        WHERE board_id = ? AND position = ?
        """,
        (parent[2], parent[3] + 1),
    ).fetchone()
    if child_level is None:
        raise RuntimeError("Detail-Ebene fehlt")
    child_id = _historical_option(connection, child_level[0], label, parent[0], stamp)
    position = connection.execute(
        """
        SELECT COALESCE(MAX(position), 0) + 1
        FROM board_option_parents
        WHERE parent_option_id = ?
        """,
        (parent_id,),
    ).fetchone()[0]
    _link(connection, parent_id, child_id, position)
    return child_id


def link_capture_options(connection, erfassung_id, stamp=None):
    stamp = stamp or _stamp()
    board = connection.execute("SELECT id FROM boards WHERE key = 'verkauf'").fetchone()
    if board is None:
        raise RuntimeError("Board Verkauf fehlt")
    connection.execute(
        "UPDATE erfassungen SET board_id = ? WHERE id = ? AND board_id IS NULL",
        (board[0], erfassung_id),
    )
    origins = connection.execute(
        """
        SELECT id, wert FROM erfassung_herkunft
        WHERE erfassung_id = ? AND option_id IS NULL
        ORDER BY position, id
        """,
        (erfassung_id,),
    ).fetchall()
    for row_id, wert in origins:
        option_id = _option_for_level_label(connection, "verkauf", 1, wert, "", stamp)
        connection.execute(
            "UPDATE erfassung_herkunft SET option_id = ? WHERE id = ?",
            (option_id, row_id),
        )
    interests = connection.execute(
        """
        SELECT id, wert FROM erfassung_interesse
        WHERE erfassung_id = ? AND option_id IS NULL
        ORDER BY position, id
        """,
        (erfassung_id,),
    ).fetchall()
    for row_id, wert in interests:
        option_id = _option_for_level_label(connection, "verkauf", 2, wert, "", stamp)
        connection.execute(
            "UPDATE erfassung_interesse SET option_id = ? WHERE id = ?",
            (option_id, row_id),
        )
    details = connection.execute(
        """
        SELECT d.id, d.wert, i.option_id
        FROM erfassung_detail AS d
        JOIN erfassung_interesse AS i ON i.id = d.interesse_id
        WHERE i.erfassung_id = ? AND d.option_id IS NULL
        ORDER BY d.position, d.id
        """,
        (erfassung_id,),
    ).fetchall()
    for row_id, wert, parent_id in details:
        if parent_id is None:
            raise RuntimeError("Detail ohne Interesse")
        option_id = _child_for_parent(connection, parent_id, wert, stamp)
        connection.execute(
            "UPDATE erfassung_detail SET option_id = ? WHERE id = ?",
            (option_id, row_id),
        )


def _link_corrections(connection, stamp):
    rows = connection.execute(
        """
        SELECT id, level, parent, wert
        FROM korrektur_status
        WHERE option_id IS NULL
        ORDER BY id
        """
    ).fetchall()
    for row_id, level, parent, wert in rows:
        if level in (1, 2):
            option_id = _option_for_level_label(connection, "verkauf", level, wert, "", stamp)
        elif level == 3 and parent:
            parent_row = _option_by_label(connection, _level_of(connection, "verkauf", 2), parent)
            if parent_row is None:
                parent_id = _option_for_level_label(connection, "verkauf", 2, parent, "", stamp)
            else:
                parent_id = parent_row[0]
            option_id = _child_for_parent(connection, parent_id, wert, stamp)
        else:
            raise RuntimeError("Korrektur ohne zuordenbare Option")
        connection.execute(
            "UPDATE korrektur_status SET option_id = ? WHERE id = ?",
            (option_id, row_id),
        )


def _place_default_grid(connection):
    total, untouched = connection.execute(
        """
        SELECT COUNT(*),
               SUM(CASE WHEN grid_row = 1 AND grid_column = 1 AND grid_width = 1 THEN 1 ELSE 0 END)
        FROM board_options
        """
    ).fetchone()
    if not total or total != untouched:
        return
    level_ids = [row[0] for row in connection.execute("SELECT id FROM board_levels")]
    for level_id in level_ids:
        options = connection.execute(
            """
            SELECT id, span FROM board_options
            WHERE level_id = ?
            ORDER BY position, id
            """,
            (level_id,),
        ).fetchall()
        column = 1
        row_number = 1
        for option_id, span in options:
            width = 4 if span and span >= 2 else 2
            if column + width - 1 > 4:
                row_number += 1
                column = 1
            connection.execute(
                """
                UPDATE board_options
                SET grid_row = ?, grid_column = ?, grid_width = ?
                WHERE id = ?
                """,
                (row_number, column, width, option_id),
            )
            column += width
            if column > 4:
                row_number += 1
                column = 1


def _assert_linked(connection):
    checks = (
        "SELECT COUNT(*) FROM erfassung_herkunft WHERE option_id IS NULL",
        "SELECT COUNT(*) FROM erfassung_interesse WHERE option_id IS NULL",
        "SELECT COUNT(*) FROM erfassung_detail WHERE option_id IS NULL",
        "SELECT COUNT(*) FROM korrektur_status WHERE option_id IS NULL",
        "SELECT COUNT(*) FROM erfassungen WHERE board_id IS NULL",
    )
    for sql in checks:
        if connection.execute(sql).fetchone()[0]:
            raise RuntimeError(f"Migration unvollständig: {sql}")


def ensure_master_data(connection):
    for statement in _MASTER_SCHEMA.split(";"):
        if statement.strip():
            connection.execute(statement)
    _add_column(connection, "erfassungen", "board_id", "INTEGER REFERENCES boards(id)")
    _add_column(connection, "erfassungen", "employee_id", "INTEGER REFERENCES employees(id)")
    _add_column(connection, "erfassung_herkunft", "option_id", "INTEGER REFERENCES board_options(id)")
    _add_column(connection, "erfassung_interesse", "option_id", "INTEGER REFERENCES board_options(id)")
    _add_column(connection, "erfassung_detail", "option_id", "INTEGER REFERENCES board_options(id)")
    _add_column(connection, "korrektur_status", "option_id", "INTEGER REFERENCES board_options(id)")
    stamp = _stamp()
    _seed_sales(connection, stamp)
    capture_ids = [
        row[0]
        for row in connection.execute(
            """
            SELECT id FROM erfassungen
            WHERE board_id IS NULL
               OR id IN (SELECT erfassung_id FROM erfassung_herkunft WHERE option_id IS NULL)
               OR id IN (SELECT erfassung_id FROM erfassung_interesse WHERE option_id IS NULL)
               OR id IN (
                    SELECT i.erfassung_id
                    FROM erfassung_detail AS d
                    JOIN erfassung_interesse AS i ON i.id = d.interesse_id
                    WHERE d.option_id IS NULL
               )
            """
        )
    ]
    for erfassung_id in capture_ids:
        link_capture_options(connection, erfassung_id, stamp)
    _link_corrections(connection, stamp)
    _assert_linked(connection)
    _add_column(connection, "board_options", "grid_row", "INTEGER NOT NULL DEFAULT 1")
    _add_column(connection, "board_options", "grid_column", "INTEGER NOT NULL DEFAULT 1")
    _add_column(connection, "board_options", "grid_width", "INTEGER NOT NULL DEFAULT 1")
    _place_default_grid(connection)
