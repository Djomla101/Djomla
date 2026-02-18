# Djomla – komplett starten (lokal ODER online URL)

Du wolltest: **"komplette App mit URL, sofort online starten"** ✅

Das geht jetzt mit **einem Befehl**.

---

## Option A: Sofort ONLINE URL (für andere teilbar)

Im Terminal:

```bash
cd /workspace/Djomla
python3 start_online.py
```

Dann zeigt dir das Terminal eine öffentliche URL wie:

`https://xxxx.trycloudflare.com`

Diese URL kannst du direkt öffnen und weitergeben.

> Hinweis: Die URL bleibt aktiv, solange das Terminal läuft.
> Falls Tunnel-Download blockiert ist (Firmennetz/VPN), nutze Option B lokal oder ich richte dir Render als feste URL ein.

---

## Option B: Nur lokal testen

```bash
cd /workspace/Djomla
python3 start_local.py
```

Dann im Browser:

`http://localhost:4173`

---

## Welches Terminal?

- Windows: PowerShell / Windows Terminal
- Mac: Terminal
- Linux: Terminal

---

## Stoppen

Im laufenden Terminal: `Ctrl + C`

---

## Was schon fertig ist

- Live-Countdown
- Blink-/Warnfarben
- ABGEFAHREN-Status
- Innsbruck-Ankunft bestätigen
- Verspätung eintragen

---

## Dateien kurz

- `start_online.py` → startet App + öffentliche URL
- `start_local.py` → startet nur lokal
- `server.py` → Backend
- `web/` → Weboberfläche
