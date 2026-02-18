#!/usr/bin/env python3
"""Start Djomla and expose it with a public URL via Cloudflare Quick Tunnel.

Usage:
  python3 start_online.py
"""

from __future__ import annotations

import os
import platform
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

PORT = 4173
LOCAL_URL = f"http://127.0.0.1:{PORT}"
ROOT = Path(__file__).resolve().parent
BIN_DIR = ROOT / ".tools"
CF_BIN = BIN_DIR / "cloudflared"
CF_URL_PATTERN = re.compile(r"https://[-a-zA-Z0-9]+\.trycloudflare\.com")


def _download_cloudflared() -> Path:
    system = platform.system().lower()
    machine = platform.machine().lower()

    if system != "linux":
        raise RuntimeError("Automatischer Download ist aktuell nur für Linux vorbereitet.")

    if machine in {"x86_64", "amd64"}:
        url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64"
    elif machine in {"aarch64", "arm64"}:
        url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64"
    else:
        raise RuntimeError(f"Nicht unterstützte CPU-Architektur: {machine}")

    BIN_DIR.mkdir(parents=True, exist_ok=True)
    tmp_file = None
    try:
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp_file = Path(tmp.name)
        print("⬇️  Lade cloudflared herunter...")
        urllib.request.urlretrieve(url, tmp_file)
        shutil.move(str(tmp_file), CF_BIN)
        CF_BIN.chmod(CF_BIN.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    finally:
        if tmp_file and tmp_file.exists():
            tmp_file.unlink(missing_ok=True)

    return CF_BIN


def ensure_cloudflared() -> Path:
    system_path = shutil.which("cloudflared")
    if system_path:
        return Path(system_path)

    if CF_BIN.exists():
        return CF_BIN

    return _download_cloudflared()


def wait_for_local_server(timeout_s: float = 15.0) -> bool:
    start = time.time()
    while time.time() - start < timeout_s:
        try:
            with urllib.request.urlopen(f"{LOCAL_URL}/api/health", timeout=2) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            time.sleep(0.5)
    return False


def start_server() -> subprocess.Popen:
    return subprocess.Popen([sys.executable, str(ROOT / "server.py")], cwd=str(ROOT), env=os.environ.copy())


def start_tunnel(cloudflared_bin: Path) -> tuple[subprocess.Popen, str | None]:
    proc = subprocess.Popen(
        [str(cloudflared_bin), "tunnel", "--url", LOCAL_URL, "--no-autoupdate"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        cwd=str(ROOT),
    )

    public_url: str | None = None
    start = time.time()
    while time.time() - start < 25:
        line = proc.stdout.readline() if proc.stdout else ""
        if not line:
            if proc.poll() is not None:
                break
            continue
        match = CF_URL_PATTERN.search(line)
        if match:
            public_url = match.group(0)
            break

    return proc, public_url


def main() -> int:
    print("=" * 68)
    print("🚀 Djomla startet ONLINE mit öffentlicher URL")
    print("ℹ️  Zum Stoppen: Ctrl + C")
    print("=" * 68)

    server = start_server()
    tunnel = None
    try:
        if not wait_for_local_server():
            print("❌ Server konnte lokal nicht gestartet werden.")
            return 1

        print(f"✅ Lokal läuft: {LOCAL_URL}")
        try:
            cloudflared_bin = ensure_cloudflared()
        except Exception as exc:
            print("❌ Online-Tunnel konnte nicht vorbereitet werden.")
            print(f"👉 Grund: {exc}")
            print("👉 Lösung: cloudflared manuell installieren ODER Render/Docker Deploy nutzen.")
            return 1

        tunnel, public_url = start_tunnel(cloudflared_bin)

        if not public_url:
            print("❌ Konnte keine öffentliche URL erzeugen.")
            print("👉 Prüfe Internetzugang und versuche erneut.")
            return 1

        print("\n" + "=" * 68)
        print("✅ ONLINE URL (sofort teilbar):")
        print(public_url)
        print("=" * 68 + "\n")

        # Keep both processes alive.
        return server.wait()
    except KeyboardInterrupt:
        print("\n🛑 Stoppe Djomla + Tunnel...")
        return 0
    finally:
        if tunnel and tunnel.poll() is None:
            tunnel.terminate()
            try:
                tunnel.wait(timeout=5)
            except subprocess.TimeoutExpired:
                tunnel.kill()
        if server.poll() is None:
            server.terminate()
            try:
                server.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server.kill()


if __name__ == "__main__":
    raise SystemExit(main())
