# VBA ➜ Moderne Web-App: Migrationsplan (Train Live Tracker)

## 1) Analyse deiner aktuellen VBA-Logik

Dein VBA-System macht im Kern bereits ein gutes Echtzeit-Monitoring:

1. **Auto-Start/Stop beim Workbook Open/Close**
2. **1-Sekunden-Tick** mit `Application.OnTime`
3. **Robustes Parsing** von Abfahrtszeiten aus Zellen
4. **Countdown-Berechnung** je Zug
5. **Statuswechsel auf „ABGEFAHREN“** bei `rest <= 0`
6. **Blinklogik:**
   - Unter 5 Minuten blinkt Countdown-Feld
   - Unter 1 Minute blinkt Zugnummer-Feld
7. **Alarm einmalig pro Zug** (Beep + Popup)

Diese Logik kann 1:1 in eine moderne Web-App überführt werden.

---

## 2) Zielarchitektur (Web)

### Frontend (Operator UI)

- Große tabellarische Live-Ansicht (wie dein Excel-Board)
- Farbzonen + Blinkzustände + „ABGEFAHREN“-Badge
- Filter (Linie, Ziel, Zeitraum, Status)
- Vollbild-/Control-Room-Modus
- Benachrichtigungscenter statt Excel-MsgBox

### Backend

- REST API für Stammdaten + Fahrten
- WebSocket-Server für sekundengenaue Live-Updates
- Scheduler/Worker für Tick-Logik und Alarm-Events
- Regel-Engine für Warnzustände (5-Min/1-Min)

### Datenbank

- Tabellen: `trains`, `departures`, `alerts`, `events`, `users`
- Audit-/Event-Log für Nachvollziehbarkeit
- Historisierung „abgefahren“, Verspätung, Änderungen

---

## 3) Mapping: VBA → Web-Komponenten

- `IBK_SystemStarten` → Service-Start + Initialisierung der offenen Fahrten
- `IBK_Tick` → Worker-Loop (jede Sekunde) oder clientseitiger Countdown mit Server-Sync
- `IBK_ParseDeparture` → Parser/Validator im Backend + Zeitzonenhandling
- `IBK_Abgefahren()` / `IBK_AlarmGemacht()` → persistenter Zustand in DB
- `MsgBox/Beep` → In-App Alert + optional Push/Audio + Eskalationsregeln
- Zellfarben/Formatierungen → UI-State-Renderer (CSS-States)

---

## 4) Feature-Backlog

### MVP (schnell online)

1. Live-Tabelle mit Countdown
2. Automatischer Statuswechsel auf „ABGEFAHREN“
3. 5-Min- und 1-Min-Warnung (Blinkzustände)
4. Basis-CRUD für Züge/Fahrten
5. Rollen: Admin, Disponent, Viewer

### Advanced ("krank modern")

1. Echtzeit-Karte (Zugpositionen/Geo)
2. Prognosen (Verspätung mit Heuristik/ML)
3. Kollisionserkennung bei Gleis-/Umlaufkonflikten
4. Multi-Bahnhof-Mandantenfähigkeit
5. KPI-Dashboard (Pünktlichkeit, Auslastung, Alarme)
6. Mobile App / PWA mit Push Notifications
7. Integrationen (GTFS, interne APIs, CSV/Excel-Import)

---

## 5) UX-Richtung (dein Wunsch: sehr modern)

- Dark-Theme als Standard (wie dein aktueller Look)
- Große kontrastreiche Zahlen für Countdown
- Sanfte Animationen statt aggressivem Flackern
- Alarm-Prioritäten (Info/Warn/Kritisch)
- Touch-friendly Bedienelemente für Leitstandscreens

---

## 6) Technische Empfehlung

### Variante A (sehr produktiv)

- Frontend: Next.js + TypeScript + Tailwind + TanStack Table
- Backend: FastAPI + SQLAlchemy + PostgreSQL + Redis
- Realtime: WebSocket + Redis Pub/Sub
- Deployment: Docker + Railway/Fly/Render oder eigener VPS

### Variante B (komplett TypeScript)

- Frontend: Next.js
- Backend: NestJS
- DB: PostgreSQL (Prisma)
- Realtime: Socket.IO

---

## 7) Projektplan in 4 Phasen

1. **Phase 1 (1–2 Wochen):** Datenmodell, API, Auth, Grund-UI
2. **Phase 2 (1 Woche):** Live-Tick, Warnregeln, Alarmcenter
3. **Phase 3 (1 Woche):** Admin-Bereich, Import/Export, Historie
4. **Phase 4 (laufend):** Map, Prognosen, Integrationen, Mobile

---

## 8) Antwort auf deine Frage

Ja – ich kann das mit dir von Ende zu Ende bauen:

- Architektur
- MVP-Implementierung
- UI/UX im modernen Stil
- Feature-Erweiterungen
- Deployment

Wenn du willst, ist der nächste konkrete Schritt:

1. Ich scaffold’e dir direkt ein **echtes Full-Stack-MVP** (Next.js + API + DB).
2. Danach übernehmen wir deine bestehende Zuglogik vollständig in den neuen Live-Tracker.
