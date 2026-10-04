from datetime import date, timedelta

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
WEEKDAY_NAMES = (
    "Montag",
    "Dienstag",
    "Mittwoch",
    "Donnerstag",
    "Freitag",
    "Samstag",
    "Sonntag",
)

# Erster und letzter Ferientag laut Hessischem Kultusministerium.
# 2025 entspricht den im Demodatenmodell verwendeten Terminen.
# Weihnachtsferien 2025/2026 und die Termine ab 2026 folgen der Veröffentlichung
# des Kultusministeriums für die Schuljahre 2025/2026 und 2026/2027.
SCHOOL_HOLIDAYS = (
    (date(2025, 1, 1), date(2025, 1, 10), "Weihnachtsferien", "2024-weihnachten"),
    (date(2025, 4, 7), date(2025, 4, 21), "Osterferien", "2025-ostern"),
    (date(2025, 7, 7), date(2025, 8, 15), "Sommerferien", "2025-sommer"),
    (date(2025, 10, 6), date(2025, 10, 18), "Herbstferien", "2025-herbst"),
    (date(2025, 12, 22), date(2026, 1, 10), "Weihnachtsferien", "2025-weihnachten"),
    (date(2026, 3, 30), date(2026, 4, 10), "Osterferien", "2026-ostern"),
    (date(2026, 6, 29), date(2026, 8, 7), "Sommerferien", "2026-sommer"),
    (date(2026, 10, 5), date(2026, 10, 17), "Herbstferien", "2026-herbst"),
    (date(2026, 12, 23), date(2027, 1, 12), "Weihnachtsferien", "2026-weihnachten"),
)

COMPARE_YEARS = (2025, 2026)
ARTS = (
    ("tag", "Tag"),
    ("kw", "Kalenderwoche"),
    ("monat", "Monat"),
    ("ferien", "Schulferien"),
    ("fest", "Festtag"),
    ("bruecke", "Brückentag"),
)


def easter(year):
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = ((h + l - 7 * m + 114) % 31) + 1
    return date(year, month, day)


def public_holidays(year):
    easter_sunday = easter(year)
    return {
        date(year, 1, 1): "Neujahr",
        easter_sunday - timedelta(days=2): "Karfreitag",
        easter_sunday + timedelta(days=1): "Ostermontag",
        date(year, 5, 1): "Tag der Arbeit",
        easter_sunday + timedelta(days=39): "Christi Himmelfahrt",
        easter_sunday + timedelta(days=50): "Pfingstmontag",
        easter_sunday + timedelta(days=60): "Fronleichnam",
        date(year, 10, 3): "Tag der Deutschen Einheit",
        date(year, 12, 25): "1. Weihnachtstag",
        date(year, 12, 26): "2. Weihnachtstag",
    }


def bridge_days(year):
    holidays = public_holidays(year)
    found = []
    for day, name in sorted(holidays.items()):
        candidate = None
        if day.weekday() == 3:
            candidate = day + timedelta(days=1)
        elif day.weekday() == 4:
            candidate = day - timedelta(days=1)
        elif day.weekday() == 1:
            candidate = day - timedelta(days=1)
        if candidate is None or candidate in holidays or candidate.year != year:
            continue
        if candidate.weekday() not in (0, 3, 4):
            continue
        prefix = "nach" if candidate > day else "vor"
        found.append((candidate, f"{prefix} {name}"))
    return found


def _span(start, end, title):
    return {
        "start": start,
        "end": end,
        "title": title,
        "detail": _range_label(start, end),
    }


def _range_label(start, end):
    if start == end:
        return f"{WEEKDAY_NAMES[start.weekday()]}, {start.strftime('%d.%m.%Y')}"
    if start.year == end.year:
        return f"{start.strftime('%d.%m.')}–{end.strftime('%d.%m.%Y')}"
    return f"{start.strftime('%d.%m.%Y')}–{end.strftime('%d.%m.%Y')}"


def resolve_tag(day):
    return _span(day, day, day.strftime("%d.%m.%Y"))


def resolve_week(token):
    try:
        year_text, week_text = token.split("-W", 1)
        year = int(year_text)
        week = int(week_text)
        start = date.fromisocalendar(year, week, 1)
        end = date.fromisocalendar(year, week, 7)
    except (ValueError, AttributeError):
        return None
    return _span(start, end, f"KW {week} {year}")


def resolve_month(token):
    try:
        year_text, month_text = token.split("-", 1)
        year = int(year_text)
        month = int(month_text)
        start = date(year, month, 1)
        if month == 12:
            end = date(year, 12, 31)
        else:
            end = date(year, month + 1, 1) - timedelta(days=1)
    except (ValueError, AttributeError):
        return None
    return _span(start, end, f"{MONTH_NAMES[month - 1]} {year}")


def resolve_ferien(token):
    for start, end, label, key in SCHOOL_HOLIDAYS:
        if key == token:
            if label == "Weihnachtsferien":
                year = int(key.split("-", 1)[0])
                title = f"{label} {year}/{year + 1}"
            else:
                title = f"{label} {start.year}"
            return _span(start, end, title)
    return None


def resolve_fest(token):
    try:
        year_text, name = token.split("-", 1)
        year = int(year_text)
    except (ValueError, AttributeError):
        return None
    easter_sunday = easter(year)
    if name == "ostern":
        return _span(easter_sunday - timedelta(days=2), easter_sunday + timedelta(days=1), f"Ostern {year}")
    if name == "weihnachten":
        return _span(date(year, 12, 24), date(year, 12, 26), f"Weihnachten {year}")
    return None


def resolve_bridge(token):
    try:
        day = date.fromisoformat(token)
    except (ValueError, TypeError):
        return None
    for candidate, label in bridge_days(day.year):
        if candidate == day:
            return _span(day, day, f"Brückentag {label}")
    return None


def comparison_choices():
    weeks = []
    months = []
    ferien = []
    feste = []
    bridges = []
    for year in COMPARE_YEARS:
        week = 1
        while True:
            try:
                start = date.fromisocalendar(year, week, 1)
                end = date.fromisocalendar(year, week, 7)
            except ValueError:
                break
            weeks.append(
                {
                    "value": f"{year}-W{week:02d}",
                    "label": f"KW {week} {year} · {start.strftime('%d.%m.')}–{end.strftime('%d.%m.')}",
                }
            )
            week += 1
        for month in range(1, 13):
            months.append({"value": f"{year}-{month:02d}", "label": f"{MONTH_NAMES[month - 1]} {year}"})
        feste.append({"value": f"{year}-ostern", "label": f"Ostern {year}"})
        feste.append({"value": f"{year}-weihnachten", "label": f"Weihnachten {year}"})
        for day, label in bridge_days(year):
            bridges.append(
                {
                    "value": day.isoformat(),
                    "label": f"{day.strftime('%d.%m.%Y')} · {label}",
                }
            )
    for start, end, label, key in SCHOOL_HOLIDAYS:
        ferien.append(
            {
                "value": key,
                "label": f"{label} {_range_label(start, end)}",
            }
        )
    return {
        "kw": weeks,
        "monat": months,
        "ferien": ferien,
        "fest": feste,
        "bruecke": bridges,
    }


def token_for_day(art, day):
    if art == "tag":
        return day.isoformat()
    if art == "kw":
        iso = day.isocalendar()
        return f"{iso.year}-W{iso.week:02d}"
    if art == "monat":
        return f"{day.year}-{day.month:02d}"
    if art == "ferien":
        for start, end, _label, key in SCHOOL_HOLIDAYS:
            if start <= day <= end:
                return key
        return None
    if art == "fest":
        ostern = resolve_fest(f"{day.year}-ostern")
        if ostern and ostern["start"] <= day <= ostern["end"]:
            return f"{day.year}-ostern"
        weihnachten = resolve_fest(f"{day.year}-weihnachten")
        if weihnachten and weihnachten["start"] <= day <= weihnachten["end"]:
            return f"{day.year}-weihnachten"
        return None
    if art == "bruecke":
        for candidate, _label in bridge_days(day.year):
            if candidate == day:
                return day.isoformat()
        return None
    return None


def resolve_period(art, value):
    if art == "tag":
        try:
            return resolve_tag(date.fromisoformat(value))
        except (ValueError, TypeError):
            return None
    if art == "kw":
        return resolve_week(value)
    if art == "monat":
        return resolve_month(value)
    if art == "ferien":
        return resolve_ferien(value)
    if art == "fest":
        return resolve_fest(value)
    if art == "bruecke":
        return resolve_bridge(value)
    return None
