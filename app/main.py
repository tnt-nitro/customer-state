from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.database import init_db, list_erfassungen, save_erfassung

app = FastAPI(title="Customer State")
init_db()
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(
        request,
        "index.html",
        {"active": "erfassung"},
    )


@app.get("/erfassungen", response_class=HTMLResponse)
async def erfassungen(request: Request):
    overview = list_erfassungen()
    return templates.TemplateResponse(
        request,
        "erfassungen.html",
        {
            "active": "erfassungen",
            "entries": overview["entries"],
            "total": overview["total"],
            "today": overview["today"],
        },
    )


def _clean_text(value):
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text:
        return None
    return text


@app.post("/api/erfassungen", status_code=201)
async def create_erfassung(payload: dict):
    level1 = _clean_text(payload.get("level1"))
    level2 = _clean_text(payload.get("level2"))
    level3 = payload.get("level3")
    if level1 is None or level2 is None or not isinstance(level3, list) or not level3:
        raise HTTPException(status_code=400, detail="Die Erfassung ist unvollständig.")

    values = []
    for item in level3:
        text = _clean_text(item)
        if text is None:
            raise HTTPException(status_code=400, detail="Die Erfassung ist unvollständig.")
        values.append(text)

    erfassung_id = save_erfassung(level1, level2, values)
    return {"id": erfassung_id}
