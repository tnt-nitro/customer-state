"""Änderungen der Stammdaten für die Adminoberfläche.

Zugriffskontrolle folgt in einer späteren Etage. Diese Funktionen prüfen nur
die fachlichen Regeln.
"""

from app.catalog import _fresh_key, _slug, _stamp
from app.database import connect

STATUSES = ("aktiv", "gesperrt", "ausgeschieden")


class AdminError(ValueError):
    pass


def _clean(value):
    if not isinstance(value, str):
        return ""
    return value.strip()


def _flag(value):
    return 1 if str(value) in {"1", "true", "on", "ja"} else 0


def _number(value, label):
    try:
        return int(value)
    except (TypeError, ValueError) as error:
        raise AdminError(f"{label} ist keine ganze Zahl.") from error


def _grid_cells(row, column, width):
    if row < 1:
        raise AdminError("Die Rasterzeile beginnt bei 1.")
    if column < 1 or column > 4:
        raise AdminError("Die Rasterspalte liegt zwischen 1 und 4.")
    if width < 1 or width > 4:
        raise AdminError("Die Breite liegt zwischen 1 und 4 Spalten.")
    if column + width - 1 > 4:
        raise AdminError("Der Button ragt über die vierte Spalte hinaus.")
    return {(row, column + offset) for offset in range(width)}


def _occupied_cells(connection, level_id, ignore_id=None):
    rows = connection.execute(
        """
        SELECT id, grid_row, grid_column, grid_width
        FROM board_options
        WHERE level_id = ? AND aktiv = 1
        """,
        (level_id,),
    ).fetchall()
    occupied = {}
    for option_id, row, column, width in rows:
        if option_id == ignore_id:
            continue
        for cell in _grid_cells(row, column, width):
            occupied[cell] = option_id
    return occupied


def _require_board(connection, board_id):
    row = connection.execute(
        "SELECT id, key, name, position, aktiv FROM boards WHERE id = ?",
        (board_id,),
    ).fetchone()
    if row is None:
        raise AdminError("Das Board ist unbekannt.")
    return row


def _require_level(connection, level_id):
    row = connection.execute(
        """
        SELECT l.id, l.board_id, l.position, l.title, l.sort_order, l.aktiv, b.key, b.name
        FROM board_levels AS l
        JOIN boards AS b ON b.id = l.board_id
        WHERE l.id = ?
        """,
        (level_id,),
    ).fetchone()
    if row is None:
        raise AdminError("Die Ebene ist unbekannt.")
    return row


def _require_option(connection, option_id):
    row = connection.execute(
        """
        SELECT o.id, o.level_id, o.key, o.label, o.position, o.aktiv,
               o.grid_row, o.grid_column, o.grid_width, l.board_id, l.position
        FROM board_options AS o
        JOIN board_levels AS l ON l.id = o.level_id
        WHERE o.id = ?
        """,
        (option_id,),
    ).fetchone()
    if row is None:
        raise AdminError("Der Button ist unbekannt.")
    return row


def list_boards():
    connection = connect()
    try:
        rows = connection.execute(
            """
            SELECT id, key, name, position, aktiv
            FROM boards
            ORDER BY position, id
            """
        ).fetchall()
    finally:
        connection.close()
    return [
        {"id": row[0], "key": row[1], "name": row[2], "position": row[3], "aktiv": row[4]}
        for row in rows
    ]


def update_board(board_id, name, position, aktiv):
    name = _clean(name)
    if not name:
        raise AdminError("Der sichtbare Name darf nicht leer sein.")
    position = _number(position, "Die Sortierung")
    if position < 1:
        raise AdminError("Die Sortierung beginnt bei 1.")
    connection = connect()
    try:
        _require_board(connection, board_id)
        connection.execute(
            """
            UPDATE boards
            SET name = ?, position = ?, aktiv = ?, updated_at = ?
            WHERE id = ?
            """,
            (name, position, _flag(aktiv), _stamp(), board_id),
        )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def list_levels(board_id):
    connection = connect()
    try:
        board = _require_board(connection, board_id)
        rows = connection.execute(
            """
            SELECT id, position, title, sort_order, aktiv
            FROM board_levels
            WHERE board_id = ?
            ORDER BY position
            """,
            (board_id,),
        ).fetchall()
    finally:
        connection.close()
    return {
        "id": board[0],
        "key": board[1],
        "name": board[2],
    }, [
        {
            "id": row[0],
            "position": row[1],
            "title": row[2],
            "sort_order": row[3],
            "aktiv": row[4],
        }
        for row in rows
    ]


def update_level(level_id, title, sort_order, aktiv):
    title = _clean(title)
    if not title:
        raise AdminError("Die Überschrift darf nicht leer sein.")
    sort_order = _number(sort_order, "Die Sortierung")
    if sort_order < 1:
        raise AdminError("Die Sortierung beginnt bei 1.")
    connection = connect()
    try:
        _require_level(connection, level_id)
        connection.execute(
            """
            UPDATE board_levels
            SET title = ?, sort_order = ?, aktiv = ?, updated_at = ?
            WHERE id = ?
            """,
            (title, sort_order, _flag(aktiv), _stamp(), level_id),
        )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def _parents_for(connection, board_id, child_id=None):
    rows = connection.execute(
        """
        SELECT o.id, o.label, o.aktiv,
               CASE WHEN link.child_option_id IS NULL THEN 0 ELSE 1 END
        FROM board_options AS o
        JOIN board_levels AS l ON l.id = o.level_id
        LEFT JOIN board_option_parents AS link
            ON link.parent_option_id = o.id AND link.child_option_id = ?
        WHERE l.board_id = ? AND l.position = 2
        ORDER BY o.position, o.id
        """,
        (child_id or 0, board_id),
    ).fetchall()
    return [
        {"id": row[0], "label": row[1], "aktiv": row[2], "selected": bool(row[3])}
        for row in rows
    ]


def _button_dict(row, parents):
    return {
        "id": row[0],
        "key": row[1],
        "label": row[2],
        "position": row[3],
        "aktiv": row[4],
        "grid_row": row[5],
        "grid_column": row[6],
        "grid_width": row[7],
        "parents": parents,
    }


def preview_cells(buttons):
    active = [button for button in buttons if button["aktiv"]]
    if not active:
        return []
    max_row = max(button["grid_row"] for button in active)
    anchors = {}
    covered = set()
    for button in active:
        for offset in range(button["grid_width"]):
            cell = (button["grid_row"], button["grid_column"] + offset)
            if offset == 0:
                anchors[cell] = button
            else:
                covered.add(cell)
    cells = []
    for row in range(1, max_row + 1):
        for column in range(1, 5):
            if (row, column) in anchors:
                cells.append({"kind": "button", "row": row, "column": column, "button": anchors[(row, column)]})
            elif (row, column) not in covered:
                cells.append({"kind": "empty", "row": row, "column": column, "button": None})
    return cells


def list_buttons(level_id):
    connection = connect()
    try:
        level = _require_level(connection, level_id)
        rows = connection.execute(
            """
            SELECT id, key, label, position, aktiv, grid_row, grid_column, grid_width
            FROM board_options
            WHERE level_id = ?
            ORDER BY position, id
            """,
            (level_id,),
        ).fetchall()
        buttons = []
        for row in rows:
            parents = _parents_for(connection, level[1], row[0]) if level[2] == 3 else []
            buttons.append(_button_dict(row, parents))
        parent_choices = _parents_for(connection, level[1]) if level[2] == 3 else []
    finally:
        connection.close()
    return {
        "id": level[0],
        "board_id": level[1],
        "position": level[2],
        "title": level[3],
        "board_key": level[6],
        "board_name": level[7],
    }, buttons, parent_choices


def _validate_parents(connection, board_id, parent_ids):
    if not parent_ids:
        raise AdminError("Ein Button der dritten Ebene braucht mindestens eine Zuordnung.")
    allowed = {
        row[0]
        for row in connection.execute(
            """
            SELECT o.id
            FROM board_options AS o
            JOIN board_levels AS l ON l.id = o.level_id
            WHERE l.board_id = ? AND l.position = 2
            """,
            (board_id,),
        )
    }
    chosen = []
    for raw in parent_ids:
        number = _number(raw, "Die Zuordnung")
        if number not in allowed or number in chosen:
            raise AdminError("Die Zuordnung gehört nicht zu Ebene 2 dieses Boards.")
        chosen.append(number)
    return chosen


def _store_parents(connection, child_id, parent_ids):
    connection.execute(
        "DELETE FROM board_option_parents WHERE child_option_id = ?",
        (child_id,),
    )
    for index, parent_id in enumerate(parent_ids, start=1):
        connection.execute(
            """
            INSERT INTO board_option_parents (parent_option_id, child_option_id, position)
            VALUES (?, ?, ?)
            """,
            (parent_id, child_id, index),
        )


def _guard_grid(connection, level_id, option_id, row, column, width, aktiv):
    cells = _grid_cells(row, column, width)
    if not aktiv:
        return cells
    occupied = _occupied_cells(connection, level_id, ignore_id=option_id)
    if any(cell in occupied for cell in cells):
        raise AdminError("Diese Rasterzellen sind bereits von einem aktiven Button belegt.")
    return cells


def create_button(level_id, label, grid_row, grid_column, grid_width, parent_ids=None, sort_order=None):
    label = _clean(label)
    if not label:
        raise AdminError("Die Bezeichnung darf nicht leer sein.")
    row = _number(grid_row, "Die Rasterzeile")
    column = _number(grid_column, "Die Rasterspalte")
    width = _number(grid_width, "Die Breite")
    connection = connect()
    try:
        level = _require_level(connection, level_id)
        _guard_grid(connection, level_id, None, row, column, width, True)
        parents = []
        if level[2] == 3:
            parents = _validate_parents(connection, level[1], parent_ids or [])
        elif parent_ids:
            raise AdminError("Zuordnungen gibt es nur auf Ebene 3.")
        if sort_order in (None, ""):
            current = connection.execute(
                "SELECT COALESCE(MAX(position), 0) FROM board_options WHERE level_id = ?",
                (level_id,),
            ).fetchone()[0]
            position = current + 1
        else:
            position = _number(sort_order, "Die Sortierung")
            if position < 1:
                raise AdminError("Die Sortierung beginnt bei 1.")
        key = _fresh_key(connection, level_id, _slug(label))
        stamp = _stamp()
        cursor = connection.execute(
            """
            INSERT INTO board_options (
                level_id, key, label, position, span, grid_row, grid_column, grid_width,
                aktiv, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, 1, ?, ?, ?, 1, ?, ?)
            """,
            (level_id, key, label, position, row, column, width, stamp, stamp),
        )
        option_id = cursor.lastrowid
        if parents:
            _store_parents(connection, option_id, parents)
        connection.commit()
        return option_id
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def update_button(option_id, label, sort_order, aktiv, grid_row, grid_column, grid_width, parent_ids=None):
    label = _clean(label)
    if not label:
        raise AdminError("Die Bezeichnung darf nicht leer sein.")
    position = _number(sort_order, "Die Sortierung")
    if position < 1:
        raise AdminError("Die Sortierung beginnt bei 1.")
    row = _number(grid_row, "Die Rasterzeile")
    column = _number(grid_column, "Die Rasterspalte")
    width = _number(grid_width, "Die Breite")
    active = _flag(aktiv)
    connection = connect()
    try:
        option = _require_option(connection, option_id)
        level = _require_level(connection, option[1])
        _guard_grid(connection, option[1], option_id, row, column, width, active)
        parents = None
        if level[2] == 3:
            parents = _validate_parents(connection, level[1], parent_ids or [])
        stamp = _stamp()
        connection.execute(
            """
            UPDATE board_options
            SET label = ?, position = ?, aktiv = ?, grid_row = ?, grid_column = ?,
                grid_width = ?, updated_at = ?
            WHERE id = ?
            """,
            (label, position, active, row, column, width, stamp, option_id),
        )
        if parents is not None:
            _store_parents(connection, option_id, parents)
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def shift_button(option_id, direction):
    connection = connect()
    try:
        option = _require_option(connection, option_id)
        row, column, width = option[6], option[7], option[8]
        if direction == "links":
            column -= 1
        elif direction == "rechts":
            column += 1
        elif direction == "hoch":
            row -= 1
        elif direction == "runter":
            row += 1
        else:
            raise AdminError("Diese Richtung ist unbekannt.")
        _guard_grid(connection, option[1], option_id, row, column, width, option[5])
        connection.execute(
            """
            UPDATE board_options
            SET grid_row = ?, grid_column = ?, updated_at = ?
            WHERE id = ?
            """,
            (row, column, _stamp(), option_id),
        )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def _employee_dict(row, boards):
    return {
        "id": row[0],
        "name": row[1],
        "login_name": row[2] or "",
        "status": row[3],
        "is_admin": row[4],
        "pin_set": row[5] is not None and row[5] != "",
        "boards": boards,
    }


def list_employees():
    connection = connect()
    try:
        people = connection.execute(
            """
            SELECT id, name, login_name, status, is_admin, pin_hash
            FROM employees
            ORDER BY CASE status WHEN 'ausgeschieden' THEN 1 ELSE 0 END, name, id
            """
        ).fetchall()
        boards = connection.execute(
            """
            SELECT eb.employee_id, b.id, b.name
            FROM employee_boards AS eb
            JOIN boards AS b ON b.id = eb.board_id
            ORDER BY b.position, b.id
            """
        ).fetchall()
    finally:
        connection.close()
    by_employee = {}
    for employee_id, board_id, board_name in boards:
        by_employee.setdefault(employee_id, []).append({"id": board_id, "name": board_name})
    return [_employee_dict(row, by_employee.get(row[0], [])) for row in people]


def _clean_login(value):
    login = _clean(value)
    return login or None


def _validate_boards(connection, board_ids):
    if not board_ids:
        raise AdminError("Mindestens ein Board muss zugeordnet sein.")
    allowed = {row[0] for row in connection.execute("SELECT id FROM boards")}
    chosen = []
    for raw in board_ids:
        number = _number(raw, "Das Board")
        if number not in allowed or number in chosen:
            raise AdminError("Ein zugeordnetes Board ist unbekannt.")
        chosen.append(number)
    return chosen


def _validate_status(status):
    if status not in STATUSES:
        raise AdminError("Der Status ist unbekannt.")
    return status


def _login_free(connection, login, employee_id=None):
    if login is None:
        return
    row = connection.execute(
        "SELECT id FROM employees WHERE login_name = ?",
        (login,),
    ).fetchone()
    if row and row[0] != employee_id:
        raise AdminError("Dieser Loginname ist bereits vergeben.")


def create_employee(name, login_name, board_ids, is_admin):
    name = _clean(name)
    if not name:
        raise AdminError("Der Name darf nicht leer sein.")
    login = _clean_login(login_name)
    connection = connect()
    try:
        _login_free(connection, login)
        chosen = _validate_boards(connection, board_ids)
        stamp = _stamp()
        cursor = connection.execute(
            """
            INSERT INTO employees (
                name, login_name, pin_hash, status, is_admin, created_at, updated_at
            )
            VALUES (?, ?, NULL, 'aktiv', ?, ?, ?)
            """,
            (name, login, _flag(is_admin), stamp, stamp),
        )
        employee_id = cursor.lastrowid
        connection.executemany(
            "INSERT INTO employee_boards (employee_id, board_id) VALUES (?, ?)",
            [(employee_id, board_id) for board_id in chosen],
        )
        connection.commit()
        return employee_id
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def update_employee(employee_id, name, login_name, status, is_admin, board_ids):
    name = _clean(name)
    if not name:
        raise AdminError("Der Name darf nicht leer sein.")
    login = _clean_login(login_name)
    status = _validate_status(status)
    connection = connect()
    try:
        row = connection.execute("SELECT id FROM employees WHERE id = ?", (employee_id,)).fetchone()
        if row is None:
            raise AdminError("Der Mitarbeiter ist unbekannt.")
        _login_free(connection, login, employee_id)
        chosen = _validate_boards(connection, board_ids)
        connection.execute(
            """
            UPDATE employees
            SET name = ?, login_name = ?, status = ?, is_admin = ?, updated_at = ?
            WHERE id = ?
            """,
            (name, login, status, _flag(is_admin), _stamp(), employee_id),
        )
        connection.execute("DELETE FROM employee_boards WHERE employee_id = ?", (employee_id,))
        connection.executemany(
            "INSERT INTO employee_boards (employee_id, board_id) VALUES (?, ?)",
            [(employee_id, board_id) for board_id in chosen],
        )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def reset_pin(employee_id):
    connection = connect()
    try:
        row = connection.execute(
            "SELECT id, pin_hash FROM employees WHERE id = ?",
            (employee_id,),
        ).fetchone()
        if row is None:
            raise AdminError("Der Mitarbeiter ist unbekannt.")
        connection.execute(
            "UPDATE employees SET pin_hash = NULL, updated_at = ? WHERE id = ?",
            (_stamp(), employee_id),
        )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()
