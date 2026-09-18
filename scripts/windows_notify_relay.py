#!/usr/bin/env python3
"""Tailscale-bound relay that turns authenticated POSTs into Windows balloon notifications."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

MAX_BODY = 16 * 1024


def notify(title: str, body: str) -> None:
    env = os.environ.copy()
    env["HARNESS_NOTIFY_TITLE"] = title[:120]
    env["HARNESS_NOTIFY_BODY"] = body[:512]
    script = (
        "Add-Type -AssemblyName System.Windows.Forms; "
        "Add-Type -AssemblyName System.Drawing; "
        "$n=New-Object System.Windows.Forms.NotifyIcon; "
        "$n.Icon=[System.Drawing.SystemIcons]::Information; $n.Visible=$true; "
        "$n.BalloonTipTitle=$env:HARNESS_NOTIFY_TITLE; "
        "$n.BalloonTipText=$env:HARNESS_NOTIFY_BODY; "
        "$n.ShowBalloonTip(5000); Start-Sleep 6; $n.Dispose()"
    )
    subprocess.Popen(
        ["powershell.exe", "-NoProfile", "-Command", script],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


class Handler(BaseHTTPRequestHandler):
    token = ""

    def log_message(self, fmt: str, *args: object) -> None:
        return

    def reply(self, status: int, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path == "/health":
            self.reply(200, {"status": "ok"})
        else:
            self.reply(404, {"error": "not_found"})

    def do_POST(self) -> None:
        if self.path != "/notify":
            self.reply(404, {"error": "not_found"})
            return
        if self.headers.get("X-Gonglz-Notify-Token", "") != self.token:
            self.reply(403, {"error": "forbidden"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            length = 0
        if length <= 0 or length > MAX_BODY:
            self.reply(400, {"error": "invalid_length"})
            return
        try:
            payload = json.loads(self.rfile.read(length))
            title = str(payload["title"])
            message = str(payload["message"])
        except (json.JSONDecodeError, KeyError, TypeError):
            self.reply(400, {"error": "invalid_payload"})
            return
        notify(title, message)
        self.reply(200, {"status": "delivered"})


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bind", required=True)
    parser.add_argument("--port", type=int, default=18791)
    parser.add_argument("--token-file", type=Path, required=True)
    args = parser.parse_args()

    token = args.token_file.read_text(encoding="utf-8").strip()
    if len(token) < 24:
        raise SystemExit("notification token is missing or too short")
    Handler.token = token
    ThreadingHTTPServer((args.bind, args.port), Handler).serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
