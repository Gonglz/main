#!/usr/bin/env python3
"""Minimal async execution harness for the Repository Agent Contract."""

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


TERMINAL_STATES = {"PASS", "FAIL", "BLOCKED", "CANCELLED"}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def git_text(*args: str) -> str:
    try:
        return subprocess.check_output(
            ["git", *args], text=True, stderr=subprocess.DEVNULL
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return ""


def atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(path)


def default_root(repo: str) -> Path:
    configured = os.environ.get("HARNESS_RUN_ROOT")
    if configured:
        return Path(configured)
    name = repo.rsplit("/", 1)[-1]
    if os.name == "nt":
        return Path(tempfile.gettempdir()) / "gonglz-runs" / name
    return Path("/var/tmp") / name


def make_run_id() -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    sha = git_text("rev-parse", "--short", "HEAD") or "nogit"
    return f"{stamp}_{sha}"


def base_state(args: argparse.Namespace, run_id: str) -> dict:
    return {
        "run_id": run_id,
        "repo": args.repo,
        "task": args.task,
        "state": "RUNNING",
        "phase": "started",
        "progress": {},
        "updated_at": utc_now(),
        "needs_user": False,
        "message": args.message or "Execution started",
        "commit": git_text("rev-parse", "HEAD"),
        "branch": git_text("branch", "--show-current"),
        "runner": socket.gethostname(),
        "worktree": str(Path.cwd()),
        "github_issue": args.github_issue,
    }


def load_status(run_dir: Path) -> dict:
    return json.loads((run_dir / "status.json").read_text(encoding="utf-8"))


def save_status(run_dir: Path, state: dict) -> None:
    state["updated_at"] = utc_now()
    atomic_json(run_dir / "status.json", state)


def powershell_notify(title: str, body: str) -> bool:
    exe = shutil.which("powershell.exe") or shutil.which("powershell")
    if not exe:
        return False
    env = os.environ.copy()
    env["HARNESS_NOTIFY_TITLE"] = title
    env["HARNESS_NOTIFY_BODY"] = body
    script = (
        "Add-Type -AssemblyName System.Windows.Forms; "
        "Add-Type -AssemblyName System.Drawing; "
        "$n=New-Object System.Windows.Forms.NotifyIcon; "
        "$n.Icon=[System.Drawing.SystemIcons]::Information; "
        "$n.Visible=$true; "
        "$n.BalloonTipTitle=$env:HARNESS_NOTIFY_TITLE; "
        "$n.BalloonTipText=$env:HARNESS_NOTIFY_BODY; "
        "$n.ShowBalloonTip(5000); Start-Sleep -Seconds 6; $n.Dispose()"
    )
    try:
        subprocess.Popen(
            [exe, "-NoProfile", "-Command", script],
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return True
    except OSError:
        return False


def local_notify(title: str, body: str) -> bool:
    if os.name == "nt" or "microsoft" in platform.release().lower():
        return powershell_notify(title, body)
    if sys.platform == "darwin" and shutil.which("osascript"):
        safe_title = title.replace('"', '\"')
        safe_body = body.replace('"', '\"')
        subprocess.Popen(
            ["osascript", "-e", f'display notification "{safe_body}" with title "{safe_title}"'],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return True
    if shutil.which("notify-send"):
        subprocess.Popen(
            ["notify-send", title, body],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return True
    return False


def github_notify(state: dict, body: str) -> bool:
    issue = state.get("github_issue")
    repo = state.get("repo")
    if not issue or not repo or not shutil.which("gh"):
        return False
    try:
        subprocess.run(
            [
                "gh", "api", f"repos/{repo}/issues/{issue}/comments",
                "-f", f"body={body}",
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return True
    except (OSError, subprocess.CalledProcessError):
        return False


def notify(state: dict) -> None:
    title = f"{state['task']}: {state['state']}"
    body = state.get("message") or state.get("phase") or state["state"]
    local_ok = local_notify(title, body)
    github_body = (
        f"### Async execution: {state['state']}\n\n"
        f"- Task: \`{state['task']}\`\n"
        f"- Run: \`{state['run_id']}\`\n"
        f"- Phase: \`{state.get('phase', '')}\`\n"
        f"- Message: {body}\n"
        f"- Runner: \`{state.get('runner', '')}\`"
    )
    github_ok = github_notify(state, github_body)
    print(json.dumps({"local_notification": local_ok, "github_notification": github_ok}))


def command_start(args: argparse.Namespace) -> int:
    run_id = args.run_id or make_run_id()
    run_dir = default_root(args.repo) / run_id
    if run_dir.exists():
        raise SystemExit(f"run already exists: {run_dir}")
    state = base_state(args, run_id)
    save_status(run_dir, state)
    print(run_dir)
    return 0


def command_update(args: argparse.Namespace) -> int:
    run_dir = Path(args.run_dir)
    state = load_status(run_dir)
    state["state"] = "RUNNING"
    state["needs_user"] = False
    if args.phase:
        state["phase"] = args.phase
    if args.message:
        state["message"] = args.message
    if args.completed is not None or args.total is not None:
        state["progress"] = {
            "completed": args.completed,
            "total": args.total,
        }
    save_status(run_dir, state)
    return 0


def command_approval(args: argparse.Namespace) -> int:
    run_dir = Path(args.run_dir)
    state = load_status(run_dir)
    state.update(
        {
            "state": "WAITING_APPROVAL",
            "needs_user": True,
            "phase": args.phase or "approval",
            "message": args.question,
            "approval": {"id": args.approval_id, "question": args.question},
        }
    )
    save_status(run_dir, state)
    notify(state)
    return 0


def command_resume(args: argparse.Namespace) -> int:
    run_dir = Path(args.run_dir)
    state = load_status(run_dir)
    state["state"] = "RUNNING"
    state["needs_user"] = False
    state.pop("approval", None)
    state["message"] = args.message or "Execution resumed"
    save_status(run_dir, state)
    return 0


def finish(run_dir: Path, status: str, message: str, exit_code: int | None = None) -> None:
    state = load_status(run_dir)
    state.update(
        {
            "state": status,
            "needs_user": False,
            "phase": "finished",
            "message": message,
        }
    )
    save_status(run_dir, state)
    result = {
        "run_id": state["run_id"],
        "repo": state["repo"],
        "task": state["task"],
        "commit": state.get("commit", ""),
        "branch": state.get("branch", ""),
        "runner": state.get("runner", ""),
        "status": status,
        "exit_code": exit_code,
        "gates": {},
        "failures": [] if status == "PASS" else [message],
        "finished_at": utc_now(),
    }
    atomic_json(run_dir / "result.json", result)
    notify(state)


def command_finish(args: argparse.Namespace) -> int:
    finish(Path(args.run_dir), args.status, args.message, args.exit_code)
    return 0


def command_status(args: argparse.Namespace) -> int:
    print((Path(args.run_dir) / "status.json").read_text(encoding="utf-8"), end="")
    return 0


def command_run(args: argparse.Namespace) -> int:
    run_id = args.run_id or make_run_id()
    run_dir = default_root(args.repo) / run_id
    state = base_state(args, run_id)
    state["phase"] = "command"
    state["message"] = f"Running: {args.command}"
    save_status(run_dir, state)
    log_path = run_dir / "run.log"
    with log_path.open("w", encoding="utf-8", errors="replace") as log:
        proc = subprocess.run(
            args.command,
            shell=True,
            stdout=log,
            stderr=subprocess.STDOUT,
        )
    status = "PASS" if proc.returncode == 0 else "FAIL"
    finish(run_dir, status, f"Command exited with code {proc.returncode}", proc.returncode)
    print(run_dir)
    return proc.returncode


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="subcommand", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--repo", required=True, help="GitHub repo, e.g. Gonglz/Quant-v2")
    common.add_argument("--task", required=True)
    common.add_argument("--github-issue", type=int)
    common.add_argument("--run-id")
    common.add_argument("--message")

    p = sub.add_parser("start", parents=[common])
    p.set_defaults(func=command_start)

    p = sub.add_parser("run", parents=[common])
    p.add_argument("--command", required=True)
    p.set_defaults(func=command_run)

    p = sub.add_parser("update")
    p.add_argument("run_dir")
    p.add_argument("--phase")
    p.add_argument("--message")
    p.add_argument("--completed", type=int)
    p.add_argument("--total", type=int)
    p.set_defaults(func=command_update)

    p = sub.add_parser("approval")
    p.add_argument("run_dir")
    p.add_argument("--approval-id", required=True)
    p.add_argument("--question", required=True)
    p.add_argument("--phase")
    p.set_defaults(func=command_approval)

    p = sub.add_parser("resume")
    p.add_argument("run_dir")
    p.add_argument("--message")
    p.set_defaults(func=command_resume)

    p = sub.add_parser("finish")
    p.add_argument("run_dir")
    p.add_argument("--status", required=True, choices=sorted(TERMINAL_STATES))
    p.add_argument("--message", required=True)
    p.add_argument("--exit-code", type=int)
    p.set_defaults(func=command_finish)

    p = sub.add_parser("status")
    p.add_argument("run_dir")
    p.set_defaults(func=command_status)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
