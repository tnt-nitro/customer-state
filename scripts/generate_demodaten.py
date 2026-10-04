"""Demodaten 2025 für einen spezialisierten ländlichen High-End-Fahrradhändler.

Schreibt neue Erfassungen in die bestehende SQLite-Datenbank. Bestehende
Datensätze, insbesondere ID 5 und ID 8, werden weder geändert noch gelöscht.
Ein zweiter Lauf bricht ab, sobald bereits Erfassungen aus 2025 vorliegen.
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path
from random import Random
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.database import BERLIN, DB_PATH  # noqa: E402

SEED = 20250101
PRESERVE_IDS = (5, 8)
BASE_CONTACTS = 11.0
DAY_CAP = 40

LEVEL1 = (
    "Empfehlung",
    "KI",
    "Google",
    "Leasingportal",
    "Arbeit",
    "Sonstiges",
)

# Entspricht den Buttons in templates/index.html und static/selection.js.
INTERESTS = {
    "MTB": ["Specialized", "Leasing", "Kauf", "Reparatur"],
    "E-MTB": ["Specialized", "PIVOT", "AMFLOW", "Leasing", "Kauf", "Reparatur"],
    "Gravel": ["PIVOT", "Specialized", "Leasing", "Kauf", "Reparatur"],
    "E-Gravel": ["Specialized", "PIVOT", "Leasing", "Kauf", "Reparatur"],
    "Kinderrad": ["woom", "Leasing", "Kauf", "Reparatur"],
    "Lastenrad": ["Riese & Müller", "Leasing", "Kauf", "Reparatur"],
    "Trekking": ["Riese & Müller", "Specialized", "Leasing", "Kauf", "Reparatur"],
    "Trekking vollgefedert": [
        "Riese & Müller",
        "Specialized",
        "AMFLOW",
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
    "Werkstatt": [
        "Inspektion",
        "Reparatur",
        "Reklamation",
        "Tuning",
        "Umbau",
        "Diagnose/Fehlersuche",
        "Unfall/Schaden",
        "Beratung",
        "Sonstiges",
    ],
}

BIKES = (
    "MTB",
    "E-MTB",
    "Gravel",
    "E-Gravel",
    "Kinderrad",
    "Lastenrad",
    "Trekking",
    "Trekking vollgefedert",
)

# Gesetzliche Feiertage in Hessen 2025. Keine kommunalen Feiertage.
HOLIDAYS = {
    date(2025, 1, 1): "Neujahr",
    date(2025, 4, 18): "Karfreitag",
    date(2025, 4, 21): "Ostermontag",
    date(2025, 5, 1): "Tag der Arbeit",
    date(2025, 5, 29): "Christi Himmelfahrt",
    date(2025, 6, 9): "Pfingstmontag",
    date(2025, 6, 19): "Fronleichnam",
    date(2025, 10, 3): "Tag der Deutschen Einheit",
    date(2025, 12, 25): "1. Weihnachtstag",
    date(2025, 12, 26): "2. Weihnachtstag",
}

# Schulferien Hessen 2025 laut Kultusministerium, erster bis letzter Ferientag.
SCHOOL_HOLIDAYS = (
    (date(2025, 1, 1), date(2025, 1, 10), "weihnachten"),
    (date(2025, 4, 7), date(2025, 4, 21), "ostern"),
    (date(2025, 7, 7), date(2025, 8, 15), "sommer"),
    (date(2025, 10, 6), date(2025, 10, 18), "herbst"),
    (date(2025, 12, 22), date(2025, 12, 31), "weihnachten"),
)

# Werktag zwischen Feiertag und Wochenende.
BRIDGE_DAYS = {
    date(2025, 5, 2),
    date(2025, 5, 30),
    date(2025, 6, 20),
    date(2025, 10, 2),
}

WEEKDAY_FACTOR = {
    0: 0.74,
    1: 0.90,
    2: 1.00,
    3: 1.08,
    4: 1.20,
    5: 1.18,
}

MONTH_FACTOR = {
    1: 0.58,
    2: 0.68,
    3: 0.95,
    4: 1.22,
    5: 1.38,
    6: 1.28,
    7: 1.12,
    8: 0.92,
    9: 1.18,
    10: 0.88,
    11: 0.62,
    12: 0.74,
}

WEEKDAY_HOURS = {
    10: 7,
    11: 11,
    12: 9,
    13: 9,
    14: 13,
    15: 15,
    16: 16,
    17: 14,
    18: 6,
}

SATURDAY_HOURS = {
    9: 16,
    10: 26,
    11: 26,
    12: 20,
    13: 12,
}

BASE_INTEREST = {
    "Werkstatt": 34,
    "E-MTB": 16,
    "Trekking": 9,
    "Gravel": 8,
    "Bekleidung": 8,
    "MTB": 6,
    "E-Gravel": 5,
    "Lastenrad": 5,
    "Trekking vollgefedert": 5,
    "Kinderrad": 4,
}

BRANDS = {
    "MTB": {"Specialized": 1},
    "E-MTB": {"Specialized": 46, "PIVOT": 32, "AMFLOW": 22},
    "Gravel": {"PIVOT": 55, "Specialized": 45},
    "E-Gravel": {"Specialized": 60, "PIVOT": 40},
    "Kinderrad": {"woom": 1},
    "Lastenrad": {"Riese & Müller": 1},
    "Trekking": {"Riese & Müller": 62, "Specialized": 38},
    "Trekking vollgefedert": {
        "Riese & Müller": 50,
        "Specialized": 30,
        "AMFLOW": 20,
    },
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
    "",
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

WEATHER_LABEL = {
    "klar": "klar",
    "bewoelkt": "bewölkt",
    "regen": "Regen",
    "ungemuetlich": "ungemütlich",
}


def school_holiday(day):
    for start, end, name in SCHOOL_HOLIDAYS:
        if start <= day <= end:
            return name
    return None


def weighted(rng, weights):
    total = sum(weights.values())
    pick = rng.random() * total
    running = 0.0
    for key, weight in weights.items():
        running += weight
        if pick <= running:
            return key
    return next(reversed(weights))


def poisson(rng, expected):
    if expected <= 0:
        return 0
    limit = pow(2.718281828, -expected)
    count = 0
    product = 1.0
    while product > limit:
        count += 1
        product *= rng.random()
    return count - 1


def weather_for(rng, month):
    rain = {
        1: 0.42,
        2: 0.38,
        3: 0.34,
        4: 0.30,
        5: 0.28,
        6: 0.26,
        7: 0.28,
        8: 0.26,
        9: 0.28,
        10: 0.34,
        11: 0.42,
        12: 0.44,
    }[month]
    clear = {
        1: 0.12,
        2: 0.16,
        3: 0.22,
        4: 0.28,
        5: 0.34,
        6: 0.36,
        7: 0.38,
        8: 0.36,
        9: 0.30,
        10: 0.22,
        11: 0.12,
        12: 0.10,
    }[month]
    roll = rng.random()
    if roll < rain * 0.28:
        return "ungemuetlich"
    if roll < rain:
        return "regen"
    if roll < rain + clear:
        return "klar"
    return "bewoelkt"


def traffic_factor(day, weather):
    factor = WEEKDAY_FACTOR[day.weekday()] * MONTH_FACTOR[day.month]
    holiday_name = school_holiday(day)
    if holiday_name == "sommer":
        factor *= 0.84
    elif holiday_name == "ostern":
        factor *= 0.92
    elif holiday_name == "herbst":
        factor *= 0.94
    elif holiday_name == "weihnachten":
        factor *= 0.78
    if day in BRIDGE_DAYS:
        factor *= 0.72
    if day.month == 12 and day.day == 24:
        factor *= 0.48
    if day.month == 12 and day.day == 31:
        factor *= 0.42
    if day.month == 12 and 15 <= day.day <= 23:
        factor *= 1.10
    weather_factor = {
        "klar": 1.12,
        "bewoelkt": 1.00,
        "regen": 0.84,
        "ungemuetlich": 0.70,
    }[weather]
    if day.weekday() == 5 and weather in ("regen", "ungemuetlich"):
        weather_factor *= 0.78
    return factor * weather_factor


def hour_weights(rng, weekday):
    source = SATURDAY_HOURS if weekday == 5 else WEEKDAY_HOURS
    weights = {hour: float(weight) for hour, weight in source.items()}
    if weekday != 5:
        swing = rng.uniform(0.72, 1.28)
        weights[12] *= swing
        weights[13] *= rng.uniform(0.72, 1.28)
    return weights


def minute_for(rng, hour, weekday):
    declining = (weekday != 5 and hour == 18) or (weekday == 5 and hour == 13)
    if declining:
        return int(rng.triangular(0, 59, 10))
    return rng.randrange(60)


def interest_weights(month, weather, school):
    weights = dict(BASE_INTEREST)
    sport = ("MTB", "E-MTB", "Gravel", "E-Gravel")
    if month in (11, 12, 1, 2):
        weights["Werkstatt"] *= 1.85
        for bike in BIKES:
            weights[bike] *= 0.48
        weights["Bekleidung"] *= 1.15
        weights["Kinderrad"] *= 1.45 if month == 12 else 0.70
    if month in (3, 4, 5):
        for bike in sport:
            weights[bike] *= 1.45
        weights["Trekking"] *= 1.25
        weights["Trekking vollgefedert"] *= 1.20
        weights["Kinderrad"] *= 1.35
        weights["Werkstatt"] *= 0.85
    if month in (6, 7, 8):
        weights["E-MTB"] *= 1.25
        weights["Gravel"] *= 1.20
        weights["E-Gravel"] *= 1.15
        weights["Lastenrad"] *= 1.20
        weights["Werkstatt"] *= 0.90
    if month in (9, 10):
        weights["Trekking"] *= 1.30
        weights["Trekking vollgefedert"] *= 1.25
        weights["Gravel"] *= 1.15
        weights["Werkstatt"] *= 1.25
        weights["Bekleidung"] *= 1.20
    if weather in ("regen", "ungemuetlich"):
        weights["Werkstatt"] *= 1.40
        weights["Bekleidung"] *= 1.15
        for bike in sport:
            weights[bike] *= 0.70
    elif weather == "klar":
        for bike in sport + ("Trekking",):
            weights[bike] *= 1.12
        weights["Werkstatt"] *= 0.92
    if school == "sommer":
        weights["Kinderrad"] *= 0.65
        weights["Lastenrad"] *= 0.85
        weights["Werkstatt"] *= 1.10
    elif school == "ostern":
        weights["Kinderrad"] *= 1.15
    elif school == "herbst":
        weights["Werkstatt"] *= 1.15
        weights["Bekleidung"] *= 1.10
    elif school == "weihnachten":
        weights["Kinderrad"] *= 1.40
        weights["Bekleidung"] *= 1.25
        weights["Werkstatt"] *= 1.15
    return weights


def herkunft_weights(level2, month):
    if level2 == "Werkstatt":
        weights = {
            "Empfehlung": 36,
            "Google": 24,
            "Leasingportal": 3,
            "Arbeit": 4,
            "KI": 5,
            "Sonstiges": 18,
        }
    elif level2 == "Bekleidung":
        weights = {
            "Empfehlung": 28,
            "Google": 26,
            "Leasingportal": 2,
            "Arbeit": 3,
            "KI": 6,
            "Sonstiges": 22,
        }
    elif level2 == "Kinderrad":
        weights = {
            "Empfehlung": 34,
            "Google": 28,
            "Leasingportal": 6,
            "Arbeit": 4,
            "KI": 5,
            "Sonstiges": 16,
        }
    elif level2 in ("E-MTB", "Lastenrad", "Trekking vollgefedert", "E-Gravel"):
        weights = {
            "Empfehlung": 22,
            "Google": 18,
            "Leasingportal": 28,
            "Arbeit": 12,
            "KI": 7,
            "Sonstiges": 10,
        }
    else:
        weights = {
            "Empfehlung": 28,
            "Google": 22,
            "Leasingportal": 16,
            "Arbeit": 8,
            "KI": 6,
            "Sonstiges": 14,
        }
    if month >= 7:
        weights["KI"] *= 1.45
    return weights


def clothing_weights(month, weather):
    weights = {
        "Helm": 14,
        "Trikot": 12,
        "Radhose": 10,
        "Handschuhe": 8,
        "Schuhe": 8,
        "Regenbekleidung": 8,
        "Jacke/Weste": 8,
        "Brille": 6,
        "Sonstiges": 8,
    }
    if month in (11, 12, 1, 2, 3):
        weights["Jacke/Weste"] *= 2.2
        weights["Handschuhe"] *= 1.6
        weights["Trikot"] *= 0.5
        weights["Radhose"] *= 0.5
    if month in (5, 6, 7, 8):
        weights["Trikot"] *= 1.8
        weights["Radhose"] *= 1.7
        weights["Brille"] *= 1.4
        weights["Jacke/Weste"] *= 0.6
    if weather in ("regen", "ungemuetlich") or month in (4, 10, 11):
        weights["Regenbekleidung"] *= 2.0
    return weights


def workshop_weights(month):
    weights = {
        "Inspektion": 24,
        "Reparatur": 26,
        "Diagnose/Fehlersuche": 14,
        "Beratung": 10,
        "Tuning": 8,
        "Umbau": 7,
        "Reklamation": 5,
        "Unfall/Schaden": 4,
        "Sonstiges": 4,
    }
    if month in (11, 12, 1, 2, 3):
        weights["Inspektion"] *= 1.6
        weights["Unfall/Schaden"] *= 0.6
    if month in (5, 6, 7, 8):
        weights["Unfall/Schaden"] *= 1.5
        weights["Tuning"] *= 1.3
    return weights


def choose_details(rng, level2, herkunft, weather, month):
    chosen = set()
    if level2 == "Werkstatt":
        weights = workshop_weights(month)
        chosen.add(weighted(rng, weights))
        if rng.random() < 0.28:
            weights.pop(next(iter(chosen)), None)
            if weights:
                chosen.add(weighted(rng, weights))
    elif level2 == "Bekleidung":
        weights = clothing_weights(month, weather)
        count = 1 if rng.random() < 0.62 else 2
        if rng.random() < 0.08:
            count = 3
        for _ in range(count):
            if not weights:
                break
            item = weighted(rng, weights)
            chosen.add(item)
            del weights[item]
    else:
        chosen.add(weighted(rng, BRANDS[level2]))
        if herkunft in ("Leasingportal", "Arbeit"):
            if rng.random() < 0.88:
                chosen.add("Leasing")
            elif rng.random() < 0.55:
                chosen.add("Kauf")
        else:
            roll = rng.random()
            if roll < 0.48:
                chosen.add("Kauf")
            elif roll < 0.78:
                chosen.add("Leasing")
        if rng.random() < 0.08:
            chosen.add("Reparatur")
    ordered = [label for label in INTERESTS[level2] if label in chosen]
    if not ordered:
        raise RuntimeError(f"Keine Details für {level2}")
    return ordered


def opening_hours(weekday):
    if weekday == 5:
        return 9, 14
    if weekday == 6:
        return None
    return 10, 19


def choose_capture(rng, month, weather, school):
    names = [weighted(rng, interest_weights(month, weather, school))]
    if rng.random() < 0.18:
        if names[0] != "Werkstatt" and rng.random() < 0.6:
            names.append("Werkstatt")
        else:
            extra = interest_weights(month, weather, school)
            extra.pop(names[0], None)
            if extra:
                names.append(weighted(rng, extra))
    names = [name for name in INTERESTS if name in names]
    origins = [weighted(rng, herkunft_weights(names[0], month))]
    if rng.random() < 0.22:
        extra = herkunft_weights(names[0], month)
        extra.pop(origins[0], None)
        if extra:
            origins.append(weighted(rng, extra))
    origins = [name for name in LEVEL1 if name in origins]
    if "Leasingportal" in origins:
        channel = "Leasingportal"
    elif "Arbeit" in origins:
        channel = "Arbeit"
    else:
        channel = origins[0]
    blocks = [
        {
            "value": name,
            "details": choose_details(rng, name, channel, weather, month),
        }
        for name in names
    ]
    return origins, blocks


def validate_record(record):
    moment = record["moment"]
    weekday = moment.weekday()
    hours = opening_hours(weekday)
    if hours is None or moment.date() in HOLIDAYS:
        raise RuntimeError(f"Erfassung außerhalb eines Öffnungstags: {moment}")
    start, end = hours
    if not (start <= moment.hour < end):
        raise RuntimeError(f"Erfassung außerhalb der Öffnungszeit: {moment}")
    if not record["level1"] or any(item not in LEVEL1 for item in record["level1"]):
        raise RuntimeError(record["level1"])
    seen = set()
    for block in record["level2"]:
        if block["value"] not in INTERESTS or block["value"] in seen:
            raise RuntimeError(block["value"])
        seen.add(block["value"])
        allowed = INTERESTS[block["value"]]
        if not block["details"] or any(item not in allowed for item in block["details"]):
            raise RuntimeError(block["details"])
        if block["details"] != [item for item in allowed if item in block["details"]]:
            raise RuntimeError("Detailreihenfolge weicht von der Erfassung ab")
    expected = moment.astimezone(BERLIN).isoformat(sep=" ", timespec="seconds")
    if record["created_at"] != expected:
        raise RuntimeError(record["created_at"])


def build_year(rng):
    records = []
    days = []
    day = date(2025, 1, 1)
    last = date(2025, 12, 31)
    while day <= last:
        weekday = day.weekday()
        if weekday == 6 or day in HOLIDAYS:
            days.append(
                {
                    "date": day,
                    "open": False,
                    "reason": "sonntag" if weekday == 6 else "feiertag",
                    "contacts": 0,
                }
            )
            day += timedelta(days=1)
            continue

        weather = weather_for(rng, day.month)
        school = school_holiday(day)
        expected = BASE_CONTACTS * traffic_factor(day, weather)
        expected *= rng.uniform(0.90, 1.10)
        count = poisson(rng, expected)
        if expected >= 4 and count == 0:
            count = 1
        count = min(count, DAY_CAP)
        hours = hour_weights(rng, weekday)
        for _ in range(count):
            hour = weighted(rng, hours)
            minute = minute_for(rng, hour, weekday)
            second = rng.randrange(60)
            moment = datetime(
                day.year,
                day.month,
                day.day,
                hour,
                minute,
                second,
                tzinfo=BERLIN,
            )
            level1, level2 = choose_capture(rng, day.month, weather, school)
            record = {
                "moment": moment,
                "created_at": moment.isoformat(sep=" ", timespec="seconds"),
                "level1": level1,
                "level2": level2,
                "weather": weather,
                "school": school or "",
            }
            validate_record(record)
            records.append(record)
        days.append(
            {
                "date": day,
                "open": True,
                "weather": weather,
                "school": school or "",
                "contacts": count,
                "expected": expected,
            }
        )
        day += timedelta(days=1)
    return records, days


def snapshot(connection):
    found = {}
    for row_id in PRESERVE_IDS:
        head = connection.execute(
            """
            SELECT id, created_at, is_demo, started_at, level1_completed_at,
                   level2_completed_at, completed_at
            FROM erfassungen WHERE id = ?
            """,
            (row_id,),
        ).fetchone()
        herkunft = connection.execute(
            """
            SELECT wert FROM erfassung_herkunft
            WHERE erfassung_id = ?
            ORDER BY position, id
            """,
            (row_id,),
        ).fetchall()
        blocks = []
        for interesse_id, wert in connection.execute(
            """
            SELECT id, wert FROM erfassung_interesse
            WHERE erfassung_id = ?
            ORDER BY position, id
            """,
            (row_id,),
        ):
            details = connection.execute(
                """
                SELECT wert FROM erfassung_detail
                WHERE interesse_id = ?
                ORDER BY position, id
                """,
                (interesse_id,),
            ).fetchall()
            blocks.append((wert, tuple(details)))
        found[row_id] = (head, tuple(herkunft), tuple(blocks))
    return found


def insert_records(records):
    connection = sqlite3.connect(DB_PATH)
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        existing = connection.execute(
            "SELECT COUNT(*) FROM erfassungen WHERE created_at LIKE '2025-%'"
        ).fetchone()[0]
        if existing:
            raise RuntimeError(
                "In der Datenbank liegen bereits Erfassungen aus 2025. "
                "Es wurde nichts gelöscht und nichts ergänzt."
            )
        before = snapshot(connection)
        for row_id, (head, _) in before.items():
            if head is None:
                raise RuntimeError(f"Datensatz ID {row_id} fehlt")
        connection.execute("BEGIN")
        for record in records:
            cursor = connection.execute(
                """
                INSERT INTO erfassungen (created_at, is_demo)
                VALUES (?, 1)
                """,
                (record["created_at"],),
            )
            new_id = cursor.lastrowid
            if new_id in PRESERVE_IDS:
                raise RuntimeError(f"Neue Zeile würde ID {new_id} belegen")
            connection.executemany(
                """
                INSERT INTO erfassung_herkunft (erfassung_id, position, wert)
                VALUES (?, ?, ?)
                """,
                [(new_id, index, wert) for index, wert in enumerate(record["level1"])],
            )
            for index, block in enumerate(record["level2"]):
                interesse = connection.execute(
                    """
                    INSERT INTO erfassung_interesse (erfassung_id, position, wert)
                    VALUES (?, ?, ?)
                    """,
                    (new_id, index, block["value"]),
                )
                connection.executemany(
                    """
                    INSERT INTO erfassung_detail (interesse_id, position, wert)
                    VALUES (?, ?, ?)
                    """,
                    [
                        (interesse.lastrowid, detail_index, wert)
                        for detail_index, wert in enumerate(block["details"])
                    ],
                )
        after = snapshot(connection)
        if after != before:
            raise RuntimeError("ID 5 oder ID 8 wurde verändert")
        connection.commit()
        return before
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def de_int(value):
    return f"{value:,}".replace(",", ".")


def de_num(value, digits=1):
    return f"{value:.{digits}f}".replace(".", ",")


def de_pct(part, whole):
    if not whole:
        return "0,0 %"
    return de_num(100 * part / whole) + " %"


def markdown_table(headers, rows):
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(str(cell) for cell in row) + " |")
    return "\n".join(lines)


def write_report(records, days, path):
    total = len(records)
    open_days = [day for day in days if day["open"]]
    closed_sunday = sum(1 for day in days if day.get("reason") == "sonntag")
    closed_holiday = sum(1 for day in days if day.get("reason") == "feiertag")
    by_weekday = Counter(record["moment"].weekday() for record in records)
    by_month = Counter(record["moment"].month for record in records)
    by_level1 = Counter()
    by_level2 = Counter()
    for record in records:
        by_level1.update(record["level1"])
        for block in record["level2"]:
            by_level2[block["value"]] += 1
    by_weather = Counter(record["weather"] for record in records)
    hours_weekday = Counter(
        record["moment"].hour for record in records if record["moment"].weekday() != 5
    )
    hours_saturday = Counter(
        record["moment"].hour for record in records if record["moment"].weekday() == 5
    )
    open_by_weekday = Counter(day["date"].weekday() for day in open_days)
    weekday_contacts = sum(
        day["contacts"] for day in open_days if day["date"].weekday() != 5
    )
    saturday_contacts = by_weekday[5]
    weekday_open = sum(count for weekday, count in open_by_weekday.items() if weekday != 5)
    saturday_open = open_by_weekday[5]
    weekday_hours = weekday_open * 9
    saturday_hours = saturday_open * 5

    detail_counts = defaultdict(Counter)
    for record in records:
        for block in record["level2"]:
            detail_counts[block["value"]].update(block["details"])

    school_contacts = Counter(record["school"] or "keine" for record in records)
    daily = [day["contacts"] for day in open_days]
    capped = sum(1 for day in open_days if day["contacts"] >= DAY_CAP)

    lines = [
        "# Plausibilitätsbericht Demodaten 2025",
        "",
        "Simulationszeitraum: 01.01.2025 bis 31.12.2025.",
        "Geschäftsmodell: ein spezialisierter ländlicher High-End-Fahrradhändler in Hessen.",
        "Gezählt wird eine beratene Kundenbegegnung (Kauf, Leasing, Werkstatt oder Bekleidung), nicht jeder kurze Ladenbesuch.",
        "Die Menge ist nicht fest vorgegeben. Sie entsteht aus Öffnungstag, Wochentag, Saison, Wetter, Ferien und Brückentagen.",
        "Die Anteile unten sind das Ergebnis dieses Laufs, keine vorgegebene Prozenttabelle.",
        "",
        "## Menge",
        "",
        f"- Erfassungen: {de_int(total)}",
        f"- Geöffnete Tage: {de_int(len(open_days))}",
        f"- Geschlossene Sonntage: {de_int(closed_sunday)}",
        f"- Geschlossene gesetzliche Feiertage in Hessen: {de_int(closed_holiday)}",
        f"- Kontakte je geöffnetem Tag: Minimum {min(daily)}, Mittel {de_num(total / len(open_days))}, Maximum {max(daily)}",
        f"- Tage an der Obergrenze von {DAY_CAP} Kontakten: {capped}",
        "",
        "Gesetzliche Feiertage ohne Erfassung: "
        + ", ".join(f"{name} ({day.strftime('%d.%m.%Y')})" for day, name in HOLIDAYS.items())
        + ".",
        "",
        "Schulferien Hessen, die in die Frequenz eingehen: Weihnachtsferien bis 10.01.2025, Osterferien 07.04.–21.04.2025, Sommerferien 07.07.–15.08.2025, Herbstferien 06.10.–18.10.2025, Weihnachtsferien ab 22.12.2025. In Hessen gibt es 2025 keine Winter- und keine Pfingstferien.",
        "",
        "## Wochenverteilung",
        "",
        "Samstag ist kürzer geöffnet (09:00–14:00 Uhr) und bleibt ein wichtiger Verkaufstag. Die Kontaktdichte je Öffnungsstunde liegt über der eines Werktags (10:00–19:00 Uhr).",
        "",
        markdown_table(
            ["Tag", "Geöffnete Tage", "Erfassungen", "Anteil", "je Tag", "je Öffnungsstunde"],
            [
                [
                    WEEKDAY_NAMES[weekday],
                    de_int(open_by_weekday[weekday]),
                    de_int(by_weekday[weekday]),
                    de_pct(by_weekday[weekday], total),
                    de_num(by_weekday[weekday] / open_by_weekday[weekday]),
                    de_num(
                        by_weekday[weekday]
                        / (open_by_weekday[weekday] * (5 if weekday == 5 else 9))
                    ),
                ]
                for weekday in range(6)
            ],
        ),
        "",
        f"Werktage gesamt: {de_num(weekday_contacts / weekday_hours)} Kontakte je Öffnungsstunde. Samstag: {de_num(saturday_contacts / saturday_hours)} Kontakte je Öffnungsstunde.",
        "",
        "## Tageszeit",
        "",
        "Montag bis Freitag: moderat nach 10:00 Uhr, vormittags zunehmend, mittags von Tag zu Tag schwankend, nachmittags stärker, später Nachmittag oft stark, kurz vor 19:00 Uhr abnehmend. Samstag hat ein eigenes Profil bis vor 14:00 Uhr.",
        "",
        "### Montag bis Freitag",
        "",
        markdown_table(
            ["Stunde", "Erfassungen", "Anteil der Werktage"],
            [
                [f"{hour:02d}:00–{hour:02d}:59", de_int(hours_weekday[hour]), de_pct(hours_weekday[hour], weekday_contacts)]
                for hour in range(10, 19)
            ],
        ),
        "",
        "### Samstag",
        "",
        markdown_table(
            ["Stunde", "Erfassungen", "Anteil des Samstags"],
            [
                [f"{hour:02d}:00–{hour:02d}:59", de_int(hours_saturday[hour]), de_pct(hours_saturday[hour], saturday_contacts)]
                for hour in range(9, 14)
            ],
        ),
        "",
        "## Saison",
        "",
        markdown_table(
            ["Monat", "Erfassungen", "Anteil"],
            [
                [MONTH_NAMES[month], de_int(by_month[month]), de_pct(by_month[month], total)]
                for month in range(1, 13)
            ],
        ),
        "",
        "## Wetter",
        "",
        "Das Wetter ist ein Simulationsmodell für ein Jahr in Hessen, keine gemessene Wetterreihe. Klares Wetter hebt Fahrradkontakte, Regen und ungemütliches Wetter senken die Frequenz und verschieben Kontakte in die Werkstatt. Samstage mit schlechtem Wetter fallen zusätzlich ab.",
        "",
        markdown_table(
            ["Wetter", "Erfassungen", "Anteil"],
            [
                [WEATHER_LABEL[key], de_int(by_weather[key]), de_pct(by_weather[key], total)]
                for key in ("klar", "bewoelkt", "regen", "ungemuetlich")
            ],
        ),
        "",
        "## Ferien",
        "",
        markdown_table(
            ["Zeitraum", "Erfassungen", "Anteil"],
            [
                [label, de_int(school_contacts[key]), de_pct(school_contacts[key], total)]
                for key, label in (
                    ("keine", "außerhalb der Schulferien"),
                    ("weihnachten", "Weihnachtsferien"),
                    ("ostern", "Osterferien"),
                    ("sommer", "Sommerferien"),
                    ("herbst", "Herbstferien"),
                )
            ],
        ),
        "",
        "## Herkunft",
        "",
        markdown_table(
            ["Herkunft", "Erfassungen", "Anteil"],
            [
                [name, de_int(by_level1[name]), de_pct(by_level1[name], total)]
                for name in LEVEL1
            ],
        ),
        "",
        "Leasingportal und Arbeit wiegen bei hochpreisigen Rädern stärker. Werkstatt, Bekleidung und Kinderrad kommen häufiger über Empfehlung, Google oder Sonstiges. Der Anteil von KI ist in der zweiten Jahreshälfte höher.",
        "",
        "## Produktgruppen",
        "",
        markdown_table(
            ["Interesse", "Erfassungen", "Anteil"],
            [
                [name, de_int(by_level2[name]), de_pct(by_level2[name], total)]
                for name in list(BIKES[:4])
                + ["Kinderrad", "Lastenrad", "Trekking", "Trekking vollgefedert", "Bekleidung", "Werkstatt"]
            ],
        ),
        "",
        "Die Werkstatt trägt das Jahr, besonders von November bis März. E-MTB, Gravel und Trekking prägen das Frühjahr und den Sommer. Kinderräder steigen vor Ostern und im Dezember und gehen in den Sommerferien zurück.",
        "",
        "## Werkstatt",
        "",
        markdown_table(
            ["Detail", "Nennungen", "Anteil der Werkstatt-Erfassungen"],
            [
                [
                    name,
                    de_int(detail_counts["Werkstatt"][name]),
                    de_pct(detail_counts["Werkstatt"][name], by_level2["Werkstatt"]),
                ]
                for name in INTERESTS["Werkstatt"]
            ],
        ),
        "",
        "Eine Werkstatt-Erfassung kann mehr als ein Detail enthalten. Die Anteile beziehen sich auf Erfassungen mit diesem Interesse, nicht auf die Summe der Nennungen.",
        "",
        "## Marken bei Fahrrädern",
        "",
    ]
    for bike in BIKES:
        lines.append(f"### {bike}")
        lines.append("")
        lines.append(
            markdown_table(
                ["Detail", "Nennungen", "Anteil der Erfassungen"],
                [
                    [
                        name,
                        de_int(detail_counts[bike][name]),
                        de_pct(detail_counts[bike][name], by_level2[bike]),
                    ]
                    for name in INTERESTS[bike]
                ],
            )
        )
        lines.append("")
    lines.extend(
        [
            "## Bekleidung",
            "",
            markdown_table(
                ["Detail", "Nennungen", "Anteil der Bekleidungs-Erfassungen"],
                [
                    [
                        name,
                        de_int(detail_counts["Bekleidung"][name]),
                        de_pct(detail_counts["Bekleidung"][name], by_level2["Bekleidung"]),
                    ]
                    for name in INTERESTS["Bekleidung"]
                ],
            ),
            "",
            "## Bestehende Datensätze",
            "",
            "ID 5 und ID 8 wurden vor dem Schreiben gelesen und nach dem Commit erneut gelesen. Zeitstempel, Herkunft, Interesse und Details sind unverändert. Es wurde kein Datensatz gelöscht.",
            "",
            "Zeitstempel der Demodaten verwenden `Europe/Berlin` im Format `YYYY-MM-DD HH:MM:SS±HH:MM`. Der Offset folgt der Sommer- und Winterzeit, ohne festen Stundenversatz.",
            "",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Demodaten 2025 erzeugen")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Nur erzeugen und prüfen, nichts schreiben",
    )
    args = parser.parse_args()
    records, days = build_year(Random(SEED))
    print(f"erzeugt {len(records)} Erfassungen, offene Tage {sum(day['open'] for day in days)}")
    if args.dry_run:
        return
    before = insert_records(records)
    report = ROOT / "docs" / "plausibilitaetsbericht-demodaten-2025.md"
    write_report(records, days, report)
    print(f"geschrieben nach {DB_PATH}")
    print(f"bericht {report}")
    for row_id, (head, details) in before.items():
        print(f"unverändert ID {row_id}: {head} {details}")


if __name__ == "__main__":
    main()
