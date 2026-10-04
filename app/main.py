from datetime import date, datetime, timedelta
from pathlib import Path
from urllib.parse import urlencode

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.database import (
    BERLIN,
    INTERESTS,
    LEVEL1_VALUES,
    build_auswertung,
    correction_report,
    compare_periods,
    erfassungen_board,
    filter_names,
    init_db,
    latest_real_capture_label,
    save_erfassung,
    save_korrektur,
    suggest_compare_days,
)
from app.periods import (
    ARTS,
    SCHOOL_HOLIDAYS,
    bridge_days,
    comparison_choices,
    resolve_period,
)

MODI = (
    ("demo", "Demodaten"),
    ("echt", "Echtdaten"),
    ("alle", "Alle"),
)
ZEITRAEUME = (
    ("heute", "Heute"),
    ("woche", "Woche"),
    ("monat", "Monat"),
    ("quartal", "Quartal"),
    ("halbjahr", "Halbjahr"),
    ("jahr", "Jahr"),
    ("gesamt", "Gesamt"),
    ("custom", "Benutzerdefiniert"),
)
MODUS_VALUES = {value for value, _label in MODI}
ZEITRAUM_VALUES = {value for value, _label in ZEITRAEUME}
STATE_LEVELS = (
    (0, "Keine"),
    (1, "Niedrig"),
    (2, "Mittel"),
    (3, "Hoch"),
    (4, "Sehr hoch"),
)

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


class FreshStaticFiles(StaticFiles):
    def file_response(self, full_path, stat_result, scope, status_code=200):
        response = super().file_response(full_path, stat_result, scope, status_code)
        response.headers["Cache-Control"] = "no-cache"
        return response


def asset(name):
    stamp = int((STATIC_DIR / name).stat().st_mtime)
    return f"/static/{name}?v={stamp}"


app = FastAPI(title="Customer State")
init_db()
templates = Jinja2Templates(directory="templates")
templates.env.globals["asset"] = asset
app.mount("/static", FreshStaticFiles(directory="static"), name="static")


@app.middleware("http")
async def fresh_pages(request, call_next):
    response = await call_next(request)
    if request.url.path in {"/", "/erfassungen", "/auswertung", "/vergleich"}:
        response.headers["Cache-Control"] = "no-cache"
    return response


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "active": "erfassung",
            "last_capture": latest_real_capture_label(),
            "last_capture_saved": bool(latest_real_capture_label()),
        },
    )


def _parse_date(value):
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _shift_month(day, months):
    index = day.year * 12 + (day.month - 1) + months
    year, month_index = divmod(index, 12)
    return date(year, month_index + 1, 1)


def _period_window(zeitraum, anchor):
    if zeitraum == "heute":
        return anchor, anchor
    if zeitraum == "woche":
        start = anchor - timedelta(days=anchor.weekday())
        return start, start + timedelta(days=6)
    if zeitraum == "monat":
        start = anchor.replace(day=1)
        last = _shift_month(start, 1) - timedelta(days=1)
        return start, last
    if zeitraum == "quartal":
        start = _shift_month(anchor, -2)
        last = _shift_month(anchor.replace(day=1), 1) - timedelta(days=1)
        return start, last
    if zeitraum == "halbjahr":
        start = _shift_month(anchor, -5)
        last = _shift_month(anchor.replace(day=1), 1) - timedelta(days=1)
        return start, last
    if zeitraum == "jahr":
        return date(anchor.year, 1, 1), date(anchor.year, 12, 31)
    return None, None


def _shift_anchor(zeitraum, anchor, step):
    if zeitraum == "heute":
        return anchor + timedelta(days=step)
    if zeitraum == "woche":
        return anchor + timedelta(days=7 * step)
    if zeitraum == "monat":
        return _shift_month(anchor, step)
    if zeitraum == "quartal":
        return _shift_month(anchor, 3 * step)
    if zeitraum == "halbjahr":
        return _shift_month(anchor, 6 * step)
    if zeitraum == "jahr":
        return date(anchor.year + step, 1, 1)
    return anchor


WEEKDAY_CHOICES = (
    (0, "Mo", "Montag"),
    (1, "Di", "Dienstag"),
    (2, "Mi", "Mittwoch"),
    (3, "Do", "Donnerstag"),
    (4, "Fr", "Freitag"),
    (5, "Sa", "Samstag"),
    (6, "So", "Sonntag"),
)


def _chosen_numbers(params, name, allowed):
    chosen = []
    invalid = False
    for value in params.getlist(name):
        if value in allowed:
            number = int(value)
            if number not in chosen:
                chosen.append(number)
        elif value:
            invalid = True
    chosen.sort()
    return chosen, invalid


def _state_levels(params):
    return _chosen_numbers(params, "stufe", {"0", "1", "2", "3", "4"})


def _weekdays(params):
    return _chosen_numbers(params, "wochentag", {"0", "1", "2", "3", "4", "5", "6"})


ARROW_LABELS = {
    "heute": ("Vorheriger Tag", "Nächster Tag"),
    "woche": ("Vorherige Woche", "Nächste Woche"),
    "monat": ("Vorheriger Monat", "Nächster Monat"),
    "quartal": ("Vorheriges Quartal", "Nächstes Quartal"),
    "halbjahr": ("Vorheriges Halbjahr", "Nächstes Halbjahr"),
    "jahr": ("Vorheriges Jahr", "Nächstes Jahr"),
    "custom": ("Vorheriger Zeitraum", "Nächster Zeitraum"),
}


def _auswertung_filters(params):
    ignored = False
    zeitraum = params.get("zeitraum") or "gesamt"
    if zeitraum not in ZEITRAUM_VALUES:
        zeitraum = "gesamt"
        ignored = True

    today = datetime.now(BERLIN).date()
    anchor = _parse_date(params.get("stand") or "") or today
    start = None
    end = None
    von_value = ""
    bis_value = ""
    if zeitraum == "custom":
        start = _parse_date(params.get("von") or "")
        end = _parse_date(params.get("bis") or "")
        if start is None or end is None:
            zeitraum = "gesamt"
            start = None
            end = None
            ignored = True
        elif start > end:
            start, end = end, start
        anchor = today
    elif zeitraum != "gesamt":
        start, end = _period_window(zeitraum, anchor)
    else:
        anchor = today

    if start is not None and end is not None:
        von_value = start.isoformat()
        bis_value = end.isoformat()

    stat_start, stat_end = start, end
    if start is not None and end is not None and end > today:
        stat_end = today if start <= today else start - timedelta(days=1)

    stand_value = ""
    if zeitraum not in {"gesamt", "custom"} and anchor != today:
        stand_value = anchor.isoformat()

    stufen, invalid_stufen = _state_levels(params)
    wochentage, invalid_days = _weekdays(params)
    if invalid_stufen or invalid_days:
        ignored = True

    return {
        "modus": "alle",
        "zeitraum": zeitraum,
        "start": start,
        "end": end,
        "stat_start": stat_start,
        "stat_end": stat_end,
        "anchor": anchor,
        "stand_value": stand_value,
        "von_value": von_value,
        "bis_value": bis_value,
        "herkunft": (params.get("herkunft") or "").strip(),
        "interesse": (params.get("interesse") or "").strip(),
        "detail": (params.get("detail") or "").strip(),
        "stufen": stufen,
        "wochentage": wochentage,
        "ignored": ignored,
        "today": today,
    }


def _auswertung_query(filters, zeitraum, stand=None, von=None, bis=None):
    params = {"zeitraum": zeitraum}
    if stand is not None:
        params["stand"] = stand.isoformat()
    if von is not None and bis is not None:
        params["von"] = von.isoformat()
        params["bis"] = bis.isoformat()
    if filters["herkunft"]:
        params["herkunft"] = filters["herkunft"]
    if filters["interesse"]:
        params["interesse"] = filters["interesse"]
    if filters["detail"]:
        params["detail"] = filters["detail"]
    query = list(params.items())
    for level in filters["stufen"]:
        query.append(("stufe", str(level)))
    for day in filters["wochentage"]:
        query.append(("wochentag", str(day)))
    return "/auswertung?" + urlencode(query)


def _page_link(filters, step):
    zeitraum = filters["zeitraum"]
    if zeitraum == "gesamt" or filters["start"] is None or filters["end"] is None:
        return None
    if zeitraum == "custom":
        span = (filters["end"] - filters["start"]).days + 1
        return _auswertung_query(
            filters,
            zeitraum,
            von=filters["start"] + timedelta(days=span * step),
            bis=filters["end"] + timedelta(days=span * step),
        )
    return _auswertung_query(
        filters,
        zeitraum,
        stand=_shift_anchor(zeitraum, filters["anchor"], step),
    )


@app.get("/auswertung", response_class=HTMLResponse)
async def auswertung(request: Request):
    filters = _auswertung_filters(request.query_params)
    mark_start = filters["start"] if filters["zeitraum"] != "gesamt" else None
    mark_end = filters["end"] if filters["zeitraum"] != "gesamt" else None
    result = build_auswertung(
        filters["modus"],
        filters["zeitraum"],
        filters["stat_start"],
        filters["stat_end"],
        filters["herkunft"],
        filters["interesse"],
        filters["detail"],
        mark_start=mark_start,
        mark_end=mark_end,
        stufen=filters["stufen"],
        wochentage=filters["wochentage"],
    )
    ignored = filters["ignored"]
    if filters["herkunft"] and filters["herkunft"] != result["applied_herkunft"]:
        ignored = True
    if filters["interesse"] and filters["interesse"] != result["applied_interesse"]:
        ignored = True
    if filters["detail"] and filters["detail"] != result["applied_detail"]:
        ignored = True
    return templates.TemplateResponse(
        request,
        "auswertung.html",
        {
            "active": "auswertung",
            "zeitraeume": [{"value": value, "label": label} for value, label in ZEITRAEUME],
            "zeitraum": filters["zeitraum"],
            "von_value": filters["von_value"],
            "bis_value": filters["bis_value"],
            "stand_value": filters["stand_value"],
            "prev_url": _page_link(filters, -1),
            "next_url": _page_link(filters, 1),
            "prev_label": ARROW_LABELS.get(filters["zeitraum"], ("", ""))[0],
            "next_label": ARROW_LABELS.get(filters["zeitraum"], ("", ""))[1],
            "stufen": filters["stufen"],
            "state_levels": [{"level": level, "label": label} for level, label in STATE_LEVELS],
            "wochentage": filters["wochentage"],
            "weekday_choices": [
                {"value": value, "short": short, "label": label}
                for value, short, label in WEEKDAY_CHOICES
            ],
            "ignored": ignored,
            "result": result,
            "corrections": correction_report(filters["start"], filters["end"]),
        },
    )


def _holiday_at(day):
    previous = None
    for start, end, label, key in SCHOOL_HOLIDAYS:
        if end < day:
            previous = (label, key, start)
        if start <= day <= end:
            return label, key, start
    if previous:
        return previous
    start, _end, label, key = SCHOOL_HOLIDAYS[0]
    return label, key, start


def _default_values(art, left_day, right_day):
    if art == "tag":
        return left_day.isoformat(), right_day.isoformat()
    if art == "kw":
        iso = left_day.isocalendar()
        left = f"{iso.year}-W{iso.week:02d}"
        try:
            previous = date.fromisocalendar(iso.year - 1, iso.week, 1)
        except ValueError:
            previous = right_day
        previous_iso = previous.isocalendar()
        right = f"{previous_iso.year}-W{previous_iso.week:02d}"
        if right == left:
            other = right_day.isocalendar()
            right = f"{other.year}-W{other.week:02d}"
        return left, right
    if art == "monat":
        return (
            f"{left_day.year}-{left_day.month:02d}",
            f"{left_day.year - 1}-{left_day.month:02d}",
        )
    if art == "ferien":
        label, left_key, start = _holiday_at(left_day)
        earlier = [
            key
            for item_start, _item_end, item_label, key in SCHOOL_HOLIDAYS
            if item_label == label and key != left_key and item_start < start
        ]
        if earlier:
            return left_key, earlier[-1]
        prior = [key for item_start, item_end, _item_label, key in SCHOOL_HOLIDAYS if item_end < start]
        return left_key, prior[-1] if prior else left_key
    if art == "fest":
        return f"{left_day.year}-weihnachten", f"{left_day.year}-ostern"
    if art == "bruecke":
        days = [item[0] for item in bridge_days(left_day.year) if item[0] <= left_day]
        if len(days) >= 2:
            return days[-1].isoformat(), days[-2].isoformat()
        previous = [item[0] for item in bridge_days(left_day.year - 1)]
        if days and previous:
            return days[0].isoformat(), previous[-1].isoformat()
        if len(previous) >= 2:
            return previous[-1].isoformat(), previous[-2].isoformat()
        if previous:
            return previous[-1].isoformat(), previous[-1].isoformat()
        token = left_day.isoformat()
        return token, token
    return left_day.isoformat(), right_day.isoformat()


def _bind_heatmap(calendar, side, art, links, rechts, base):
    for week in calendar["weeks"]:
        for cell in week["days"]:
            token = cell.get("token") or ""
            if not token:
                cell["href"] = ""
                continue
            params = dict(base)
            params["art"] = art
            if side == "links":
                params["links"] = token
                params["rechts"] = rechts
            else:
                params["links"] = links
                params["rechts"] = token
            cell["href"] = "/vergleich?" + urlencode(params)


@app.get("/vergleich", response_class=HTMLResponse)
async def vergleich(request: Request):
    params = request.query_params
    ignored = False
    modus = params.get("modus") or "demo"
    if modus not in MODUS_VALUES:
        modus = "demo"
        ignored = True
    art = params.get("art") or "tag"
    if art not in {value for value, _label in ARTS}:
        art = "tag"
        ignored = True
    herkunft_names, interesse_names = filter_names(modus)
    herkunft = (params.get("herkunft") or "").strip()
    interesse = (params.get("interesse") or "").strip()
    if herkunft and herkunft not in herkunft_names:
        herkunft = ""
        ignored = True
    if interesse and interesse not in interesse_names:
        interesse = ""
        ignored = True
    today = datetime.now(BERLIN).date()
    left_day, right_day = suggest_compare_days(modus, herkunft, interesse, today)
    default_links, default_rechts = _default_values(art, left_day, right_day)
    links = (params.get("links") or "").strip()
    rechts = (params.get("rechts") or "").strip()
    if not links and not rechts:
        links, rechts = default_links, default_rechts
    left_period = resolve_period(art, links)
    right_period = resolve_period(art, rechts)
    if left_period is None or right_period is None:
        if links or rechts:
            ignored = True
        links, rechts = default_links, default_rechts
        left_period = resolve_period(art, links)
        right_period = resolve_period(art, rechts)
    report = compare_periods(modus, herkunft, interesse, left_period, right_period, art)
    base = {"modus": modus}
    if herkunft:
        base["herkunft"] = herkunft
    if interesse:
        base["interesse"] = interesse
    _bind_heatmap(report["left"]["calendar"], "links", art, links, rechts, base)
    _bind_heatmap(report["right"]["calendar"], "rechts", art, links, rechts, base)
    choices = comparison_choices()
    return templates.TemplateResponse(
        request,
        "vergleich.html",
        {
            "active": "vergleich",
            "modi": [{"value": value, "label": label} for value, label in MODI],
            "arts": [{"value": value, "label": label} for value, label in ARTS],
            "modus": modus,
            "modus_label": dict(MODI)[modus],
            "art": art,
            "art_label": dict(ARTS)[art],
            "links": links,
            "rechts": rechts,
            "herkunft": herkunft,
            "interesse": interesse,
            "herkunft_options": herkunft_names,
            "interesse_options": interesse_names,
            "choices": choices.get(art, []),
            "ignored": ignored,
            "report": report,
        },
    )


@app.get("/erfassungen", response_class=HTMLResponse)
async def erfassungen(request: Request):
    today = datetime.now(BERLIN).date()
    selected = _parse_date(request.query_params.get("tag") or "")
    if selected is None:
        year_text = request.query_params.get("jahr") or ""
        if year_text.isdigit():
            year = int(year_text)
            selected = date(year, 12, 31) if year != today.year else today
        else:
            selected = today
    board = erfassungen_board(selected)
    if request.query_params.get("jahr") and not request.query_params.get("tag"):
        year = selected.year
        counted = [
            day
            for week in board["calendar"]["weeks"]
            for day in week["days"]
            if day["in_range"] and day["count"] and day["date"].startswith(str(year))
        ]
        if counted and selected.isoformat() not in {day["date"] for day in counted}:
            selected = date.fromisoformat(counted[-1]["date"])
            board = erfassungen_board(selected)
    return templates.TemplateResponse(
        request,
        "erfassungen.html",
        {
            "active": "erfassungen",
            "entries": board["entries"],
            "total": board["total"],
            "selected_label": board["selected_label"],
            "selected_iso": board["selected_iso"],
            "weekday": board["weekday"],
            "calendar": board["calendar"],
            "years": board["years"],
            "is_today": selected == today,
        },
    )


def _clean_text(value):
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text:
        return None
    return text


def _validate_capture(payload):
    if not isinstance(payload, dict):
        raise ValueError("Die Erfassung ist unvollständig.")
    raw_level1 = payload.get("level1")
    raw_level2 = payload.get("level2")
    if not isinstance(raw_level1, list) or not raw_level1:
        raise ValueError("Die Erfassung ist unvollständig.")
    if not isinstance(raw_level2, list) or not raw_level2:
        raise ValueError("Die Erfassung ist unvollständig.")

    level1 = []
    for item in raw_level1:
        text = _clean_text(item)
        if text not in LEVEL1_VALUES or text in level1:
            raise ValueError("Die Erfassung ist unvollständig.")
        level1.append(text)

    level2 = []
    seen = set()
    for block in raw_level2:
        if not isinstance(block, dict):
            raise ValueError("Die Erfassung ist unvollständig.")
        value = _clean_text(block.get("value"))
        allowed = INTERESTS.get(value)
        details = block.get("level3")
        if allowed is None or value in seen or not isinstance(details, list) or not details:
            raise ValueError("Die Erfassung ist unvollständig.")
        seen.add(value)
        clean_details = []
        for detail in details:
            text = _clean_text(detail)
            if text not in allowed or text in clean_details:
                raise ValueError("Die Erfassung ist unvollständig.")
            clean_details.append(text)
        level2.append({"value": value, "level3": clean_details})

    for key in (
        "started_at",
        "level1_completed_at",
        "level2_started_at",
        "level2_completed_at",
        "level3_started_at",
    ):
        if _clean_text(payload.get(key)) is None:
            raise ValueError("Die Erfassung ist unvollständig.")
    return level1, level2


@app.post("/api/erfassungen", status_code=201)
async def create_erfassung(payload: dict):
    try:
        level1, level2 = _validate_capture(payload)
        erfassung_id, completed_label = save_erfassung(
            level1,
            level2,
            payload.get("started_at"),
            payload.get("level1_completed_at"),
            payload.get("level2_started_at"),
            payload.get("level2_completed_at"),
            payload.get("level3_started_at"),
            payload.get("level2_opened_at"),
            payload.get("level3_opened_at"),
        )
    except ValueError as error:
        message = str(error)
        if not message.startswith("Die "):
            message = "Die Erfassung ist unvollständig."
        raise HTTPException(status_code=400, detail=message) from error
    return {"id": erfassung_id, "completed_label": completed_label}


def _validate_korrektur(payload):
    if not isinstance(payload, dict):
        raise ValueError("Die Korrektur ist unvollständig.")
    try:
        from_level = int(payload.get("from_level"))
        to_level = int(payload.get("to_level"))
        elapsed = int(payload.get("elapsed_seconds"))
    except (TypeError, ValueError) as error:
        raise ValueError("Die Korrektur ist unvollständig.") from error
    if from_level not in (1, 2, 3) or to_level not in (1, 2, 3) or to_level > from_level:
        raise ValueError("Die Korrektur ist unvollständig.")
    if elapsed < 0 or elapsed > 86400:
        raise ValueError("Die Korrektur ist unvollständig.")
    raw_level1 = payload.get("level1") or []
    raw_level2 = payload.get("level2") or []
    if not isinstance(raw_level1, list) or not isinstance(raw_level2, list):
        raise ValueError("Die Korrektur ist unvollständig.")
    level1 = []
    for item in raw_level1:
        text = _clean_text(item)
        if text not in LEVEL1_VALUES or text in level1:
            raise ValueError("Die Korrektur ist unvollständig.")
        level1.append(text)
    level2 = []
    seen = set()
    for block in raw_level2:
        if not isinstance(block, dict):
            raise ValueError("Die Korrektur ist unvollständig.")
        value = _clean_text(block.get("value"))
        allowed = INTERESTS.get(value)
        details = block.get("level3") or []
        if allowed is None or value in seen or not isinstance(details, list):
            raise ValueError("Die Korrektur ist unvollständig.")
        seen.add(value)
        clean_details = []
        for detail in details:
            text = _clean_text(detail)
            if text not in allowed or text in clean_details:
                raise ValueError("Die Korrektur ist unvollständig.")
            clean_details.append(text)
        level2.append({"value": value, "level3": clean_details})
    had_selection = bool(payload.get("had_selection"))
    return from_level, to_level, elapsed, had_selection, level1, level2


@app.post("/api/korrekturen", status_code=201)
async def create_korrektur(payload: dict):
    try:
        from_level, to_level, elapsed, had_selection, level1, level2 = _validate_korrektur(payload)
        korrektur_id = save_korrektur(from_level, to_level, elapsed, had_selection, level1, level2)
    except ValueError as error:
        message = str(error)
        if not message.startswith("Die "):
            message = "Die Korrektur ist unvollständig."
        raise HTTPException(status_code=400, detail=message) from error
    return {"id": korrektur_id}
