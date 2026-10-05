from datetime import date, datetime, timedelta
from pathlib import Path
from urllib.parse import parse_qs, urlencode

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app import auth
from app.admin_data import (
    AdminError,
    create_button,
    create_employee,
    list_boards,
    list_buttons,
    list_employees,
    list_levels,
    preview_cells,
    reset_pin,
    shift_button,
    update_board,
    update_button,
    update_employee,
    update_level,
)
from app.database import (
    BERLIN,
    apply_option_filter,
    build_auswertung,
    capture_catalog,
    correction_report,
    compare_periods,
    erfassungen_board,
    filter_names,
    init_db,
    latest_real_capture_label,
    prepare_capture,
    prepare_korrektur,
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


def render(request, name, context):
    user = getattr(request.state, "user", None)
    payload = {"user": user, "show_admin": bool(user and user["is_admin"])}
    payload.update(context)
    return templates.TemplateResponse(request, name, payload)


def _stamp_session(response, token):
    response.set_cookie(
        auth.COOKIE,
        token,
        httponly=True,
        samesite="lax",
        path="/",
        max_age=auth.seconds_until_day_end(datetime.now(BERLIN)),
    )
    return response


def _clear_session_cookie(response):
    response.delete_cookie(auth.COOKIE, path="/")
    return response


def _data_scope(user):
    if user["is_admin"]:
        return None
    return [board["id"] for board in auth.allowed_boards(user["id"])]


@app.middleware("http")
async def fresh_pages(request, call_next):
    response = await call_next(request)
    if request.url.path in {"/", "/erfassungen", "/auswertung", "/vergleich", "/login"} or request.url.path.startswith("/admin"):
        response.headers["Cache-Control"] = "no-cache"
    return response


@app.middleware("http")
async def require_login(request, call_next):
    path = request.url.path
    now = datetime.now(BERLIN)
    token = request.cookies.get(auth.COOKIE)
    user = auth.session_user(token, now) if token else None
    request.state.user = user
    public = path.startswith("/static") or path == "/login" or path.startswith("/login/")
    if path == "/logout":
        return await call_next(request)
    if not public and user is None:
        if path.startswith("/api/"):
            response = JSONResponse({"detail": "Anmeldung erforderlich."}, status_code=401)
        else:
            response = RedirectResponse("/login", status_code=303)
        if token:
            auth.drop_session(token)
            _clear_session_cookie(response)
        return response
    if path.startswith("/admin") and (user is None or not user["is_admin"]):
        return HTMLResponse("Kein Zugriff auf die Administration.", status_code=403)
    return await call_next(request)


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    if request.state.user:
        return RedirectResponse("/", status_code=303)
    mitarbeiter = request.query_params.get("mitarbeiter")
    person = None
    fehler = request.query_params.get("fehler", "")
    if mitarbeiter and mitarbeiter.isdigit():
        person = auth.employee_record(int(mitarbeiter))
        if person is None or person["status"] != "aktiv":
            person = None
            fehler = fehler or "Anmeldung nicht möglich."
        else:
            person.pop("pin_hash", None)
    return render(
        request,
        "login.html",
        {"people": auth.active_employees(), "person": person, "fehler": fehler},
    )


@app.post("/login/auswahl")
async def login_choose(request: Request):
    form, _many = await _form(request)
    person = auth.employee_record(form("mitarbeiter"))
    if person is None or person["status"] != "aktiv":
        return RedirectResponse("/login?" + urlencode({"fehler": "Anmeldung nicht möglich."}), status_code=303)
    return RedirectResponse(f"/login?mitarbeiter={person['id']}", status_code=303)


@app.post("/login/pin")
async def login_pin(request: Request):
    form, _many = await _form(request)
    now = datetime.now(BERLIN)
    person = auth.employee_record(form("mitarbeiter"))
    if person is None or person["status"] != "aktiv":
        return RedirectResponse("/login?" + urlencode({"fehler": "Anmeldung nicht möglich."}), status_code=303)
    target = "/login?" + urlencode({"mitarbeiter": person["id"]})

    def deny(message):
        return RedirectResponse(target + "&" + urlencode({"fehler": message}), status_code=303)

    if auth.pin_locked(person["id"], now):
        return deny("Bitte einen Moment warten.")
    pin = form("pin")
    repeat = form("pin_wiederholen")
    if not person["pin_set"]:
        if not auth.pin_valid(pin) or pin != repeat:
            return deny("Der PIN muss aus vier Ziffern bestehen und beide Eingaben müssen übereinstimmen.")
        try:
            auth.set_pin(person["id"], pin)
        except ValueError:
            return deny("Anmeldung nicht möglich.")
    else:
        if not auth.pin_valid(pin) or not auth.pin_matches(pin, person["pin_hash"]):
            auth.note_pin_failure(person["id"], now)
            if auth.pin_locked(person["id"], now):
                return deny("Bitte einen Moment warten.")
            return deny("Der PIN ist nicht korrekt.")
    auth.clear_pin_failures(person["id"])
    token = auth.open_session(person["id"], now)
    return _stamp_session(RedirectResponse("/", status_code=303), token)


@app.post("/logout")
async def logout(request: Request):
    auth.drop_session(request.cookies.get(auth.COOKIE))
    return _clear_session_cookie(RedirectResponse("/login", status_code=303))


def _catalog_ready(catalog):
    return any(level.get("options") for level in catalog.get("levels") or [])


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    user = request.state.user
    boards = auth.allowed_boards(user["id"])
    if not boards:
        return render(
            request,
            "access.html",
            {"active": "erfassung", "mode": "keine", "boards": []},
        )
    requested = (request.query_params.get("board") or "").strip()
    if len(boards) == 1 and not requested:
        chosen = boards[0]
    else:
        chosen = next((board for board in boards if board["key"] == requested), None)
        if requested and chosen is None:
            return HTMLResponse("Dieses Board ist nicht freigegeben.", status_code=403)
        if chosen is None:
            return render(
                request,
                "access.html",
                {"active": "erfassung", "mode": "auswahl", "boards": boards},
            )
    catalog = capture_catalog(chosen["key"])
    if not _catalog_ready(catalog):
        return render(
            request,
            "access.html",
            {"active": "erfassung", "mode": "leer", "boards": boards, "board": chosen},
        )
    last_capture = latest_real_capture_label([chosen["id"]])
    return render(
        request,
        "index.html",
        {
            "active": "erfassung",
            "last_capture": last_capture,
            "last_capture_saved": bool(last_capture),
            "catalog": catalog,
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
        board_ids=_data_scope(request.state.user),
        stufen=filters["stufen"],
        wochentage=filters["wochentage"],
    )
    ignored = filters["ignored"]
    if filters["herkunft"] and not result["applied_herkunft"]:
        ignored = True
    if filters["interesse"] and not result["applied_interesse"]:
        ignored = True
    if filters["detail"] and not result["applied_detail"]:
        ignored = True
    return render(
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
    scope = _data_scope(request.state.user)
    herkunft_options, interesse_options = filter_names(modus, scope)
    herkunft, invalid_herkunft = apply_option_filter(
        herkunft_options, (params.get("herkunft") or "").strip()
    )
    interesse, invalid_interesse = apply_option_filter(
        interesse_options, (params.get("interesse") or "").strip()
    )
    if invalid_herkunft or invalid_interesse:
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
    report = compare_periods(modus, herkunft, interesse, left_period, right_period, art, scope)
    base = {"modus": modus}
    if herkunft:
        base["herkunft"] = herkunft
    if interesse:
        base["interesse"] = interesse
    _bind_heatmap(report["left"]["calendar"], "links", art, links, rechts, base)
    _bind_heatmap(report["right"]["calendar"], "rechts", art, links, rechts, base)
    choices = comparison_choices()
    return render(
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
            "herkunft_label": next(
                (item["label"] for item in herkunft_options if str(item["id"]) == herkunft),
                herkunft,
            ),
            "interesse_label": next(
                (item["label"] for item in interesse_options if str(item["id"]) == interesse),
                interesse,
            ),
            "herkunft_options": herkunft_options,
            "interesse_options": interesse_options,
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
    scope = _data_scope(request.state.user)
    board = erfassungen_board(selected, scope)
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
            board = erfassungen_board(selected, scope)
    return render(
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


def _authorized_board(user, payload):
    board_key = payload.get("board") if isinstance(payload, dict) else None
    allowed = {board["key"] for board in auth.allowed_boards(user["id"])}
    if not isinstance(board_key, str) or board_key not in allowed:
        raise HTTPException(status_code=403, detail="Dieses Board ist nicht freigegeben.")
    return board_key


def _validate_capture(payload, board_key):
    if not isinstance(payload, dict):
        raise ValueError("Die Erfassung ist unvollständig.")
    for key in (
        "started_at",
        "level1_completed_at",
        "level2_started_at",
        "level2_completed_at",
        "level3_started_at",
    ):
        if _clean_text(payload.get(key)) is None:
            raise ValueError("Die Erfassung ist unvollständig.")
    board_id, level1, level2 = prepare_capture(payload.get("level1"), payload.get("level2"), board_key)
    return board_id, level1, level2


@app.post("/api/erfassungen", status_code=201)
async def create_erfassung(payload: dict, request: Request):
    board_key = _authorized_board(request.state.user, payload)
    try:
        board_id, level1, level2 = _validate_capture(payload, board_key)
        erfassung_id, completed_label = save_erfassung(
            board_id,
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
    level1, level2 = prepare_korrektur(
        payload.get("level1") or [],
        payload.get("level2") or [],
        payload.get("board") or "",
    )
    had_selection = bool(payload.get("had_selection"))
    return from_level, to_level, elapsed, had_selection, level1, level2


async def _form(request):
    parsed = parse_qs((await request.body()).decode(), keep_blank_values=True)

    def one(name, default=""):
        values = parsed.get(name)
        if not values:
            return default
        return values[-1]

    def many(name):
        return parsed.get(name, [])

    return one, many


def _admin_target(path, **params):
    clean = {key: value for key, value in params.items() if value not in (None, "")}
    if not clean:
        return path
    return path + "?" + urlencode(clean)


def _admin_back(path, **params):
    return RedirectResponse(_admin_target(path, **params), status_code=303)


def _admin_page(request, section, **extra):
    # Zugriff nur für angemeldete Admins. Die Middleware prüft is_admin erneut.
    return render(
        request,
        "admin.html",
        {
            "active": "admin",
            "section": section,
            "boards": extra.pop("boards", list_boards()),
            "fehler": request.query_params.get("fehler", ""),
            "hinweis": request.query_params.get("hinweis", ""),
            **extra,
        },
    )


def _pick_board(boards, raw):
    if raw and str(raw).isdigit():
        number = int(raw)
        for board in boards:
            if board["id"] == number:
                return board
    return boards[0] if boards else None


@app.get("/admin", response_class=HTMLResponse)
@app.get("/admin/boards", response_class=HTMLResponse)
async def admin_boards(request: Request):
    return _admin_page(request, "boards", board=None, level=None)


@app.post("/admin/boards/{board_id}")
async def admin_save_board(board_id: int, request: Request):
    form, _many = await _form(request)
    try:
        update_board(board_id, form("name"), form("position"), form("aktiv"))
    except AdminError as error:
        return _admin_back("/admin", fehler=str(error))
    return _admin_back("/admin", hinweis="Das Board wurde gespeichert.")


@app.get("/admin/ebenen", response_class=HTMLResponse)
async def admin_levels(request: Request):
    boards = list_boards()
    board = _pick_board(boards, request.query_params.get("board"))
    levels = []
    fehler = request.query_params.get("fehler", "")
    if board:
        try:
            _board, levels = list_levels(board["id"])
        except AdminError as error:
            fehler = str(error)
    return _admin_page(
        request,
        "ebenen",
        boards=boards,
        board=board,
        level=None,
        levels=levels,
        fehler=fehler,
    )


@app.post("/admin/ebenen/{level_id}")
async def admin_save_level(level_id: int, request: Request):
    form, _many = await _form(request)
    board_id = form("board")
    try:
        update_level(level_id, form("title"), form("sort_order"), form("aktiv"))
    except AdminError as error:
        return _admin_back("/admin/ebenen", board=board_id, fehler=str(error))
    return _admin_back("/admin/ebenen", board=board_id, hinweis="Die Ebene wurde gespeichert.")


@app.get("/admin/buttons", response_class=HTMLResponse)
async def admin_buttons(request: Request):
    boards = list_boards()
    board = _pick_board(boards, request.query_params.get("board"))
    levels = []
    level = None
    buttons = []
    parent_choices = []
    cells = []
    selected = None
    fehler = request.query_params.get("fehler", "")
    if board:
        try:
            _board, levels = list_levels(board["id"])
            raw_level = request.query_params.get("ebene")
            if raw_level and str(raw_level).isdigit():
                chosen, buttons, parent_choices = list_buttons(int(raw_level))
                if chosen["board_id"] == board["id"]:
                    level = chosen
                    cells = preview_cells(buttons)
                    raw_button = request.query_params.get("button")
                    if raw_button and str(raw_button).isdigit():
                        number = int(raw_button)
                        selected = next((item for item in buttons if item["id"] == number), None)
                else:
                    buttons = []
                    parent_choices = []
        except AdminError as error:
            fehler = str(error)
            level = None
    return _admin_page(
        request,
        "buttons",
        boards=boards,
        board=board,
        levels=levels,
        level=level,
        buttons=buttons,
        parent_choices=parent_choices,
        cells=cells,
        selected=selected,
        fehler=fehler,
    )


@app.post("/admin/buttons")
async def admin_create_button(request: Request):
    form, many = await _form(request)
    board_id = form("board")
    level_id = form("ebene")
    try:
        option_id = create_button(
            int(level_id),
            form("label"),
            form("grid_row"),
            form("grid_column"),
            form("grid_width"),
            many("parents"),
        )
    except (AdminError, TypeError, ValueError) as error:
        message = str(error) if isinstance(error, AdminError) else "Der Button konnte nicht angelegt werden."
        return _admin_back("/admin/buttons", board=board_id, ebene=level_id, fehler=message)
    return _admin_back(
        "/admin/buttons",
        board=board_id,
        ebene=level_id,
        button=option_id,
        hinweis="Der Button wurde angelegt.",
    )


@app.post("/admin/buttons/{option_id}")
async def admin_save_button(option_id: int, request: Request):
    form, many = await _form(request)
    board_id = form("board")
    level_id = form("ebene")
    try:
        update_button(
            option_id,
            form("label"),
            form("position"),
            form("aktiv"),
            form("grid_row"),
            form("grid_column"),
            form("grid_width"),
            many("parents"),
        )
    except AdminError as error:
        return _admin_back("/admin/buttons", board=board_id, ebene=level_id, button=option_id, fehler=str(error))
    return _admin_back(
        "/admin/buttons",
        board=board_id,
        ebene=level_id,
        button=option_id,
        hinweis="Der Button wurde gespeichert.",
    )


@app.post("/admin/buttons/{option_id}/schieben")
async def admin_shift_button(option_id: int, request: Request):
    form, _many = await _form(request)
    board_id = form("board")
    level_id = form("ebene")
    try:
        shift_button(option_id, form("richtung"))
    except AdminError as error:
        return _admin_back("/admin/buttons", board=board_id, ebene=level_id, button=option_id, fehler=str(error))
    return _admin_back(
        "/admin/buttons",
        board=board_id,
        ebene=level_id,
        button=option_id,
        hinweis="Die Position wurde geändert.",
    )


@app.get("/admin/mitarbeiter", response_class=HTMLResponse)
async def admin_employees(request: Request):
    people = list_employees()
    for person in people:
        person["board_ids"] = [board["id"] for board in person["boards"]]
    return _admin_page(
        request,
        "mitarbeiter",
        board=None,
        level=None,
        current_employees=[person for person in people if person["status"] != "ausgeschieden"],
        former_employees=[person for person in people if person["status"] == "ausgeschieden"],
    )


@app.post("/admin/mitarbeiter")
async def admin_create_employee(request: Request):
    form, many = await _form(request)
    try:
        create_employee(form("name"), form("login_name"), many("boards"), form("is_admin"))
    except AdminError as error:
        return _admin_back("/admin/mitarbeiter", fehler=str(error))
    return _admin_back("/admin/mitarbeiter", hinweis="Der Mitarbeiter wurde angelegt.")


@app.post("/admin/mitarbeiter/{employee_id}")
async def admin_save_employee(employee_id: int, request: Request):
    form, many = await _form(request)
    try:
        update_employee(
            employee_id,
            form("name"),
            form("login_name"),
            form("status"),
            form("is_admin"),
            many("boards"),
        )
    except AdminError as error:
        return _admin_back("/admin/mitarbeiter", fehler=str(error))
    return _admin_back("/admin/mitarbeiter", hinweis="Der Mitarbeiter wurde gespeichert.")


@app.post("/admin/mitarbeiter/{employee_id}/pin")
async def admin_reset_pin(employee_id: int):
    try:
        reset_pin(employee_id)
    except AdminError as error:
        return _admin_back("/admin/mitarbeiter", fehler=str(error))
    return _admin_back("/admin/mitarbeiter", hinweis="Der PIN wurde zurückgesetzt.")


@app.post("/api/korrekturen", status_code=201)
async def create_korrektur(payload: dict, request: Request):
    _authorized_board(request.state.user, payload)
    try:
        from_level, to_level, elapsed, had_selection, level1, level2 = _validate_korrektur(payload)
        korrektur_id = save_korrektur(from_level, to_level, elapsed, had_selection, level1, level2)
    except ValueError as error:
        message = str(error)
        if not message.startswith("Die "):
            message = "Die Korrektur ist unvollständig."
        raise HTTPException(status_code=400, detail=message) from error
    return {"id": korrektur_id}
