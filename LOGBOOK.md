# Logbook — Customer State

## Projektgrundlagen

Stand der hier festgehaltenen Grundlagen: 2026-10-02 00:42 (UTC+2).

- Projektname: Customer State
- Projektpfad: /opt/customer-state
- Backend: Python / FastAPI
- Webanwendung
- Git-Repository ist vorhanden
- Python Virtual Environment: .venv
- aktueller Einstiegspunkt: app/main.py
- vorhandene Verzeichnisse: app, data, static, templates
- aktuelle Startseite zeigt „Customer State“ und „System läuft.“

## Regeln

- Neue Einträge werden chronologisch ergänzt.
- Bestehende Einträge dürfen nicht überschrieben oder nachträglich umformuliert werden.
- Jeder Eintrag enthält Datum und Uhrzeit.
- Dokumentiere relevante Änderungen am Projekt.
- Dokumentiere neu erstellte, geänderte oder entfernte Dateien.
- Dokumentiere wichtige technische Entscheidungen.
- Dokumentiere Fehler und deren Lösung, wenn sie für spätere Arbeiten relevant sind.
- Dokumentiere den aktuellen Entwicklungsstand nach einer Änderung.
- Keine unnötigen Detailprotokolle über triviale Befehle.

## Einträge

### 2026-10-02 00:42 (UTC+2)

Logbook angelegt. Neu erstellt: `LOGBOOK.md`. Keine andere Datei geändert.

Entwicklungsstand: FastAPI-Webanwendung mit Einstiegspunkt `app/main.py`. Die Startseite (`GET /`) liefert HTML mit der Überschrift „Customer State“ und dem Text „System läuft.“ Verzeichnisse `app`, `data`, `static` und `templates` sowie das Virtual Environment `.venv` und ein Git-Repository sind vorhanden. `README.md` ist leer.

### 2026-10-02 01:03 (UTC+2)

Eingebettete HTML-Testseite durch ein Jinja2-Template ersetzt. Jinja2 3.1.6 war bereits in `.venv` installiert; nichts neu installiert.

Neu erstellt: `templates/index.html`. Geändert: `app/main.py`. `GET /` lädt die Startseite über `Jinja2Templates` aus dem Ordner `templates` (Arbeitsverzeichnis des Dienstes ist `/opt/customer-state`). Template-Antwort folgt der Signatur von Starlette 1.7: `TemplateResponse(request, name)`.

Entscheidung: vorerst nur die Überschrift „Customer State“. Kein CSS, kein JavaScript, keine Datenbank, keine Buttons oder Eingabefelder. Projektstruktur unverändert.

Entwicklungsstand: FastAPI-Webanwendung. Die Startseite rendert `templates/index.html` und zeigt nur die Überschrift „Customer State“. Der Text „System läuft.“ ist entfernt. `customer-state.service` startet Uvicorn ohne `--reload`; die Änderung wird erst nach einem Neustart des Dienstes wirksam.

### 2026-10-02 01:11 (UTC+2)

Visuelles Grundlayout der Startseite angelegt. Neu erstellt: `static/style.css`. Geändert: `templates/index.html`, `app/main.py`.

`app/main.py` bindet `/static` als `StaticFiles` auf den Ordner `static` ein. Das Template verlinkt `/static/style.css`. Gestaltung nur mit eigener CSS-Datei und der Systemschrift, ohne externe Frameworks, Schriftarten oder andere externe Ressourcen.

Entscheidung: Kopfbereich mit dem Titel „Customer State“ und darunter ein leerer, abgegrenzter Inhaltsbereich. Keine Buttons, Formulare, Datenlogik und kein JavaScript.

Entwicklungsstand: FastAPI- und Jinja2-Struktur unverändert. Die Startseite zeigt den Kopf und den zentralen Inhaltsbereich. `customer-state.service` startet Uvicorn ohne `--reload`; die Änderung wird erst nach einem Neustart des Dienstes wirksam.

### 2026-10-02 01:13 (UTC+2)

Diensttest des Grundlayouts. `customer-state.service` neu gestartet. Keine Datei außer diesem Logbucheintrag geändert.

Ergebnis: Dienst aktiv, Start ohne Fehler im Journal. `GET /` liefert HTTP 200 mit Kopf „Customer State“, Inhaltsbereich und Verweis auf `/static/style.css`. `GET /static/style.css` liefert HTTP 200.

Entwicklungsstand: unverändert gegenüber 01:11. Das Grundlayout läuft über den Dienst.
