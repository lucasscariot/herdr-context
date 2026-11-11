#!/usr/bin/env python3
"""Read context metadata without sending input, changing settings, or using an API."""

import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import math
from pathlib import Path
import re
import shutil
import sqlite3
import subprocess
import time


ANSI = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]|\x1b\][^\x07]*(?:\x07|\x1b\\)")
CONTEXT = re.compile(r"\bcontext\s+(\d+(?:\.\d+)?)%\s*\(([\d.]+[kKmM]?)/([\d.]+[kKmM]?)\)", re.I)
REMAINING = re.compile(r"\b(\d+(?:\.\d+)?)%\s+context\s+(?:left|remaining)\b", re.I)
CURSOR = re.compile(r"^\s*[^·\n]+\s+·\s+(\d+(?:\.\d+)?)%\s+·\s+\d+\s+files?\s+edited\b")


def provider(terminal):
    status = terminal.get("status")
    status_app = status.get("app") if isinstance(status, dict) else None
    return (terminal.get("report") or {}).get("app") or terminal.get("app") or status_app or (terminal.get("program") or {}).get("key", "")


def identity(terminal):
    app = provider(terminal)
    title = session_name(terminal.get("title", "")) if app == "codex" else terminal.get("title", "")
    return {"title": title, "pid": (terminal.get("foreground") or {}).get("pid"), "app": app}


def session_name(title):
    title = re.sub(r"^[\u2800-\u28ff]\s*", "", title.strip())
    title = re.sub(r"^(?:\[[^\]]{1,8}\]\s*)?(?:Action Required|Working|Ready|Waiting|Idle|Done)\s*\|\s*", "", title)
    return title.rsplit(" | ", 1)[0].strip()


def reading(percent, source, **details):
    if not isinstance(percent, (int, float)) or not math.isfinite(percent) or percent < 0:
        return None
    return {"percent": percent, "source": source, **details}


def tokens(value):
    return float(value.rstrip("kKmM")) * (1000 if value[-1:].lower() == "k" else 1000000 if value[-1:].lower() == "m" else 1)


def parse_screen(text, app):
    # Only the current screen's footer, never scrollback or arbitrary percentages
    # in tool output. A Claude meter must include the token denominator too.
    lines = ANSI.sub("", text).splitlines()[-16:]
    for line in reversed(lines):
        match = CONTEXT.search(line) if app in ("claude-code", "claude") else None
        if match:
            return reading(float(match[1]), "terminal footer", used=tokens(match[2]), capacity=tokens(match[3]))
        match = REMAINING.search(line) if app == "codex" else None
        if match and 0 <= float(match[1]) <= 100:
            return reading(100 - float(match[1]), "terminal footer")
        match = CURSOR.search(line) if app in ("cursor", "cursor-agent") else None
        if match:
            return reading(float(match[1]), "Cursor context footer")
    return None


def codex_usage(path, limit=4 * 1024 * 1024):
    """Use the most recent request, never cumulative/billable token totals."""
    with Path(path).open("rb") as stream:
        size = stream.seek(0, 2)
        start = max(0, size - limit)
        stream.seek(start)
        data = stream.read(limit)
    lines = data.decode("utf8", errors="replace").splitlines()
    if start:
        lines = lines[1:]  # The first record may have been cut in half.
    for line in reversed(lines):
        try:
            event = json.loads(line)
        except (ValueError, TypeError):
            continue
        payload = event.get("payload") or {}
        if event.get("type") == "compacted" or (event.get("type") == "event_msg" and payload.get("type") == "context_compacted"):
            return None  # Wait for a fresh count after a compaction.
        if event.get("type") != "event_msg" or payload.get("type") != "token_count":
            continue
        info = payload.get("info") or {}
        used = (info.get("last_token_usage") or {}).get("total_tokens")
        capacity = info.get("model_context_window")
        if isinstance(used, (int, float)) and isinstance(capacity, (int, float)) and capacity > 0:
            return reading(used / capacity * 100, "Codex latest request", used=used, capacity=capacity, reportedAt=event.get("timestamp"))
    return None


def codex_threads(home):
    # Read only metadata columns. Do not read prompts, messages, or credentials.
    database = home / ".codex" / "state_5.sqlite"
    if not database.exists():
        return []
    with sqlite3.connect(database.as_uri() + "?mode=ro", uri=True, timeout=1) as connection:
        connection.row_factory = sqlite3.Row
        return [dict(row) for row in connection.execute("SELECT id, name, source, rollout_path FROM threads WHERE archived = 0")]


def select_thread(terminal, threads, opened=()):
    roots = [thread for thread in threads if "subagent" not in thread["source"]]
    # Older CLI sessions hold their rollout file/lock open. Prefer that direct
    # process identity and exclude guardian/sub-agent sessions in the same process.
    direct = [thread for thread in roots if any(thread["id"] in name for name in opened)]
    if len(direct) == 1:
        return direct[0]
    if direct:
        return None
    # New Codex versions close rollout files between writes. Herdr's OSC title
    # carries the session's exact name. Refuse duplicate names; never match cwd
    # alone or pick whichever project transcript was modified most recently.
    name = session_name(terminal.get("title", ""))
    matching = [thread for thread in roots if thread["name"] and thread["name"] == name]
    return matching[0] if len(matching) == 1 else None


def opened_files(pid):
    if not isinstance(pid, int) or pid < 1 or not shutil.which("lsof"):
        return []
    result = subprocess.run(["lsof", "-a", "-p", str(pid), "-Fn"], capture_output=True, text=True, timeout=3)
    return [line[1:] for line in result.stdout.splitlines() if line.startswith("n") and "/.codex/" in line]


def collect_one(terminal, threads, hc):
    result = {"identity": identity(terminal), "percent": None, "reason": "This agent does not expose a readable context meter yet."}
    app = provider(terminal)
    try:
        if app == "codex" and "/" not in terminal["address"]:
            thread = select_thread(terminal, threads, opened_files((terminal.get("foreground") or {}).get("pid")))
            if thread:
                value = codex_usage(thread["rollout_path"])
                if value:
                    return {"identity": identity(terminal), **value, "session": thread["id"]}
        if app in ("claude", "claude-code", "cursor", "cursor-agent", "codex"):
            # --lines 0 is a screen snapshot; no keyboard input or history scroll.
            screen = subprocess.run([hc, "read", terminal["address"], "--lines", "0"], capture_output=True, text=True, timeout=3)
            if screen.returncode == 0:
                value = parse_screen(screen.stdout, app)
                if value:
                    return {"identity": identity(terminal), **value}
            result["reason"] = "No current context meter could be read for this session."
    except (OSError, ValueError, sqlite3.Error, subprocess.SubprocessError):
        result["reason"] = "Context reading unavailable; waiting for the next refresh."
    return result


def collect(terminals, home=None, hc=None):
    home = home or Path.home()
    hc = hc or shutil.which("hc") or str(home / ".local/bin/hc")
    try:
        threads = codex_threads(home)
    except (OSError, sqlite3.Error):
        threads = []
    live = [t for t in terminals if t.get("state") == "live" and provider(t)]
    with ThreadPoolExecutor(max_workers=4) as pool:
        readings = list(pool.map(lambda terminal: collect_one(terminal, threads, hc), live))
    return {"collectedAt": int(time.time() * 1000), "terminals": {terminal["address"]: value for terminal, value in zip(live, readings)}}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--terminals", required=True, help="Herdr terminal metadata as JSON (no screen content)")
    args = parser.parse_args()
    print(json.dumps(collect(json.loads(args.terminals)), allow_nan=False))
