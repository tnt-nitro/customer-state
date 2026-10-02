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

### 2026-10-02 01:32 (UTC+2)

Ebene 1 der Erfassung im zentralen Inhaltsbereich. Neu erstellt: `static/selection.js`. Geändert: `templates/index.html`, `static/style.css`. `app/main.py` unverändert. Keine Pakete installiert.

Der Inhaltsbereich zeigt die Überschrift „Wie ist der Kunde auf uns aufmerksam geworden?“ und sechs große Buttons: Empfehlung, KI, Google, Leasingportal, Arbeit, Sonstiges. Die Auswahl läuft nur im Browser über `aria-pressed`. Genau ein Button kann ausgewählt sein; ein anderer Button hebt die vorherige Auswahl auf. Keine Speicherung, keine Datenbank, keine Ebene 2, keine Weiterleitung.

`customer-state.service` neu gestartet und aktiv. `GET /`, `GET /static/style.css` und `GET /static/selection.js` liefern HTTP 200. Auswahlwechsel im Browser geprüft, auch auf Tabletbreite.

Entwicklungsstand: Startseite mit Kopf „Customer State“ und Einzelauswahl Ebene 1 im Inhaltsbereich. Auswahl wird nicht gespeichert.

### 2026-10-02 09:24 (UTC+2)

Ebene 2 der Erfassung ergänzt. Geändert: `templates/index.html`, `static/style.css`, `static/selection.js`. Keine neue Datei, `app/main.py` unverändert. Keine Pakete installiert.

Ebene 2 ist ein eigener Kartenbereich unter Ebene 1 und bleibt zunächst verborgen. Nach einer Auswahl in Ebene 1 wird sie sichtbar. Überschrift: „Für welchen Fahrradtyp interessiert sich der Kunde?“ Buttons: MTB, E-MTB, Gravel, E-Gravel, Kinderrad, Lastenrad, Trekking, Trekking vollgefedert. Beide Ebenen sind unabhängige Einzelauswahlen über dieselbe Logik in `selection.js`. Ebene 1 bleibt sichtbar und markiert. Ein Wechsel der Herkunft blendet Ebene 2 nicht wieder aus und setzt eine bereits gewählte Fahrradauswahl nicht zurück. Keine Speicherung, keine Datenbank, keine Ebene 3.

`customer-state.service` neu gestartet und aktiv. `GET /`, `GET /static/style.css` und `GET /static/selection.js` liefern HTTP 200. Im Browser geprüft: Ebene 2 erscheint erst nach Ebene 1, beide Einzelauswahlen, Wechsel der Herkunft lässt Ebene 2 sichtbar. Auch auf Tabletbreite geprüft.

Entwicklungsstand: Startseite mit Kopf und zwei Auswahlbereichen. Auswahl nur im Browser, nicht gespeichert.

### 2026-10-02 20:44 (UTC+2)

Ebene 3 der Erfassung ergänzt. Geändert: `templates/index.html`, `static/selection.js`. Keine neue Datei, `static/style.css` und `app/main.py` unverändert. Keine Pakete installiert.

Ebene 3 ist ein eigener Kartenbereich und bleibt verborgen, bis in Ebene 2 ein Fahrradtyp gewählt wurde. Überschrift: „Wofür interessiert sich der Kunde?“. Die Buttons hängen vom Fahrradtyp ab und sind eine Mehrfachauswahl: erneuter Klick hebt nur diesen Button auf. Ein anderer Fahrradtyp tauscht die Buttons und setzt die Ebene-3-Auswahl zurück. Ein erneuter Klick auf denselben Fahrradtyp setzt nicht zurück. Eine Änderung nur in Ebene 1 lässt Fahrradtyp und Ebene-3-Auswahl bestehen. Keine Speicherung, keine Datenbank, keine weitere Ebene.

Konfigurationen: MTB: Specialized, Leasing, Kauf, Reparatur. E-MTB: Specialized, PIVOT, AMFLOW, Leasing, Kauf, Reparatur. Gravel: PIVOT, Specialized, Leasing, Kauf, Reparatur. E-Gravel: Specialized, PIVOT, Leasing, Kauf, Reparatur. Kinderrad: woom, Leasing, Kauf, Reparatur. Lastenrad: Riese & Müller, Leasing, Kauf, Reparatur. Trekking: Riese & Müller, Specialized, Leasing, Kauf, Reparatur. Trekking vollgefedert: Riese & Müller, Specialized, AMFLOW, Leasing, Kauf, Reparatur.

`customer-state.service` neu gestartet und aktiv. `GET /` liefert HTTP 200. Im Browser für alle acht Fahrradtypen die Buttonliste geprüft, Mehrfachauswahl und Abwahl, Reset beim Fahrradtypwechsel und Erhalt bei Wechsel nur in Ebene 1. Auch auf Tabletbreite geprüft.

Entwicklungsstand: Startseite mit drei Auswahlbereichen. Auswahl nur im Browser, nicht gespeichert.

### 2026-10-02 21:26 (UTC+2)

Ebene 2 um Bekleidung und Werkstatt erweitert. Geändert: `templates/index.html`, `static/selection.js`. Auswahlmechanik unverändert. Die bisherigen acht Fahrradtypen und ihre Ebene-3-Listen sind unverändert. Keine neue Datei, kein Paket installiert.

Ebene 2 hat jetzt 10 Einzelauswahlen. Bekleidung zeigt in Ebene 3: Helm, Trikot, Radhose, Handschuhe, Schuhe, Regenbekleidung, Jacke/Weste, Brille, Sonstiges. Werkstatt zeigt: Inspektion, Reparatur, Reklamation, Tuning, Umbau, Diagnose/Fehlersuche, Unfall/Schaden, Beratung, Sonstiges. Beide nutzen die vorhandene Mehrfachauswahl. Wechsel in Ebene 2 setzt Ebene 3 zurück. Wechsel nur in Ebene 1 erhält Ebene 2 und Ebene 3.

`customer-state.service` neu gestartet und aktiv. `GET /` liefert HTTP 200. Im Browser alle acht bisherigen Fahrradtypen sowie Bekleidung und Werkstatt geprüft, dazu Mehrfachauswahl, Abwahl, Reset und Erhalt bei Wechsel nur in Ebene 1.

Entwicklungsstand: drei Auswahlbereiche, Ebene 2 mit zehn Optionen. Auswahl nur im Browser, nicht gespeichert.

### 2026-10-02 21:41 (UTC+2)

Abschlussbutton unter Ebene 3 ergänzt. Geändert: `templates/index.html`, `static/style.css`, `static/selection.js`. Keine neue Datei, `app/main.py` unverändert. Keine Pakete installiert. Auswahlmechanik der drei Ebenen unverändert.

Der Button „Erfassung speichern“ steht unter den Ebene-3-Buttons, durch eine Trennlinie abgesetzt, und ist zunächst deaktiviert. Er wird nur aktiv, wenn Ebene 1, Ebene 2 und mindestens eine Ebene-3-Auswahl gesetzt sind. Fällt eine Bedingung weg, wird er wieder deaktiviert. Ein Klick speichert nichts und setzt nichts zurück. Er schreibt nur das aktuelle Objekt `{ level1, level2, level3 }` in die Browser-Konsole. `level3` enthält die ausgewählten Bezeichnungen in der angezeigten Reihenfolge.

`customer-state.service` neu gestartet und aktiv. `GET /` liefert HTTP 200. Geprüft: deaktiviert ohne Auswahl, nur mit Ebene 1 und mit Ebene 1 plus Ebene 2; aktiv mit mindestens einer Ebene-3-Auswahl; mehrere Ebene-3-Werte vollständig im Objekt; Wechsel von Ebene 2 deaktiviert; erneute Ebene-3-Auswahl aktiviert wieder; Wechsel nur von Ebene 1 lässt Ebene 2, Ebene 3 und den aktiven Button bestehen. Beispielobjekt: `{ level1: "Google", level2: "E-MTB", level3: ["Specialized", "Leasing"] }`. Auch auf Tabletbreite geprüft.

Entwicklungsstand: drei Auswahlbereiche und ein noch nicht speichernder Abschlussbutton. Auswahl nur im Browser.
