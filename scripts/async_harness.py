#!/usr/bin/env python3
"""Small durable run-state + notification harness."""

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import socket
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

STATES = {"PENDING", "RUNNING", "WAITING_APPROVAL", "BLOCKED", "PASS", "FAIL", "CANCELLED"}
TERMINAL = {"BLOCKED", "PASS", "FAIL", "CANCELLED"}
NOTIFY = {"WAITING_APPROVAL", "BLOCKED", "PASS", "FAIL"}


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def git(*args: str) -> str:
    try:
        return subprocess.check_output(["git", *args], text=True, stderr=subprocess.DEVNULL).strip()
    except (OSError, subprocess.CalledProcessError):
        return ""


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(path)


def read_state(run_dir: Path) -> dict:
    return json.loads((run_dir / "status.json").read_text(encoding="utf-8"))


def run_root(repo: str) -> Path:
    if root := os.environ.get("HARNESS_RUN_ROOT"):
        return Path(root)
    name = repo.rsplit("/", 1)[-1]
    if os.name == "nt":
        return Path(tempfile.gettempdir()) / "gonglz-runs" / name
    return Path("/var/tmp") / name


def new_run_id() -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{stamp}_{git('rev-parse', '--short', 'HEAD') or 'nogit'}"


def local_notify(title: str, body: str) -> bool:
    env = os.environ.copy()
    env["HARNESS_NOTIFY_TITLE"] = title
    env["HARNESS_NOTIFY_BODY"] = body

    if os.name == "nt" or "microsoft" in platform.release().lower():
        exe = shutil.which("powershell.exe") or shutil.which("powershell")
        if not exe:
            return False
        script = (
            "Add-Type -AssemblyName System.Windows.Forms; "
            "Add-Type -AssemblyName System.Drawing; "
            "$n=New-Object System.Windows.Forms.NotifyIcon; "
            "$n.Icon=[System.Drawing.SystemIcons]::Information; $n.Visible=$true; "
            "$n.BalloonTipTitle=$env:HARNESS_NOTIFY_TITLE; "
            "$n.BalloonTipText=$env:HARNESS_NOTIFY_BODY; "
            "$n.ShowBalloonTip(5000); Start-Sleep 6; $n.Dispose()"
        )
        command = [exe, "-NoProfile", "-Command", script]
    elif sys.platform == "darwin" and shutil.which("osascript"):
        body = body.replace('"', '\\"')
        title = title.replace('"', '\\"')
        command = ["osascript", "-e", f'display notification "{body}" with title "{title}"']
    elif shutil.which("notify-send"):
        command = ["notify-send", title, body]
    else:
        return False

    try:
        subprocess.Popen(command, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except OSError:
        return False


def github_notify(state: dict, body: str) -> bool:
    repo, issue = state.get("repo"), state.get("github_issue")
    if not repo or not issue or not shutil.which("gh"):
        return False
    try:
        subprocess.run(
            ["gh", "api", f"repos/{repo}/issues/{issue}/comments", "-f", f"body={body}"],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return True
    except (OSError, subprocess.CalledProcessError):
        return False


def notify(state: dict) -> None:
    message = state.get("message") or state["state"]
    title = f"{state['task']}: {state['state']}"
    github_body = (
        f"### Async execution: {state['state']}\n\n"
        f"- Task: `{state['task']}`\n"
        f"- Run: `{state['run_id']}`\n"
        f"- Phase: `{state.get('phase', '')}`\n"
        f"- Message: {message}\n"
        f"- Runner: `{state.get('runner', '')}`"
    )
    print(json.dumps({
        "local_notification": local_notify(title, message),
        "github_notification": github_notify(state, github_body),
    }))


def persist(run_dir: Path, state: dict) -> None:
    state["updated_at"] = now()
    write_json(run_dir / "status.json", state)
    if state["state"] in TERMINAL:
        write_json(run_dir / "result.json", {
            "run_id": state["run_id"],
            "repo": state["repo"],
            "task": state["task"],
            "commit": state.get("commit", ""),
            "branch": state.get("branch", ""),
            "runner": state.get("runner", ""),
            "status": state["state"],
            "exit_code": state.get("exit_code"),
            "gates": state.get("gates", {}),
            "failures": [] if state["state"] == "PASS" else [state.get("message", "")],
            "finished_at": now(),
        })
    if state["state"] in NOTIFY:
        notify(state)


def start(args: argparse.Namespace) -> int:
    run_id = args.run_id or new_run_id()
    run_dir = run_root(args.repo) / run_id
    if run_dir.exists():
        raise SystemExit(f"run already exists: {run_dir}")
    state = {
        "run_id": run_id,
        "repo": args.repo,
        "task": args.task,
        "state": "RUNNING",
        "phase": "started",
        "progress": {},
        "updated_at": now(),
        "needs_user": False,
        "message": args.message or "Execution started",
        "commit": git("rev-parse", "HEAD"),
        "branch": git("branch", "--show-current"),
        "runner": socket.gethostname(),
        "worktree": str(Path.cwd()),
        "github_issue": args.github_issue,
    }
    persist(run_dir, state)
    print(run_dir)
    return 0


def set_state(args: argparse.Namespace) -> int:
    run_dir = Path(args.run_dir)
    state = read_state(run_dir)
    state["state"] = args.state
    state["needs_user"] = args.state == "WAITING_APPROVAL"
    if args.phase:
        state["phase"] = args.phase
    if args.message:
        state["message"] = args.message
    if args.completed is not None or args.total is not None:
        state["progress"] = {"completed": args.completed, "total": args.total}
    if args.exit_code is not None:
        state["exit_code"] = args.exit_code
    persist(run_dir, state)
    return 0


def run_command(args: argparse.Namespace) -> int:
    run_id = args.run_id or new_run_id()
    run_dir = run_root(args.repo) / run_id
    state = {
        "run_id": run_id,
        "repo": args.repo,
        "task": args.task,
        "state": "RUNNING",
        "phase": "command",
        "progress": {},
        "updated_at": now(),
        "needs_user": False,
        "message": f"Running: {args.command}",
        "commit": git("rev-parse", "HEAD"),
        "branch": git("branch", "--show-current"),
        "runner": socket.gethostname(),
        "worktree": str(Path.cwd()),
        "github_issue": args.github_issue,
    }
    persist(run_dir, state)

    with (run_dir / "run.log").open("w", encoding="utf-8", errors="replace") as log:
        result = subprocess.run(args.command, shell=True, stdout=log, stderr=subprocess.STDOUT)

    state["state"] = "PASS" if result.returncode == 0 else "FAIL"
    state["phase"] = "finished"
    state["message"] = f"Command exited with code {result.returncode}"
    state["exit_code"] = result.returncode
    persist(run_dir, state)
    print(run_dir)
    return result.returncode


def show_status(args: argparse.Namespace) -> int:
    print((Path(args.run_dir) / "status.json").read_text(encoding="utf-8"), end="")
    return 0


def common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--repo", required=True)
    parser.add_argument("--task", required=True)
    parser.add_argument("--github-issue", type=int)
    parser.add_argument("--run-id")
    parser.add_argument("--message")


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    sub = root.add_subparsers(dest="command_name", required=True)

    p = sub.add_parser("start")
    common(p)
    p.set_defaults(func=start)

    p = sub.add_parser("set")
    p.add_argument("run_dir")
    p.add_argument("--state", required=True, choices=sorted(STATES))
    p.add_argument("--phase")
    p.add_argument("--message")
    p.add_argument("--completed", type=int)
    p.add_argument("--total", type=int)
    p.add_argument("--exit-code", type=int)
    p.set_defaults(func=set_state)

    p = sub.add_parser("run")
    common(p)
    p.add_argument("--command", required=True)
    p.set_defaults(func=run_command)

    p = sub.add_parser("status")
    p.add_argument("run_dir")
    p.set_defaults(func=show_status)
    return root


def main() -> int:
    args = parser().parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
