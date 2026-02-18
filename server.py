#!/usr/bin/env python3
import json
import sqlite3
from datetime import datetime, timedelta, timezone
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parent
WEB_DIR = ROOT / "web"
DB_PATH = ROOT / "tracker.db"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def db_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def parse_iso(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone(timezone.utc)


def ensure_columns(conn: sqlite3.Connection):
    cols = {r["name"] for r in conn.execute("PRAGMA table_info(trains)").fetchall()}
    required = {
        "innsbruck_arrival_at": "TEXT",
        "arrival_confirmed": "INTEGER DEFAULT 0",
        "arrival_prompted_at": "TEXT",
        "delay_minutes": "INTEGER DEFAULT 0",
    }
    for col, ddl in required.items():
        if col not in cols:
            conn.execute(f"ALTER TABLE trains ADD COLUMN {col} {ddl}")


def init_db():
    conn = db_conn()
    with conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS trains (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              route TEXT NOT NULL,
              train_no TEXT NOT NULL,
              start_station TEXT NOT NULL,
              departure_at TEXT NOT NULL,
              innsbruck_arrival_at TEXT,
              note TEXT DEFAULT '',
              departed INTEGER DEFAULT 0,
              alarmed INTEGER DEFAULT 0,
              arrival_confirmed INTEGER DEFAULT 0,
              arrival_prompted_at TEXT,
              delay_minutes INTEGER DEFAULT 0,
              created_at TEXT NOT NULL
            )
            """
        )
        ensure_columns(conn)

    count = conn.execute("SELECT COUNT(*) FROM trains").fetchone()[0]
    if count == 0:
        now = utc_now()
        seeds = [
            ("Railjet → Wien", "867", "Bregenz", 6, 12, "Wendet auf 666"),
            ("Railjet → Wien", "163", "Buchs", 2, 7, "Aus 164"),
            ("Nightjet → Graz", "465", "Buchs", 1, 4, "LOK&KLASSEN"),
            ("DANI → München", "286", "Innsbruck", -2, -1, "ABGEFAHREN Demo"),
        ]
        with conn:
            for route, train_no, start, arrival_offset_min, dep_offset_min, note in seeds:
                arrival_at = (now + timedelta(minutes=arrival_offset_min)).isoformat()
                departure_at = (now + timedelta(minutes=dep_offset_min)).isoformat()
                conn.execute(
                    """
                    INSERT INTO trains(
                      route, train_no, start_station, departure_at, innsbruck_arrival_at, note, created_at
                    ) VALUES(?,?,?,?,?,?,?)
                    """,
                    (route, train_no, start, departure_at, arrival_at, note, now.isoformat()),
                )

    # Backfill old rows
    with conn:
        conn.execute(
            """
            UPDATE trains
            SET innsbruck_arrival_at = datetime(departure_at, '-30 minutes')
            WHERE innsbruck_arrival_at IS NULL
            """
        )
    conn.close()


def serialize_train(row: sqlite3.Row):
    now = utc_now()
    departure = parse_iso(row["departure_at"])
    inns_arrival = parse_iso(row["innsbruck_arrival_at"])
    rest = int((departure - now).total_seconds())
    arrival_rest = int((inns_arrival - now).total_seconds())
    departed = row["departed"] == 1 or rest <= 0

    prompted_at = row["arrival_prompted_at"]
    arrival_window_active = False
    if prompted_at:
        prompt_dt = parse_iso(prompted_at)
        arrival_window_active = (now - prompt_dt).total_seconds() <= 10

    return {
        "id": row["id"],
        "route": row["route"],
        "trainNo": row["train_no"],
        "start": row["start_station"],
        "departureAt": row["departure_at"],
        "innsbruckArrivalAt": row["innsbruck_arrival_at"],
        "note": row["note"],
        "departed": departed,
        "alarmed": row["alarmed"] == 1,
        "restSeconds": rest,
        "arrivalRestSeconds": arrival_rest,
        "arrivalConfirmed": row["arrival_confirmed"] == 1,
        "arrivalWindowActive": arrival_window_active,
        "delayMinutes": row["delay_minutes"] or 0,
    }


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(WEB_DIR), **kwargs)

    def _json(self, payload, status=200):
        data = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _read_json(self):
        length = int(self.headers.get("Content-Length", "0"))
        if length == 0:
            return {}
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/trains":
            q = parse_qs(parsed.query)
            search = q.get("search", [""])[0].strip().lower()
            conn = db_conn()
            rows = conn.execute("SELECT * FROM trains ORDER BY departure_at").fetchall()
            conn.close()
            trains = [serialize_train(r) for r in rows]
            if search:
                trains = [
                    t
                    for t in trains
                    if search in f"{t['route']} {t['trainNo']} {t['start']} {t['note']}".lower()
                ]
            self._json({"trains": trains, "serverTime": utc_now().isoformat()})
            return

        if parsed.path == "/api/health":
            self._json({"ok": True, "time": utc_now().isoformat()})
            return

        return super().do_GET()

    def do_POST(self):
        if self.path == "/api/trains":
            body = self._read_json()
            now = utc_now()
            dep_iso = body.get("departureAt")
            arrival_iso = body.get("innsbruckArrivalAt")
            try:
                parse_iso(dep_iso)
                parse_iso(arrival_iso)
            except Exception:
                self._json({"error": "departureAt and innsbruckArrivalAt must be ISO datetime"}, 400)
                return

            conn = db_conn()
            with conn:
                cur = conn.execute(
                    """
                    INSERT INTO trains(
                      route, train_no, start_station, departure_at, innsbruck_arrival_at,
                      note, created_at
                    ) VALUES(?,?,?,?,?,?,?)
                    """,
                    (
                        body.get("route", "Railjet → Vorarlberg"),
                        body.get("trainNo", "000"),
                        body.get("start", "Innsbruck"),
                        dep_iso,
                        arrival_iso,
                        body.get("note", "Dynamisch hinzugefügt"),
                        now.isoformat(),
                    ),
                )
                row = conn.execute("SELECT * FROM trains WHERE id=?", (cur.lastrowid,)).fetchone()
            conn.close()
            self._json({"train": serialize_train(row)}, 201)
            return

        if self.path == "/api/arrival-confirmation":
            body = self._read_json()
            train_id = body.get("trainId")
            is_present = bool(body.get("isPresent"))
            delay_minutes = int(body.get("delayMinutes", 0))

            conn = db_conn()
            row = conn.execute("SELECT * FROM trains WHERE id=?", (train_id,)).fetchone()
            if not row:
                conn.close()
                self._json({"error": "train not found"}, 404)
                return

            with conn:
                if is_present:
                    conn.execute(
                        "UPDATE trains SET arrival_confirmed=1 WHERE id=?",
                        (train_id,),
                    )
                else:
                    base_arrival = parse_iso(row["innsbruck_arrival_at"])
                    base_departure = parse_iso(row["departure_at"])
                    new_arrival = base_arrival + timedelta(minutes=delay_minutes)
                    new_departure = base_departure + timedelta(minutes=delay_minutes)
                    conn.execute(
                        """
                        UPDATE trains
                        SET innsbruck_arrival_at=?, departure_at=?, delay_minutes=delay_minutes+?,
                            arrival_prompted_at=NULL, arrival_confirmed=0
                        WHERE id=?
                        """,
                        (new_arrival.isoformat(), new_departure.isoformat(), delay_minutes, train_id),
                    )
            conn.close()
            self._json({"ok": True})
            return

        if self.path == "/api/tick":
            conn = db_conn()
            departure_alerts = []
            arrival_checks = []
            now = utc_now()

            with conn:
                rows = conn.execute("SELECT * FROM trains").fetchall()
                for row in rows:
                    train = serialize_train(row)

                    if train["departed"] and not train["alarmed"]:
                        conn.execute("UPDATE trains SET departed=1, alarmed=1 WHERE id=?", (row["id"],))
                        departure_alerts.append({"id": row["id"], "trainNo": row["train_no"]})
                    elif train["departed"]:
                        conn.execute("UPDATE trains SET departed=1 WHERE id=?", (row["id"],))

                    should_check_arrival = (
                        train["arrivalRestSeconds"] <= 0
                        and not train["arrivalConfirmed"]
                        and row["arrival_prompted_at"] is None
                    )
                    if should_check_arrival:
                        conn.execute(
                            "UPDATE trains SET arrival_prompted_at=? WHERE id=?",
                            (now.isoformat(), row["id"]),
                        )
                        arrival_checks.append(
                            {
                                "id": row["id"],
                                "trainNo": row["train_no"],
                                "innsbruckArrivalAt": row["innsbruck_arrival_at"],
                            }
                        )

            conn.close()
            self._json({"alerts": departure_alerts, "arrivalChecks": arrival_checks})
            return

        self.send_error(404, "Not found")


def main():
    init_db()
    server = ThreadingHTTPServer(("0.0.0.0", 4173), Handler)
    print("Serving app+API on http://0.0.0.0:4173")
    server.serve_forever()


if __name__ == "__main__":
    main()
