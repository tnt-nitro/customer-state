"""Anmeldung nur für Zugriff und Boards.

Die Session enthält die Mitarbeiter-ID ausschließlich zur Rechteprüfung.
Sie wird nicht in Erfassungen, Zeitmessungen, Korrekturen oder Auswertungen
übernommen. erfassungen.employee_id bleibt unbenutzt und NULL.
"""

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta

from app.database import BERLIN, connect

COOKIE = "cs_session"
PIN_ITERATIONS = 210_000
MAX_PIN_FAILURES = 5
PIN_WINDOW = timedelta(minutes=10)
PIN_LOCK = timedelta(seconds=60)

_sessions = {}
_failures = {}


def berlin_day(moment):
    return moment.astimezone(BERLIN).date()


def day_end(moment):
    local = moment.astimezone(BERLIN)
    next_day = local.date() + timedelta(days=1)
    return datetime(next_day.year, next_day.month, next_day.day, tzinfo=BERLIN)


def seconds_until_day_end(moment):
    return max(int((day_end(moment) - moment.astimezone(BERLIN)).total_seconds()), 1)


def same_workday(login_at, now):
    return berlin_day(login_at) == berlin_day(now)


def pin_valid(pin):
    return isinstance(pin, str) and len(pin) == 4 and pin.isdigit()


def hash_pin(pin):
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", pin.encode("utf-8"), salt, PIN_ITERATIONS)
    return f"pbkdf2_sha256${PIN_ITERATIONS}${salt.hex()}${digest.hex()}"


def pin_matches(pin, stored):
    try:
        algorithm, iterations, salt_hex, digest_hex = stored.split("$")
        if algorithm != "pbkdf2_sha256":
            return False
        digest = hashlib.pbkdf2_hmac(
            "sha256",
            pin.encode("utf-8"),
            bytes.fromhex(salt_hex),
            int(iterations),
        )
    except (AttributeError, TypeError, ValueError):
        return False
    return hmac.compare_digest(digest.hex(), digest_hex)


def _prune_failures(employee_id, now):
    recent = [moment for moment in _failures.get(employee_id, []) if now - moment < PIN_WINDOW]
    if recent:
        _failures[employee_id] = recent
    else:
        _failures.pop(employee_id, None)
    return recent


def pin_locked(employee_id, now):
    recent = _prune_failures(employee_id, now)
    if len(recent) < MAX_PIN_FAILURES:
        return False
    return now - recent[-1] < PIN_LOCK


def note_pin_failure(employee_id, now):
    recent = _prune_failures(employee_id, now)
    recent.append(now)
    _failures[employee_id] = recent


def clear_pin_failures(employee_id):
    _failures.pop(employee_id, None)


def clear_sessions():
    _sessions.clear()
    _failures.clear()


def active_employees():
    connection = connect()
    try:
        rows = connection.execute(
            """
            SELECT id, name
            FROM employees
            WHERE status = 'aktiv'
            ORDER BY name, id
            """
        ).fetchall()
    finally:
        connection.close()
    return [{"id": row[0], "name": row[1]} for row in rows]


def employee_record(employee_id):
    connection = connect()
    try:
        row = connection.execute(
            """
            SELECT id, name, status, is_admin, pin_hash
            FROM employees
            WHERE id = ?
            """,
            (employee_id,),
        ).fetchone()
    finally:
        connection.close()
    if row is None:
        return None
    return {
        "id": row[0],
        "name": row[1],
        "status": row[2],
        "is_admin": bool(row[3]),
        "pin_set": row[4] not in (None, ""),
        "pin_hash": row[4],
    }


def allowed_boards(employee_id):
    connection = connect()
    try:
        rows = connection.execute(
            """
            SELECT b.id, b.key, b.name
            FROM employee_boards AS eb
            JOIN boards AS b ON b.id = eb.board_id
            WHERE eb.employee_id = ? AND b.aktiv = 1
            ORDER BY b.position, b.id
            """,
            (employee_id,),
        ).fetchall()
    finally:
        connection.close()
    return [{"id": row[0], "key": row[1], "name": row[2]} for row in rows]


def set_pin(employee_id, pin):
    from app.catalog import _stamp

    connection = connect()
    try:
        row = connection.execute(
            "SELECT status, pin_hash FROM employees WHERE id = ?",
            (employee_id,),
        ).fetchone()
        if row is None or row[0] != "aktiv":
            raise ValueError("Anmeldung nicht möglich.")
        if row[1] not in (None, ""):
            raise ValueError("Anmeldung nicht möglich.")
        connection.execute(
            "UPDATE employees SET pin_hash = ?, updated_at = ? WHERE id = ?",
            (hash_pin(pin), _stamp(), employee_id),
        )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def open_session(employee_id, now):
    token = secrets.token_urlsafe(32)
    _sessions[token] = {"employee_id": employee_id, "workday": berlin_day(now).isoformat()}
    return token


def drop_session(token):
    if token:
        _sessions.pop(token, None)


def session_user(token, now):
    record = _sessions.get(token)
    if not record:
        return None
    if record["workday"] != berlin_day(now).isoformat():
        _sessions.pop(token, None)
        return None
    person = employee_record(record["employee_id"])
    if person is None or person["status"] != "aktiv":
        _sessions.pop(token, None)
        return None
    person.pop("pin_hash", None)
    return person
