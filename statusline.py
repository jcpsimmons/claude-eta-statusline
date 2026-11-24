#!/usr/bin/env python3
"""Claude Code status line with a live ETA progress bar.

Claude Code pipes session JSON to this script on stdin. We print one line:

    Opus 5.5 │ my-repo (master) │ ⠹ render edit ████████░░░░░░░ 52% 3/6 ~7m left

The progress part comes from a per-session file that Claude writes with the
`claude-eta` helper (see README). No file, no bar: the line just shows the
model, folder and git branch.
"""
import json
import os
import subprocess
import sys
import time

ETA_DIR = os.path.expanduser(os.environ.get("CLAUDE_ETA_DIR", "~/.claude/eta"))
BAR_WIDTH = int(os.environ.get("CLAUDE_ETA_BAR_WIDTH", "16"))
SHOW_FINISHED_FOR = 90  # seconds a finished task lingers before it disappears
STALE_AFTER = 6 * 3600  # ignore abandoned files older than this

RESET = "\033[0m"
DIM = "\033[2m"
BOLD = "\033[1m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
CYAN = "\033[36m"
SPINNER = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"


def fmt_dur(sec):
    sec = int(round(max(0, sec)))
    if sec < 60:
        return f"{sec}s"
    mins = int(round(sec / 60))
    if mins < 60:
        return f"{mins}m"
    h, m = divmod(mins, 60)
    return f"{h}h{m:02d}m" if m else f"{h}h"


def git_branch(cwd):
    try:
        out = subprocess.run(
            ["git", "-C", cwd, "branch", "--show-current"],
            capture_output=True, text=True, timeout=0.5,
        )
        return out.stdout.strip() or None
    except Exception:
        return None


def bar(frac, color):
    frac = min(max(frac, 0.0), 1.0)
    eighths = "▏▎▍▌▋▊▉"
    total = frac * BAR_WIDTH
    full = int(total)
    rem = int((total - full) * 8)
    s = "█" * full
    if full < BAR_WIDTH:
        s += eighths[rem - 1] if rem else ""
    pad = BAR_WIDTH - len(s)
    return f"{color}{s}{RESET}{DIM}{'░' * pad}{RESET}"


def estimate(st, now):
    """Return (fraction, seconds_left_or_None, overrun_seconds)."""
    started = st.get("started", now)
    elapsed = now - started
    eta = st.get("eta_sec")
    done = st.get("done") or 0
    total = st.get("total") or 0

    claude_left = (eta - elapsed) if eta else None

    if total:
        step_frac = min(done / total, 1.0)
        pace_left = None
        if done > 0:
            pace_left = elapsed / done * (total - done)
        # Trust Claude's guess early, trust the measured pace as steps finish.
        if pace_left is not None and claude_left is not None:
            w = step_frac
            left = w * pace_left + (1 - w) * max(claude_left, 0)
        elif pace_left is not None:
            left = pace_left
        else:
            left = claude_left
        # Smooth the bar inside a step using time, without passing the next step.
        frac = step_frac
        if left is not None and left > 0 and done < total:
            time_frac = elapsed / (elapsed + left)
            frac = min(max(step_frac, time_frac), (done + 1) / total - 0.001)
        overrun = -claude_left if (claude_left is not None and claude_left < 0 and done < total) else 0
        return frac, left, overrun

    if eta:
        frac = min(elapsed / eta, 0.99)
        if claude_left < 0:
            return 0.99, None, -claude_left
        return frac, claude_left, 0

    return None, None, 0


def progress_segment(session_id, now):
    if not session_id:
        return None
    path = os.path.join(ETA_DIR, f"{session_id}.json")
    try:
        with open(path) as f:
            st = json.load(f)
    except Exception:
        return None

    task = (st.get("task") or "working")[:32]
    if st.get("finished"):
        if now - st["finished"] > SHOW_FINISHED_FOR:
            return None
        took = st["finished"] - st.get("started", st["finished"])
        return f"{GREEN}✓ {task}{RESET} {DIM}done in {fmt_dur(took)}{RESET}"

    if now - st.get("updated", st.get("started", now)) > STALE_AFTER:
        return None

    frac, left, overrun = estimate(st, now)
    spin = SPINNER[int(now * 4) % len(SPINNER)]
    parts = [f"{CYAN}{spin}{RESET} {BOLD}{task}{RESET}"]

    if frac is None:
        parts.append(f"{DIM}{fmt_dur(now - st.get('started', now))} elapsed{RESET}")
        return " ".join(parts)

    color = GREEN
    if overrun:
        color = YELLOW if overrun < 0.5 * (st.get("eta_sec") or 1) else RED
    parts.append(bar(frac, color))
    parts.append(f"{int(frac * 100)}%")
    if st.get("total"):
        parts.append(f"{DIM}{st.get('done') or 0}/{st['total']}{RESET}")
    if overrun and not st.get("total"):
        parts.append(f"{color}+{fmt_dur(overrun)} over{RESET}")
    elif left is not None:
        parts.append(f"{DIM}~{fmt_dur(left)} left{RESET}")
    if st.get("note"):
        parts.append(f"{DIM}· {st['note'][:40]}{RESET}")
    return " ".join(parts)


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        data = {}
    now = time.time()

    model = (data.get("model") or {}).get("display_name") or "Claude"
    cwd = (data.get("workspace") or {}).get("current_dir") or data.get("cwd") or os.getcwd()
    folder = os.path.basename(cwd.rstrip("/")) or cwd
    branch = git_branch(cwd)

    left = f"{BOLD}{model}{RESET} {DIM}│{RESET} {folder}"
    if branch:
        left += f" {DIM}({branch}){RESET}"

    seg = progress_segment(data.get("session_id"), now)
    print(f"{left} {DIM}│{RESET} {seg}" if seg else left)


if __name__ == "__main__":
    main()
