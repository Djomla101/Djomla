#!/usr/bin/env python3
"""One-click local launcher for non-technical users.

- Starts Djomla server on port 4173
- Tries to open the browser automatically
- Always prints the exact URL to click/copy
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

PORT = 4173
URL = f"http://localhost:{PORT}"


def _try_open_browser(url: str) -> bool:
    """Best-effort browser open across environments."""
    try:
        if webbrowser.open(url):
            return True
    except Exception:
        pass

    # Fallback commands (Linux desktop environments)
    for cmd in (["xdg-open", url], ["gio", "open", url]):
        try:
            result = subprocess.run(cmd, check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if result.returncode == 0:
                return True
        except Exception:
            continue

    return False


def main() -> int:
    repo_dir = Path(__file__).resolve().parent
    server_file = repo_dir / "server.py"

    if not server_file.exists():
        print("❌ Fehler: server.py wurde nicht gefunden.")
        return 1

    print("=" * 64)
    print("✅ Djomla startet jetzt")
    print(f"🌐 URL: {URL}")
    print("⛔ Stoppen: im Terminal Ctrl + C")
    print("=" * 64)

    process = subprocess.Popen(
        [sys.executable, str(server_file)],
        cwd=str(repo_dir),
        env=os.environ.copy(),
    )

    try:
        time.sleep(1.2)
        opened = _try_open_browser(URL)
        if opened:
            print("✅ Browser wurde geöffnet.")
        else:
            print("⚠️ Browser konnte nicht automatisch geöffnet werden.")
            print(f"👉 Bitte diese Adresse manuell öffnen: {URL}")

        return process.wait()
    except KeyboardInterrupt:
        print("\n🛑 Stoppe Djomla...")
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
