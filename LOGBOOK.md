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

### 2026-10-02 22:24 (UTC+2)

SQLite-Grundlage angelegt. Neu erstellt: `app/database.py`. Geändert: `app/main.py` (ruft nur `init_db()` auf). Oberfläche, Templates, CSS und JavaScript unverändert. Kein Speicher-Endpunkt, keine Pakete installiert.

Datenbankdatei: `data/customer_state.db`, über `sqlite3` aus der Standardbibliothek. `init_db()` legt die Tabellen mit `CREATE TABLE IF NOT EXISTS` an und überschreibt oder leert eine vorhandene Datenbank nicht. `created_at` ist `TEXT NOT NULL` mit Default `datetime('now', 'localtime')`, Format `YYYY-MM-DD HH:MM:SS`, damit Datum, Wochentag und Uhrzeit später auswertbar sind. `erfassung_level3.erfassung_id` verweist auf `erfassungen.id` mit `ON DELETE CASCADE`. Fremdschlüssel werden pro Verbindung mit `PRAGMA foreign_keys = ON` aktiviert.

`.gitignore` schließt `*.db` bereits aus. Die Datenbankdatei erscheint nicht in `git status`.

`customer-state.service` neu gestartet und aktiv. `GET /` liefert HTTP 200. Schema, Fremdschlüssel, Cascade und erneutes Initialisieren ohne Datenverlust geprüft. Testdaten wurden wieder entfernt. Beide Tabellen sind leer.

Entwicklungsstand: Erfassung weiterhin nur im Browser. Die Datenbank existiert, ist aber noch nicht mit dem Speicherbutton verbunden.

### 2026-10-02 22:33 (UTC+2)

Speicherbutton mit SQLite verbunden. Geändert: `app/database.py`, `app/main.py`, `static/selection.js`, `templates/index.html`, `static/style.css`. Keine neue Datei, keine Pakete installiert.

`POST /api/erfassungen` speichert nur vollständige Datensätze: `level1` und `level2` nicht leer, `level3` eine Liste mit mindestens einem nicht leeren Wert. `save_erfassung()` legt die Erfassung und alle Level-3-Werte in einer Transaktion an. `created_at` setzt weiterhin SQLite. Schlägt ein Teil fehl, bleibt kein unvollständiger Datensatz. Der Button sendet den aktuellen Datensatz einmalig per POST. Nur bei erfolgreicher Antwort werden alle drei Ebenen zurückgesetzt, Ebene 2 und 3 ausgeblendet, der Button deaktiviert und „Erfassung gespeichert“ angezeigt. Bei Fehler bleibt die Auswahl bestehen, es gibt keine automatische Wiederholung.

`customer-state.service` neu gestartet und aktiv. `GET /` liefert HTTP 200. Geprüft: eine Erfassung mit einem Level-3-Wert, eine weitere mit drei Level-3-Werten, ungültige Requests ohne neue Zeilen, Rollback bei Fehler während der Level-3-Speicherung, Zurücksetzen der Oberfläche nach Erfolg. Testdaten anschließend gelöscht. Beide Tabellen sind leer.

Entwicklungsstand: Ein aktiver Klick auf „Erfassung speichern“ legt genau eine Erfassung in `data/customer_state.db` an. Die Datenbank ist leer.

### 2026-10-02 22:41 (UTC+2)

Zeitstempel auf deutsche Ortszeit umgestellt. Geändert: `app/database.py`. Auswahl- und Speicherablauf unverändert. Keine Pakete installiert. Bestehende Datensätze nicht verändert.

Ursache: `created_at` kam aus SQLite `datetime('now', 'localtime')`. Die Systemzeitzone ist UTC, deshalb lag der gespeicherte Zeitpunkt zwei Stunden vor der deutschen Ortszeit. SQLite kennt keine Zeitzone `Europe/Berlin` und keine automatische Sommer- und Winterzeit.

`save_erfassung()` setzt `created_at` jetzt in Python mit `zoneinfo.ZoneInfo("Europe/Berlin")`. Format: `YYYY-MM-DD HH:MM:SS±HH:MM`, zum Beispiel `2026-10-02 22:41:54+02:00`. Der Offset kommt aus der Zeitzone. Für neue Datenbanken entfällt der SQLite-Default `localtime`; die bestehende Tabelle und der Datensatz ID 5 bleiben unverändert.

`customer-state.service` neu gestartet. Testdatensatz geprüft und danach nur dieser Datensatz gelöscht. ID 5 ist unverändert: `2026-10-02 20:36:11`, Google, Gravel, Specialized. Sommerzeit `+02:00` und Winterzeit `+01:00` wurden über `Europe/Berlin` geprüft, nicht fest addiert.

Entwicklungsstand: Neue Erfassungen speichern die deutsche Ortszeit. ID 5 behält den bisherigen UTC-Zeitstempel.

### 2026-10-02 23:34 (UTC+2)

Zeitstempelbehandlung erneut geprüft. Keine weitere Codeänderung. `save_erfassung()` setzt `created_at` weiterhin mit `zoneinfo` und `Europe/Berlin`. Testdatensatz `2026-10-02 23:34:25+02:00` geprüft und danach nur dieser Datensatz gelöscht. ID 5 unverändert: `2026-10-02 20:36:11`, Google, Gravel, Specialized.

Entwicklungsstand: Neue Erfassungen speichern die deutsche Ortszeit. ID 5 behält den bisherigen Zeitstempel.

### 2026-10-02 23:42 (UTC+2)

Verwaltungsbereich für gespeicherte Erfassungen. Neu erstellt: `templates/erfassungen.html`, `templates/header.html`. Geändert: `app/database.py`, `app/main.py`, `templates/index.html`, `static/style.css`. Keine Pakete installiert. Speichern und Auswahl unverändert. Keine Bearbeitung, kein Löschen, kein Import, kein Export.

Navigation im Kopf: „Erfassung“ nach `/`, „Erfassungen“ nach `GET /erfassungen`. Die Liste lädt Erfassungen und Level-3-Werte in einer Join-Abfrage, ordnet die Werte in Python zu und sortiert nach Zeitpunkt in `Europe/Berlin`, neueste zuerst. Sichtbare Bezeichnungen: Herkunft, Interesse, Details. Datum und Uhrzeit werden nur für die Anzeige als `TT.MM.JJJJ` und `HH:MM` formatiert; der gespeicherte Zeitstempel bleibt unverändert. Oberhalb stehen Gesamtzahl und Anzahl von heute, berechnet mit `Europe/Berlin`. Ohne Datensätze erscheint „Noch keine Erfassungen vorhanden.“ Der Leerfall wurde an einer temporären Datenbank geprüft, nicht an der echten.

`customer-state.service` neu gestartet und aktiv. `GET /` und `GET /erfassungen` liefern HTTP 200. ID 5 wird als 02.10.2026, 22:36, Google, Gravel, Specialized angezeigt. Temporäre Datensätze für Sortierung, Zuordnung und Zählung wurden danach nur diese Datensätze gelöscht. ID 5 ist unverändert. Bestehende Erfassungen bleiben erhalten.

Entwicklungsstand: Erfassungsseite und Verwaltungsseite. Die Datenbank wird von der Liste nur gelesen.

### 2026-10-03 00:48 (UTC+2)

Demodaten für 2025 in die bestehende Datenbank geschrieben. Neu erstellt: `scripts/generate_demodaten.py`, `docs/plausibilitaetsbericht-demodaten-2025.md`. Anwendungscode unverändert. Keine Pakete installiert. Kein Datensatz gelöscht.

Zeitraum 01.01.2025 bis 31.12.2025. 2.975 neue Erfassungen, nur an geöffneten Tagen: Montag bis Freitag 10:00–19:00 Uhr, Samstag 09:00–14:00 Uhr. Sonntage und die gesetzlichen Feiertage in Hessen ohne Erfassung. Samstag hat eine eigene Tagesverteilung und eine höhere Kontaktdichte je Öffnungsstunde. Zeitstempel mit `Europe/Berlin`, Format `YYYY-MM-DD HH:MM:SS±HH:MM`. Menge und Verteilungen entstehen aus dem Modell eines ländlichen High-End-Händlers; die Ist-Anteile stehen im Plausibilitätsbericht. Ein zweiter Lauf bricht ab, solange Erfassungen aus 2025 vorhanden sind.

ID 5 bleibt `2026-10-02 22:36:11+02:00`, Google, Gravel, Specialized. ID 8 bleibt `2026-10-02 23:37:10+02:00`, Leasingportal, Kinderrad, woom. Gesamtzahl in der Datenbank: 2.977. Dienstneustart nicht nötig, die Liste liest bei jedem Aufruf. `GET /` und `GET /erfassungen` liefern HTTP 200. Die Liste zeigt 2.977 Erfassungen, 0 heute, oben ID 8 und ID 5.

Entwicklungsstand: Erfassung und Verwaltung unverändert. Die Datenbank enthält die beiden bestehenden Datensätze und die Demodaten 2025.

### 2026-10-03 01:02 (UTC+2)

Analyse-Dashboard. Neu erstellt: `templates/auswertung.html`, `static/auswertung.js`. Geändert: `app/database.py`, `app/main.py`, `templates/header.html`, `static/style.css`, `scripts/generate_demodaten.py`. Keine Pakete, keine externen Bibliotheken. Kein Commit.

Neue Route `GET /auswertung`. Navigation: Erfassung, Erfassungen, Auswertung. Die Seite rechnet Kennzahlen, Verläufe und Tabellen aus einer Join-Abfrage in SQLite und verdichtet sie in Python. Dieselben gefilterten Erfassungen speisen alle Bereiche. Keine Zahlen aus dem Plausibilitätsbericht.

Datenmodus Alle, Echtdaten (`is_demo = 0`) und Demodaten (`is_demo = 1`), Standard Demodaten. Die Spalte `is_demo` wird beim Start ergänzt, falls sie fehlt. Bestehende Erfassungen aus 2025 wurden dabei einmalig als Demodaten gekennzeichnet. Zeitpunkt, Herkunft, Interesse und Details blieben unverändert. Neue Speicherungen setzen `is_demo = 0`. Der Generator schreibt künftige Demodaten mit `is_demo = 1`; er wurde nicht erneut ausgeführt.

Filter über Query-Parameter, kombinierbar: Datenmodus, Zeitraum (Heute, 7 Tage, 30 Tage, Dieses Jahr, Gesamt, Benutzerdefiniert mit Von/Bis), Herkunft, Interesse. Ungültige Werte ergeben HTTP 200 und werden ignoriert. Zeitzone `Europe/Berlin`; der lokale Kalendertag kommt aus dem gespeicherten Offset, nicht aus UTC.

Kennzahlen: Anzahl, Durchschnitt je Tag mit Erfassungen, stärkster Tag, stärkster Monat, häufigste Herkunft, häufigstes Interesse. Diagramme mit HTML/CSS: Monate Januar bis Dezember, bei kurzen Zeiträumen Tage; Wochentage inklusive 0, dazu Erfassungen je Öffnungsstunde (Mo–Fr 9 Stunden, Sa 5 Stunden, So geschlossen, Kalendertage ohne eigenen Feiertagskalender); Tageszeit nur in den Öffnungsstunden. Herkunft und Interessen mit Anzahl und Prozent. Level 3 ist Mehrfachauswahl: Prozent bezieht sich auf Erfassungen mit diesem Detail und summiert sich nicht zu 100 %. Kombinationen Herkunft → Interesse → Detail nach Häufigkeit.

Gegenprüfung Demodaten/Gesamt mit dem Bericht: 2.975 Erfassungen, Herkunft und Interessen und Monate und Wochentage und Stunden stimmen überein. Stärkste Monate Mai und September mit je 356. Häufigste Herkunft Empfehlung, häufigstes Interesse Werkstatt. Echtdaten/Gesamt: 2. Alle/Gesamt: 2.977. Filter Google 687, Werkstatt 1.122, Google und Werkstatt 290. Leerer Zeitraum, ungültige Parameter, Sommerzeit, Winterzeit und die Jahresgrenze geprüft. Die beiden echten Erfassungen liegen nach 19:00 Uhr und erscheinen deshalb als außerhalb der Öffnungsstunden, nicht in einer Nullstunde.

`customer-state.service` neu gestartet. `GET /`, `GET /erfassungen`, `GET /auswertung` liefern HTTP 200. Speichern im Browser geprüft und nur diese Testerfassung gelöscht. ID 5 und ID 8 unverändert. Weiterhin 2.975 Demodatensätze.

Entwicklungsstand: Erfassung, Verwaltung und Auswertung. Die Datenbank enthält die zwei echten Datensätze und die Demodaten 2025.

### 2026-10-03 20:08 (UTC+2)

Mehrfachauswahl auf allen drei Ebenen, Zeitmessung abgeschlossener Erfassungen und Aktivitätskalender. Geändert: `app/database.py`, `app/main.py`, `static/selection.js`, `static/style.css`, `templates/index.html`, `templates/erfassungen.html`, `templates/auswertung.html`, `scripts/generate_demodaten.py`. Keine Pakete, keine externen Bibliotheken. Kein Commit, kein Push. Die noch nicht committete Auswertung bleibt im Arbeitsbaum.

Schema, relational, ohne JSON und ohne kommaseparierte Werte: `erfassungen` behält `id`, `created_at`, `is_demo` und erhält `started_at`, `level1_completed_at`, `level2_completed_at`, `completed_at`, alle nullable. `erfassung_herkunft` und `erfassung_interesse` hängen an der Erfassung, `erfassung_detail` hängt am jeweiligen Interesse. Alte Spalten `level1` und `level2` sowie die Tabelle `erfassung_level3` sind nach der Migration entfernt. Dauerwerte werden nicht gespeichert, sie ergeben sich aus den Zeitpunkten.

Vor der Migration lag eine Kopie unter `/tmp/customer_state_pre_migration.db`: 2.983 Zeilen, davon 2.975 Demodaten und 8 Echtdaten. Der Dienst war für die Live-Migration kurz gestoppt. Jede alte Erfassung wurde mit derselben ID übernommen: eine Herkunft, ein Interesse, die bisherigen Details in derselben Reihenfolge, `created_at` und `is_demo` unverändert, alle vier Zeitpunkte leer. Prüfung danach: keine verwaisten Beziehungen, keine doppelten Herkünfte, kein Interesse ohne Detail, keine gesetzte Zeitmessung. Ein zweiter Start legt nichts neu an. Die Datenbankdatei bleibt über `*.db` außerhalb von Git.

Ebene 1 und Ebene 2 sind Mehrfachauswahl. Ein Klick schaltet ein, ein erneuter Klick aus. „Weiter“ bleibt deaktiviert, bis mindestens ein Wert aktiv ist. Ebene 1 bleibt sichtbar, Ebene 2 ebenfalls. Ebene 3 zeigt je gewähltem Interesse eine eigene Gruppe. Details werden an genau dieses Interesse gespeichert.

Zeitmessung beginnt beim ersten Auswahlklick in Ebene 1, nicht beim Laden. Der Browser sendet `started_at`, `level1_completed_at` und `level2_completed_at`. `completed_at` setzt der Server in `Europe/Berlin`. Die Folge muss `started_at` ≤ `level1_completed_at` ≤ `level2_completed_at` ≤ `completed_at` sein, sonst HTTP 400 „Die Zeitangaben sind ungültig.“ Unbekannte Werte, Details der falschen Kategorie und unvollständige Angaben werden abgelehnt. Die Speicherung ist eine Transaktion. Abgebrochene Erfassungen schreiben keine Zeile. Bestehende Daten bekommen keine erfundenen Etappenzeiten.

`POST /api/erfassungen` nimmt `level1` als Liste und `level2` als Liste von Objekten mit `value` und `level3`. `/erfassungen` zeigt mehrere Herkünfte und je Interesse die zugehörigen Details. Die Auswertung zählt eine Erfassung pro enthaltenem Wert nur einmal. Filter treffen auch dann, wenn weitere Werte daneben stehen. Prozentwerte von Herkunft, Interesse und Details sind als Anteil gekennzeichnet und summieren sich nicht zu 100 %. „Erfassungsdauer“ nutzt nur Zeilen mit Zeitmessung. Ohne solche Zeilen steht „Noch keine Erfassungen mit Zeitmessung vorhanden.“ Der Aktivitätskalender ist HTML/CSS, Spalten sind Wochen, Zeilen Wochentage inklusive Sonntag. Intensität ist 0, niedrig, mittel, hoch, sehr hoch, aus den Quartilen der Tage mit Erfassungen im aktuellen Filter. Tooltip und `aria-label` nennen Wochentag, Datum und Anzahl. Der Kalender folgt Datenmodus, Zeitraum, Herkunft und Interesse. Bei schmaler Breite scrollt nur der Kalender, nicht die Seite.

Der Generator kann künftig mehrere Herkünfte, mehrere Interessen und je Interesse passende Details schreiben und lässt die Zeitpunkte leer. Er wurde nicht ausgeführt. Die 2.975 Demodatensätze wurden nicht neu erzeugt.

Geprüft: `GET /`, `GET /erfassungen`, `GET /auswertung` jeweils HTTP 200. Im Browser Mehrfachauswahl und „Weiter“ auf Ebene 1 und 2, getrennte Detailgruppen für E-MTB und Werkstatt, Fehlerfall behält die Auswahl, Speichern setzt die Maske zurück. Temporäre Erfassung ID 2994: Empfehlung und Google, E-MTB mit Specialized und Leasing, Werkstatt mit Inspektion und Reparatur, Zeitfolge gültig, Gesamtdauer 51 Sekunden, Median 51 Sekunden, Klasse 30–60 Sekunden. Filter Google, Empfehlung, E-MTB und Werkstatt enthielten sie. Danach nur diese ID gelöscht, Kindzeilen per Cascade mit. Demodaten/Gesamt danach unverändert 2.975. Der Kalender zeigt für Freitag, 23.05.2025 weiterhin 25 Erfassungen, Intensität sehr hoch, Wert aus der Datenbank. Sonntag 05.01.2025 bleibt mit 0 sichtbar. Zeitmessung danach bei allen 2.983 Zeilen leer.

ID 5 bleibt `2026-10-02 22:36:11+02:00`, Google, Gravel, Specialized, ohne Zeitmessung. ID 8 bleibt `2026-10-02 23:37:10+02:00`, Leasingportal, Kinderrad, woom, ohne Zeitmessung. Neben diesen beiden lagen vor der Migration bereits sechs weitere echte Erfassungen vom 03.10.2026, IDs 2988 bis 2993. Sie wurden mitmigriert und nicht gelöscht. Echtdaten danach: 8.

Entwicklungsstand: Mehrfachauswahl, zugeordnete Details, Zeitpunkte nur bei neuen abgeschlossenen Erfassungen, Dauerauswertung und Aktivitätskalender. Datenbank: 2.975 Demodatensätze und 8 Echtdatensätze. Kein Commit.

### 2026-10-03 20:15 (UTC+2)

Mehrfachauswahl in der Erfassung war im Browser nicht angekommen. Geändert: `app/main.py`, `templates/index.html`, `templates/erfassungen.html`, `templates/auswertung.html`. Keine Datenbankänderung. Kein Commit.

Ursache: Die Seite lud das neue HTML mit „Weiter“, der Browser behielt aber `selection.js` aus dem alten Einzelauswahl-Stand im Cache und forderte die Datei nicht neu an. Dieses Skript löscht bei einem zweiten Klick die vorherige Auswahl und aktiviert „Weiter“ nicht. Dadurch blieben Ebene 2 und Ebene 3 unerreichbar.

Statische Dateien werden jetzt mit `Cache-Control: no-cache` ausgeliefert. Stylesheet und Skripte hängen am Änderungszeitpunkt der Datei, zum Beispiel `/static/selection.js?v=1791050750`. Die Seiten `/`, `/erfassungen` und `/auswertung` senden ebenfalls `no-cache`.

Im Browser geprüft, ohne zu speichern: eine Herkunft aktiviert „Weiter“, eine zweite Herkunft bleibt zusätzlich aktiv. Dasselbe auf Ebene 2. Ebene 3 zeigt E-MTB und Werkstatt getrennt, Specialized und Leasing sowie Inspektion und Reparatur bleiben gleichzeitig aktiv. `GET /`, `GET /erfassungen` und `GET /auswertung` liefern HTTP 200. Dienst neu gestartet.

Entwicklungsstand: Mehrfachauswahl gilt in allen drei Ebenen, sobald die Seite neu geladen wird.

### 2026-10-03 20:27 (UTC+2)

Etappen der Zeitmessung und Anzeige der Dauer. Geändert: `app/database.py`, `app/main.py`, `static/selection.js`, `static/style.css`, `templates/erfassungen.html`, `templates/auswertung.html`. Keine Pakete. Kein Commit. Bestehende Zeilen nicht gelöscht und nicht mit erfundenen Klickzeiten gefüllt.

Neue nullable Spalten `level2_started_at` und `level3_started_at`, per `ALTER TABLE` ergänzt. Gemessen wird: erster Klick Ebene 1 bis „Weiter“, dann bis zum ersten Klick in Ebene 2, dann bis „Weiter“ in Ebene 2, dann bis zum ersten Klick in Ebene 3, dann bis zum Speichern. „Start bis Ende“ ist erster Klick Ebene 1 bis Speichern. Dauern werden berechnet, nicht zusätzlich gespeichert. Die Folge der Zeitpunkte wird serverseitig geprüft.

`/erfassungen` zeigt je Erfassung die vorhandenen Etappen. Ohne Zeitpunkte steht „Zeitmessung nicht vorhanden.“ Die drei Erfassungen 2995, 2996 und 2997 haben Ebene 1 und Start bis Ende, weil die Zwischenklicks damals noch nicht gespeichert wurden. Die Auswertung „Erfassungsdauer“ folgt Zeitraum, Herkunft und Interesse und hängt nicht am Datenmodus, damit die gemessenen Erfassungen auch bei Demodaten sichtbar sind. Je Etappe Durchschnitt, Median und Anzahl, dazu die Verteilung der Gesamtdauer.

Geprüft: ungültige Zeitfolge HTTP 400 ohne neue Zeile. Eine vollständige Testerfassung mit allen sechs Zeitpunkten, danach nur diese Zeile gelöscht. Danach 2.975 Demodaten und 11 Echtdaten, davon drei mit Teilmessung. ID 5 und ID 8 ohne Zeitmessung. `GET /`, `GET /erfassungen`, `GET /auswertung` HTTP 200. Sichtbar: Ebene 1 Ø 2 s, Start bis Ende Ø 31 s, Median 35 s, eine Erfassung unter 30 Sekunden und zwei zwischen 30 und 60 Sekunden.

Entwicklungsstand: Neue Erfassungen messen alle Etappen. Die drei schon gespeicherten Messungen zeigen Ebene 1 und die Gesamtdauer.

### 2026-10-03 20:39 (UTC+2)

Verteilung der Gesamtdauer unter 30 Sekunden feiner aufgeteilt. Geändert: `app/database.py`. Keine Datenänderung. Kein Commit.

Statt einer Klasse „unter 30 Sekunden“ gibt es „unter 10 Sekunden“, „10–20 Sekunden“ und „20–30 Sekunden“. Die Klassen ab 30 Sekunden bleiben. Aktuell: eine Erfassung unter 10 Sekunden, eine zwischen 10 und 20 Sekunden, keine zwischen 20 und 30 Sekunden, zwei zwischen 30 und 60 Sekunden. `GET /auswertung` HTTP 200. Dienst neu gestartet.

### 2026-10-03 20:42 (UTC+2)

Klassen der Gesamtdauer auf 5-Sekunden-Schritte bis 60 Sekunden gestellt, danach „über 1 Minute“. Geändert: `app/database.py`. Keine Datenänderung. Kein Commit. Ergänzt sind „unter 10 Sekunden“, „35–40 Sekunden“ und „45–50 Sekunden“, damit keine Dauer ohne Klasse bleibt. Aktuell: 1 unter 10 Sekunden, 1 in 10–15, 1 in 35–40, 1 in 50–55. `GET /auswertung` HTTP 200. Dienst neu gestartet.

### 2026-10-03 21:00 (UTC+2)

Dauer an den Ebenen, Tagesliste mit Hotmap und Zeitraumvergleich. Neu: `app/periods.py`. Geändert: `app/database.py`, `app/main.py`, `templates/erfassungen.html`, `templates/auswertung.html`, `static/auswertung.js`, `static/style.css`. Keine Daten gelöscht, keine Zeiten erfunden. Kein Commit.

In `/erfassungen` steht die Dauer an der Ebene. Ebene 1 zeigt die Etappe vom ersten Klick bis „Weiter“. Ebene 2 und Ebene 3 zeigen zuerst die Verweildauer ohne Aktion bis zum ersten Klick, danach die Etappe bis „Weiter“ beziehungsweise bis zum Speichern. Darunter steht Start bis Ende. Ohne Messung bleibt „Zeitmessung nicht vorhanden.“

Die Hotmap liegt über der Liste. Angezeigt wird das Jahr des gewählten Tages. Ohne Auswahl ist der aktuelle Tag geladen. Ein Klick auf ein Feld lädt genau diesen Tag, ein Jahreslink das letzte Datum mit Erfassungen in diesem Jahr. Freitag, 23.05.2025 bleibt bei 25 Erfassungen.

`/auswertung` vergleicht zwei Zeiträume nebeneinander: Tag, Kalenderwoche, Monat, hessische Schulferien, Ostern (Karfreitag bis Ostermontag), Weihnachten (24.–26.12.) und Brückentage. Brückentage sind der Freitag nach einem Donnerstag-Feiertag, der Donnerstag vor einem Freitag-Feiertag und der Montag vor einem Dienstag-Feiertag. Der Vergleich folgt Datenmodus, Herkunft und Interesse, nicht dem übrigen Zeitraumfilter. Standard bei Demodaten: 31.12.2025 gegen 30.12.2025. Sommerferien 2025 haben 366 Erfassungen, Ostern 2025 als Festtag 10. `GET /`, `GET /erfassungen` und `GET /auswertung` liefern HTTP 200. Dienst neu gestartet.

### 2026-10-03 21:15 (UTC+2)

Zeitraumvergleich auf eine eigene Seite gelegt. Neu: `templates/vergleich.html`, `static/vergleich.js`. Geändert: `app/main.py`, `app/database.py`, `app/periods.py`, `templates/auswertung.html`, `templates/header.html`, `static/auswertung.js`, `static/style.css`. Keine Daten gelöscht. Kein Commit.

`/auswertung` enthält den Vergleich nicht mehr. Navigation: Erfassung, Erfassungen, Auswertung, Vergleich. Route `GET /vergleich`.

Die Art wird einmal gewählt und gilt für links und rechts: Tag, Kalenderwoche, Monat, Schulferien, Festtag, Brückentag. Jede Seite zeigt die Heatmap ihres Jahres. Markiert sind die Tage des gewählten Zeitraums. Ein Klick auf ein Feld setzt nur diese Seite. Bei Schulferien, Festtag und Brückentag sind nur die passenden Tage anklickbar. Datenmodus, Herkunft und Interesse bleiben Filter. Der Zeitraumfilter der Auswertung gilt hier nicht.

Standard bei Demodaten und Tag: 31.12.2025 gegen 30.12.2025. Schulferien ohne weitere Wahl: Weihnachtsferien 2025/2026 gegen Weihnachtsferien 2024/2025. Ein Klick auf die Sommerferien links lässt rechts die Weihnachtsferien stehen: 366 gegen 41 Erfassungen. `GET /`, `GET /erfassungen`, `GET /auswertung` und `GET /vergleich` liefern HTTP 200. Bei 768 px bleibt die Seite ohne seitlichen Überlauf, die Heatmap scrollt in ihrer Spalte. Dienst neu gestartet.

### 2026-10-03 21:31 (UTC+2)

Gleiches Seitenmaß und gleiche Lage der Heatmap. Geändert: `app/main.py`, `templates/index.html`, `templates/erfassungen.html`, `templates/auswertung.html`, `templates/vergleich.html`, `static/style.css`, `static/selection.js`. Keine Datenänderung. Kein Commit.

Alle vier Seiten nutzen dieselbe Breite. Erfassung, Erfassungen, Auswertung und Vergleich haben oben einen Bereich gleicher Höhe. Darunter beginnt die Aktivität an derselben Stelle und bleibt im sichtbaren Bereich. In der Auswertung steht die Aktivität direkt unter dem Datenmodus, vor den Kennzahlen. Im Vergleich liegen die beiden Heatmaps nebeneinander auf dieser Höhe. Auf der Erfassung zeigt dieselbe Jahresansicht den aktuellen Tag; ein Klick öffnet den Tag in den Erfassungen. Ebene 2 und Ebene 3 folgen unter der Heatmap. `GET /`, `GET /erfassungen`, `GET /auswertung` und `GET /vergleich` liefern HTTP 200. Demodaten gesamt bleiben 2.975. Bei 768 px kein seitlicher Überlauf. Dienst neu gestartet.

### 2026-10-03 21:40 (UTC+2)

Erfassung ohne Heatmap, eine Ebene nach der anderen, Buttons hochkant. Geändert: `app/main.py`, `templates/index.html`, `static/selection.js`, `static/style.css`. Keine Datenänderung. Kein Commit.

Die Erfassung zeigt keine Aktivität mehr. Sichtbar ist immer nur eine Ebene: zuerst Ebene 1, nach Weiter nur Ebene 2, danach nur Ebene 3. Der Seitenrahmen mit Kopfzeile bleibt. Die Auswahl steht in einer Spalte von 420 Pixeln, untereinander, damit dieselbe Maske später in einer Android-App liegen kann. Erfassungen, Auswertung und Vergleich behalten die Desktop-Heatmap. Geprüft ohne Speichern: nur die jeweils aktive Ebene, eine Buttonspalte, bei 390 px Breite kein seitlicher Überlauf. `GET /` HTTP 200. Dienst neu gestartet.

### 2026-10-03 21:44 (UTC+2)

Hinweis nach dem Speichern an die Frage von Ebene 1 gelegt. Geändert: `app/database.py`, `app/main.py`, `templates/index.html`, `static/selection.js`, `static/style.css`. Keine Datenänderung. Kein Commit.

Nach einem Durchlauf von Ebene 1 bis 3 steht nicht mehr „Erfassung gespeichert“ über der Ebene. Neben „Wie ist der Kunde auf uns aufmerksam geworden?“ steht in kleinerer Schrift „Letzte Erfassung:“ mit Wochentag, Uhrzeit und Datum der letzten echten Erfassung, zum Beispiel Samstag 21:39:41 03:10:2026. Ein Fehler beim Speichern bleibt als Hinweis stehen. `GET /` HTTP 200. Dienst neu gestartet.

### 2026-10-03 22:10 (UTC+2)

Feste Handyfläche, Punkteanzeige und Korrekturen. Geändert: `app/database.py`, `app/main.py`, `templates/index.html`, `templates/auswertung.html`, `static/selection.js`, `static/style.css`. Neue Tabellen `korrektur` und `korrektur_status`. Neue Spalten `level2_opened_at` und `level3_opened_at` an `erfassungen`. Keine Erfassung gelöscht. Kein Commit.

Die Erfassung ist immer 420×640 Pixel, auf schmalen Fenstern nur schmaler, nicht flacher. Die Buttons stehen zweispaltig, gleich groß, und beginnen und enden auf allen drei Ebenen an derselben Stelle. „Weiter“ und „Auswahl bestätigen“ liegen im selben Feld. Drei Punkte: auf Ebene 1 einer gefüllt, auf Ebene 2 zwei, auf Ebene 3 drei. Nur gefüllte Punkte sind klickbar und öffnen diese Ebene ohne Auswahl. Zurück auf Ebene 1 setzt die Zeit auf 0:00 und zeigt „Letzte Erfassung: Abgebrochen“ in Rot. Eine gespeicherte Erfassung bleibt grün. Von Ebene 3 nach Ebene 2 ist Ebene 2 leer, die Zeit von Ebene 2 beginnt neu. Die Verweildauer zählt ab dem neuen Öffnen, damit ein Rücksprung die Etappe nicht verlängert. Jeder Rücksprung speichert Ausgangsebene, Zielebene, vergangene Sekunden und den damaligen Stand. In der Auswertung zeigt „Korrekturen“ Tageszeit, Rücksprung und Stand, unabhängig vom Datenmodus. Hintergrund, Logos und Farben aus dem Mockup sind nicht übernommen. Beim Prüfen sind zwei Korrekturen entstanden (Ebene 3 nach 2, Ebene 2 nach 1); es wurde keine Erfassung gespeichert. Demodaten bleiben 2.975, echte Erfassungen 14. `GET /`, `/erfassungen`, `/auswertung` und `/vergleich` liefern HTTP 200. Dienst neu gestartet.

### 2026-10-03 22:20 (UTC+2)

Zeitanzeige entfernt, letzte Erfassung zurück an die Frage, Punkte mittig. Geändert: `templates/index.html`, `static/style.css`, `static/selection.js`. Keine Datenänderung. Kein Commit.

Die laufende Zeit wird nicht mehr angezeigt. Die Messung für Etappen und Korrekturen bleibt. „Letzte Erfassung“ steht wieder in kleinerer Schrift direkt neben der Frage. Die drei Punkte sind in der Handyfläche zentriert. `GET /` HTTP 200. Dienst neu gestartet.

### 2026-10-03 22:34 (UTC+2)

Zwei Sekunden Pause nach Ebene 3. Geändert: `static/selection.js`, `static/style.css`. Keine Datenänderung. Kein Commit.

Nach dem Speichern ist Ebene 1 für zwei Sekunden nicht anklickbar, damit kein versehentlicher Tipp eine neue Erfassung startet. Danach sind die Buttons wieder frei. Die Zeit wird dabei nicht angezeigt. Geprüft ohne Speichern. `GET /` HTTP 200.

### 2026-10-03 22:40 (UTC+2)

Vierte Ebene mit der Auswahl. Geändert: `templates/index.html`, `static/selection.js`, `static/style.css`. Keine Datenänderung. Kein Commit.

Nach „Auswahl bestätigen“ zeigt Ebene 4 die gespeicherte Auswahl als Buttons, drei Sekunden lang. Die drei Punkte sind dabei alle gefüllt und nicht klickbar. Danach folgt Ebene 1, weiterhin mit der Zwei-Sekunden-Sperre. Die Zeit wird nicht angezeigt. Geprüft ohne Speichern. `GET /` HTTP 200. Dienst neu gestartet.

### 2026-10-03 22:42 (UTC+2)

Ebene 2 auf dem Drei-Sekunden-Screen als Button. Geändert: `static/selection.js`. Keine Datenänderung. Kein Commit.

Die Fahrradtypen aus Ebene 2 stehen dort nicht mehr als Überschrift, sondern als Button in derselben Größe wie Herkunft und Details. Geprüft ohne Speichern.

### 2026-10-03 22:46 (UTC+2)

Zusammenfassung in drei Sektoren. Geändert: `static/selection.js`, `static/style.css`. Keine Datenänderung. Kein Commit.

Ebene 1, Ebene 2 und Ebene 3 haben auf dem Drei-Sekunden-Screen jeweils einen eigenen Bereich. Die Auswahl aus Ebene 2 steht über der aus Ebene 3. Geprüft ohne Speichern.

### 2026-10-03 22:51 (UTC+2)

Sektorbeschriftung entfernt, Rennrad, Triathlon und Zubehör ergänzt. Geändert: `app/database.py`, `templates/index.html`, `static/selection.js`, `static/style.css`. Keine Datenänderung. Kein Commit.

Auf dem Drei-Sekunden-Screen steht nicht mehr „Ebene“. Die drei Bereiche bleiben untereinander. In Ebene 2 gibt es zusätzlich Rennrad und Triathlon, jeweils mit Specialized, sowie Zubehör mit Luftpumpe, Beleuchtung, Schutzbleche, Schlösser, Griffe, Pflege und Reinigungsprodukte. Geprüft ohne Speichern. `GET /` HTTP 200. Dienst neu gestartet.

### 2026-10-03 22:54 (UTC+2)

Werkstatt aus der Erfassung genommen, Fragetext in Ebene 2 geändert. Geändert: `app/database.py`, `templates/index.html`, `static/selection.js`. Keine bestehenden Erfassungen gelöscht. Kein Commit.

Werkstatt ist in Ebene 2 nicht mehr wählbar. Die Frage lautet „Für was interessierte sich der Kunde?“. Ältere Werkstatt-Erfassungen bleiben in der Auswertung sichtbar. Geprüft ohne Speichern. `GET /` HTTP 200. Dienst neu gestartet.

### 2026-10-03 23:02 (UTC+2)

Button „Produkt fehlte“ bei den Marken. Geändert: `app/database.py`, `static/selection.js`. Keine Datenänderung. Kein Commit.

In Ebene 3 steht der Button bei jedem Fahrradtyp hinter den Marken. Bekleidung und Zubehör haben ihn nicht. Geprüft ohne Speichern. `GET /` HTTP 200. Dienst neu gestartet.

### 2026-10-03 23:07 (UTC+2)

Stammkunde in Ebene 1. Geändert: `app/database.py`, `templates/index.html`, `static/style.css`. Keine Datenänderung. Kein Commit.

Unter Arbeit und Sonstiges liegt ein Button über beide Spalten, gleiche Höhe wie die anderen. Geprüft ohne Speichern. `GET /` HTTP 200. Dienst neu gestartet.

### 2026-10-03 23:23 (UTC+2)

Heatmaps im Vergleich verkleinert. Geändert: `static/style.css`, `static/vergleich.js`. Keine Datenänderung. Kein Commit.

Auf der Vergleichsseite sind die Tageszellen halb so groß wie auf den anderen Seiten. Beide Jahressichten stehen nebeneinander ohne seitliches Scrollen. Ein Kalender über zwei Jahre wird zusätzlich so eingepasst, dass er in seiner Spalte bleibt. Erfassungen und Auswertung behalten die bisherige Größe. Geprüft bei 1440 px.

### 2026-10-03 23:38 (UTC+2)

Zeitraum-Buttons in der Auswertung. Geändert: `app/main.py`, `app/database.py`, `templates/auswertung.html`, `static/auswertung.js`, `static/style.css`. Keine Datenänderung. Kein Commit.

Statt der Auswahlliste gibt es Buttons: Heute, Woche (Montag bis Sonntag der laufenden Woche), Monat, Quartal (die letzten drei Monate, der aktuelle Monat ist der letzte), Halbjahr (die letzten sechs Monate, ebenso), Jahr. Gesamt und Benutzerdefiniert bleiben. Die Zählung endet am heutigen Tag, die Heatmap zeigt die ganze Periode. Geprüft: Quartal 01.08.–31.10.2026, Halbjahr 01.05.–31.10.2026, Woche 28.09.–04.10.2026, Gesamt bleibt 2.975. `GET /auswertung` HTTP 200. Dienst neu gestartet.

### 2026-10-03 23:51 (UTC+2)

Pfeile zum Blättern, Heatmap immer das ganze Jahr. Geändert: `app/main.py`, `app/database.py`, `templates/auswertung.html`, `static/auswertung.js`, `static/style.css`. Keine Datenänderung. Kein Commit.

Links und rechts neben dem Zeitraum steht ein Pfeil. Er rückt die gewählte Spanne um eine Einheit: bei Woche um eine Woche, bei Monat um einen Monat, bei Quartal um drei Monate, bei Halbjahr um sechs, bei Jahr um ein Jahr, bei Heute um einen Tag. Die Heatmap zeigt immer das volle Jahr der Auswahl, die gewählte Spanne ist darin markiert. Geprüft: aktuelle Woche 28.09.–04.10.2026 im Jahr 2026, ein Klick links auf 21.09.–27.09.2026, rechts wieder zurück. Eine Woche im Mai 2025 zeigt das Jahr 2025 mit 84 Erfassungen in der markierten Woche. Gesamt bleibt 2.975. `GET /auswertung` HTTP 200. Dienst neu gestartet.

### 2026-10-03 23:55 (UTC+2)

Von und Bis zeigen die gewählte Spanne. Geändert: `app/main.py`, `static/style.css`. Keine Datenänderung. Kein Commit.

Nach Heute, Woche, Monat, Quartal, Halbjahr, Jahr und beim Blättern stehen Anfang und Ende in Von und Bis. Die Felder folgen der Auswahl. Unter Benutzerdefiniert bleiben sie eingebbar. Bei Gesamt bleiben sie leer. Geprüft: Woche 28.09.–04.10.2026, ein Klick links 21.09.–27.09.2026, Monat 01.10.–31.10.2026. `GET /auswertung` HTTP 200. Dienst neu gestartet.

### 2026-10-03 23:58 (UTC+2)

Statuszeile unter dem Filter entfernt. Geändert: `templates/auswertung.html`, `app/main.py`. Keine Datenänderung. Kein Commit.

Die Zeile mit Datenmodus, Zeitraum und Datum steht nicht mehr unter Von und Bis. Auswahl, Pfeile und die beiden Datumsfelder bleiben. `GET /auswertung` HTTP 200. Dienst neu gestartet.

### 2026-10-04 00:09 (UTC+2)

Filter für die dritte Ebene. Geändert: `app/database.py`, `app/main.py`, `templates/auswertung.html`. Keine Datenänderung. Kein Commit.

Neben Herkunft und Interesse gibt es das Feld Detail. Es filtert die Marken und die übrigen Werte der dritten Ebene. Steht zusätzlich ein Interesse, zählt nur das Detail zu diesem Interesse. Ältere Werte wie Reklamation bleiben wählbar. Geprüft: Specialized 686 von 2.975, MTB und Specialized 150. Unbekannte Werte werden ignoriert. `GET /auswertung` und `GET /vergleich` HTTP 200. Dienst neu gestartet.

### 2026-10-04 00:14 (UTC+2)

Filterzeile in der Auswertung neu gesetzt. Geändert: `templates/auswertung.html`, `static/style.css`. Keine Datenänderung. Kein Commit.

Herkunft, Interesse, Detail und Anwenden stehen in einer Zeile. Von und Bis liegen darüber und haben dieselbe Breite wie Herkunft und Interesse. Geprüft bei 1440 px: Von schließt mit Herkunft ab, Bis mit Interesse. Bei 390 px kein seitlicher Überlauf. `GET /auswertung` HTTP 200. Dienst neu gestartet.

### 2026-10-04 00:20 (UTC+2)

Legende der Aktivität immer mit fünf Farben. Geändert: `app/database.py`. Keine Datenänderung. Kein Commit.

Unter Erfassungen standen zwischen Weniger und Mehr nur die Farben, die im Jahr vorkamen, also drei. Die Leiste zeigt jetzt immer alle fünf Stufen, von keiner Erfassung bis sehr hoch. Geprüft auf `/erfassungen`. `GET /erfassungen` HTTP 200. Dienst neu gestartet.

### 2026-10-04 00:26 (UTC+2)

Zustandsfarben in der Auswertung wählbar. Geändert: `app/main.py`, `app/database.py`, `templates/auswertung.html`, `static/auswertung.js`, `static/style.css`. Keine Datenänderung. Kein Commit.

Rechts neben Bis und über Detail stehen die fünf Farben. Ein Klick zählt nur Tage dieser Stufe, weitere Farben lassen sich dazunehmen. Ohne Auswahl bleibt alles gezählt, gesamt 2.975. Die dunkelste Stufe allein ergibt 1.021. Die übrigen Tage in der Heatmap werden blasser. `GET /auswertung` HTTP 200. Dienst neu gestartet.

### 2026-10-04 00:45 (UTC+2)

Wochentage in der Auswertung, Hinweistext entfernt. Geändert: `app/main.py`, `app/database.py`, `templates/auswertung.html`, `static/style.css`. Keine Datenänderung. Kein Commit.

Der Satz unter Aktivität ist weg. Darunter im Filter stehen Mo bis So. Mehrere Tage lassen sich zusammen wählen, zum Beispiel Montag, Mittwoch und Freitag. Ohne Auswahl bleibt alles gezählt, gesamt 2.975. Montag allein ergibt 359, die drei Tage zusammen 1.435. Andere Wochentage in der Heatmap werden blasser. `GET /auswertung` HTTP 200. Dienst neu gestartet.

### 2026-10-04 00:48 (UTC+2)

Datenmodus aus der Auswertung genommen. Geändert: `templates/auswertung.html`, `app/main.py`. Keine Datenänderung. Kein Commit.

Demodaten, Echtdaten und Alle sind dort nicht mehr wählbar. In der Entwicklung zählen die Demodaten mit den echten Erfassungen zusammen, gesamt 3.000. Der Vergleich behält den Datenmodus. `GET /auswertung` HTTP 200. Dienst neu gestartet.

### 2026-10-04 01:04 (UTC+2)

Zeitraum abwählbar, Zustand und Wochentag umrandet. Geändert: `app/database.py`, `templates/auswertung.html`, `static/auswertung.js`, `static/style.css`. Keine Datenänderung. Kein Commit.

Ein zweiter Klick auf den aktiven Zeitraum setzt die Auswahl auf Gesamt. Zustand und Wochentag umranden die passenden Tage so wie ein Zeitraum, die übrigen Felder bleiben deckend. Liegt zusätzlich ein Zeitraum, gilt die Umrandung nur in diesem Bereich. Geprüft: Quartal Juni bis August 2025 markiert 92 Tage, zusammen mit der dunkelsten Stufe bleiben 20 umrandet, alle in diesem Quartal. Ein zweiter Klick auf Quartal hebt den Zeitraum auf und behält die Stufe. `GET /auswertung` HTTP 200. Dienst neu gestartet.

### 2026-10-05 00:24 (UTC+2)

Boards, Stammdaten und Mitarbeitergrundmodell. Neu: `app/catalog.py`. Geändert: `app/database.py`, `app/main.py`, `static/selection.js`, `templates/index.html`, `templates/auswertung.html`, `templates/vergleich.html`, `scripts/generate_demodaten.py`. Kein Commit, kein Push. Die Datenbankdatei bleibt außerhalb von Git.

Es gibt die Boards `verkauf` (Verkauf) und `werkstatt` (Werkstatt). Jedes Board hat drei Ebenen mit eigener Überschrift, Sortierung und Aktiv-Flag. Auswahloptionen haben eine stabile ID, einen Schlüssel und eine sichtbare Bezeichnung. Ein Schlüssel ändert sich nicht, wenn die Bezeichnung später geändert wird. Details hängen über `board_option_parents` an den Interessen, nur über IDs. Eine Detailoption kann mehreren Interessen gehören. Boards, Ebenen und Optionen werden nicht gelöscht, sondern mit `aktiv` aus- und eingeblendet.

Die Verkaufserfassung liest Überschriften und Buttons aus diesen Stammdaten. Die bisherige Route zeigt weiterhin Verkauf. Werkstatt hat die drei Ebenen, aber keine Kategorien. Historische Werte, die im aktuellen Katalog nicht mehr wählbar sind, insbesondere Werkstatt und ihre Details, liegen als inaktive Verkaufsoptionen vor, damit alte Erfassungen lesbar und filterbar bleiben. Neue Erfassungen bieten nur aktive Optionen an. Auswertung und Vergleich listen, was im gewählten Datenbestand tatsächlich vorkommt, auch wenn die Option inzwischen inaktiv ist. Die Bezeichnung kommt aus den Stammdaten; in der Erfassungszeile bleibt zusätzlich der Text zum Speicherzeitpunkt stehen.

Jede bestehende Erfassung zeigt auf das Board Verkauf. `employee_id` ist bei allen historischen Sätzen leer. Neue Tabellen `employees` und `employee_boards`: Anzeigename, optionaler Loginname, `pin_hash` ohne Klartext, Status `aktiv`, `gesperrt` oder `ausgeschieden`, Kennzeichen `is_admin`. Es wurde kein Mitarbeiter und kein PIN angelegt. Login, Adminoberfläche und Werkstattmaske fehlen bewusst.

Migration beim Start, wiederholbar. Ein zweiter Start legt nichts doppelt an und vergibt keine IDs neu. Vorher und nachher: 3.000 Erfassungen, 2.975 Demo, 25 echt. ID 5 bleibt Google, Gravel, Specialized. ID 8 bleibt Leasingportal, Kinderrad, woom. 17 Zeitmessungen und 5 Korrekturen unverändert, alle an Options-IDs gebunden. Keine verwaisten Beziehungen, keine doppelten Schlüssel, `foreign_key_check` leer.

Getestet und danach entfernt: aktive Verkaufsoption „Testoption“, eine Erfassung damit, Sichtbarkeit in Erfassung, Erfassungen und Auswertung, danach deaktiviert und aus der neuen Erfassung verschwunden, historisch weiter sichtbar. Anschließend nur diese Erfassung und diese Option gelöscht. Testmitarbeiter mit Verkauf und Werkstatt, ohne PIN, danach nur dieser Mitarbeiter gelöscht. Bestand danach wieder 3.000 / 2.975 / 25.

`GET /`, `/erfassungen`, `/auswertung` und `/vergleich` liefern HTTP 200. Im Browser: Mehrfachauswahl, Weiter, getrennte Detailgruppen, Speichern wird erst mit einem Detail je Interesse aktiv. Freitag, 23.05.2025 bleibt bei 25 Erfassungen. Filter Herkunft Google zählt 692. Dienst neu gestartet.

### 2026-10-05 09:38 (UTC+2)

Adminoberfläche für die Konfiguration am Desktop. Neu: `app/admin_data.py`, `templates/admin.html`. Geändert: `app/catalog.py`, `app/database.py`, `app/main.py`, `static/selection.js`, `static/style.css`, `templates/header.html`. Kein Commit, kein Push. Die Datenbankdatei bleibt außerhalb von Git.

`GET /admin` zeigt Boards, Ebenen, Buttons und Mitarbeiter. Eine Anmeldung ist bewusst noch nicht eingebaut und im Code sowie auf der Seite als später markiert. Es gibt keine Löschrouten. Boards, Ebenen, Buttons und Mitarbeiter bleiben in der Datenbank und werden nur über aktiv bzw. den Mitarbeiterstatus aus dem Alltag genommen.

Boards: sichtbarer Name, Sortierung und aktiv. Der Schlüssel bleibt fest. Ebenen: sichtbare Überschrift, Sortierung und aktiv. Die Position 1, 2 oder 3 bleibt die Ebene. Die Erfassung liest die Überschriften daraus. Buttons: Bezeichnung, logische Sortierung, aktiv, Rasterzeile, Rasterspalte und Breite. Die Sortierung und die Rasterposition sind getrennt. Ein neuer Button bekommt ID und Schlüssel automatisch. Umbenennen ändert den Schlüssel nicht.

Jede Ebene hat ein Raster mit vier Spalten und beliebig vielen Zeilen. Breite 1 bis 4, ohne über die vierte Spalte hinaus. Leerplätze bleiben leer. Zwei aktive Buttons derselben Ebene dürfen dieselben Zellen nicht belegen. Ein breiter Button belegt mehrere Zellen. Inaktive Buttons belegen keine Zellen. Die Erfassung setzt die Buttons mit Zeile und Breite in dieses Raster. Das bisherige Verkaufslayout liegt darin als Zweierpaare, Stammkunde über alle vier Spalten.

Ebene-3-Buttons werden über `board_option_parents` einem oder mehreren Ebene-2-Buttons zugeordnet. Mitarbeiter: Anzeigename, optionaler Loginname, ein oder mehrere Boards, Admin ja oder nein, Status aktiv, gesperrt oder ausgeschieden. Ausgeschiedene stehen getrennt. Der PIN wird nicht vergeben und der Hash nie angezeigt. „PIN zurücksetzen“ setzt nur `pin_hash` auf leer, auch wenn noch keiner hinterlegt ist.

Geprüft und danach zurückgesetzt: Layouts 3+1, 1 plus Leerplatz plus 2, 2+2, 1+1+1+1, Breite 4 und Leerplatz plus 1 plus Leerplatz plus 1, jeweils in der Adminansicht, in der Speicherung und in der Erfassung. Kollision Zeile 1 Spalte 1 Breite 3 gegen Spalte 3 Breite 2 abgelehnt, Bestand unverändert. Überstand über Spalte 4 abgelehnt. Temporärer Button „Testbutton Admin“ ohne Codeänderung in Admin, Erfassung, Speicherung, Erfassungen, Auswertung und Vergleich. Nach dem Deaktivieren weg aus der neuen Erfassung, historisch weiter sichtbar. Temporäre Ebene-3-Zuordnung an zwei Interessen, danach geändert. Testmitarbeiter mit Verkauf und Werkstatt, Status aktiv, gesperrt, ausgeschieden und zurück, Admin an und aus, PIN-Reset bei leerem Hash ohne Fehler. Anschließend nur die Testdaten entfernt.

Danach wieder 3.000 Erfassungen, 2.975 Demo, 25 echt, 17 Zeitmessungen, 5 Korrekturen, keine Mitarbeiter, 53 Optionen, Stammkunde wieder Zeile 4 Breite 4. `foreign_key_check` leer. `GET /`, `/erfassungen`, `/auswertung`, `/vergleich` und `/admin` liefern HTTP 200. Im Browser: Vierspaltenraster, Mehrfachauswahl und Weiter. Die letzte echte Erfassung bleibt Samstag 23:11:42 vom 03.10.2026. Dienst neu gestartet.

### 2026-10-05 21:05 (UTC+2)

Buttonverwaltung auf Einzel-Editor umgestellt. Geändert: `templates/admin.html`, `app/main.py`, `static/style.css`. Kein Commit, kein Push. Schema, Rastermodell und Validierung bleiben.

Unter `/admin/buttons` ist das Vierspaltenraster das Auswahlwerkzeug. Ein Klick auf einen Button öffnet genau einen Editor mit Bezeichnung, Sortierung, Zeile, Spalte, Breite, aktiv und dem festen Schlüssel. Hoch, Runter, Links und Rechts wirken nur auf diese Auswahl. Nach Speichern oder Bewegung bleibt derselbe Button ausgewählt, das Raster zeigt die neue Position. Ohne Auswahl steht „Button im Raster auswählen.“ Der Bereich zum Anlegen bleibt darunter. Inaktive Buttons sind über eine kurze Liste wieder erreichbar. Auf Ebene 3 bleibt die Zuordnung zu einer oder mehreren Ebene-2-Optionen im Editor und beim Anlegen erhalten.

Geprüft: Verkauf Ebene 1 ohne und mit Auswahl, Wechsel von Empfehlung zu KI, Breite testweise geändert und zurückgesetzt, Bewegung und abgelehnte Bewegung, Ebene 3 mit Elternzuordnung. Ein temporärer Button wurde direkt ausgewählt und wieder entfernt. Bestand danach 3.000 / 2.975 / 25. `GET /`, `/erfassungen`, `/auswertung`, `/vergleich`, `/admin` und `/admin/buttons` liefern HTTP 200. Dienst neu gestartet.

### 2026-10-05 21:47 (UTC+2)

Mitarbeiteranmeldung für den gemeinsamen Arbeitsplatz. Neu: `app/auth.py`, `templates/login.html`, `templates/access.html`. Geändert: `app/main.py`, `app/database.py`, `static/selection.js`, `static/style.css`, `templates/header.html`, `templates/admin.html`. Kein Commit, kein Push. Die Datenbankdatei bleibt außerhalb von Git. Es wurde keine Bibliothek installiert.

Die Mitarbeiteranmeldung dient ausschließlich der Zugriffskontrolle. Fachliche Erfassungen werden nicht mit Mitarbeitern verknüpft und können nicht personenbezogen nach Mitarbeitern ausgewertet werden.

`erfassungen.employee_id` bleibt im Schema, wird aber nicht beschrieben. Alle bestehenden Werte bleiben NULL, auch eine neue Erfassung. Die Mitarbeiter-ID steht nur in der serverseitigen Sitzung und dient dort der Anmeldung, der Boardfreigabe und der Adminprüfung. Sie wird nicht in Erfassungen, Zeitmessungen, Korrekturen oder Auswertungen geschrieben. Es gibt keine Zuordnung über Sitzungs-ID, IP oder Gerätekennung und keine personenbezogene Erfassungsstatistik. Auch Admins bekommen keine Auswertung nach Mitarbeiter, keine Rangliste und keinen Mitarbeiterfilter.

Ohne Sitzung zeigt `GET /login` nur aktive Mitarbeiter als große Namen. Loginname, E-Mail und Registrierung sind dort nicht nötig. Gesperrte Mitarbeiter lassen sich nicht anmelden, ausgeschiedene erscheinen nicht in der Auswahl. Ist `pin_hash` leer, legt der Mitarbeiter nach der Auswahl selbst einen PIN aus genau vier Ziffern fest und wiederholt ihn. Der Admin vergibt diesen PIN nicht. „PIN zurücksetzen“ setzt weiterhin nur `pin_hash` auf leer; beim nächsten Login wird der PIN neu festgelegt. Ein vorhandener Hash wird mit dem eingegebenen PIN geprüft. Falsch ist die Meldung „Der PIN ist nicht korrekt.“, ohne den PIN und ohne technische Einzelheiten. Der Adminstatus umgeht diese Prüfung nicht.

Der Hash ist PBKDF2-HMAC-SHA256 aus der Standardbibliothek, 210.000 Runden, 16 Byte Zufallssalz pro Mitarbeiter, Vergleich über `hmac.compare_digest`. Gespeichert wird `pbkdf2_sha256$Runden$Salz$Hash`. Kein Klartext, kein bloßes SHA256, kein Hash im HTML und kein PIN im Protokoll. Nach fünf falschen Versuchen innerhalb von zehn Minuten für denselben Mitarbeiter sperrt der Server diesen PIN für 60 Sekunden. Die Sperre liegt im Arbeitsspeicher des Dienstes.

Die Sitzung ist ein zufälliges Token im HttpOnly-Cookie `cs_session`. Sie gilt für den Kalendertag Europe/Berlin des Logins und endet zum nächsten Mitternachtspunkt in dieser Zeitzone, nicht 24 Stunden nach der Anmeldung. Sommer- und Winterzeit laufen über `ZoneInfo`. Ein Neustart des Dienstes beendet alle Sitzungen, weil sie nicht in der Datenbank liegen. `POST /logout` löscht die Sitzung sofort und kehrt zur Auswahl zurück.

Bei jedem geschützten Aufruf werden Status, Adminrecht und Boards neu aus der Datenbank gelesen. Gesperrt oder ausgeschieden beendet die Sitzung. Ein entzogenes Board ist danach nicht mehr benutzbar. Genau ein aktives freigegebenes Board öffnet direkt die Erfassung. Mehrere Boards zeigen „Was möchtest du erfassen?“. Kein Board erlaubt keine Erfassung und vergibt Verkauf nicht automatisch. Werkstatt ohne Optionen zeigt „Dieses Board ist noch nicht konfiguriert.“ Der Boardschlüssel wird beim Speichern mitgeschrieben. Das ist die vorhandene Zuordnung Erfassung zu Board, keine Mitarbeiterzuordnung. Ein fremdes Board liefert serverseitig „Dieses Board ist nicht freigegeben.“

`/admin` und die schreibenden Adminaufrufe verlangen einen angemeldeten Mitarbeiter mit `is_admin`. Andere erhalten keinen Zugriff, auch nicht über die direkte Adresse. Der Menüpunkt Admin erscheint nur dann. Adminrecht und Boardfreigabe sind getrennt: ein Admin sieht die vorhandenen Gesamtansichten, erfasst aber nur auf seinen eigenen Boards. Erfassungen, Auswertung und Vergleich eines normalen Mitarbeiters sind auf seine aktuell freigegebenen Boards begrenzt.

Beim ersten Seitenaufbau rief die Ausgabe sich selbst auf und lieferte HTTP 500. Behoben, indem die Vorlage über `TemplateResponse` ausgegeben wird. Dienst danach neu gestartet.

Geprüft und danach entfernt: erster Login, Ablehnung von 123, 12345, ABCD und ungleichen vier Ziffern, gesetzter Hash ohne Klartext, Logout, falscher und richtiger PIN, Versuchssperre auch für einen Admin, Tagesgrenze für Wintertag, Sommertag, kurz vor Mitternacht und die Zeitumstellungen am 29.03.2026 und 25.10.2026. Verkauf allein, Werkstatt allein, beide Boards und kein Board. Normaler Mitarbeiter erhält auf `/admin` HTTP 403, ein Admin kommt hinein, nach Entzug des Adminrechts nicht mehr. Eine Test-Erfassung unter Anmeldung bleibt bei `employee_id` NULL. Zeitmessungen und Korrekturen haben keine Mitarbeiterspalte. Erfassungen, Auswertung und Vergleich zeigen den Testmitarbeiter nicht. Keine neue Tabelle. Boldt, Fynn und Zeisler bleiben ohne PIN, Boldt und Fynn an Verkauf, Zeisler an Werkstatt. Bestand danach wieder 3.000 / 2.975 / 25, 17 Zeitmessungen, 5 Korrekturen, `foreign_key_check` leer. Im Browser: Namensauswahl, PIN-Festlegung ohne Speichern bei Boldt, Anmeldung eines temporären Mitarbeiters direkt in die Verkaufserfassung, Mehrfachauswahl, Weiter, kein Admin-Menü, Abmelden. Dieser Mitarbeiter wurde entfernt. `GET /` ohne Anmeldung leitet auf `/login`.
